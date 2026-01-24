"""
Test audio playback functionality.

This script demonstrates:
1. Real-time monitoring (duplex mode) - hear what you're recording as it happens
2. Recording audio through selected input channels
3. Playing back the recorded audio through selected output channels
4. Supporting ASIO multi-channel routing
"""

import os
import sys
import logging
import yaml
import numpy as np

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Enable ASIO before importing sounddevice
from set_audio_config import *  # This sets SD_ENABLE_ASIO=1

from sampling.audio_engine import AudioEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

def load_config():
    """Load audio configuration."""
    config_file = 'conf/autosamplerT_config.yaml'
    
    if not os.path.exists(config_file):
        logging.error(f"Configuration file not found: {config_file}")
        logging.info("Please run: python src/set_audio_config.py")
        return None
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    return config.get('audio_interface', {})


def test_playback():
    """Test recording and playback."""
    print("="*70)
    print("AUDIO PLAYBACK TEST")
    print("="*70)
    
    # Load configuration
    audio_config = load_config()
    if audio_config is None:
        return
    
    print("\nAudio Configuration:")
    print(f"  Input device: {audio_config.get('input_device_index')}")
    print(f"  Output device: {audio_config.get('output_device_index')}")
    print(f"  Input channels: {audio_config.get('input_channels', '3-4')}")
    print(f"  Output channels: {audio_config.get('output_channels', 'same as input')}")
    print(f"  Sample rate: {audio_config.get('samplerate', 44100)} Hz")
    print(f"  Bit depth: {audio_config.get('bitdepth', 24)} bit")
    
    # Create audio engine
    engine = AudioEngine(audio_config, test_mode=False)
    
    if not engine.setup():
        logging.error("Audio engine setup failed")
        return
    
    print("\n" + "="*70)
    print("TEST OPTIONS")
    print("="*70)
    print("1. Record with real-time monitoring (duplex mode)")
    print("2. Record 3 seconds and play back afterwards")
    print("3. Play a test tone (1kHz sine wave)")
    print("4. Exit")
    
    while True:
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            print("\n--- Recording with Real-Time Monitoring ---")
            print("You will hear what you're recording in real-time!")
            print("Make some noise into your microphone/synth...")
            print("Recording 5 seconds...")
            
            audio_data = engine.record_with_monitoring(5.0)
            
            if audio_data is None:
                logging.error("Recording failed")
                continue
            
            print(f"\nRecorded: {audio_data.shape} samples")
            print(f"Peak level: {np.max(np.abs(audio_data)):.3f}")
            
            playback = input("Play back the recording? (y/n): ").strip().lower()
            if playback == 'y':
                print("Playing back...")
                engine.play(audio_data, blocking=True)
                print("Playback complete!")
        
        elif choice == '2':
            print("\n--- Recording 3 seconds ---")
            print("Make some noise into your microphone/synth...")
            
            audio_data = engine.record(3.0)
            
            if audio_data is None:
                logging.error("Recording failed")
                continue
            
            print(f"Recorded: {audio_data.shape} samples")
            print(f"Peak level: {np.max(np.abs(audio_data)):.3f}")
            
            print("\n--- Playing back recording ---")
            success = engine.play(audio_data, blocking=True)
            
            if success:
                print("Playback complete!")
            else:
                logging.error("Playback failed")
        
        elif choice == '3':
            print("\n--- Generating test tone ---")
            duration = 2.0
            frequency = 1000  # 1kHz
            
            t = np.linspace(0, duration, int(engine.samplerate * duration), False)
            tone = np.sin(2 * np.pi * frequency * t) * 0.3  # 30% amplitude
            
            # Make stereo if needed
            if engine.channels == 2:
                tone = np.column_stack([tone, tone])
            else:
                tone = tone.reshape(-1, 1)
            
            tone = tone.astype(np.float32)
            
            print(f"Playing 1kHz tone for {duration}s...")
            success = engine.play(tone, blocking=True)
            
            if success:
                print("Test tone complete!")
            else:
                logging.error("Playback failed")
        
        elif choice == '4':
            print("\nExiting...")
            break
        
        else:
            print("Invalid choice. Please enter 1-4.")
    
    print("\nDone!")


if __name__ == "__main__":
    try:
        test_playback()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        logging.error(f"Test failed: {e}", exc_info=True)
