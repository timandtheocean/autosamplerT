import os
os.environ['SD_ENABLE_ASIO'] = '1'

import sounddevice as sd
import threading
import time

# Test ASIO recording from a thread (like the sampler does)
def record_in_thread():
    print('Thread: Creating AsioSettings...')
    settings = sd.AsioSettings(channel_selectors=[2, 3])
    
    print('Thread: Starting recording...')
    rec = sd.rec(132300, samplerate=44100, channels=2, device=16, dtype='float32', extra_settings=settings, blocking=False)
    
    print('Thread: Waiting for recording to complete...')
    sd.wait()
    
    print(f'Thread: Recording complete! Shape: {rec.shape}')
    return rec

print('Main: Starting thread...')
result = [None]
def target():
    result[0] = record_in_thread()

thread = threading.Thread(target=target)
thread.start()

time.sleep(1)  # Simulate hold time
print('Main: Hold time complete')

thread.join()
print(f'Main: Thread joined, result shape: {result[0].shape if result[0] is not None else "None"}')
print('Success!')
