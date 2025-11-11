# MIDI Control Feature - Feature Branch Updates

## Overview
Added comprehensive MIDI control capabilities for per-layer MIDI message transmission, enabling advanced sampling workflows with CC, Program Change, and SysEx messages sent before each sample.

## Key Features Added

### 1. Per-Layer MIDI Control
- **Velocity Layer MIDI**: Send different MIDI messages for each velocity layer
- **Round-Robin Layer MIDI**: Send different MIDI messages for each round-robin layer
- Support for 7-bit CC, 14-bit CC, Program Change, and SysEx messages

### 2. SysEx Structured Format
- **Structured format**: `{header: "43 10 7F", controller: "10", value: 64}` - User-friendly format with automatic hex conversion
- **Header reuse**: Omit header key to reuse previous header across messages in same layer
- **Raw format**: `{raw: "43 10 7F 13 7F"}` - Direct hex bypass for complex messages
- **Value validation**: Automatic 0-127 range checking with error logging
- **Auto-wrapping**: Automatic F0/F7 framing added to all messages
- **Cross-layer state**: Header persists between layers for easy configuration

### 3. Pre-Sampling Summary
- Interactive summary display before sampling starts
- Shows output settings (name, location, format)
- Sample configuration (notes, layers, total samples)
- Audio settings (sample rate, bit depth, channels)
- **Timing settings** (hold, release, pause times)
- MIDI control configuration per layer (CC, SysEx, Program Changes)
- **Estimates**: Total duration (minutes) and disk space (MB)
- User confirmation prompt to proceed or cancel

### 4. MIDI Message Delay
- Configurable delay between MIDI message transmission and note-on
- Gives hardware synths time to process CC/PC/SysEx changes before note triggers
- Parameter: `midi_message_delay` (seconds) in `midi_interface` section

### 5. Enhanced MIDI Setup
- Improved MIDI device selection with fuzzy matching
- Support for device name substring matching
- Skip option for input/output selection
- Validation status display (OK/SKIPPED/NOT FOUND)
- Absolute path display for config file

### 6. Separate Setup Modes
- `--setup audio`: Audio configuration only
- `--setup midi`: MIDI configuration only  
- `--setup all`: Both audio and MIDI (default)

### 7. Enhanced Logging
- All MIDI messages now log at INFO level (visible in standard output)
- CC, CC14, Program Change, and SysEx messages fully logged
- Layer configuration loading status displayed
- Timing information logged at startup (hold, release, pause)

## Modified Files

### Core Files
- **`autosamplerT.py`**
  - Added `sampling_midi` to script merge sections
  - Modified `--setup` argument to accept sub-modes
  - Conditional setup script launching based on mode

- **`src/sampler.py`**
  - Added `midi_message_delay` parameter support
  - Pass delay to MIDI layer application methods
  - Added logging for velocity/roundrobin MIDI config counts

- **`src/sampler_midicontrol.py`**
  - Added `message_delay` parameter to `apply_velocity_layer_midi()`
  - Added `message_delay` parameter to `apply_roundrobin_layer_midi()`
  - Changed logging level from DEBUG to INFO for all MIDI messages
  - Implemented configurable delay after CC/PC/SysEx transmission
  - **Enhanced `parse_sysex_messages()`** with structured format support
  - Added `sysex_header_state` tracking in MIDIController class
  - Implemented `_parse_hex_value()` and `_ensure_sysex_wrapper()` helpers
  - Header state passed between layer parsing calls for reuse

- **`src/set_midi_config.py`**
  - Complete rewrite with enhanced UX
  - Fuzzy device name matching
  - Skip support for optional selections
  - Device validation with status output
  - Improved error handling and user guidance

### Test Scripts
- **`conf/test_roundrobin_cc.yaml`**: 4 roundrobin layers with different CC controllers
- **`conf/test_roundrobin_6layers_cc.yaml`**: 6 layers with all 4 CCs at different values
- **`conf/test_cc1_sweep.yaml`**: 13 layers sweeping CC1 from 1-121 in steps of 10
- **`conf/test_cc1_with_delay.yaml`**: CC1 sweep with 100ms message delay
- **`conf/test_velocity_cc.yaml`**: 5 velocity layers with CC74 brightness sweep
- **`conf/test_sysex_structured.yaml`**: Structured SysEx format with header reuse, multiple messages, raw format
- **`conf/test_program_change.yaml`**: Program change messages per layer (4 different programs)
- **`conf/test_suite_full.yaml`**: Comprehensive test with 3 velocity × 4 roundrobin layers, mixed MIDI control

## Configuration Examples

### Basic Per-Layer CC Messages
```yaml
sampling_midi:
  roundrobin_midi_control:
    - roundrobin_layer: 0
      midi_channel: 0
      cc_messages: {1: 10}
    - roundrobin_layer: 1
      midi_channel: 0
      cc_messages: {1: 50}
    - roundrobin_layer: 2
      midi_channel: 0
      cc_messages: {1: 90}
```

### MIDI Message Delay
```yaml
midi_interface:
  midi_message_delay: 0.1  # 100ms delay after CC/PC/SysEx before note-on
```

### Multiple CC Messages Per Layer
```yaml
roundrobin_midi_control:
  - roundrobin_layer: 0
    midi_channel: 0
    cc_messages: {1: 0, 2: 0, 3: 0, 4: 0}
  - roundrobin_layer: 1
    midi_channel: 0
    cc_messages: {1: 20, 2: 20, 3: 20, 4: 20}
```

### Velocity Layer MIDI
```yaml
velocity_midi_control:
  - velocity_layer: 0
    midi_channel: 0
    cc_messages: {74: 20}  # Brightness low for soft notes
    program_change: 0
  - velocity_layer: 1
    midi_channel: 0
    cc_messages: {74: 80}  # Brightness high for loud notes
    program_change: 1
```

### SysEx Structured Format
```yaml
roundrobin_midi_control:
  # Layer 0: Full structured format with header
  - roundrobin_layer: 0
    midi_channel: 0
    sysex_messages:
      - header: "43 10 7F"     # Manufacturer/device header
        controller: "10"        # Parameter number (hex)
        value: 0                # Parameter value (0-127)
  
  # Layer 1: Reuse header from layer 0
  - roundrobin_layer: 1
    midi_channel: 0
    sysex_messages:
      - controller: "10"        # Header automatically reused
        value: 64
  
  # Layer 2: Multiple messages per layer
  - roundrobin_layer: 2
    midi_channel: 0
    sysex_messages:
      - header: "43 10 7F"
        controller: "10"
        value: 100
      - controller: "11"        # Reuse header
        value: 100
      - controller: "12"        # Reuse header again
        value: 100
  
  # Layer 3: Raw format for complex messages
  - roundrobin_layer: 3
    midi_channel: 0
    sysex_messages:
      - raw: "43 10 7F 13 7F"  # Direct hex (F0/F7 added automatically)
```

## Usage

### Run Separate Setup
```bash
# MIDI setup only
python autosamplerT.py --setup midi

# Audio setup only
python autosamplerT.py --setup audio

# Both (default)
python autosamplerT.py --setup all
```

### Sample with MIDI Control
```bash
python autosamplerT.py --script conf/test_roundrobin_cc.yaml
```

### Sample with Message Delay
```bash
python autosamplerT.py --script conf/test_cc1_with_delay.yaml
```

## Testing Notes

### MIDI Monitor Verification
Used `receivemidi` with virtual MIDI cable (loopMIDI) and OP-1 Field to verify:
- ✅ CC messages transmitted with correct values
- ✅ CC messages sent before note-on
- ✅ Timing correct (~10ms between CC and note without delay)
- ✅ Configurable delay working (~110ms with 100ms setting)
- ✅ All roundrobin layers execute in sequence
- ✅ Velocity layer CC messages working (CC74 brightness sweep verified)
- ✅ Program changes sent correctly (0, 24, 40, 80 verified)
- ✅ SysEx structured format working with header reuse
- ✅ SysEx raw format working (receivemidi shows hex payload without F0/F7)
- ✅ Multiple SysEx messages per layer working
- ✅ Comprehensive test suite (36 samples, 3×4 layers) successful

### Log Output
Messages now visible in standard output with timing:
```
INFO: Sampling range: Note 60-60, interval 1
INFO: Velocity layers: 1, Round-robin: 4
INFO: Timing: hold=0.50s, release=0.10s, pause=0.20s
INFO: Velocity MIDI config: 0 layers
INFO: Round-robin MIDI config: 4 layers
INFO: Applying MIDI settings for round-robin layer 0
INFO: MIDI Program Change: program=0, channel=0
INFO: MIDI CC sent: cc=1, value=10, channel=0
INFO: MIDI SysEx sent: F0 43 10 7F 10 00 F7
INFO: Sampling: Note=60, Vel=127, RR=0
```

### Pre-Sampling Summary Example
```
======================================================================
SAMPLING SUMMARY
======================================================================

Output Settings:
  Name:          OP1_Test_Suite
  Location:      output\OP1_Test_Suite
  Format:        SFZ

Sample Configuration:
  Note range:    60 to 62 (interval: 1)
  Notes:         3
  Velocity layers: 3
  Round-robin:   4
  Total samples: 36

Audio Settings:
  Sample rate:   44100 Hz
  Bit depth:     24 bit
  Channels:      2 (stereo)

Timing Settings:
  Hold time:     0.50s
  Release time:  0.10s
  Pause time:    0.30s
  Sample duration: 0.60s (hold + release)
  Total per sample: 0.90s (inc. pause)

MIDI Control:
  Velocity layers: 3 configured
    Layer 0: CC: 1
    Layer 1: CC: 1
    Layer 2: CC: 1
  Round-robin layers: 4 configured
    Layer 0: CC: 1, PC: 0
    Layer 1: CC: 1, PC: 1
    Layer 2: CC: 2
    Layer 3: CC: 1, SysEx: 1

Estimates:
  Duration:      0.5 minutes
  Disk space:    5.5 MB
======================================================================

Proceed with sampling? (y/n):
```

## Breaking Changes
None - all changes are backward compatible. Existing scripts without `sampling_midi` section continue to work.

## Future Enhancements
- Per-note MIDI control (different messages per MIDI note)
- NRPN message support
- MIDI learn mode for CC discovery
- 2-byte nibble support for SysEx values (currently single-byte 0-127)

## Implementation Details

### SysEx Format Parsing
The `parse_sysex_messages()` function handles three input formats:
1. **Structured**: Dict with `header`, `controller`, `value` keys
2. **Raw**: Dict with `raw` key for direct hex input
3. **Legacy**: Plain strings (backward compatible)

Header state is tracked in `MIDIController.sysex_header_state` and passed between parsing calls, allowing header reuse across layers without repeating the manufacturer/device ID in every message.

### Summary Calculation
File size estimation: `samples × samplerate × duration × channels × (bitdepth/8)`
Duration estimation: `total_samples × (sample_duration + pause_time)`

## Commits
- `7253f52` - Initial MIDI control with CC, delays, setup improvements
- `9b1186b` - SysEx structured format and pre-sampling summary

## Status
✅ **Merged to main** - All features tested and production ready
