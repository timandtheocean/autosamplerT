"""Quick test of buffer size selection display."""
import os
os.environ['SD_ENABLE_ASIO'] = '1'

import sys
sys.path.insert(0, '.')

from src.set_audio_config import select_blocksize, test_available_blocksizes
import sounddevice as sd
import math

device_idx = 16
samplerate = 44100

# Show what the menu would look like
print("="*70)
print("BUFFER SIZE SELECTION")
print("="*70)

device_info = sd.query_devices(device_idx)
current_latency = device_info.get('default_low_input_latency', 0)
current_blocksize = int(round(current_latency * samplerate))
if current_blocksize > 0:
    current_blocksize = 2 ** round(math.log2(current_blocksize))

print(f"\nCurrent device buffer size: {current_blocksize} samples ({current_latency*1000:.1f} ms)")
print("\nTesting available buffer sizes...")

available = test_available_blocksizes(device_idx, samplerate)

# Find current option
current_option = 0
for idx, (blocksize, _) in enumerate(available, 1):
    if blocksize == current_blocksize:
        current_option = idx
        break

print("\nAvailable buffer sizes:")
print(f"  0. Use driver default (recommended)")
for idx, (blocksize, latency_ms) in enumerate(available, 1):
    stability = ""
    if blocksize <= 128:
        stability = " (lowest latency, may cause glitches)"
    elif blocksize <= 256:
        stability = " (low latency)"
    elif blocksize <= 512:
        stability = " (balanced)"
    elif blocksize <= 1024:
        stability = " (stable)"
    else:
        stability = " (very stable, higher latency)"
    
    current_marker = " <-- CURRENT" if blocksize == current_blocksize else ""
    print(f"  {idx}. {blocksize} samples ({latency_ms:.1f} ms){stability}{current_marker}")

print("\nTip: Larger buffer = more stable but higher latency")
print("     If you hear clicks/pops, try a larger buffer size")
print(f"\nDefault selection would be: [{current_option}] ({current_blocksize} samples)")
