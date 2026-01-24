#!/usr/bin/env python3
"""Check device configuration for wavetable mode debugging."""

import os
# Enable ASIO support (must be before sounddevice import)
os.environ["SD_ENABLE_ASIO"] = "1"

import yaml
import sounddevice as sd


def check_config():
    """Check the current configuration."""
    print("=== Configuration Check ===")
    
    # Load main config
    try:
        with open('conf/autosamplerT_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        audio_config = config.get('audio_interface', {})
        print(f"Audio config: {audio_config}")
        
        input_device_index = audio_config.get('input_device_index')
        output_device_index = audio_config.get('output_device_index')
        input_channels = audio_config.get('input_channels', '1-2')
        
        print(f"Input device index: {input_device_index}")
        print(f"Output device index: {output_device_index}")
        print(f"Input channels: {input_channels}")
        
    except Exception as e:
        print(f"Failed to load config: {e}")
        return


def check_devices():
    """Check available audio devices."""
    print("\n=== Device Check ===")
    
    # Get host APIs
    host_apis = sd.query_hostapis()
    print("Host APIs:")
    for i, api in enumerate(host_apis):
        print(f"  {i}: {api['name']}")
        if 'ASIO' in api['name'].upper():
            print(f"      *** ASIO FOUND ***")
    
    # Get devices
    devices = sd.query_devices()
    print(f"\nTotal devices: {len(devices)}")
    
    print("\nASIO devices:")
    asio_count = 0
    for idx, dev in enumerate(devices):
        if dev['max_output_channels'] > 0 or dev['max_input_channels'] > 0:
            host_api_name = host_apis[dev['hostapi']]['name']
            if 'ASIO' in host_api_name.upper():
                print(f"  {idx}: {dev['name'][:45]:45s} [{host_api_name}] "
                      f"(in:{dev['max_input_channels']}, out:{dev['max_output_channels']})")
                asio_count += 1
    
    if asio_count == 0:
        print("  No ASIO devices found!")
        print("\nAll devices:")
        for idx, dev in enumerate(devices):
            if dev['max_output_channels'] > 0 or dev['max_input_channels'] > 0:
                host_api_name = host_apis[dev['hostapi']]['name']
                print(f"  {idx}: {dev['name'][:45]:45s} [{host_api_name}] "
                      f"(in:{dev['max_input_channels']}, out:{dev['max_output_channels']})")


def simulate_wavetable_init():
    """Simulate wavetable audio initialization."""
    print("\n=== Wavetable Init Simulation ===")
    
    try:
        # Load config like wavetable mode does
        with open('conf/autosamplerT_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        audio_config = config.get('audio_interface', {})
        
        # Parse input channels like wavetable mode does
        input_channels_str = audio_config.get('input_channels', '1-2')
        if '-' in input_channels_str:
            start_ch, end_ch = input_channels_str.split('-')
            channel_offset = int(start_ch) - 1  # Convert to 0-based
        else:
            channel_offset = 0
        
        # Create audio config dict like wavetable mode does (FIXED version)
        audio_config_dict = {
            'input_device_index': audio_config.get('input_device_index'),  # Fixed: no fallback to 0
            'output_device_index': audio_config.get('output_device_index'),
            'samplerate': audio_config.get('samplerate', 44100),
            'bitdepth': audio_config.get('bitdepth', 24),
            'mono_stereo': 'stereo',
            'channel_offset': channel_offset,
            'silence_detection': False
        }
        
        print(f"Audio config dict: {audio_config_dict}")
        
        # Check the devices that would be used
        input_device = audio_config_dict['input_device_index']
        output_device = audio_config_dict['output_device_index']
        
        if input_device is not None:
            device_info = sd.query_devices(input_device)
            host_apis = sd.query_hostapis()
            host_api_name = host_apis[device_info['hostapi']]['name']
            is_asio = 'ASIO' in host_api_name
            print(f"Input device {input_device}: {device_info['name']} [{host_api_name}] ASIO={is_asio}")
        else:
            print("Input device: None (will use system default)")
            
        if output_device is not None:
            device_info = sd.query_devices(output_device)
            host_apis = sd.query_hostapis()
            host_api_name = host_apis[device_info['hostapi']]['name']
            is_asio = 'ASIO' in host_api_name
            print(f"Output device {output_device}: {device_info['name']} [{host_api_name}] ASIO={is_asio}")
        else:
            print("Output device: None (will use system default)")
        
        print(f"Channel offset: {channel_offset}")
        
    except Exception as e:
        print(f"Simulation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_config()
    check_devices()
    simulate_wavetable_init()