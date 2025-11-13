# ASIO Testing

This directory contains tests for ASIO multi-channel audio functionality.

## Files

- `test_asio_enable.py` - Test ASIO driver availability
- `test_asio_device.py` - Test ASIO device enumeration
- `test_asio_channels.py` - Test ASIO channel detection
- `test_asio_channel_selection.py` - Test channel selection with AsioSettings
- `test_asio_direct.py` - Test direct ASIO recording from main thread
- `test_asio_thread.py` - Test ASIO recording from worker thread (expected to fail)
- `check_asio.py` - Quick ASIO availability check
- `check_device_channels.py` - Display device channel information

## Quick Tests

### Check if ASIO is Available

```bash
cd tests\asio
python check_asio.py
```

### Check Device Channels

```bash
python check_device_channels.py
```

## Running Specific Tests

### Test ASIO Direct Recording (Main Thread)

```bash
python test_asio_direct.py
```

**Expected**:  Success - Records 2 seconds, displays shape

### Test ASIO Thread Recording (Worker Thread)

```bash
python test_asio_thread.py
```

**Expected**: Failure - "Failed to load ASIO driver" (this proves ASIO threading limitation)

### Test Channel Selection

```bash
python test_asio_channel_selection.py
```

**Expected**:  Success - Records from specific channel pair

## ASIO Threading Issue

**Key Discovery**: ASIO streams cannot be initialized from worker threads.

### Problem
```python
# This FAILS in worker thread:
def worker_thread():
    settings = sd.AsioSettings(channel_selectors=[2, 3])
    audio = sd.rec(frames, extra_settings=settings)  # ERROR
```

### Solution
```python
# This WORKS in main thread:
settings = sd.AsioSettings(channel_selectors=[2, 3])
audio = sd.rec(frames, extra_settings=settings)  #  SUCCESS
```

### Implementation in Sampler

The sampler detects ASIO and records in the main thread:

```python
# In sample_note() method
is_asio = 'ASIO' in host_api_name

if is_asio:
    # Record in main thread
    audio = self.record_audio(total_duration)
    # Send note-off after recording
else:
    # Use threading for non-ASIO
    threading.Thread(target=record_thread).start()
```

## Validated Configuration

### Working Setup
- **Device**: Audio 4 DJ (device 16)
- **Channels**: 4 input channels (0-3)
- **Channel Pairs**:
  - Ch A: channels 0-1 (In 1|2) - offset 0
  - Ch B: channels 2-3 (In 3|4) - offset 2
- **Sample Rate**: 44100 Hz
- **Bit Depth**: 24-bit

### Configuration File
```yaml
audio_interface:
  input_device_index: 16
  output_device_index: 16
  channel_offset: 2  # Ch B selected
  samplerate: 44100
  bitdepth: 24
```

## Test Results

All ASIO tests validated:
-  ASIO driver loads successfully
-  Multi-channel device detection works
-  Channel pair selection works (Ch A, Ch B)
-  Direct recording from main thread works
-  Threading limitation confirmed (expected behavior)
-  Long recordings (10s+) work without hanging

## Documentation

See `doc/ASIO_MULTICHANNEL.md` for complete ASIO multi-channel guide.
