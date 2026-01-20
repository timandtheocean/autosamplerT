# Waldorf Quantum/Iridium Sample Map Format - Complete Documentation

Based on extensive hardware testing and reverse engineering of the Waldorf QPAT/MAP format.

## Overview

Waldorf Quantum and Iridium synthesizers use a 16-column tab-separated sample map format for multisamples. Each line represents one sample with its complete parameter mapping.

## Column Format (16 Columns, Tab-Separated)

| Column | Parameter | Format | Verified | Description |
|--------|-----------|--------|----------|-------------|
| 1 | Sample Location | String | ✅ | `"LOCATION:path/sample.wav"` |
| 2 | Pitch | Float | ✅ | Root note (always 60.0 for C4 in practice) |
| 3 | From Note | Integer | ✅ | Key range start (0-127) |
| 4 | To Note | Integer | ✅ | Key range end (0-127) |
| 5 | Sample Gain | Float | ✅ | Linear gain multiplier from dB: `10^(dB/20)` |
| 6 | From Velo | Integer | ✅ | Velocity range start (1-127) |
| 7 | To Velo | Integer | ✅ | Velocity range end (1-127) |
| 8 | Unknown Field | Float | ❓ | Mystery parameter (0.0-1.0) - possibly pan/stereo width |
| 9 | Sample Start | Float | ✅ | Sample start position (0.0-1.0) |
| 10 | Sample End | Float | ✅ | Sample end position (0.0-1.0) |
| 11 | Loop Mode | Integer | ✅ | 0=off, 1=forward, 2=ping-pong |
| 12 | Loop Start | Float | ✅ | Loop start position (0.0-1.0) |
| 13 | Loop End | Float | ✅ | Loop end position (0.0-1.0) |
| 14 | Direction | Integer | ❓ | 0=forward, 1=reverse |
| 15 | X-Fade | Float | ❓ | Crossfade amount (0.0-1.0) |
| 16 | Track Pitch | Integer | ✅ | 0=off, 1=on (key tracking) |

## Sample Location Prefixes

Controls where samples are loaded from:

- `2:` = SD Card (default for external samples)
- `3:` = Internal Memory  
- `4:` = USB Drive (triggers auto-import)

## Multi-Layer Support

Waldorf supports up to **3 groups** (velocity layers or round-robin) per multisample:

### Velocity Layers
```yaml
sampling:
  velocity_layers: 3
  roundrobin_layers: 1

sampling_midi:
  velocity_midi_control:
    - layer: 0
      cc_messages: {7: 32}   # Soft layer
    - layer: 1  
      cc_messages: {7: 80}   # Medium layer
    - layer: 2
      cc_messages: {7: 127}  # Hard layer
```

### Round-Robin Layers  
```yaml
sampling:
  velocity_layers: 1
  roundrobin_layers: 3

sampling_midi:
  roundrobin_midi_control:
    - layer: 0
      nrpn_messages: {45: 0}     # First variation
    - layer: 1
      nrpn_messages: {45: 55}    # Second variation  
    - layer: 2
      nrpn_messages: {45: 110}   # Third variation
```

## Key Discoveries

### Column 5 Fix (Critical)
- **Was**: Tune parameter (cents) - WRONG
- **Now**: Sample Gain (linear from dB) - CORRECT
- **Formula**: `linear_gain = 10^(dB/20)`
- **Examples**:
  - `-12dB → 0.251189`
  - `0dB → 1.000000`  
  - `+6dB → 1.995262`

### Column 8 Mystery Field
- **Status**: Unknown purpose
- **Range**: 0.0-1.0  
- **Theories**: Pan, stereo width, filter cutoff, or modulation
- **Current**: Set to 0.5 (neutral)

### Loop Points (Columns 11-13)
- **Source**: WAV SMPL chunk (from auto-looping)
- **Format**: Normalized 0.0-1.0 positions
- **Loop Mode**: Only enabled if WAV contains loop points
- **Auto-Detection**: Reads loop markers from sample files

### Track Pitch (Column 16)
- **Verified**: 0=off (no key tracking), 1=on (follow keys)
- **Hardware**: Shows as "track pitch: no/yes"
- **Default**: 1 (enabled) for musical samples

## Round-Robin Algorithm Discovery

Based on filename patterns in test files:

### Round-Robin Types
- **Standard**: `rule roundrobin` - Sequential playback
- **Random**: `rule random` - Random selection
- **Reverse**: `rule reverse roundrobin` - Reverse order

### Loop Direction vs Round-Robin  
- **Loop Direction**: Controls sample playback direction
- **"Loop Ping Pong"**: Actually refers to round-robin algorithm, not loop mode

## MIDI Control Integration

### Per-Layer MIDI Commands
```yaml
velocity_midi_control:
  - layer: 0
    cc_messages: {7: 0}        # CC7 (volume)
    cc14_messages: {1: 8192}   # CC1 (14-bit mod wheel)  
    nrpn_messages: {45: 164}   # NRPN 45 (device-specific)
    program_change: 1          # Program change
    sysex_messages: ["43 10 7F 1C 00"]  # SysEx (no F0/F7)
```

### MIDI Message Types
- **CC (7-bit)**: Standard MIDI controllers (0-127)
- **CC14 (14-bit)**: High-resolution controllers (0-16383)  
- **NRPN**: Non-Registered Parameter Numbers (device-specific)
- **Program Change**: Preset selection (0-127)
- **SysEx**: System Exclusive messages (hex strings)

## Audio Processing Features

### Auto-Loop Detection
- **Source**: Analyzes audio waveforms for loop points
- **Method**: Correlation analysis and zero-crossing detection
- **Output**: SMPL chunk with loop markers in WAV files
- **Integration**: Automatically used in Column 11-13

### Silence Trimming
- **Mode**: Post-processing only (preserves original recording)
- **Algorithm**: Energy-based detection with configurable thresholds
- **Control**: `--trim_silence` flag or YAML config

### Normalization
- **Range**: Audio data always [-1.0, 1.0] float32
- **Source**: Converts from various input formats
- **Metadata**: MIDI note stored in WAV RIFF chunks

## File Format Support

### Native Format: SFZ
```sfz
<group>
lovel=1 hivel=127
volume=0.0

<region>
sample=sample.wav
key=60
lokey=60 hikey=60
```

### Export Formats
- **MAP**: Plain text sample maps (Waldorf native)
- **QPAT**: Binary header + text maps (Waldorf preset format)
- **SFZ**: Standard sampler format (always generated)

## Hardware Constraints

### Waldorf Limits
- **Maximum Groups**: 3 (velocity/round-robin layers)
- **Maximum Samples**: 128 per map
- **Memory Limit**: ~360MB total RAM for 32-bit float
- **Audio Format**: Prefers 44.1kHz, 32-bit float

### File Organization
```
output/
└── MySynth/
    ├── MySynth.sfz          # Generated SFZ
    ├── MySynth.map          # Waldorf MAP
    ├── MySynth.qpat         # Waldorf QPAT
    ├── my_script.yaml       # Auto-copied script
    └── samples/             # WAV files with metadata
        ├── MySynth_60_v127_rr0.wav
        └── ...
```

## Testing and Validation

### Hardware Testing Files
- `output/waldorf_column_tests/` - Individual column tests
- `output/complete_test/` - All 16 columns in one file
- `output/hardware_test/` - Volume difference verification

### Test Strategy
1. **Column Mapping**: Individual parameter verification
2. **Volume Levels**: -12dB, 0dB, +6dB gain tests
3. **Key Ranges**: Multi-note spread verification
4. **Velocity Layers**: Multiple dynamic levels
5. **Round-Robin**: Variation switching tests

## Implementation Notes

### Critical Fixes Applied
- ✅ **Column 5**: Fixed gain calculation (was tune, now dB→linear)
- ✅ **SFZ Parser**: Handles multiple parameters per line
- ✅ **MIDI Integration**: Per-layer control commands
- ✅ **Auto-Loop**: WAV SMPL chunk integration

### Remaining Questions
- ❓ **Column 8**: What parameter does this control?
- ❓ **Columns 14-15**: Verify direction and crossfade behavior
- ❓ **Sample Counts**: Are loop positions normalized or raw?

---

*Documentation updated: January 16, 2026*  
*Based on: Hardware testing + reverse engineering*  
*Status: Column 5 fix verified and implemented*