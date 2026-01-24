#!/usr/bin/env python3
"""
Debug wavetable device selection.
"""

import yaml
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    # Load the config like wavetable mode does
    with open('conf/autosamplerT_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    print("Config loaded:")
    print(f"  input_device_index: {config.get('audio_interface', {}).get('input_device_index')}")
    print(f"  input_channels: {config.get('audio_interface', {}).get('input_channels')}")
    
    # Simulate wavetable_mode initialization
    audio_config = config.get('audio_interface', {})
    
    # Parse input channels
    input_channels_str = audio_config.get('input_channels', '1-2')
    if '-' in input_channels_str:
        start_ch, end_ch = input_channels_str.split('-')
        channel_offset = int(start_ch) - 1  # Convert to 0-based
    else:
        channel_offset = 0
    
    # Prepare audio configuration for AudioEngine
    audio_config_dict = {
        'input_device_index': audio_config.get('input_device_index', 0),
        'samplerate': audio_config.get('samplerate', 44100),
        'bitdepth': audio_config.get('bitdepth', 24),
        'mono_stereo': 'stereo',
        'input_channels': f"{start_ch}-{int(start_ch)+1}" if start_ch else None
    }
    
    print("\\nAudio config dict for AudioEngine:")
    for key, value in audio_config_dict.items():
        print(f"  {key}: {value}")
    
    from sampling.audio_engine import AudioEngine
    audio_engine = AudioEngine(audio_config_dict)
    
    print("\\nAudioEngine created:")
    print(f"  input_device: {audio_engine.input_device}")
    print(f"  channel_offset: {audio_engine.channel_offset}")
    
    # This is what gets passed to WavetableSampler
    audio_device_index = audio_engine.input_device or 0
    print(f"\\nDevice index passed to WavetableSampler: {audio_device_index}")
    
    # WavetableSampler creates its own AudioEngine with hardcoded channel_offset=2
    wavetable_audio_config = {
        'input_device_index': audio_device_index,
        'samplerate': 44100,
        'bitdepth': 24,
        'mono_stereo': 'stereo',
        'channel_offset': 2  # Hardcoded!
    }
    
    print("\\nWavetableSampler AudioEngine config:")
    for key, value in wavetable_audio_config.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    main()