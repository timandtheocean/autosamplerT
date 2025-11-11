# Setup & Configuration

Guide for configuring audio and MIDI devices in AutosamplerT.

## Overview

AutosamplerT requires proper audio and MIDI device configuration before sampling. The setup system provides:
- Interactive device selection
- Fuzzy matching for device names
- Device validation and testing
- Persistent configuration storage
- Separate audio/MIDI setup modes

## What It's Used For

- **First-time setup**: Configure devices when first using AutosamplerT
- **Device changes**: Switch to different audio interfaces or MIDI devices
- **Troubleshooting**: Validate and fix device configuration issues
- **Virtual MIDI**: Configure virtual MIDI cables for testing

## Setup Modes

### All Devices (Default)
```bash
python autosamplerT.py --setup all
```
Configure both audio and MIDI devices in one session.

### Audio Only
```bash
python autosamplerT.py --setup audio
```
Configure only audio input/output devices. MIDI devices are not enumerated or modified.

**Use when:**
- Changing audio interface
- MIDI already configured
- Working without MIDI control

### MIDI Only
```bash
python autosamplerT.py --setup midi
```
Configure only MIDI input/output devices. Audio devices are not enumerated or modified.

**Use when:**
- Changing MIDI devices
- Audio already configured
- Testing MIDI without audio sampling

## Audio Configuration

### Interactive Setup Process

1. **List available devices**
   ```
   Available audio devices:
   [0] Microsoft Sound Mapper - Input
   [1] Focusrite USB (input)
   [2] Virtual Cable (input)
   ...
   ```

2. **Select input device**
   ```
   Enter input device number (or 'skip' to keep current): 1
   ```

3. **Select output device**
   ```
   Enter output device number (or 'skip' to keep current): 4
   ```

4. **Sample rate selection**
   ```
   Enter sample rate (44100 or 48000) [44100]: 48000
   ```

5. **Bit depth selection**
   ```
   Enter bit depth (16 or 24) [24]: 24
   ```

### Configuration Storage

Audio settings are saved to `conf/autosamplerT_config.yaml`:

```yaml
audio_interface:
  input_device_idx: 1
  output_device_idx: 4
  sample_rate: 48000
  sample_width: 24
  audio_validated: true
```

### Skip Options

Use `skip` to keep current configuration:
```
Enter input device number (or 'skip' to keep current): skip
✓ Keeping current input device: Focusrite USB
```

## MIDI Configuration

### Interactive Setup Process

1. **List available MIDI ports**
   ```
   Available MIDI Input Ports:
   [0] loopMIDI Port 1
   [1] OP-1 0
   [2] Microsoft GS Wavetable Synth
   
   Available MIDI Output Ports:
   [0] loopMIDI Port 1
   [1] OP-1 1
   [2] Microsoft GS Wavetable Synth
   ```

2. **Select input port**
   ```
   Enter MIDI input port name or number (or 'skip'): OP-1 0
   ```

3. **Select output port**
   ```
   Enter MIDI output port name or number (or 'skip'): OP-1 1
   ```

### Fuzzy Matching

The MIDI setup supports flexible device matching:

**Exact match:**
```
Enter MIDI input port name or number: OP-1 0
✓ Selected: OP-1 0
```

**Partial match:**
```
Enter MIDI input port name or number: op-1
✓ Selected: OP-1 0
```

**Case-insensitive:**
```
Enter MIDI input port name or number: LOOPMIDI
✓ Selected: loopMIDI Port 1
```

**Numeric index:**
```
Enter MIDI input port name or number: 0
✓ Selected: loopMIDI Port 1
```

### Configuration Storage

MIDI settings are saved to `conf/autosamplerT_config.yaml`:

```yaml
midi_interface:
  input_port: "OP-1 0"
  output_port: "OP-1 1"
  midi_validated: true
```

### Skip Options

Use `skip` to keep current configuration:
```
Enter MIDI input port name or number (or 'skip'): skip
✓ Keeping current MIDI input: OP-1 0
```

## Configuration File

All settings are stored in `conf/autosamplerT_config.yaml`:

```yaml
audio_interface:
  input_device_idx: 1
  output_device_idx: 4
  sample_rate: 48000
  sample_width: 24
  audio_validated: true

midi_interface:
  input_port: "OP-1 0"
  output_port: "OP-1 1"
  midi_validated: true
```

### Manual Editing

You can manually edit the configuration file, but validation flags will be reset until you run setup again.

### Validation Flags

- `audio_validated: true` - Audio devices tested successfully
- `midi_validated: true` - MIDI ports opened successfully

## Examples

### Example 1: First-Time Setup
```bash
# Setup everything
python autosamplerT.py --setup all

# Follow prompts to select devices
# Enter input device number: 1
# Enter output device number: 4
# Enter sample rate: 48000
# Enter bit depth: 24
# Enter MIDI input port: OP-1 0
# Enter MIDI output port: OP-1 1

# Configuration saved automatically
```

### Example 2: Change Audio Interface Only
```bash
# Setup audio only (MIDI unchanged)
python autosamplerT.py --setup audio

# Select new audio devices
# MIDI configuration remains untouched
```

### Example 3: Setup Virtual MIDI for Testing
```bash
# Install loopMIDI (Windows) or IAC Driver (Mac)
# Create virtual port: "loopMIDI Port 1"

# Configure MIDI
python autosamplerT.py --setup midi

# Enter MIDI input port: loopMIDI
# Enter MIDI output port: loopMIDI

# Both input/output use same virtual port
```

### Example 4: Skip Some Settings
```bash
python autosamplerT.py --setup all

# Keep current input device
Enter input device number: skip

# Change output device
Enter output device number: 3

# Keep current sample rate
Enter sample rate [44100]: skip

# Continue with rest of setup...
```

### Example 5: Fuzzy MIDI Matching
```bash
python autosamplerT.py --setup midi

# Various ways to select "OP-1 Field 0":
Enter MIDI input port: op-1          # Partial match
Enter MIDI input port: OP-1 FIELD    # Case-insensitive
Enter MIDI input port: field         # Substring match
Enter MIDI input port: 1             # Numeric index
Enter MIDI input port: OP-1 Field 0  # Exact match
```

## Troubleshooting

### Device Not Found
```
Error: Device not found or unavailable
```
**Solution:** Run setup again and verify device is connected and powered on.

### MIDI Port Already Open
```
Error: MIDI port already in use
```
**Solution:** Close other applications using the MIDI port, or restart the system.

### Invalid Device Index
```
Error: Invalid device index
```
**Solution:** Check available devices with `--setup` and use valid index number.

### Sample Rate Not Supported
```
Error: Sample rate not supported by device
```
**Solution:** Use 44100 or 48000 Hz. Check device specifications.

### Configuration Not Persisting
**Solution:** Ensure `conf/` directory exists and is writable. Check file permissions.

## Best Practices

1. **Test after setup**: Run a simple sampling script to verify configuration
2. **Use descriptive device names**: Helps with fuzzy matching
3. **Document your setup**: Note which ports/devices are used for your workflow
4. **Virtual MIDI for testing**: Use virtual cables to test MIDI without hardware
5. **Separate setup modes**: Use `--setup midi` when audio is already working
6. **Skip unchanged settings**: Use `skip` to avoid reconfiguring working devices

## Related Documentation

- [CLI Documentation](CLI.md) - Command-line interface details
- [MIDI Control](MIDI_CONTROL_FEATURE.md) - MIDI message configuration
- [Quick Start](QUICKSTART.md) - Getting started guide

---

*Last updated: November 11, 2025*
