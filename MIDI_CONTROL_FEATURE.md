# MIDI Control Feature - Feature Branch Updates

## Overview
Added comprehensive MIDI control capabilities for per-layer MIDI message transmission, enabling advanced sampling workflows with CC, Program Change, and SysEx messages sent before each sample.

## Key Features Added

### 1. Per-Layer MIDI Control
- **Velocity Layer MIDI**: Send different MIDI messages for each velocity layer
- **Round-Robin Layer MIDI**: Send different MIDI messages for each round-robin layer
- Support for 7-bit CC, 14-bit CC, Program Change, and SysEx messages

### 2. MIDI Message Delay
- Configurable delay between MIDI message transmission and note-on
- Gives hardware synths time to process CC/PC/SysEx changes before note triggers
- Parameter: `midi_message_delay` (seconds) in `midi_interface` section

### 3. Enhanced MIDI Setup
- Improved MIDI device selection with fuzzy matching
- Support for device name substring matching
- Skip option for input/output selection
- Validation status display (OK/SKIPPED/NOT FOUND)
- Absolute path display for config file

### 4. Separate Setup Modes
- `--setup audio`: Audio configuration only
- `--setup midi`: MIDI configuration only  
- `--setup all`: Both audio and MIDI (default)

### 5. Enhanced Logging
- All MIDI messages now log at INFO level (visible in standard output)
- CC, CC14, Program Change, and SysEx messages fully logged
- Layer configuration loading status displayed

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
Used `receivemidi` with virtual MIDI cable (loopMIDI) to verify:
- ✅ CC messages transmitted with correct values
- ✅ CC messages sent before note-on
- ✅ Timing correct (~10ms between CC and note without delay)
- ✅ Configurable delay working (~110ms with 100ms setting)
- ✅ All roundrobin layers execute in sequence

### Log Output
Messages now visible in standard output:
```
INFO: Applying MIDI settings for round-robin layer 0
INFO: MIDI CC sent: cc=1, value=10, channel=0
INFO: Sampling: Note=60, Vel=127, RR=0
```

## Breaking Changes
None - all changes are backward compatible. Existing scripts without `sampling_midi` section continue to work.

## Future Enhancements
- Per-note MIDI control (different messages per MIDI note)
- MIDI channel per layer (already supported in config structure)
- NRPN message support
- MIDI learn mode for CC discovery

## Branch Status
Branch: `feature/midicontrol`
Ready for: Testing and merge review
