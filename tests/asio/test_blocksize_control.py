"""
Test if changing blocksize actually affects ASIO recording.

This test records a short audio segment with different blocksizes
and measures the actual callback timing to verify if the blocksize
is being respected by the ASIO driver.
"""
import os
os.environ['SD_ENABLE_ASIO'] = '1'

import sounddevice as sd
import numpy as np
import time

def find_asio_device():
    """Find the first ASIO device."""
    devices = sd.query_devices()
    host_apis = sd.query_hostapis()
    for i, dev in enumerate(devices):
        if host_apis[dev['hostapi']]['name'] == 'ASIO':
            return i, dev
    return None, None

def test_blocksize(device_idx, blocksize, duration=1.0, samplerate=44100):
    """
    Test recording with a specific blocksize and measure actual callback timing.
    
    Returns:
        dict with test results
    """
    callback_times = []
    callback_sizes = []
    last_time = [None]
    
    def callback(indata, frames, time_info, status):
        now = time.perf_counter()
        if last_time[0] is not None:
            callback_times.append(now - last_time[0])
        callback_sizes.append(frames)
        last_time[0] = now
        if status:
            print(f"  Status: {status}")
    
    try:
        stream = sd.InputStream(
            device=device_idx,
            channels=2,
            samplerate=samplerate,
            blocksize=blocksize,
            callback=callback,
            dtype='float32'
        )
        
        with stream:
            sd.sleep(int(duration * 1000))
        
        if callback_times:
            avg_time = np.mean(callback_times) * 1000  # ms
            std_time = np.std(callback_times) * 1000   # ms
            avg_size = np.mean(callback_sizes)
            
            # Expected time between callbacks
            expected_time = blocksize / samplerate * 1000  # ms
            
            return {
                'success': True,
                'requested_blocksize': blocksize,
                'actual_avg_blocksize': avg_size,
                'expected_callback_ms': expected_time,
                'actual_callback_ms': avg_time,
                'callback_std_ms': std_time,
                'num_callbacks': len(callback_times),
                'blocksize_match': abs(avg_size - blocksize) < 1
            }
        else:
            return {'success': False, 'error': 'No callbacks received'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


def main():
    print("=== ASIO Blocksize Test ===\n")
    
    device_idx, device_info = find_asio_device()
    if device_idx is None:
        print("ERROR: No ASIO device found!")
        print("Make sure SD_ENABLE_ASIO=1 is set")
        return
    
    print(f"Using ASIO device: {device_info['name']} (index {device_idx})")
    print(f"Default latency: {device_info['default_low_input_latency']*1000:.2f} ms")
    print()
    
    blocksizes_to_test = [128, 256, 512, 1024, 2048]
    
    print("Testing different blocksizes (1 second each)...\n")
    print(f"{'Requested':>10} | {'Actual':>10} | {'Expected':>10} | {'Actual':>10} | {'Std Dev':>8} | {'Match':>6}")
    print(f"{'Blocksize':>10} | {'Blocksize':>10} | {'Callback':>10} | {'Callback':>10} | {'':>8} | {'':>6}")
    print(f"{'(samples)':>10} | {'(samples)':>10} | {'(ms)':>10} | {'(ms)':>10} | {'(ms)':>8} | {'':>6}")
    print("-" * 75)
    
    results = []
    for blocksize in blocksizes_to_test:
        result = test_blocksize(device_idx, blocksize)
        results.append(result)
        
        if result['success']:
            match_str = "YES" if result['blocksize_match'] else "NO"
            print(f"{result['requested_blocksize']:>10} | "
                  f"{result['actual_avg_blocksize']:>10.1f} | "
                  f"{result['expected_callback_ms']:>10.2f} | "
                  f"{result['actual_callback_ms']:>10.2f} | "
                  f"{result['callback_std_ms']:>8.2f} | "
                  f"{match_str:>6}")
        else:
            print(f"{blocksize:>10} | FAILED: {result['error']}")
        
        # Small pause between tests
        time.sleep(0.2)
    
    print()
    
    # Analysis
    successful = [r for r in results if r['success']]
    if successful:
        all_match = all(r['blocksize_match'] for r in successful)
        if all_match:
            print("RESULT: Blocksize IS controllable via sounddevice!")
            print("        You can set blocksize in the config to control buffer size.")
        else:
            # Check if ASIO is using a fixed buffer
            actual_sizes = [r['actual_avg_blocksize'] for r in successful]
            if len(set([int(s) for s in actual_sizes])) == 1:
                fixed_size = int(actual_sizes[0])
                print(f"RESULT: ASIO driver is using FIXED buffer size of {fixed_size} samples")
                print(f"        The blocksize parameter is being IGNORED by the ASIO driver.")
                print(f"        To change buffer size, use the ASIO control panel.")
            else:
                print("RESULT: Mixed results - blocksize partially controllable")
    else:
        print("RESULT: All tests failed!")


if __name__ == '__main__':
    main()
