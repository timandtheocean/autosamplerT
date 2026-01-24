"""
Wavetable creation mode for AutosamplerT.

Main entry point for wavetable creation functionality.
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, Optional

from .wavetable import MIDILearn, WaveCalculator, WavetableSampler
from .sampler_midicontrol import MIDIController
from .sampling.audio_engine import AudioEngine
from .midi_interface_manager import MidiInterfaceManager


def run_wavetable_mode(args) -> bool:
    """
    Run wavetable creation mode.
    
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
        
        # Initialize interfaces
        audio_engine, midi_manager, midi_controller = initialize_interfaces(config)
        if not audio_engine:
            return False
        
        # Get audio device info from the audio engine
        audio_device_index = audio_engine.input_device or 0
        sample_rate = audio_engine.samplerate
        bit_depth = audio_engine.bitdepth
        
        # Check if monitoring is enabled in audio config
        audio_config = config.get('audio_interface', {})
        enable_monitoring = audio_config.get('enable_monitoring', False)
        
        # Initialize wavetable sampler
        wavetable_sampler = WavetableSampler(
            audio_engine=audio_engine,
            midi_controller=midi_controller,
            enable_monitoring=enable_monitoring
        )
        
        try:
            # Run wavetable creation workflow
            success = run_wavetable_workflow(wavetable_sampler, config, midi_manager)
        finally:
            # Cleanup (always runs, even if workflow fails)
            wavetable_sampler.cleanup()
            
            # Also cleanup the audio engine to release ASIO devices
            if hasattr(audio_engine, 'cleanup'):
                audio_engine.cleanup()
            else:
                # Fallback for older AudioEngine versions
                try:
                    import sounddevice as sd
                    sd.stop()
                    logging.debug("Audio operations stopped for ASIO device release")
                except Exception as e:
                    logging.warning(f"Failed to stop audio operations: {e}")
                
            if midi_controller and hasattr(midi_controller, 'close'):
                midi_controller.close()
        
        return success
        
    except Exception as e:
        logging.error(f"Wavetable mode failed: {e}")
        return False


def run_wavetable_workflow(sampler: WavetableSampler, config: Dict, 
                          midi_manager: Optional[MidiInterfaceManager]) -> bool:
    """Run the complete wavetable creation workflow."""
    try:
        # Get wavetable parameters from user
        wavetable_config = get_wavetable_parameters(config)
        if not wavetable_config:
            return False
        
        # Control Setup: Learn vs Manual
        print("\n=== Control Setup ===")
        if midi_manager and midi_manager.input_name:
            print("Options:")
            print("  (l) Learn MIDI control automatically")  
            print("  (m) Enter control details manually")
            choice = input("Choose option [l]: ").strip().lower()
            if not choice:
                choice = 'l'
            elif choice in ['1', 'l', 'learn']:
                choice = 'l'
            elif choice in ['2', 'm', 'manual']:
                choice = 'm'
            else:
                print("Invalid choice, defaulting to learn mode")
                choice = 'l'
        else:
            print("No MIDI input available - manual entry only")
            choice = 'm'
            
        # MIDI Learn workflow
        if choice == 'l' and midi_manager and midi_manager.input_name:
            print(f"\n=== MIDI Learn ===")
            print(f"Using MIDI input: {midi_manager.input_name}")
            import sys
            sys.stdout.flush()
            
            # Open MIDI input port for learning
            try:
                print("Opening MIDI input port...")
                sys.stdout.flush()
                import mido
                with mido.open_input(midi_manager.input_name) as midi_input_port:
                    print("MIDI input port opened successfully")
                    sys.stdout.flush()
                    midi_learn = MIDILearn(midi_input_port)
                    
                    # Learn control
                    control_info = midi_learn.learn_control()
                    if not control_info:
                        print("MIDI learn failed - falling back to manual entry")
                        choice = 'm'
                    else:
                        # Learn range
                        control_range = midi_learn.learn_range(control_info)
                        if not control_range:
                            print("Range learning failed - falling back to manual entry")
                            choice = 'm'
                        else:
                            # Ask for parameter name after successful learning
                            parameter_name = input("\nParameter name for this control (e.g., 'cutoff', 'resonance'): ").strip()
                            if not parameter_name:
                                parameter_name = f"{control_info.get('name', 'parameter')}"
                            
                            # Update config with learned control
                            wavetable_config['control'] = {
                                **control_info,
                                'min_value': control_range[0],
                                'max_value': control_range[1],
                                'name': parameter_name
                            }
            except Exception as e:
                print(f"MIDI learn failed: {e}")
                sys.stdout.flush()
                choice = 'm'
        elif choice == 'l':
            # Debug: Why didn't MIDI learn start?
            if not midi_manager:
                print("No MIDI manager available")
            elif not midi_manager.input_name:
                print(f"No MIDI input name (input_name: {getattr(midi_manager, 'input_name', None)})")
            choice = 'm'
        
        # Manual entry workflow  
        if choice == 'm':
            print("\n=== Manual Control Entry ===")
            
            # Parameter name
            parameter_name = input("Parameter name (e.g., 'cutoff', 'resonance', 'filter'): ").strip()
            if not parameter_name:
                parameter_name = "parameter"
                
            # Control type
            print("\nControl types:")
            print("  (1) CC - Standard MIDI Continuous Controller") 
            print("  (2) CC14 - 14-bit High Resolution Controller")
            print("  (3) NRPN - Non-Registered Parameter Number")
            
            while True:
                control_type_choice = input("Choose control type [1]: ").strip()
                if not control_type_choice:
                    control_type_choice = '1'
                if control_type_choice in ['1', '2', '3']:
                    break
                print("Invalid choice. Enter 1, 2, or 3.")
                
            control_type_map = {'1': 'cc', '2': 'cc14', '3': 'nrpn'}
            control_type = control_type_map[control_type_choice]
            
            # MIDI channel
            while True:
                channel_input = input("MIDI channel [1-16] [1]: ").strip()
                if not channel_input:
                    channel = 0  # Internal representation 0-15
                    break
                try:
                    channel_display = int(channel_input)
                    if 1 <= channel_display <= 16:
                        channel = channel_display - 1  # Convert to 0-15
                        break
                    else:
                        print("Invalid channel. Enter 1-16.")
                except ValueError:
                    print("Invalid input. Enter a number 1-16.")
            
            # Controller number with NRPN-friendly input
            while True:
                if control_type == 'nrpn':
                    controller_input = input(f"NRPN parameter number [0-16383] (e.g., 3 for NRPN3) [3]: ").strip()
                    default_controller = 3
                else:
                    controller_input = input(f"Controller number [0-127] [1]: ").strip()
                    default_controller = 1
                    
                if not controller_input:
                    controller = default_controller
                    break
                try:
                    controller = int(controller_input)
                    max_controller = 16383 if control_type == 'nrpn' else 127
                    if 0 <= controller <= max_controller:
                        break
                    else:
                        print(f"Invalid controller. Enter 0-{max_controller}.")
                except ValueError:
                    print(f"Invalid input. Enter a number 0-{16383 if control_type == 'nrpn' else 127}.")
                    
            # Value range - check for Prophet 6 presets first
            suggested_range = None
            if control_type == 'nrpn':
                # Check for Prophet 6 NRPN presets
                prophet_ranges = config.get('prophet_6_ranges', {})
                nrpn_key = f"nrpn{controller}"
                for range_name, range_info in prophet_ranges.items():
                    if nrpn_key in range_name:
                        suggested_range = (range_info['min_value'], range_info['max_value'])
                        print(f"\nProphet 6 preset found for NRPN{controller}: {range_name}")
                        print(f"   Suggested range: {suggested_range[0]} to {suggested_range[1]}")
                        break
            
            max_value = 16383 if control_type == 'cc14' else 127
            if control_type == 'nrpn':
                max_value = 16383  # NRPNs can use full 14-bit range
                
            print(f"\nValue range for {control_type.upper()} (0 to {max_value}):")
            
            # Use suggested range if available
            if suggested_range:
                use_preset = input(f"Use Prophet 6 preset range {suggested_range[0]}-{suggested_range[1]}? [y]: ").strip().lower()
                if not use_preset or use_preset in ['y', 'yes']:
                    min_value, max_val = suggested_range
                else:
                    suggested_range = None
            
            if not suggested_range:
                while True:
                    min_input = input(f"Minimum value [0]: ").strip()
                    if not min_input:
                        min_value = 0
                        break
                    try:
                        min_value = int(min_input)
                        if 0 <= min_value <= max_value:
                            break
                        else:
                            print(f"Invalid minimum. Enter 0-{max_value}.")
                    except ValueError:
                        print("Invalid input. Enter a number.")
                        
                while True:
                    max_input = input(f"Maximum value [{max_value}]: ").strip()
                    if not max_input:
                        max_val = max_value
                        break
                    try:
                        max_val = int(max_input)
                        if min_value <= max_val <= max_value:
                            break
                        else:
                            print(f"Invalid maximum. Enter {min_value}-{max_value}.")
                    except ValueError:
                        print("Invalid input. Enter a number.")
            
            # Create manual control config
            wavetable_config['control'] = {
                'type': control_type,
                'channel': channel,
                'controller': controller,
                'min_value': min_value,
                'max_value': max_val,
                'name': parameter_name
            }
        
        # Calculate optimal note (can be overridden)
        frequency, midi_note, note_name = WaveCalculator.calculate_optimal_note(
            sampler.audio_engine.samplerate,
            wavetable_config['samples_per_waveform']
        )
        
        # Override with MIDI note 3 (D#-1)
        midi_note = 3
        frequency = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
        # Calculate note name for MIDI note 3
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note = notes[midi_note % 12]
        note_name = f"{note}{octave}"
        
        wavetable_config.update({
            'note_frequency': frequency,
            'midi_note': midi_note,
            'note_name': note_name
        })
        
        # Ensure we have a control configuration
        if 'control' not in wavetable_config:
            # Fallback to default control
            wavetable_config['control'] = {
                'type': 'cc',
                'channel': 0,
                'controller': 1,
                'min_value': 0,
                'max_value': 127,
                'name': 'CC1'
            }
            print("Using default CC1 control")
        
        print(f"\n=== Wavetable Configuration ===")
        print(f"Name: {wavetable_config['name']}")
        print(f"Samples per waveform: {wavetable_config['samples_per_waveform']}")
        print(f"Number of waves: {wavetable_config['number_of_waves']}")
        print(f"Optimal note: {note_name} (MIDI {midi_note}, {frequency:.2f} Hz)")
        print(f"Control: {wavetable_config['control']['name']}")
        print(f"Range: {wavetable_config['control']['min_value']} to {wavetable_config['control']['max_value']}")
        print(f"Output: {wavetable_config['output_folder']}")
        
        # Confirm before proceeding
        print("\n=== Ready to Sample ===")
        response = input("Proceed with wavetable creation? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled by user")
            return False
        
        # Create wavetables
        print("\n=== Starting Wavetable Creation ===")
        success = sampler.create_wavetables(wavetable_config)
        
        if success:
            print("\nWavetable creation completed successfully!")
        else:
            print("\nWavetable creation failed")
            
        return success
        
    except Exception as e:
        logging.error(f"Wavetable workflow failed: {e}")
        return False


def get_wavetable_parameters(config: Dict) -> Optional[Dict]:
    """Get wavetable parameters from user input."""
    try:
        defaults = config.get('wavetable_defaults', {})
        
        print("=== Wavetable Parameters ===")
        
        # Wavetable name
        name = input(f"Wavetable name [{defaults.get('name_prefix', 'wavetable')}]: ").strip()
        if not name:
            name = defaults.get('name_prefix', 'wavetable')
        
        # Samples per waveform
        valid_samples = [128, 512, 1024, 2048, 4096]
        default_samples = defaults.get('samples_per_waveform', 2048)
        
        while True:
            samples_input = input(f"Samples per waveform {valid_samples} [{default_samples}]: ").strip()
            if not samples_input:
                samples_per_waveform = default_samples
                break
            try:
                samples_per_waveform = int(samples_input)
                if samples_per_waveform in valid_samples:
                    break
                else:
                    print(f"Invalid value. Choose from: {valid_samples}")
            except ValueError:
                print("Invalid input. Enter a number.")
        
        # Number of waves
        max_waves = 217 if samples_per_waveform == 4096 else 256
        default_waves = min(defaults.get('number_of_waves', 64), max_waves)
        
        while True:
            waves_input = input(f"Number of waves [2-{max_waves}] [{default_waves}]: ").strip()
            if not waves_input:
                number_of_waves = default_waves
                break
            try:
                number_of_waves = int(waves_input)
                if 2 <= number_of_waves <= max_waves:
                    break
                else:
                    print(f"Invalid value. Range: 2 to {max_waves}")
            except ValueError:
                print("Invalid input. Enter a number.")
        
        # Output folder
        default_output = defaults.get('output_folder', './output/wavetables')
        output_folder = input(f"Output folder [{default_output}]: ").strip()
        if not output_folder:
            output_folder = default_output
        
        # Validate configuration
        if not WaveCalculator.validate_wavetable_config(samples_per_waveform, number_of_waves):
            return None

        return {
            'name': name,
            'samples_per_waveform': samples_per_waveform,
            'number_of_waves': number_of_waves,
            'output_folder': output_folder
        }
        
    except Exception as e:
        logging.error(f"Failed to get wavetable parameters: {e}")
        return None


def load_wavetable_config(args) -> Optional[Dict]:
    """Load wavetable configuration."""
    try:
        # Load main config
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
            config.update(wavetable_config)
        else:
            logging.warning(f"Wavetable config not found: {wavetable_config_path}")
        
        return config
        
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return None


def initialize_interfaces(config: Dict) -> tuple:
    """Initialize audio and MIDI interfaces."""
    try:
        # Initialize audio engine directly
        audio_config = config.get('audio_interface', {})
        
        # Preemptive cleanup to ensure ASIO device is available
        # This is more aggressive than the main sampler because wavetable mode
        # may be started after other audio operations
        try:
            import sounddevice as sd
            import time
            
            # Multiple cleanup attempts with increasing delays
            for attempt in range(3):
                sd.stop()
                sd.abort()
                sd.default.reset()
                time.sleep(0.2)  # Let ASIO driver fully release
            
            logging.debug("Preemptive ASIO cleanup completed")
        except Exception as e:
            logging.debug(f"Preemptive cleanup failed (normal if no active streams): {e}")
        
        # Pass audio_interface config directly to AudioEngine (like main sampler does)
        # AudioEngine handles parsing of input_channels, monitor_channels, etc.
        # Only override settings that are specific to wavetable mode
        audio_config_dict = dict(audio_config)  # Make a copy
        audio_config_dict['silence_detection'] = False  # Disable for wavetables
        if 'mono_stereo' not in audio_config_dict:
            audio_config_dict['mono_stereo'] = 'stereo'  # Default to stereo
        
        audio_engine = AudioEngine(audio_config_dict)
        
        # Setup audio engine (configure devices and verify settings)
        if not audio_engine.setup():
            logging.warning("Audio engine setup failed with configured device, trying default device...")
            
            # Fallback to default system device if ASIO fails
            # Keep most settings but use system default devices
            fallback_audio_config = dict(audio_config)  # Start with original config
            fallback_audio_config['input_device_index'] = None  # Use system default
            fallback_audio_config['output_device_index'] = None  # Use system default
            fallback_audio_config['silence_detection'] = False  # Appropriate for wavetables
            # Reset channel settings to defaults since we're using default device
            fallback_audio_config.pop('input_channels', None)
            fallback_audio_config.pop('monitor_channels', None)
            fallback_audio_config.pop('output_channels', None)
            
            audio_engine = AudioEngine(fallback_audio_config)
            if not audio_engine.setup():
                logging.error("Audio engine setup failed even with default device")
                return None, None, None
            else:
                logging.info("Audio engine initialized with fallback default device")
        
        print(f"Audio engine initialized")
        
        # Initialize MIDI interface (optional)
        midi_config = config.get('midi_interface', {})
        midi_manager = None
        midi_controller = None
        
        if midi_config:
            midi_manager = MidiInterfaceManager()
            
            # Set up MIDI input/output if configured
            if 'midi_input_name' in midi_config:
                midi_manager.set_midi_input(midi_config['midi_input_name'])
            if 'midi_output_name' in midi_config:
                midi_manager.set_midi_output(midi_config['midi_output_name'])
            
            midi_manager.verify_settings()
            
            # Check if MIDI output is available and create controller
            if midi_manager.output_name:
                try:
                    import mido
                    midi_output_port = mido.open_output(midi_manager.output_name)
                    midi_controller = MIDIController(midi_output_port)
                    print(f"MIDI interface initialized ({midi_manager.output_name})")
                except Exception as e:
                    print(f"MIDI interface setup failed: {e} - continuing without MIDI")
                    midi_controller = None
            else:
                print("No MIDI output configured - continuing without MIDI")
                midi_controller = None
        else:
            print("No MIDI configuration - continuing without MIDI")
        
        return audio_engine, midi_manager, midi_controller
        
    except Exception as e:
        logging.error(f"Interface initialization failed: {e}")
        return None, None, None