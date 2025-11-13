# ASIO Multi-Channel Support

Guide for using multi-channel ASIO audio interfaces with AutosamplerT.

## Overview

AutosamplerT supports ASIO audio interfaces with multiple channel pairs (4, 6, or 8 channels). You can select which specific stereo pair or individual mono channel to record from using the `--channel_offset` argument.

## What It's Used For

- **Multi-channel interfaces**: Record from specific input pairs on devices with 4+ channels
- **ASIO devices**: Professional low-latency audio interfaces
- **Channel isolation**: Record different sound sources connected to different input pairs
- **Flexible routing**: Choose which physical inputs to use without rewiring

## Supported Devices

Any ASIO-compatible audio interface with multiple channel pairs:
- **4-channel devices**: Audio 4 DJ, Focusrite Scarlett 4i4, etc.
- **6-channel devices**: RME Babyface, MOTU UltraLite, etc.
- **8-channel devices**: Focusrite Scarlett 8i6, PreSonus Studio 1824c, etc.

## Requirements

### Windows
ASIO support in sounddevice requires setting an environment variable:
```python
import os
os.environ["SD_ENABLE_ASIO"] = "1"
import sounddevice as sd
```

AutosamplerT handles this automatically - no manual configuration needed.

### macOS/Linux
ASIO is Windows-only. Use CoreAudio (macOS) or ALSA/JACK (Linux) for multi-channel interfaces.

## Channel Mapping

### 4-Channel Device Example (Audio 4 DJ)

Physical device: **Audio 4 DJ** (ASIO)
- Total channels: 4 input, 4 output
- Channel 0: Ch A, Input 1 (Left)
- Channel 1: Ch A, Input 2 (Right)
- Channel 2: Ch B, Input 3 (Left)
- Channel 3: Ch B, Input 4 (Right)

### 8-Channel Device Example

Physical device: **8-Channel ASIO Interface**
- Total channels: 8 input, 8 output
- Channels 0-1: First stereo pair
- Channels 2-3: Second stereo pair
- Channels 4-5: Third stereo pair
- Channels 6-7: Fourth stereo pair

## Usage

### Command-Line Arguments

**`--channel_offset`**

Selects which stereo pair to record from:
- `0` = Channels 0-1 (first pair)
- `2` = Channels 2-3 (second pair)
- `4` = Channels 4-5 (third pair)
- `6` = Channels 6-7 (fourth pair)

**`--mono_stereo`**

Recording mode:
- `stereo` = Record stereo pair (default)
- `mono` = Record single channel from selected pair

**`--mono_channel`**

Which channel within the selected pair:
- `0` = Left channel of the pair
- `1` = Right channel of the pair

### Examples

#### Example 1: Record Stereo from Ch A
```bash
python autosamplerT.py \
  --channel_offset 0 \
  --note_range_start C2 \
  --note_range_end C7 \
  --multisample_name synth_ch_a
```

#### Example 2: Record Stereo from Ch B
```bash
python autosamplerT.py \
  --channel_offset 2 \
  --note_range_start C2 \
  --note_range_end C7 \
  --multisample_name synth_ch_b
```

#### Example 3: Record Mono from Ch B Left
```bash
python autosamplerT.py \
  --channel_offset 2 \
  --mono_stereo mono \
  --mono_channel 0 \
  --note_range_start C2 \
  --note_range_end C7 \
  --multisample_name synth_ch_b_left
```

#### Example 4: Record Mono from Ch B Right
```bash
python autosamplerT.py \
  --channel_offset 2 \
  --mono_stereo mono \
  --mono_channel 1 \
  --note_range_start C2 \
  --note_range_end C7 \
  --multisample_name synth_ch_b_right
```

#### Example 5: 8-Channel Device - Record from Pair 3
```bash
python autosamplerT.py \
  --channel_offset 4 \
  --note_range_start C2 \
  --note_range_end C7 \
  --multisample_name synth_pair_3
```

### YAML Configuration

Configure channel selection in your script YAML file:

```yaml
audio_interface:
  input_device_index: 16        # Your ASIO device
  output_device_index: 16
  channel_offset: 2             # Record from Ch B (channels 2-3)
  mono_stereo: stereo           # Or 'mono' for single channel
  mono_channel: 0               # 0=left, 1=right
  samplerate: 44100
  bitdepth: 24
```

## How It Works

### Detection

1. AutosamplerT queries the audio device:
   ```python
   device_info = sd.query_devices(device_index)
   device_channels = device_info['max_input_channels']
   host_api = device_info['hostapi']
   ```

2. Checks if device is ASIO:
   ```python
   host_api_name = host_apis[device_info['hostapi']]['name']
   is_asio = 'ASIO' in host_api_name
   ```

3. If ASIO with >2 channels, uses channel selection

### Channel Selection

For ASIO devices, AutosamplerT uses `sounddevice.AsioSettings`:

**Stereo recording:**
```python
channel_selectors = [channel_offset, channel_offset + 1]  # e.g., [2, 3]
asio_settings = sd.AsioSettings(channel_selectors=channel_selectors)
recording = sd.rec(..., extra_settings=asio_settings)
```

**Mono recording:**
```python
channel_selectors = [channel_offset + mono_channel]  # e.g., [2] or [3]
asio_settings = sd.AsioSettings(channel_selectors=channel_selectors)
recording = sd.rec(..., extra_settings=asio_settings)
```

### Non-ASIO Devices

For non-ASIO devices (WASAPI, MME, WDM-KS):
- Records all available channels
- Extracts requested channels after recording
- Works but less efficient than ASIO

## Device Discovery

### List Available Devices

Check which devices support multi-channel:

```bash
python autosamplerT.py --setup audio
```

Output shows channel counts:
```
Available INPUT devices:
  16: Audio 4 DJ [ASIO]                          | In: 4 | Out: 4
  20: Audio 4 DJ (Ch B, In 3|4) [Windows WASAPI] | In: 2 | Out: 0
  21: Audio 4 DJ (Ch A, In 1|2) [Windows WASAPI] | In: 2 | Out: 0
```

**Key observations:**
- **ASIO device (16)**: Single device with 4 channels
- **WASAPI devices (20, 21)**: Split into separate 2-channel devices
- Use ASIO device for `channel_offset` support

### Check Device Channels

Use the included test script:

```bash
python check_device_channels.py
```

Output shows detailed channel information for all devices.

## Testing

### Test Script

A comprehensive test script is included: `test_asio_channel_selection.py`

```bash
python test_asio_channel_selection.py
```

Tests all combinations:
-  Ch A (0-1) Stereo
-  Ch B (2-3) Stereo
-  Ch A Left (0) Mono
-  Ch A Right (1) Mono
-  Ch B Left (2) Mono
-  Ch B Right (3) Mono

### Test Mode

Test without recording:

```bash
python autosamplerT.py \
  --channel_offset 2 \
  --test_mode \
  --note_range_start C4 \
  --note_range_end C4
```

Verifies configuration without saving files.

## Logging

AutosamplerT logs channel selection:

**Stereo with offset:**
```
INFO: Channels: 2 (stereo, offset 2: channels 2-3)
INFO: ASIO: Selecting channels [2, 3] (stereo pair)
```

**Mono with offset:**
```
INFO: Channels: 1 (mono, using left channel from offset 2, actual channel 2)
INFO: ASIO: Selecting channel 2 (mono)
```

## Troubleshooting

### ASIO Device Not Showing

**Problem:** ASIO device doesn't appear in device list

**Solution:**
- Ensure ASIO driver is installed
- Restart AutosamplerT (it sets SD_ENABLE_ASIO automatically)
- Check Windows audio settings

### Wrong Channels Recorded

**Problem:** Recording from wrong input pair

**Solution:**
- Verify channel_offset value:
  - Ch A = 0
  - Ch B = 2
  - Ch C = 4
  - Ch D = 6
- Check physical cable connections
- Use `test_asio_channel_selection.py` to verify

### No Audio Signal

**Problem:** Recording succeeds but no audio captured

**Solution:**
- Verify synth is connected to correct physical inputs
- Check input levels on audio interface
- Test with different channel_offset values
- Ensure synth is playing during recording

### Device Channel Mismatch

**Problem:** "Failed to load ASIO driver" error

**Solution:**
- Ensure channel_offset + mono_channel < device channels
- For 4-channel device, max offset is 2
- For 8-channel device, max offset is 6

## Best Practices

1. **Use ASIO for multi-channel**: ASIO provides direct channel selection
2. **Test first**: Use `test_asio_channel_selection.py` before sampling
3. **Document your setup**: Note which synths connect to which channels
4. **Consistent routing**: Keep synth → input mappings consistent
5. **Label cables**: Physical labels help track which cable goes where
6. **Monitor levels**: Check input levels before long sampling sessions

## Comparison: ASIO vs Other APIs

| Feature | ASIO | WASAPI | MME/DirectSound |
|---------|------|--------|-----------------|
| **Channel Selection** | Direct (AsioSettings) | Post-recording extraction | Post-recording extraction |
| **Efficiency** |  Records only requested channels | ⚠️ Records all, extracts | ⚠️ Records all, extracts |
| **Latency** |  Lowest (~5-10ms) |  Low (~10-20ms) | ⚠️ Higher (~20-50ms) |
| **Multi-channel** |  Single 4/6/8-ch device | ⚠️ Split into 2-ch devices | ⚠️ Split into 2-ch devices |
| **Professional Use** |  Industry standard |  Good | ⚠️ Acceptable |
| **Recommendation** | **Best for multi-channel** | Good alternative | Last resort |

## Related Documentation

- [Setup Guide](SETUP.md) - Device configuration
- [CLI Reference](CLI.md) - Command-line arguments
- [Quick Start](QUICKSTART.md) - Getting started

---

*Last updated: November 12, 2025*
