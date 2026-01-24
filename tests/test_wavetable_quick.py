#!/usr/bin/env python3
"""
Quick wavetable test - bypasses interactive setup and uses known Prophet 6 NRPN3 settings.
"""

import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from wavetable.wavetable_sampler import WavetableSampler
from sampler_midicontrol import MIDIController
from sampling.audio_engine import AudioEngine
import mido

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

def main():
    try:
        print("=== Quick Wavetable Test ===")
        
        # MIDI setup - use the same pattern as main sampler
        try:
            midi_output_port = mido.open_output("Prophet 6 1")
        except Exception as e:
            logging.warning(f"Failed to open MIDI port: {e}")
            midi_output_port = None
        
        midi_controller = MIDIController(midi_output_port) if midi_output_port else None
        
        # Audio config - use ASIO device same as main sampler
        audio_config = {
            'input_device_index': 37,    # ASIO device  
            'output_device_index': 37,   # Same device for output
            'samplerate': 44100,
            'bitdepth': 24,
            'mono_stereo': 'stereo',
            'input_channels': '3-4',     # Same channels as main sampler
            'silence_detection': False,  # Disable for wavetable recording
            'gain_db': 0.0
        }
        
        # Initialize audio engine the same way as main sampler
        audio_engine = AudioEngine(audio_config, test_mode=False)
        print(f"Audio engine created with config: {audio_config}")
        
        setup_success = audio_engine.setup()
        print(f"Audio engine setup result: {setup_success}")
        
        if not setup_success:
            print("Failed to setup audio engine")
            return
        
        # Create wavetable sampler with context manager for proper cleanup
        with WavetableSampler(
            audio_engine=audio_engine,
            midi_controller=midi_controller
        ) as wavetable_sampler:
            
            # Wavetable configurations to test
            test_configs = [
                {
                    'name': 'test-waveshape-lin-2048',
                    'samples_per_waveform': 2048,
                    'number_of_waves': 5,  # Quick test - just 5 waves
                    'note_frequency': 440.0,  # A4
                    'midi_note': 69,  # A4
                    'control': {
                        'type': 'nrpn',
                        'controller': 3,
                        'channel': 0,
                        'min_value': 0,
                        'max_value': 254,
                        'name': 'waveshape'
                    },
                    'output_folder': './output/wavetables'
                }
            ]
            
            # Test each configuration
            for config in test_configs:
                print(f"\\nTesting: {config['name']}")
                success = wavetable_sampler.create_wavetables(config)
                print(f"Result: {'SUCCESS' if success else 'FAILED'}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Ensure proper cleanup like main sampler does
        try:
            # Close MIDI ports
            if midi_output_port:
                midi_output_port.close()
                logging.info("MIDI output port closed")
        except Exception as e:
            logging.warning(f"Error closing MIDI port: {e}")
    
    print("\\nTest completed!")
    return True

if __name__ == "__main__":
    main()