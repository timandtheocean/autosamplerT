import os
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd

devices = sd.query_devices()
host_apis = sd.query_hostapis()

print("ASIO Device Details:")
for i, dev in enumerate(devices):
    if host_apis[dev['hostapi']]['name'] == 'ASIO':
        print(f"\nDevice {i}: {dev['name']}")
        print(f"  Host API: ASIO")
        print(f"  Max input channels: {dev['max_input_channels']}")
        print(f"  Max output channels: {dev['max_output_channels']}")
        print(f"  Default sample rate: {dev.get('default_samplerate', 'Unknown')}")
        print(f"  Default low input latency: {dev.get('default_low_input_latency', 'Unknown')}")
        print(f"  Default low output latency: {dev.get('default_low_output_latency', 'Unknown')}")
        
        # Try to test if device is accessible
        try:
            print(f"  Testing device access...")
            sd.check_input_settings(device=i, channels=1, samplerate=44100)
            print(f"  ✓ Input access OK")
        except Exception as e:
            print(f"  ✗ Input access failed: {e}")
        
        try:
            sd.check_output_settings(device=i, channels=2, samplerate=44100)
            print(f"  ✓ Output access OK")
        except Exception as e:
            print(f"  ✗ Output access failed: {e}")
