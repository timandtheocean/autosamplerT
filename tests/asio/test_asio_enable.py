import os

# Set environment variable before importing sounddevice. Value is not important.
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd

print("Available Host APIs:")
host_apis = sd.query_hostapis()
for i, api in enumerate(host_apis):
    print(f"  {i}: {api['name']}")
    if 'ASIO' in api['name'].upper():
        print(f"      *** ASIO FOUND! ***")

print("\n\nASIO Devices:")
devices = sd.query_devices()
for idx, dev in enumerate(devices):
    if dev['max_output_channels'] > 0 or dev['max_input_channels'] > 0:
        host_api_name = host_apis[dev['hostapi']]['name']
        if 'ASIO' in host_api_name.upper():
            print(f"{idx}: {dev['name']} (in:{dev['max_input_channels']}, out:{dev['max_output_channels']})")
