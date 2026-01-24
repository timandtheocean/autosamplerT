"""
Test that blocksize configuration works with AudioEngine recording.
"""
import os
os.environ['SD_ENABLE_ASIO'] = '1'

import sys
sys.path.insert(0, '.')

from src.sampling.audio_engine import AudioEngine
import numpy as np
import time

def test_record_with_blocksize(blocksize, duration=0.5):
    """Test recording with a specific blocksize."""
    config = {
        'samplerate': 44100,
        'input_device_index': 16,
        'output_device_index': 16,
        'input_channels': '3-4',
        'blocksize': blocksize
    }
    
    engine = AudioEngine(config)
    engine.setup()
    
    print(f"Recording with blocksize={blocksize}...", end=" ", flush=True)
    start = time.perf_counter()
    audio = engine.record(duration)
    elapsed = time.perf_counter() - start
    
    if audio is not None:
        expected_samples = int(duration * 44100)
        actual_samples = len(audio)
        print(f"OK - {actual_samples} samples in {elapsed:.2f}s")
        return True
    else:
        print("FAILED")
        return False

def main():
    print("=== AudioEngine Blocksize Recording Test ===\n")
    
    blocksizes = [None, 256, 512, 1024]  # None = driver default
    
    for bs in blocksizes:
        bs_str = str(bs) if bs else "default"
        try:
            test_record_with_blocksize(bs)
        except Exception as e:
            print(f"blocksize={bs_str}: ERROR - {e}")
        
        time.sleep(0.2)
    
    print("\nDone!")

if __name__ == '__main__':
    main()
