import os
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd
import numpy as np

# Get ASIO device
devices = sd.query_devices()
host_apis = sd.query_hostapis()

asio_device = None
for i, dev in enumerate(devices):
    if host_apis[dev['hostapi']]['name'] == 'ASIO':
        asio_device = i
        print(f"ASIO Device {i}: {dev['name']}")
        print(f"  Input channels: {dev['max_input_channels']}")
        print(f"  Output channels: {dev['max_output_channels']}")
        break

if asio_device is not None:
    # Test recording 2 channels (Ch 1-2)
    print("\n--- Testing 2-channel recording (Ch 1-2) ---")
    try:
        sd.default.device = (asio_device, asio_device)
        sd.default.samplerate = 44100
        
        # Record 0.1 seconds, 2 channels
        recording = sd.rec(frames=4410, channels=2, dtype='float32', blocking=True)
        print(f"✓ SUCCESS: Recorded 2 channels, shape: {recording.shape}")
    except Exception as e:
        print(f"✗ FAILED: {e}")
    
    # Test recording 4 channels (All channels)
    print("\n--- Testing 4-channel recording (All channels) ---")
    try:
        recording = sd.rec(frames=4410, channels=4, dtype='float32', blocking=True)
        print(f"✓ SUCCESS: Recorded 4 channels, shape: {recording.shape}")
        print(f"  Can access Ch 1-2 via recording[:, 0:2]")
        print(f"  Can access Ch 3-4 via recording[:, 2:4]")
    except Exception as e:
        print(f"✗ FAILED: {e}")
else:
    print("No ASIO device found!")
