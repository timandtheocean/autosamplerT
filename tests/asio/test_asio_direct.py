import os
os.environ['SD_ENABLE_ASIO'] = '1'

import sounddevice as sd

# Check device
dev = sd.query_devices(16)
print(f'Device: {dev["name"]}')
print(f'Input Channels: {dev["max_input_channels"]}')

apis = sd.query_hostapis()
print(f'Host API: {apis[dev["hostapi"]]["name"]}')

# Test Ch B (channels 2-3) with AsioSettings
print('\nTesting Ch B (channels 2-3) with AsioSettings...')
settings = sd.AsioSettings(channel_selectors=[2, 3])
print(f'AsioSettings created: {settings}')

print('Recording 2 seconds...')
rec = sd.rec(88200, samplerate=44100, channels=2, device=16, dtype='float32', extra_settings=settings)
sd.wait()
print(f'Recording complete! Shape: {rec.shape}')
print('Success!')
