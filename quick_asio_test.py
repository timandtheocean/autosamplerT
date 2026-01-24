import os
os.environ['SD_ENABLE_ASIO'] = '1'

import sounddevice as sd

dev = sd.query_devices(16)
print(f'Device 16: {dev["name"]}')
print(f'Max input: {dev["max_input_channels"]}')

settings = sd.AsioSettings(channel_selectors=[2, 3])
print('Testing ASIO recording channels 2-3...')

rec = sd.rec(44100, samplerate=44100, channels=2, device=16, dtype='float32', extra_settings=settings)
sd.wait()
print(f'Success! Shape: {rec.shape}')
