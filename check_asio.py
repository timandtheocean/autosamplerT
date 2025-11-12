import sounddevice as sd

print("Available Host APIs:")
host_apis = sd.query_hostapis()
for i, api in enumerate(host_apis):
    print(f"  {i}: {api['name']}")
    if 'ASIO' in api['name'].upper():
        print(f"      *** ASIO FOUND ***")

print("\n\nAll devices with host API info:")
devices = sd.query_devices()
for idx, dev in enumerate(devices):
    if dev['max_output_channels'] > 0 or dev['max_input_channels'] > 0:
        host_api_name = host_apis[dev['hostapi']]['name']
        print(f"{idx}: {dev['name'][:50]:50s} [{host_api_name}] (in:{dev['max_input_channels']}, out:{dev['max_output_channels']})")
