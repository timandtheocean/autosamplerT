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
        audio_device_index = audio_engine.device_index
        sample_rate = audio_engine.sample_rate
        bit_depth = audio_engine.bit_depth
        
        # Initialize wavetable sampler
        wavetable_sampler = WavetableSampler(
            audio_device_index=audio_device_index,
            sample_rate=sample_rate,
            bit_depth=bit_depth,
            midi_controller=midi_controller
        )
        
        # Run wavetable creation workflow
        success = run_wavetable_workflow(wavetable_sampler, config, midi_manager)
        
        # Cleanup
        if midi_controller:
            midi_controller.close()
        
        return success
        
    except Exception as e:
        logging.error(f"Wavetable mode failed: {e}")
        return False


def run_wavetable_workflow(sampler: WavetableSampler, config: Dict, 
                          midi_manager: Optional[MIDIInterfaceManager]) -> bool:
    """Run the complete wavetable creation workflow."""
    try:
        # Get wavetable parameters from user
        wavetable_config = get_wavetable_parameters(config)
        if not wavetable_config:
            return False
        
        # MIDI Learn workflow
        if midi_manager and midi_manager.input_name:
            print("\\n=== MIDI Learn ===")
            
            # Open MIDI input port for learning
            try:
                import mido
                with mido.open_input(midi_manager.input_name) as midi_input_port:
                    midi_learn = MIDILearn(midi_input_port)
                    
                    # Learn control
                    control_info = midi_learn.learn_control()
                    if not control_info:
                        print("✗ MIDI learn failed - cannot continue")
                        return False
                    
                    # Learn range
                    control_range = midi_learn.learn_range(control_info)
                    if not control_range:
                        print("✗ Range learning failed - cannot continue")
                        return False
                    
                    # Update config with learned control
                    wavetable_config['control'] = {
                        **control_info,
                        'min_value': control_range[0],
                        'max_value': control_range[1]
                    }
            except Exception as e:
                print(f"✗ MIDI learn failed: {e}")
                return False
        else:
            print("\\n⚠ No MIDI input available - skipping MIDI learn")
            # Use default control (CC1)
            wavetable_config['control'] = {
                'type': 'cc',
                'channel': 0,
                'controller': 1,
                'min_value': 0,
                'max_value': 127,
                'name': 'CC1'
            }
        
        # Calculate optimal note
        frequency, midi_note, note_name = WaveCalculator.calculate_optimal_note(
            sampler.sample_rate,
            wavetable_config['samples_per_waveform']
        )
        
        wavetable_config.update({
            'note_frequency': frequency,
            'midi_note': midi_note,
            'note_name': note_name
        })
        
        print(f"\\n=== Wavetable Configuration ===")
        print(f"Name: {wavetable_config['name']}")
        print(f"Samples per waveform: {wavetable_config['samples_per_waveform']}")
        print(f"Number of waves: {wavetable_config['number_of_waves']}")
        print(f"Optimal note: {note_name} (MIDI {midi_note}, {frequency:.2f} Hz)")
        print(f"Control: {wavetable_config['control']['name']}")
        print(f"Range: {wavetable_config['control']['min_value']} to {wavetable_config['control']['max_value']}")
        print(f"Output: {wavetable_config['output_folder']}")
        
        # Confirm before proceeding
        print("\\n=== Ready to Sample ===")
        response = input("Proceed with wavetable creation? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Cancelled by user")
            return False
        
        # Create wavetables
        print("\\n=== Starting Wavetable Creation ===")
        success = sampler.create_wavetables(wavetable_config)
        
        if success:
            print("\\n✓ Wavetable creation completed successfully!")
        else:
            print("\\n✗ Wavetable creation failed")
            
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
        
        # Parse input channels
        input_channels_str = audio_config.get('input_channels', '1-2')
        if '-' in input_channels_str:
            start_ch, end_ch = input_channels_str.split('-')
            channel_offset = int(start_ch) - 1  # Convert to 0-based
        else:
            channel_offset = 0
        
        audio_engine = AudioEngine(
            device_index=audio_config.get('input_device_index', 0),
            sample_rate=audio_config.get('samplerate', 44100),
            bit_depth=audio_config.get('bitdepth', 24),
            channels=2,  # Stereo
            channel_offset=channel_offset
        )
        
        print(f"✓ Audio engine initialized")
        
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
            
            if hasattr(midi_manager, 'midi_output_port') and midi_manager.midi_output_port:
                midi_controller = MIDIController(
                    midi_manager.midi_output_port,
                    getattr(midi_manager, 'midi_input_port', None)
                )
                print(f"✓ MIDI interface initialized")
            else:
                print("⚠ MIDI interface setup failed - continuing without MIDI")
        else:
            print("⚠ No MIDI configuration - continuing without MIDI")
        
        return audio_engine, midi_manager, midi_controller
        
    except Exception as e:
        logging.error(f"Interface initialization failed: {e}")
        return None, None, None