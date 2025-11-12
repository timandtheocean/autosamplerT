#!/usr/bin/env python3
"""Check channel count for audio devices."""

import os
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd

def check_device_channels():
    """Display channel information for all devices."""
    devices = sd.query_devices()
    host_apis = sd.query_hostapis()
    
    print("=" * 80)
    print("AUDIO DEVICE CHANNEL INFORMATION")
    print("=" * 80)
    
    # Find ASIO devices first
    asio_devices = []
    for idx, dev in enumerate(devices):
        host_api_name = host_apis[dev['hostapi']]['name']
        if 'ASIO' in host_api_name and dev['max_input_channels'] > 0:
            asio_devices.append((idx, dev))
    
    if asio_devices:
        print("\n🎯 ASIO INPUT DEVICES (Professional Audio):")
        print("-" * 80)
        for idx, dev in asio_devices:
            host_api_name = host_apis[dev['hostapi']]['name']
            print(f"\nDevice {idx}: {dev['name']}")
            print(f"  Host API: {host_api_name}")
            print(f"  Max Input Channels: {dev['max_input_channels']}")
            print(f"  Max Output Channels: {dev['max_output_channels']}")
            print(f"  Default Sample Rate: {dev['default_samplerate']}")
    
    # Show other input devices
    print("\n\n📥 ALL INPUT DEVICES:")
    print("-" * 80)
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            host_api_name = host_apis[dev['hostapi']]['name']
            print(f"{idx:3d}: {dev['name'][:50]:50s} | In: {dev['max_input_channels']:2d} | [{host_api_name}]")
    
    # Specific check for Audio 4 DJ
    print("\n\n🎛️  AUDIO 4 DJ DEVICES:")
    print("-" * 80)
    for idx, dev in enumerate(devices):
        if 'Audio 4 DJ' in dev['name']:
            host_api_name = host_apis[dev['hostapi']]['name']
            print(f"\nDevice {idx}: {dev['name']}")
            print(f"  Host API: {host_api_name}")
            print(f"  Input Channels: {dev['max_input_channels']}")
            print(f"  Output Channels: {dev['max_output_channels']}")
            print(f"  Sample Rate: {dev['default_samplerate']}")
            
            # Show what you can do with this device
            if dev['max_input_channels'] == 4:
                print(f"  ✅ Can record 4 channels simultaneously")
                print(f"     - Channels 0-1: Ch A (In 1|2)")
                print(f"     - Channels 2-3: Ch B (In 3|4)")
            elif dev['max_input_channels'] == 2:
                print(f"  ✅ Can record 2 channels (stereo)")

if __name__ == "__main__":
    check_device_channels()
