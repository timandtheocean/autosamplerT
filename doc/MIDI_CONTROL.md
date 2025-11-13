# MIDI Control Guide

Complete guide to MIDI control features in AutosamplerT - enabling advanced sampling workflows with per-layer CC, Program Change, and SysEx messages.

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Basic MIDI Control](#basic-midi-control)
4. [Per-Velocity-Layer Control](#per-velocity-layer-control)
5. [Per-Round-Robin-Layer Control](#per-round-robin-layer-control)
6. [Patch Iteration](#patch-iteration)
7. [Combined Layer Control](#combined-layer-control)
8. [SysEx Messages](#sysex-messages)
9. [MIDI Message Delay](#midi-message-delay)
10. [Practical Use Cases](#practical-use-cases)
11. [Configuration Reference](#configuration-reference)
12. [Testing and Verification](#testing-and-verification)
13. [Tips and Best Practices](#tips-and-best-practices)
14. [Troubleshooting](#troubleshooting)

---

## Overview

AutosamplerT provides comprehensive MIDI control capabilities for per-layer MIDI message transmission. This enables advanced sampling workflows where different MIDI messages (CC, Program Change, SysEx) are sent before each sample, allowing you to capture different synth settings, patches, or parameters per velocity or round-robin layer.

**What you can do:**
- Send different CC values per velocity layer (e.g., filter sweep)
- Switch patches per round-robin layer (e.g., multiple piano samples)
- Control synthesis parameters via SysEx per layer
- Add configurable delays for hardware processing time
- Combine multiple message types for complex workflows

---

## Key Features

### 1. Per-Layer MIDI Control
- **Velocity Layer MIDI**: Send different MIDI messages for each velocity layer
- **Round-Robin Layer MIDI**: Send different MIDI messages for each round-robin layer
- Support for 7-bit CC, 14-bit CC, Program Change, and SysEx messages

### 2. Message Types Supported
- **CC (Control Change)**: 7-bit messages (0-127)
- **CC14 (14-bit CC)**: High-resolution control with MSB/LSB
- **Program Change**: Switch patches/programs (0-127)
- **SysEx**: Manufacturer-specific parameter control

### 3. SysEx Structured Format
- **Structured format**: `{header: "43 10 7F", controller: "10", value: 64}` - User-friendly format with automatic hex conversion
- **Header reuse**: Omit header key to reuse previous header across messages in same layer
- **Raw format**: `{raw: "43 10 7F 13 7F"}` - Direct hex bypass for complex messages
- **Value validation**: Automatic 0-127 range checking with error logging
- **Auto-wrapping**: Automatic F0/F7 framing added to all messages
- **Cross-layer state**: Header persists between layers for easy configuration

### 4. MIDI Message Delay
- Configurable delay between MIDI message transmission and note-on
- Gives hardware synths time to process CC/PC/SysEx changes before note triggers
- Parameter: `midi_message_delay` (seconds) in `sampling_midi` section

### 5. Pre-Sampling Summary
- Interactive summary display before sampling starts
- Shows MIDI control configuration per layer (CC, SysEx, Program Changes)
- Estimates: Total duration (minutes) and disk space (MB)
- User confirmation prompt to proceed or cancel

### 6. Enhanced MIDI Setup
- Improved MIDI device selection with fuzzy matching
- Support for device name substring matching
- Skip option for input/output selection
- Validation status display (OK/SKIPPED/NOT FOUND)

### 7. Separate Setup Modes
- `--setup audio`: Audio configuration only
- `--setup midi`: MIDI configuration only  
- `--setup all`: Both audio and MIDI (default)

### 8. Enhanced Logging
- All MIDI messages log at INFO level (visible in standard output)
- CC, CC14, Program Change, and SysEx messages fully logged
- Layer configuration loading status displayed
- Timing information logged at startup

---

## Basic MIDI Control

### Command Line Usage

Send MIDI messages before sampling begins:

```bash
# Send Program Change
python autosamplerT.py --program_change 10

# Send 7-bit CC messages
# Format: "cc,value;cc,value;cc,value"
python autosamplerT.py --cc_messages "7,127;10,64;74,80"

# Send 14-bit CC messages (high-resolution)
# Format: "cc,msb,lsb;cc,msb,lsb"
python autosamplerT.py --cc14_messages "1,64,0;11,100,50"

# Send SysEx messages (without F0/F7 - added automatically)
# Semicolon separates multiple messages
python autosamplerT.py --sysex_messages "43 10 7F 1C 00;41 10 00 20 12"

# Combine multiple message types
python autosamplerT.py --program_change 5 --cc_messages "7,127;74,64"

# Complete example with all types
python autosamplerT.py \
  --program_change 10 \
  --cc_messages "7,127;10,64;74,80" \
  --cc14_messages "1,64,0" \
  --sysex_messages "43 10 7F 1C 00"
```

**Format Details:**

| Argument | Format | Example |
|----------|--------|---------|
| `--program_change` | Single number (0-127) | `10` |
| `--cc_messages` | `"cc,value;cc,value"` | `"7,127;10,64;74,80"` |
| `--cc14_messages` | `"cc,msb,lsb;cc,msb,lsb"` | `"1,64,0;11,100,50"` |
| `--sysex_messages` | `"data bytes;data bytes"` (no F0/F7) | `"43 10 7F 1C 00;41 10 00 20 12"` |

**Platform Notes:**
- **Windows PowerShell:** Use double quotes (`"`) for all arguments
- **Linux/Mac:** Use single quotes (`'`) or double quotes (`"`)
- **Semicolons (`;`)** separate multiple messages (CC, CC14, SysEx)
- **Spaces** separate hex bytes in SysEx messages
- **SysEx wrappers:** F0 and F7 are added automatically - just provide data bytes

### Script YAML Configuration

Create a script file `conf/basic_midi.yaml`:

```yaml
multisample_name: "BasicMIDI_Test"

sampling_midi:
  # Global MIDI settings (sent once at start)
  program_change: 10          # Load program/patch 10
  cc_messages:
    7: 127                    # Volume: maximum
    10: 64                    # Pan: center
    74: 80                    # Filter cutoff: half open

sampling:
  # Sampling settings
  startNote: 36
  endNote: 96
  noteInterval: 1
  velocities: [100]
  rr_layers: 1
  hold: 1.0
  release: 0.5
  pause: 0.5
```

Run with:
```bash
python autosamplerT.py --script conf/basic_midi.yaml
```

**When messages are sent:**
- Program Change: Once at the start
- CC messages: Once at the start, in the order specified
- All messages are sent before any note sampling begins

---

## Per-Velocity-Layer Control

### Use Case: Dynamic Filter Sweep

Sample different filter cutoff values per velocity layer to create expressive velocity response.

**Configuration:** `conf/velocity_filter.yaml`

```yaml
multisample_name: "VelocityFilterSweep"

sampling_midi:
  midi_message_delay: 0.05
  
  # Per-velocity-layer MIDI control
  velocity_layers:
    - velocity: 40            # Softest layer (ppp)
      cc: 
        - {controller: 74, value: 20}    # Filter: mostly closed
        - {controller: 71, value: 30}    # Resonance: low
        - {controller: 11, value: 40}    # Expression: soft
    
    - velocity: 80            # Medium (mf)
      cc:
        - {controller: 74, value: 80}    # Filter: half open
        - {controller: 71, value: 50}    # Resonance: medium
        - {controller: 11, value: 80}    # Expression: medium
    
    - velocity: 120           # Loudest (fff)
      cc:
        - {controller: 74, value: 127}   # Filter: fully open
        - {controller: 71, value: 90}    # Resonance: maximum
        - {controller: 11, value: 127}   # Expression: maximum

sampling:
  startNote: 36
  endNote: 84
  noteInterval: 4
  rr_layers: 1
  hold: 2.0
  release: 1.5
  pause: 0.5
```

**Execution Flow:**
```
1. For each note:
   a. Set velocity layer 0 → Send CC 74=20, 71=30, 11=40 → Sample note at velocity 40
   b. Set velocity layer 1 → Send CC 74=80, 71=50, 11=80 → Sample note at velocity 80
   c. Set velocity layer 2 → Send CC 74=127, 71=90, 11=127 → Sample note at velocity 120
```

### Use Case: Different Waveforms per Layer

```yaml
sampling_midi:
  velocity_layers:
    - velocity: 40
      program_change: 10      # Sine wave patch
    
    - velocity: 80
      program_change: 11      # Triangle wave patch
    
    - velocity: 120
      program_change: 12      # Sawtooth wave patch

sampling:
  startNote: 24
  endNote: 96
  noteInterval: 3
  rr_layers: 1
```

---

## Per-Round-Robin-Layer Control

### Use Case: Multiple Patches for Variation

Sample different synth programs as round-robin variations to create more realistic instruments.

**Configuration:** `conf/roundrobin_patches.yaml`

```yaml
multisample_name: "RoundRobinPatches"

sampling_midi:
  midi_message_delay: 0.2    # Longer delay for program changes
  
  # Per-round-robin-layer control
  roundrobin_layers:
    - layer: 1
      program_change: 20      # Piano patch 1
      cc:
        - {controller: 7, value: 127}    # Full volume
        - {controller: 91, value: 40}    # Reverb depth
    
    - layer: 2
      program_change: 21      # Piano patch 2 (slightly different)
      cc:
        - {controller: 7, value: 125}    # Slightly lower volume
        - {controller: 91, value: 45}    # Slightly more reverb
    
    - layer: 3
      program_change: 22      # Piano patch 3 (bright)
      cc:
        - {controller: 7, value: 124}
        - {controller: 91, value: 35}    # Less reverb

sampling:
  startNote: 48
  endNote: 72
  noteInterval: 2
  velocities: [80, 120]
  hold: 2.0
  release: 2.0
  pause: 1.0
```

**Execution Flow:**
```
For each note:
  For each velocity layer:
    1. Set RR layer 1 → Send PC=20, CC 7=127, 91=40 → Sample note
    2. Set RR layer 2 → Send PC=21, CC 7=125, 91=45 → Sample note
    3. Set RR layer 3 → Send PC=22, CC 7=124, 91=35 → Sample note
```

### Use Case: CC Sweep per Round-Robin Layer

```yaml
sampling_midi:
  roundrobin_layers:
    - layer: 1
      cc: [{controller: 1, value: 10}]     # Mod wheel: 10
    - layer: 2
      cc: [{controller: 1, value: 50}]     # Mod wheel: 50
    - layer: 3
      cc: [{controller: 1, value: 90}]     # Mod wheel: 90
    - layer: 4
      cc: [{controller: 1, value: 127}]    # Mod wheel: 127
```

---

## Patch Iteration

[NEW] Sample multiple patches automatically with MIDI program changes. Instead of sampling one patch with multiple velocity/round-robin layers, you can sample many patches (e.g., all 128 programs) with the same note configuration.

### Key Features
- Automatic MIDI program change before each patch
- Automatic folder and multisample naming
- Separate SFZ file per patch
- Progress tracking and error handling
- Works from both CLI and YAML scripts

### Configuration

```yaml
name: "Sample All Patches"

# MIDI configuration
midi_interface:
  output_port_name: "Prophet 6"
  cc_messages: {7: 127}  # Full volume

# Sampling configuration
sampling:
  note_range_start: 36   # C2
  note_range_end: 84     # C5
  note_range_interval: 12  # One note per octave = 4 notes
  
  velocity_layers: 1
  roundrobin_layers: 1
  
  hold_time: 8.0
  release_time: 2.0

# Patch iteration - sample multiple programs
sampling_midi:
  patch_iteration:
    enabled: true
    program_start: 0      # First program to sample
    program_end: 19       # Last program to sample (inclusive)
    auto_naming: true     # Generate names automatically
    name_template: "Patch"  # Optional: default name prefix
```

### Automatic Naming

When `auto_naming: true`:
- **Patch_000** (program 0)
- **Patch_001** (program 1)
- **Patch_002** (program 2)
- ...
- **Patch_127** (program 127)

Each patch gets:
- Separate folder: `output/Patch_000/samples/`
- Separate SFZ: `output/Patch_000/Patch_000.sfz`
- All samples named: `Patch_000_C2_v127.wav`, etc.

### Execution Flow

```
Program 0:
  Send MIDI program change: 0
  Wait for midi_message_delay
  Sample notes: 36, 48, 60, 72 (4 notes)
  Generate SFZ: Patch_000.sfz

Program 1:
  Send MIDI program change: 1
  Wait for midi_message_delay
  Sample notes: 36, 48, 60, 72 (4 notes)
  Generate SFZ: Patch_001.sfz

... continues through program_end
```

### CLI Usage

Patch iteration is configured in YAML scripts only (not available as CLI arguments).

```bash
# Sample patches 0-19
python autosamplerT.py --script conf/sample_patches.yaml

# With postprocessing
python autosamplerT.py --script conf/sample_patches.yaml --auto_loop
```

### Use Cases

**1. Sample All Presets on a Synthesizer**
```yaml
sampling_midi:
  patch_iteration:
    enabled: true
    program_start: 0
    program_end: 127  # All 128 MIDI programs
    auto_naming: true
```

**2. Sample Specific Patch Range**
```yaml
sampling_midi:
  patch_iteration:
    enabled: true
    program_start: 8    # Bank 1, patches 9-16
    program_end: 15
    auto_naming: true
    name_template: "Bank1"  # Results: Bank1_008, Bank1_009, etc.
```

**3. Quick Multi-Patch Test**
```yaml
sampling_midi:
  patch_iteration:
    enabled: true
    program_start: 0
    program_end: 3      # Just 4 patches for testing
```

### Notes

- Patch iteration creates folders automatically (no manual creation needed)
- Each patch is independent - failure on one patch doesn't stop the others
- Progress is reported: "Program 5 (6/20)" shows current position
- Final summary shows success/failure count
- Works with all audio settings (ASIO, sample rate, bit depth, etc.)
- Compatible with postprocessing (`--auto_loop`, `--trim_silence`, etc.)

---

## Combined Layer Control

### Use Case: Filter per Velocity + Patches per Round-Robin

Combine both types of layer control for maximum flexibility.

**Configuration:** `conf/combined_layers.yaml`

```yaml
multisample_name: "CombinedLayers"

sampling_midi:
  midi_message_delay: 0.1
  
  # Velocity control: Filter sweep
  velocity_layers:
    - velocity: 40
      cc: [{controller: 74, value: 40}]    # Filter: closed
    
    - velocity: 80
      cc: [{controller: 74, value: 80}]    # Filter: half
    
    - velocity: 120
      cc: [{controller: 74, value: 127}]   # Filter: open
  
  # Round-robin control: Different patches
  roundrobin_layers:
    - layer: 1
      program_change: 10      # Bright patch
      cc: [{controller: 10, value: 50}]    # Pan left
    
    - layer: 2
      program_change: 11      # Dark patch
      cc: [{controller: 10, value: 78}]    # Pan right

sampling:
  startNote: 36
  endNote: 72
  noteInterval: 4
  hold: 1.5
  release: 1.0
  pause: 0.5
```

**Execution Flow:**
```
For note 36:
  Velocity 40:
    - Send CC 74=40 (filter for vel 40)
    - RR 1: Send PC=10, CC 10=50 → Sample C2_v40_rr1
    - RR 2: Send PC=11, CC 10=78 → Sample C2_v40_rr2
  Velocity 80:
    - Send CC 74=80 (filter for vel 80)
    - RR 1: Send PC=10, CC 10=50 → Sample C2_v80_rr1
    - RR 2: Send PC=11, CC 10=78 → Sample C2_v80_rr2
  Velocity 120:
    - Send CC 74=127 (filter for vel 120)
    - RR 1: Send PC=10, CC 10=50 → Sample C2_v120_rr1
    - RR 2: Send PC=11, CC 10=78 → Sample C2_v120_rr2
```

**Priority:** Round-robin settings override velocity settings for the same parameters.

---

## SysEx Messages

### What is SysEx?

System Exclusive (SysEx) messages allow deep control of synthesizer parameters that aren't available via CC messages. They provide manufacturer-specific control over synthesis engines.

### Structured Format (Recommended)

AutosamplerT provides a user-friendly structured format:

```yaml
sampling_midi:
  roundrobin_layers:
    # Layer 1: Full structured format with header
    - layer: 1
      sysex:
        - header: "43 10 7F"     # Manufacturer/device header
          controller: "10"        # Parameter number (hex)
          value: 0                # Parameter value (0-127)
    
    # Layer 2: Reuse header from layer 1
    - layer: 2
      sysex:
        - controller: "10"        # Header automatically reused
          value: 64
    
    # Layer 3: Multiple messages per layer
    - layer: 3
      sysex:
        - header: "43 10 7F"
          controller: "10"
          value: 100
        - controller: "11"        # Reuse header
          value: 100
        - controller: "12"        # Reuse header again
          value: 100
```

**Benefits:**
- Header defined once, reused automatically
- Clear parameter/value separation
- Automatic F0/F7 wrapping
- Value range validation (0-127)
- Error logging for invalid values

### Raw Format

For complex messages or custom protocols:

```yaml
sampling_midi:
  roundrobin_layers:
    - layer: 1
      sysex:
        - raw: "43 10 7F 13 7F"  # Direct hex (F0/F7 added automatically)
    
    - layer: 2
      sysex:
        - raw: "43 10 7F 14 40"  # Another raw message
```

### Velocity Layer SysEx Example

```yaml
sampling_midi:
  velocity_layers:
    - velocity: 40
      sysex:
        - header: "43 10 7F"
          controller: "1C"
          value: 1              # Soft timbre
    
    - velocity: 80
      sysex:
        - controller: "1C"
          value: 2              # Medium timbre
    
    - velocity: 120
      sysex:
        - controller: "1C"
          value: 3              # Bright timbre
```

### Finding SysEx Messages

Consult your synthesizer's manual for:
- MIDI Implementation Chart
- SysEx message format
- Parameter addresses
- Manufacturer ID

**Common manufacturer IDs:**
- Yamaha: `43`
- Roland: `41`
- Korg: `42`
- Moog: `04`
- Sequential: `01`

---

## MIDI Message Delay

### Purpose

Hardware synthesizers need time to process MIDI messages (especially Program Changes and SysEx). The `midi_message_delay` parameter adds a configurable delay between message transmission and note-on.

### Configuration

```yaml
sampling_midi:
  midi_message_delay: 0.1  # 100ms delay (default: 0.05)
```

### When to Adjust

**Shorter delays (0.01 - 0.05s):**
- Fast digital synths
- VST plugins
- Modern MIDI interfaces

**Medium delays (0.05 - 0.2s):**
- Most hardware synths (recommended)
- CC messages
- Standard processing time

**Longer delays (0.2 - 0.5s):**
- Analog synths with slow envelopes
- Program change patch switching
- Complex SysEx parameter changes
- Vintage gear

### Example with Delay

```yaml
sampling_midi:
  midi_message_delay: 0.15    # 150ms for analog synth
  
  roundrobin_layers:
    - layer: 1
      program_change: 10
      cc: [{controller: 74, value: 80}]
```

**Timing:**
```
Send Program Change → Wait 150ms → Send CC → Wait 150ms → Note-on
```

---

## Practical Use Cases

### 1. Multi-Mode Synthesizer Sampling

Sample all oscillator modes of a synth:

```yaml
sampling_midi:
  roundrobin_layers:
    - layer: 1
      cc: [{controller: 70, value: 0}]      # Waveform: Sine
    - layer: 2
      cc: [{controller: 70, value: 42}]     # Waveform: Triangle
    - layer: 3
      cc: [{controller: 70, value: 84}]     # Waveform: Sawtooth
    - layer: 4
      cc: [{controller: 70, value: 127}]    # Waveform: Square
```

### 2. Modulation Wheel Layers

Sample different modulation wheel positions:

```yaml
sampling_midi:
  velocity_layers:
    - velocity: 20
      cc: [{controller: 1, value: 0}]       # Mod wheel: 0%
    - velocity: 50
      cc: [{controller: 1, value: 32}]      # Mod wheel: 25%
    - velocity: 80
      cc: [{controller: 1, value: 64}]      # Mod wheel: 50%
    - velocity: 110
      cc: [{controller: 1, value: 96}]      # Mod wheel: 75%
    - velocity: 127
      cc: [{controller: 1, value: 127}]     # Mod wheel: 100%
```

### 3. Multi-Timbral Setup

Sample different sounds using different MIDI channels:

```yaml
sampling_midi:
  roundrobin_layers:
    - layer: 1
      midi_channel: 1         # Channel 1
      program_change: 0
    - layer: 2
      midi_channel: 2         # Channel 2
      program_change: 8
    - layer: 3
      midi_channel: 3         # Channel 3
      program_change: 16
```

### 4. Expression + Filter Layers

Combine expression and filter for natural dynamics:

```yaml
sampling_midi:
  velocity_layers:
    - velocity: 40            # ppp
      cc:
        - {controller: 11, value: 30}     # Expression
        - {controller: 74, value: 20}     # Filter
    
    - velocity: 80            # mf
      cc:
        - {controller: 11, value: 80}
        - {controller: 74, value: 80}
    
    - velocity: 120           # fff
      cc:
        - {controller: 11, value: 127}
        - {controller: 74, value: 127}
```

### 5. Yamaha DX7 Algorithm Sweep

```yaml
sampling_midi:
  midi_message_delay: 0.2
  
  roundrobin_layers:
    - layer: 1
      sysex:
        - header: "43 10 7F"
          controller: "10"      # Algorithm
          value: 0              # Algorithm 0
    - layer: 2
      sysex:
        - controller: "10"
          value: 10             # Algorithm 10
    - layer: 3
      sysex:
        - controller: "10"
          value: 20             # Algorithm 20
```

---

## Configuration Reference

### Structure Overview

```yaml
multisample_name: "MySynth_MultiSample"

sampling_midi:
  # MIDI message delay (seconds)
  midi_message_delay: 0.1
  
  # Velocity layers (different MIDI per velocity)
  velocity_layers:
    - velocity: 40
      cc: [{controller: 74, value: 30}]
      cc14: [{controller: 1, msb: 64, lsb: 0}]
      program_change: 0
      sysex:
        - {header: "43 10 7F", controller: "10", value: 64}
  
  # Round-robin layers (different MIDI per RR layer)
  roundrobin_layers:
    - layer: 1
      cc: [{controller: 1, value: 10}]
      program_change: 10
      sysex:
        - {raw: "43 10 7F 13 7F"}

sampling:
  startNote: 36
  endNote: 96
  noteInterval: 4
  velocities: [40, 80, 120]    # If not using velocity_layers
  rr_layers: 4
  hold: 2.0
  release: 2.0
  pause: 0.5
```

### Common CC Numbers

| CC # | Parameter | Range |
|------|-----------|-------|
| 1 | Modulation Wheel | 0-127 |
| 7 | Volume | 0-127 |
| 10 | Pan | 0 (left) - 64 (center) - 127 (right) |
| 11 | Expression | 0-127 |
| 64 | Sustain Pedal | 0 (off) - 127 (on) |
| 70 | Sound Controller 1 (Timbre/Waveform) | 0-127 |
| 71 | Resonance (Filter Q) | 0-127 |
| 74 | Filter Cutoff (Brightness) | 0-127 |
| 91 | Reverb Depth | 0-127 |
| 93 | Chorus Depth | 0-127 |

### Execution Order

1. **For each note**:
   - **For each velocity layer**:
     - Send velocity layer SysEx (if defined)
     - Send velocity layer CC (if defined)
     - Send velocity layer Program Change (if defined)
     - Wait `midi_message_delay` seconds
     - **For each round-robin layer**:
       - Send round-robin layer SysEx (if defined)
       - Send round-robin layer CC (if defined)
       - Send round-robin layer Program Change (if defined)
       - Wait `midi_message_delay` seconds
       - **Sample the note**

### Priority Rules

When the same parameter is defined at multiple levels:
1. **Round-robin layer** settings (highest priority)
2. **Velocity layer** settings
3. Layer settings override any global settings

---

## Testing and Verification

### Using Virtual MIDI for Testing

**Windows (loopMIDI):**
```bash
# 1. Install and create virtual port "loopMIDI Port 1"
# 2. Setup MIDI in AutosamplerT
python autosamplerT.py --setup midi
# Select: loopMIDI Port 1

# 3. Monitor MIDI in separate terminal
receivemidi dev "loopMIDI Port 1"

# 4. Run sampling
python autosamplerT.py --script conf/test/test_roundrobin_cc.yaml
```

**macOS (IAC Driver):**
```bash
# 1. Enable IAC Driver in Audio MIDI Setup
# 2. Setup MIDI
python autosamplerT.py --setup midi

# 3. Monitor with receivemidi
receivemidi dev "IAC Driver Bus 1"
```

### Test Scripts

Located in `conf/test/`:

- **`test_single_note.yaml`** - Basic single note test
- **`test_roundrobin_cc.yaml`** - 4 RR layers with different CC controllers
- **`test_velocity_cc.yaml`** - 5 velocity layers with CC74 brightness sweep
- **`test_cc1_sweep.yaml`** - 13 RR layers, CC1 sweep 1→121 step 10
- **`test_cc1_with_delay.yaml`** - CC1 sweep with 100ms delay
- **`test_sysex_structured.yaml`** - SysEx structured format with header reuse
- **`test_program_change.yaml`** - Program changes (0, 24, 40, 80)
- **`test_suite_full.yaml`** - Comprehensive test (3 velocity × 4 RR = 36 samples)

### Verified Features

 CC messages transmitted with correct values  
 CC messages sent before note-on  
 Configurable delay working correctly  
 All roundrobin layers execute in sequence  
 Velocity layer CC messages working  
 Program changes sent correctly  
 SysEx structured format with header reuse  
 SysEx raw format working  
 Multiple SysEx messages per layer  
 Comprehensive test suite successful (36 samples, 3×4 layers)  

### Log Output Example

```
INFO: Sampling range: Note 60-60, interval 1
INFO: Velocity layers: 1, Round-robin: 4
INFO: Timing: hold=0.50s, release=0.10s, pause=0.20s
INFO: Velocity MIDI config: 0 layers
INFO: Round-robin MIDI config: 4 layers
INFO: Applying MIDI settings for round-robin layer 1
INFO: MIDI Program Change: program=0, channel=1
INFO: MIDI CC sent: cc=1, value=10, channel=1
INFO: MIDI SysEx sent: F0 43 10 7F 10 00 F7
INFO: Sampling: Note=60, Vel=127, RR=1
INFO: Recorded sample: MySynth_C4_v127_rr1.wav
```

### Pre-Sampling Summary Example

```
=== Sampling Configuration Summary ===

Multisample: OP1_Test_Suite
Output Directory: output/OP1_Test_Suite/samples/

Notes to Sample: 3 notes (C4, C#4, D4)
Velocity Layers: 3 (40, 80, 120)
Round-Robin Layers: 4
Total Samples: 36

Estimated Duration: ~0.5 minutes
Estimated Disk Space: ~5.5 MB

Recording Parameters:
  Hold: 0.50s | Release: 0.10s | Pause: 0.30s | Total: 0.90s per sample

MIDI Configuration:
  Velocity Layer 1 (vel=40): CC74=30
  Velocity Layer 2 (vel=80): CC74=70
  Velocity Layer 3 (vel=120): CC74=110
  RR Layer 1: CC1=10, PC=0
  RR Layer 2: CC1=50, PC=1
  RR Layer 3: CC1=90
  RR Layer 4: CC1=127, SysEx: 1 message

Proceed with sampling? (y/n):
```

---

## Tips and Best Practices

### 1. Start Simple

Test with one velocity layer and one round-robin first, then expand:

```yaml
# Simple test first
velocities: [100]
rr_layers: 1

# Then expand
velocities: [40, 80, 120]
rr_layers: 4
```

### 2. Test with Virtual MIDI

Use virtual MIDI cables (loopMIDI, IAC Driver) and `receivemidi` to verify MIDI messages before sampling with hardware.

### 3. Monitor the First Sample

Watch the first note being sampled to verify:
- MIDI messages are sent correctly
- Timing is appropriate
- Hardware responds to messages

### 4. Use Appropriate Delays

- **Fast digital synths:** 0.05s
- **Most hardware:** 0.1s
- **Program changes:** 0.2s+
- **Analog synths:** 0.2-0.5s

### 5. Document Your CC Mappings

Different synths use different CC numbers. Add comments:

```yaml
sampling_midi:
  velocity_layers:
    - velocity: 40
      cc:
        - {controller: 74, value: 30}    # Filter cutoff (Moog: CC74)
        - {controller: 71, value: 40}    # Resonance (Moog: CC71)
```

### 6. Use Descriptive Names

```yaml
# Good
multisample_name: "MoogSub37_FilterSweep_4vel_2rr"

# Bad
multisample_name: "test2"
```

### 7. Organize Test Scripts

```
conf/
  test/                    # Test scripts
    test_single_note.yaml
    test_velocity_cc.yaml
  production/              # Production scripts
    synth_bass.yaml
    synth_lead.yaml
```

### 8. Review Pre-Sampling Summary

Always review the summary before proceeding:
- Verify sample count is correct
- Check estimated duration and disk space
- Confirm MIDI configuration matches intent

### 9. Use Skip for Unchanged Devices

When running `--setup midi`, use `skip` to keep current devices:

```
Enter MIDI output port (or 'skip'): skip
✓ Keeping current MIDI output: OP-1 1
```

### 10. Combine with Other Features

MIDI control works seamlessly with:
- Pre-sampling summary
- Post-processing (normalization, trimming)
- SFZ generation with velocity/RR layers

---

## Troubleshooting

### Problem: MIDI messages not sent

**Solutions:**
- Check MIDI output device is configured: `python autosamplerT.py --setup midi`
- Verify synth is receiving MIDI (check its display/LEDs)
- Check MIDI cable connections
- Review INFO logs - MIDI messages should be visible

### Problem: Program Change not switching patches

**Solutions:**
- Ensure synth is in the correct mode (some need "Program Change Enable")
- Check program number range (some synths use 0-127, others 1-128)
- Increase `midi_message_delay`: `midi_message_delay: 0.5`
- Increase pause time: `pause: 1.0` in sampling section

### Problem: CC messages not working

**Solutions:**
- Verify CC numbers are correct for your synth (check manual)
- Some CCs require specific value ranges
- Try sending CC manually via MIDI monitor tool first
- Check if synth has CC learn mode

### Problem: SysEx not working

**Solutions:**
- Verify exact hex format from synth manual
- Check manufacturer ID is correct
- Ensure synth is in mode that accepts SysEx (some have SysEx enable/disable)
- Add longer delays: `midi_message_delay: 0.3`
- Try raw format instead of structured format
- Use MIDI monitor to verify exact bytes sent

### Problem: Delay too short/long

**Solutions:**
- Adjust `midi_message_delay` for your hardware
- Fast digital synths: 0.05s
- Most hardware: 0.1-0.2s
- Analog synths: 0.2-0.5s
- Listen to first few samples - if sound changes mid-note, increase delay

### Problem: Wrong velocity or RR layer

**Solutions:**
- Check layer numbering (1-based in YAML)
- Verify `velocities` matches `velocity_layers` count
- Verify `rr_layers` matches `roundrobin_layers` count
- Review pre-sampling summary for layer configuration

### Problem: Header not reusing in SysEx

**Solutions:**
- Ensure first message in first layer has `header` key
- Omit `header` key in subsequent messages to reuse
- Header persists across layers automatically
- Use raw format if structured format causes issues

### Problem: MIDI setup keeps resetting

**Solutions:**
- Don't use `skip` - select the device explicitly
- Check `conf/autosamplerT_config.yaml` has correct device names
- Use fuzzy matching: partial device names work
- Verify device is powered on and connected

---

## Related Documentation

- [Setup & Configuration](SETUP.md) - MIDI device configuration
- [Scripting System](SCRIPTING.md) - YAML script structure
- [CLI Documentation](CLI.md) - Command-line interface
- [Sampling Engine](SAMPLING.md) - Recording parameters

---

## Technical Implementation

### Modified Files

**Core files:**
- `autosamplerT.py` - Added sampling_midi to merge sections, --setup sub-modes
- `src/sampler.py` - midi_message_delay support, pre-sampling summary
- `src/sampler_midicontrol.py` - Enhanced logging, structured SysEx parsing, header state
- `src/set_midi_config.py` - Complete rewrite with fuzzy matching

### SysEx Format Parsing

The `parse_sysex_messages()` function handles three input formats:
1. **Structured**: Dict with `header`, `controller`, `value` keys
2. **Raw**: Dict with `raw` key for direct hex input
3. **Legacy**: Plain strings (backward compatible)

Header state is tracked in `MIDIController.sysex_header_state` and passed between parsing calls, allowing header reuse across layers without repeating the manufacturer/device ID in every message.

### File Size Estimation

```python
file_size = samples × samplerate × duration × channels × (bitdepth/8)
```

### Duration Estimation

```python
duration = total_samples × (hold + release + pause)
```

---

*Last updated: November 11, 2025*
