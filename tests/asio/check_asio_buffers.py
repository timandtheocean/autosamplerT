"""
Check ASIO device information including buffer sizes and latency.
"""
import os
os.environ['SD_ENABLE_ASIO'] = '1'

import sounddevice as sd

devices = sd.query_devices()
host_apis = sd.query_hostapis()

print('=== ASIO Device Information ===\n')
for i, dev in enumerate(devices):
    if host_apis[dev['hostapi']]['name'] == 'ASIO':
        name = dev['name']
        sr = dev['default_samplerate']
        low_in_lat = dev['default_low_input_latency']
        high_in_lat = dev['default_high_input_latency']
        low_out_lat = dev['default_low_output_latency']
        high_out_lat = dev['default_high_output_latency']
        
        # Calculate buffer sizes from latency
        low_buf = int(low_in_lat * sr)
        high_buf = int(high_in_lat * sr)
        
        print(f'Device {i}: {name}')
        print(f'  Max Input Channels: {dev["max_input_channels"]}')
        print(f'  Max Output Channels: {dev["max_output_channels"]}')
        print(f'  Default Sample Rate: {sr} Hz')
        print()
        print(f'  Input Latency:')
        print(f'    Low:  {low_in_lat*1000:.2f} ms (~{low_buf} samples)')
        print(f'    High: {high_in_lat*1000:.2f} ms (~{high_buf} samples)')
        print()
        print(f'  Output Latency:')
        print(f'    Low:  {low_out_lat*1000:.2f} ms')
        print(f'    High: {high_out_lat*1000:.2f} ms')
        print()

# Check if we can set blocksize
print('=== Buffer Size Control ===\n')
print('sounddevice allows setting blocksize parameter in streams:')
print('  - blocksize=256  (low latency, higher CPU)')
print('  - blocksize=512  (balanced)')
print('  - blocksize=1024 (higher latency, lower CPU)')
print('  - blocksize=2048 (high latency, very low CPU)')
print()
print('For ASIO, the actual buffer size is controlled by:')
print('  1. The ASIO driver control panel (preferred)')
print('  2. The blocksize parameter in sounddevice (may be ignored by ASIO)')
print()
print('To open ASIO control panel:')
print('  - Look for your audio interface software')
print('  - Or use a DAW to access ASIO settings')

# Test different blocksizes
print('\n=== Testing Buffer Sizes ===\n')
asio_device = None
for i, dev in enumerate(devices):
    if host_apis[dev['hostapi']]['name'] == 'ASIO':
        asio_device = i
        break

if asio_device is not None:
    for blocksize in [128, 256, 512, 1024]:
        try:
            # Test if this blocksize works
            stream = sd.InputStream(
                device=asio_device,
                channels=2,
                samplerate=44100,
                blocksize=blocksize,
                dtype='float32'
            )
            stream.close()
            latency_ms = blocksize / 44100 * 1000
            print(f'  blocksize={blocksize}: OK ({latency_ms:.1f} ms per buffer)')
        except Exception as e:
            print(f'  blocksize={blocksize}: FAILED - {e}')
