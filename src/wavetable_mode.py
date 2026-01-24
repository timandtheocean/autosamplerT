"""
Wavetable creation mode for AutosamplerT.

Uses the main sampler's audio and MIDI infrastructure.
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, Optional

from .sampler import AutoSampler
from .wavetable.wavetable_sampler import WavetableSampler
from .wavetable.wave_calculator import WaveCalculator
from .wavetable.midi_learn import MIDILearn


def run_wavetable_mode(args) -> bool:
    """
    Run wavetable creation mode using main sampler infrastructure.
    
    Args:
        args: Command line arguments
        
    Returns:
        True if successful, False otherwise
    """
    print("=== AutosamplerT Wavetable Creator ===")
    print()
    
    try:
        # Load configuration
        config = load_wavetable_config(args)
        if not config:
            return False
        
        # Create main sampler instance (handles all audio/MIDI setup)
        print("Initializing audio and MIDI interfaces...")
        sampler = AutoSampler(config)
        
        # Setup audio (same as main sampler)
        if not sampler.setup_audio():
            logging.error("Audio setup failed")
            return False
        print(f"Audio: {sampler.audio_engine.samplerate}Hz, {sampler.audio_engine.bitdepth}-bit")
        
        # Setup MIDI (same as main sampler)
        if not sampler.setup_midi():
            logging.warning("MIDI setup failed - continuing without MIDI")
        else:
            print(f"MIDI output: {sampler.midi_config.get('midi_output_name', 'default')}")
        
        # Do a short warm-up recording to prime the ASIO driver (same as main sampler)
        print("Warming up audio interface...")
        warmup_audio = sampler.audio_engine.record(0.5)  # 0.5 second test recording
        if warmup_audio is None:
            logging.error("Audio warm-up failed - ASIO driver may be locked by another application")
            return False
        print(f"Audio warm-up OK ({len(warmup_audio)} samples)")
        
        # Create wavetable sampler using main sampler's infrastructure
        with WavetableSampler(sampler) as wavetable_sampler:
            # Run wavetable creation workflow
            success = run_wavetable_workflow(wavetable_sampler, config, sampler)
        
        return success
        
    except Exception as e:
        logging.error(f"Wavetable mode failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_wavetable_workflow(wavetable_sampler: WavetableSampler, config: Dict, 
                          sampler: AutoSampler) -> bool:
    """Run the complete wavetable creation workflow."""
    try:
        # Get wavetable parameters from user
        wavetable_config = get_wavetable_parameters(config, sampler)
        if not wavetable_config:
            return False
        
        # Control Setup
        print("\n=== Control Setup ===")
        control_config = get_control_parameters(config, sampler)
        if not control_config:
            return False
        
        wavetable_config['control'] = control_config
        
        # Use all curve types automatically
        from .wavetable.sweep_curves import SweepCurves
        curve_types = SweepCurves.get_all_curves()  # ['lin', 'log', 'exp', 'log-lin', 'lin-log']
        wavetable_config['curve_types'] = curve_types
        
        # Confirm and create
        print("\n=== Configuration Summary ===")
        print(f"Name: {wavetable_config['name']}")
        print(f"Samples per wave: {wavetable_config['samples_per_waveform']}")
        print(f"Number of waves: {wavetable_config['number_of_waves']}")
        print(f"MIDI note: {wavetable_config['midi_note']}")
        print(f"Control: {control_config['type']} {control_config.get('controller', '')}")
        print(f"Range: {control_config['min_value']} - {control_config['max_value']}")
        print(f"Curves: {', '.join(curve_types)} (all)")
        print(f"Output: {wavetable_config['output_folder']}")
        # Audio processing info
        gain_db = wavetable_config.get('gain_boost_db', 0.0)
        normalize = wavetable_config.get('normalize', True)
        normalize_db = wavetable_config.get('normalize_target_db', -6.0)
        if gain_db != 0 or normalize:
            processing = []
            if gain_db != 0:
                processing.append(f"gain: {gain_db:+.1f}dB")
            if normalize:
                processing.append(f"normalize to {normalize_db}dB")
            print(f"Audio processing: {', '.join(processing)}")
        else:
            print(f"Audio processing: none (raw audio)")
        
        # Monitoring info
        enable_monitoring = wavetable_config.get('enable_monitoring', False)
        if enable_monitoring:
            print(f"Monitoring: enabled (audio routed to output)")
        
        confirm = input("\nProceed with wavetable creation? [Y/n]: ").strip().lower()
        if confirm == 'n':
            print("Cancelled.")
            return False
        
        # Create wavetables
        return wavetable_sampler.create_wavetables(wavetable_config)
        
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return False
    except Exception as e:
        logging.error(f"Wavetable workflow failed: {e}")
        return False


def load_wavetable_config(args) -> Optional[Dict]:
    """Load configuration from files."""
    try:
        config_path = args.config
        if not os.path.exists(config_path):
            print(f"Config file not found: {config_path}")
            return None
            
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Load wavetable defaults
        wavetable_config_path = 'conf/wavetable_config.yaml'
        if os.path.exists(wavetable_config_path):
            with open(wavetable_config_path, 'r') as f:
                wavetable_config = yaml.safe_load(f)
            
            # Merge wavetable defaults (don't override existing)
            if 'wavetable_defaults' in wavetable_config:
                defaults = wavetable_config['wavetable_defaults']
                if 'wavetable' not in config:
                    config['wavetable'] = {}
                for key, value in defaults.items():
                    if key not in config['wavetable']:
                        config['wavetable'][key] = value
        
        return config
        
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return None


def get_wavetable_parameters(config: Dict, sampler: AutoSampler) -> Optional[Dict]:
    """Get wavetable parameters from user."""
    try:
        wavetable_defaults = config.get('wavetable', {})
        
        # Wavetable name
        default_name = wavetable_defaults.get('name_prefix', 'wavetable')
        name = input(f"Wavetable name [{default_name}]: ").strip() or default_name
        
        # Samples per waveform
        valid_samples = [128, 512, 1024, 2048, 4096]
        default_samples = wavetable_defaults.get('samples_per_waveform', 2048)
        print(f"Samples per waveform options: {valid_samples}")
        samples_input = input(f"Samples per waveform [{default_samples}]: ").strip()
        samples_per_waveform = int(samples_input) if samples_input else default_samples
        
        if samples_per_waveform not in valid_samples:
            print(f"Invalid value. Using {default_samples}")
            samples_per_waveform = default_samples
        
        # Number of waves
        max_waves = 217 if samples_per_waveform == 4096 else 256
        default_waves = min(wavetable_defaults.get('number_of_waves', 64), max_waves)
        waves_input = input(f"Number of waves (1-{max_waves}) [{default_waves}]: ").strip()
        number_of_waves = int(waves_input) if waves_input else default_waves
        number_of_waves = max(1, min(number_of_waves, max_waves))
        
        # Calculate optimal note
        frequency, midi_note, note_name = WaveCalculator.calculate_optimal_note(
            sampler.audio_engine.samplerate, samples_per_waveform)
        print(f"Optimal note for clean wave periods: {note_name} (MIDI {midi_note})")
        
        note_input = input(f"MIDI note [{midi_note}]: ").strip()
        if note_input:
            try:
                midi_note = int(note_input)
            except ValueError:
                # Try to parse note name
                midi_note = parse_note_name(note_input) or midi_note
        
        # Output folder
        default_output = wavetable_defaults.get('output_folder', './output/wavetables')
        output_folder = input(f"Output folder [{default_output}]: ").strip() or default_output
        
        # Audio processing settings from config
        gain_boost_db = wavetable_defaults.get('gain_boost_db', 0.0)
        normalize = wavetable_defaults.get('normalize', True)
        normalize_target_db = wavetable_defaults.get('normalize_target_db', -6.0)
        
        # Monitoring setting (routes audio input to output during recording)
        enable_monitoring = wavetable_defaults.get('enable_monitoring', False)
        
        # Hold times before/after sweep
        hold_time_before = wavetable_defaults.get('hold_time_before', 0.5)
        hold_time_after = wavetable_defaults.get('hold_time_after', 0.5)
        
        return {
            'name': name,
            'samples_per_waveform': samples_per_waveform,
            'number_of_waves': number_of_waves,
            'midi_note': midi_note,
            'output_folder': output_folder,
            # Audio processing settings
            'gain_boost_db': gain_boost_db,
            'normalize': normalize,
            'normalize_target_db': normalize_target_db,
            # Monitoring
            'enable_monitoring': enable_monitoring,
            # Hold times
            'hold_time_before': hold_time_before,
            'hold_time_after': hold_time_after
        }
        
    except Exception as e:
        logging.error(f"Failed to get wavetable parameters: {e}")
        return None


def get_control_parameters(config: Dict, sampler: AutoSampler) -> Optional[Dict]:
    """Get MIDI control parameters from user - with MIDI learn support."""
    try:
        # Check if MIDI learn is available
        has_midi_input = sampler.midi_input_port is not None
        
        print("\nControl setup options:")
        print("  1. Manual entry")
        if has_midi_input:
            print("  2. MIDI Learn (detect control automatically)")
        
        setup_choice = input(f"Select option [1]: ").strip() or "1"
        
        # MIDI Learn path
        if setup_choice == "2" and has_midi_input:
            return _midi_learn_control(sampler, config)
        
        # Manual entry path
        print("\nControl type options:")
        print("  1. CC (Control Change)")
        print("  2. NRPN")
        print("  3. CC14 (14-bit CC)")
        print("  4. Pitch Wheel")
        
        choice = input("Select control type [1]: ").strip() or "1"
        
        control_types = {'1': 'cc', '2': 'nrpn', '3': 'cc14', '4': 'pitchwheel'}
        ctrl_type = control_types.get(choice, 'cc')
        
        control_config = {
            'type': ctrl_type,
            'channel': 0
        }
        
        # Get controller number (except for pitch wheel)
        if ctrl_type != 'pitchwheel':
            default_ctrl = 74 if ctrl_type == 'cc' else 3
            ctrl_input = input(f"Controller number [{default_ctrl}]: ").strip()
            control_config['controller'] = int(ctrl_input) if ctrl_input else default_ctrl
        
        # Get channel
        channel_input = input("MIDI channel (1-16) [1]: ").strip()
        if channel_input:
            control_config['channel'] = int(channel_input) - 1  # Convert to 0-based
        
        # Get value range
        if ctrl_type == 'cc':
            max_default = 127
        elif ctrl_type in ['nrpn', 'cc14']:
            max_default = 16383
        else:  # pitchwheel
            max_default = 127  # We'll convert internally
        
        min_input = input(f"Minimum value [0]: ").strip()
        max_input = input(f"Maximum value [{max_default}]: ").strip()
        
        control_config['min_value'] = int(min_input) if min_input else 0
        control_config['max_value'] = int(max_input) if max_input else max_default
        
        # Control name for filename
        name_input = input("Control name (for filename) [parameter]: ").strip()
        control_config['name'] = name_input or 'parameter'
        
        return control_config
        
    except Exception as e:
        logging.error(f"Failed to get control parameters: {e}")
        return None


def _midi_learn_control(sampler: AutoSampler, config: Dict) -> Optional[Dict]:
    """Use MIDI learn to detect control and range."""
    try:
        wavetable_defaults = config.get('wavetable', {})
        learn_timeout = wavetable_defaults.get('learn_timeout', 30.0)
        range_timeout = wavetable_defaults.get('range_timeout', 60.0)
        
        # Create MIDI learn instance
        midi_learn = MIDILearn(sampler.midi_input_port)
        
        # Step 1: Learn the control
        print("\n--- MIDI Learn: Control Detection ---")
        print("Move the control/knob on your synth...")
        
        control_info = midi_learn.learn_control(timeout=learn_timeout)
        if not control_info:
            print("No control detected. Falling back to manual entry.")
            return get_control_parameters(config, sampler)  # Retry with manual
        
        print(f"Detected: {control_info['type'].upper()} {control_info.get('controller', '')} "
              f"on channel {control_info['channel'] + 1}")
        
        # Step 2: Learn the range (pass control_info so it knows what to listen for)
        print("\n--- MIDI Learn: Range Detection ---")
        print("Move the control from minimum to maximum position...")
        
        range_result = midi_learn.learn_range(control_info, timeout=range_timeout)
        if range_result is None or range_result[0] is None:
            print("Range detection failed. Using default range.")
            if control_info['type'] == 'cc':
                min_val, max_val = 0, 127
            else:
                min_val, max_val = 0, 16383
        else:
            min_val, max_val = range_result
        
        print(f"Range: {min_val} - {max_val}")
        
        # Build control config
        control_config = {
            'type': control_info['type'],
            'channel': control_info['channel'],
            'controller': control_info.get('controller', 0),
            'min_value': min_val,
            'max_value': max_val
        }
        
        # Get control name for filename
        default_name = control_info.get('name', 'parameter')
        name_input = input(f"Control name (for filename) [{default_name}]: ").strip()
        control_config['name'] = name_input or default_name
        
        return control_config
        
    except Exception as e:
        logging.error(f"MIDI learn failed: {e}")
        return None


def parse_note_name(note_str: str) -> Optional[int]:
    """Parse note name like 'C4' or 'A#3' to MIDI number."""
    try:
        note_str = note_str.upper().strip()
        
        # Note names to semitone offsets
        notes = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
        
        # Parse note letter
        note_letter = note_str[0]
        if note_letter not in notes:
            return None
        
        offset = notes[note_letter]
        rest = note_str[1:]
        
        # Check for sharp/flat
        if rest.startswith('#'):
            offset += 1
            rest = rest[1:]
        elif rest.startswith('B'):
            offset -= 1
            rest = rest[1:]
        
        # Parse octave
        octave = int(rest) if rest else 4
        
        # Calculate MIDI note (C4 = 60)
        midi_note = (octave + 1) * 12 + offset
        
        return midi_note
        
    except Exception:
        return None
