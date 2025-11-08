# AutosamplerT - MIDI Control Messages Guide

This guide explains how to use MIDI control messages (CC, Program Change, and SysEx) in AutosamplerT, including advanced per-layer control for velocity and round-robin sampling.

## Table of Contents

1. [Basic MIDI Control](#basic-midi-control)
2. [Per-Velocity-Layer Control](#per-velocity-layer-control)
3. [Per-Round-Robin-Layer Control](#per-round-robin-layer-control)
4. [Combined Layer Control](#combined-layer-control)
5. [SysEx Messages](#sysex-messages)
6. [Practical Use Cases](#practical-use-cases)
7. [Configuration Reference](#configuration-reference)

---

## Basic MIDI Control

### Command Line Usage

Send MIDI messages before sampling begins:

```bash
# Send Program Change
python autosamplerT.py --program_change 10

# Send CC messages
python autosamplerT.py --cc_messages '{"7":127,"10":64,"74":80}'

# Combine both
python autosamplerT.py --program_change 5 --cc_messages '{"7":127}'
```

### Script YAML Configuration

Create a script file `conf/basic_midi.yaml`:

```yaml
sampling_midi:
  # Global MIDI settings (sent once at start)
  program_change: 10          # Load program/patch 10
  cc_messages:
    7: 127                    # Volume: maximum
    10: 64                    # Pan: center
    74: 80                    # Filter cutoff: half open
  
  # Sampling settings
  note_range: {start: 36, end: 96, interval: 1}
  velocity_layers: 1
  roundrobin_layers: 1
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
sampling_midi:
  note_range: {start: 36, end: 84, interval: 1}
  velocity_layers: 4
  roundrobin_layers: 1
  
  # Global setup (sent once)
  program_change: 8
  
  # Per-velocity-layer MIDI control
  velocity_midi_control:
    - velocity_layer: 0       # Softest layer (ppp)
      midi_channel: 0
      cc_messages:
        74: 20                # Filter: mostly closed
        71: 30                # Resonance: low
        11: 40                # Expression: soft
    
    - velocity_layer: 1       # Medium-soft (mp)
      midi_channel: 0
      cc_messages:
        74: 60                # Filter: half open
        71: 50                # Resonance: medium
        11: 70                # Expression: medium
    
    - velocity_layer: 2       # Medium-loud (mf)
      midi_channel: 0
      cc_messages:
        74: 100               # Filter: mostly open
        71: 70                # Resonance: higher
        11: 100               # Expression: strong
    
    - velocity_layer: 3       # Loudest (fff)
      midi_channel: 0
      cc_messages:
        74: 127               # Filter: fully open
        71: 90                # Resonance: maximum
        11: 127               # Expression: maximum
```

**Execution Flow:**
```
1. Send global Program Change 8
2. For each note:
   a. Set velocity layer 0 → Send CC 74=20, 71=30, 11=40 → Sample note at soft velocity
   b. Set velocity layer 1 → Send CC 74=60, 71=50, 11=70 → Sample note at medium velocity
   c. Set velocity layer 2 → Send CC 74=100, 71=70, 11=100 → Sample note at loud velocity
   d. Set velocity layer 3 → Send CC 74=127, 71=90, 11=127 → Sample note at maximum velocity
```

### Use Case: Different Waveforms per Layer

```yaml
sampling_midi:
  note_range: {start: 24, end: 96, interval: 1}
  velocity_layers: 3
  
  velocity_midi_control:
    - velocity_layer: 0
      program_change: 10      # Sine wave patch
    
    - velocity_layer: 1
      program_change: 11      # Triangle wave patch
    
    - velocity_layer: 2
      program_change: 12      # Sawtooth wave patch
```

---

## Per-Round-Robin-Layer Control

### Use Case: Multiple Patches for Variation

Sample different synth programs as round-robin variations to create more realistic instruments.

**Configuration:** `conf/roundrobin_patches.yaml`

```yaml
sampling_midi:
  note_range: {start: 48, end: 72, interval: 1}
  velocity_layers: 2
  roundrobin_layers: 3
  
  # Per-round-robin-layer control
  roundrobin_midi_control:
    - roundrobin_layer: 0
      midi_channel: 0
      program_change: 20      # Piano patch 1
      cc_messages:
        7: 127                # Full volume
        91: 40                # Reverb depth
    
    - roundrobin_layer: 1
      midi_channel: 0
      program_change: 21      # Piano patch 2 (slightly different)
      cc_messages:
        7: 125                # Slightly lower volume for variation
        91: 45                # Slightly more reverb
    
    - roundrobin_layer: 2
      midi_channel: 0
      program_change: 22      # Piano patch 3 (bright)
      cc_messages:
        7: 124
        91: 35                # Less reverb for brighter sound
```

**Execution Flow:**
```
For each note:
  For each velocity layer:
    1. Set RR layer 0 → Send PC=20, CC 7=127, 91=40 → Sample note
    2. Set RR layer 1 → Send PC=21, CC 7=125, 91=45 → Sample note
    3. Set RR layer 2 → Send PC=22, CC 7=124, 91=35 → Sample note
```

### Use Case: Different MIDI Channels per Layer

Route different round-robin layers to different MIDI channels (useful for multi-timbral setups):

```yaml
sampling_midi:
  note_range: {start: 36, end: 60, interval: 1}
  velocity_layers: 1
  roundrobin_layers: 4
  
  roundrobin_midi_control:
    - roundrobin_layer: 0
      midi_channel: 0         # Channel 1
      program_change: 1
    
    - roundrobin_layer: 1
      midi_channel: 1         # Channel 2
      program_change: 2
    
    - roundrobin_layer: 2
      midi_channel: 2         # Channel 3
      program_change: 3
    
    - roundrobin_layer: 3
      midi_channel: 3         # Channel 4
      program_change: 4
```

---

## Combined Layer Control

### Use Case: Filter per Velocity + Patches per Round-Robin

Combine both types of layer control for maximum flexibility.

**Configuration:** `conf/combined_layers.yaml`

```yaml
sampling_midi:
  note_range: {start: 36, end: 72, interval: 1}
  velocity_layers: 3
  roundrobin_layers: 2
  
  # Global setup
  program_change: null
  cc_messages:
    93: 64                    # Chorus depth
  
  # Velocity control: Filter sweep
  velocity_midi_control:
    - velocity_layer: 0
      cc_messages:
        74: 40                # Filter: closed
    
    - velocity_layer: 1
      cc_messages:
        74: 80                # Filter: half
    
    - velocity_layer: 2
      cc_messages:
        74: 127               # Filter: open
  
  # Round-robin control: Different patches
  roundrobin_midi_control:
    - roundrobin_layer: 0
      program_change: 10      # Bright patch
      cc_messages:
        10: 50                # Pan left
    
    - roundrobin_layer: 1
      program_change: 11      # Dark patch
      cc_messages:
        10: 78                # Pan right
```

**Execution Flow:**
```
1. Send global CC 93=64 (chorus)
2. For note 36:
   Velocity 0:
     - Send CC 74=40 (filter for vel 0)
     - RR 0: Send PC=10, CC 10=50 → Sample C1_v20_rr0
     - RR 1: Send PC=11, CC 10=78 → Sample C1_v20_rr1
   Velocity 1:
     - Send CC 74=80 (filter for vel 1)
     - RR 0: Send PC=10, CC 10=50 → Sample C1_v73_rr0
     - RR 1: Send PC=11, CC 10=78 → Sample C1_v73_rr1
   Velocity 2:
     - Send CC 74=127 (filter for vel 2)
     - RR 0: Send PC=10, CC 10=50 → Sample C1_v127_rr0
     - RR 1: Send PC=11, CC 10=78 → Sample C1_v127_rr1
3. Move to next note...
```

**Priority:** Round-robin settings override velocity settings for the same parameters.

---

## SysEx Messages

### What is SysEx?

System Exclusive (SysEx) messages allow deep control of synthesizer parameters that aren't available via CC messages.

### Format

SysEx messages are hex strings that must:
- Start with `F0` (SysEx start)
- End with `F7` (SysEx end)
- Contain manufacturer-specific data in between

### Basic SysEx Configuration

```yaml
sampling_midi:
  note_range: {start: 36, end: 96, interval: 1}
  
  # Global SysEx messages
  sysex_messages:
    - "F0 43 10 7F 1C 00 00 00 01 F7"   # Yamaha: Set parameter
    - "F0 41 10 00 00 00 20 12 F7"      # Roland: Set mode
```

### SysEx per Layer

**Velocity layer example:**

```yaml
sampling_midi:
  velocity_layers: 3
  
  velocity_midi_control:
    - velocity_layer: 0
      sysex_messages:
        - "F0 43 10 7F 1C 00 00 00 01 F7"   # Yamaha: Soft timbre
    
    - velocity_layer: 1
      sysex_messages:
        - "F0 43 10 7F 1C 00 00 00 02 F7"   # Yamaha: Medium timbre
    
    - velocity_layer: 2
      sysex_messages:
        - "F0 43 10 7F 1C 00 00 00 03 F7"   # Yamaha: Bright timbre
```

**Round-robin layer example:**

```yaml
sampling_midi:
  roundrobin_layers: 2
  
  roundrobin_midi_control:
    - roundrobin_layer: 0
      sysex_messages:
        - "F0 41 10 00 00 00 20 12 00 F7"   # Roland: Setup A
    
    - roundrobin_layer: 1
      sysex_messages:
        - "F0 41 10 00 00 00 20 12 01 F7"   # Roland: Setup B
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

## Practical Use Cases

### 1. Multi-Mode Synthesizer Sampling

Sample all oscillator modes of a synth:

```yaml
sampling_midi:
  roundrobin_layers: 4
  
  roundrobin_midi_control:
    - roundrobin_layer: 0
      cc_messages: {70: 0}      # Waveform: Sine
    - roundrobin_layer: 1
      cc_messages: {70: 42}     # Waveform: Triangle
    - roundrobin_layer: 2
      cc_messages: {70: 84}     # Waveform: Sawtooth
    - roundrobin_layer: 3
      cc_messages: {70: 127}    # Waveform: Square
```

### 2. Modulation Wheel Layers

Sample different modulation wheel positions:

```yaml
sampling_midi:
  velocity_layers: 5
  
  velocity_midi_control:
    - velocity_layer: 0
      cc_messages: {1: 0}       # Mod wheel: 0%
    - velocity_layer: 1
      cc_messages: {1: 32}      # Mod wheel: 25%
    - velocity_layer: 2
      cc_messages: {1: 64}      # Mod wheel: 50%
    - velocity_layer: 3
      cc_messages: {1: 96}      # Mod wheel: 75%
    - velocity_layer: 4
      cc_messages: {1: 127}     # Mod wheel: 100%
```

### 3. Multi-Timbral Drum Machine

Sample different drum sounds using different MIDI channels:

```yaml
sampling_midi:
  note_range: {start: 36, end: 51, interval: 1}  # GM drum notes
  roundrobin_layers: 3
  
  roundrobin_midi_control:
    - roundrobin_layer: 0
      midi_channel: 0         # Kit 1
      program_change: 0
    - roundrobin_layer: 1
      midi_channel: 1         # Kit 2
      program_change: 8
    - roundrobin_layer: 2
      midi_channel: 2         # Kit 3
      program_change: 16
```

### 4. Expression + Filter Layers

Combine expression and filter for natural dynamics:

```yaml
sampling_midi:
  velocity_layers: 4
  
  velocity_midi_control:
    - velocity_layer: 0       # ppp
      cc_messages:
        11: 30                # Expression
        74: 20                # Filter
        7: 100                # Volume
    
    - velocity_layer: 1       # mp
      cc_messages:
        11: 60
        74: 60
        7: 110
    
    - velocity_layer: 2       # mf
      cc_messages:
        11: 90
        74: 100
        7: 120
    
    - velocity_layer: 3       # fff
      cc_messages:
        11: 127
        74: 127
        7: 127
```

---

## Configuration Reference

### Structure Overview

```yaml
sampling_midi:
  # Global MIDI settings (sent once at start)
  midi_channels: [0]              # Default channel(s)
  program_change: null            # Global program change (0-127)
  cc_messages: {}                 # Global CC messages {cc_num: value}
  sysex_messages: []              # Global SysEx messages
  
  # Sampling configuration
  note_range: {start: 36, end: 96, interval: 1}
  velocity_layers: 1              # Number of velocity layers
  roundrobin_layers: 1            # Number of round-robin layers
  
  # Per-velocity-layer control (optional)
  velocity_midi_control:
    - velocity_layer: 0           # Layer index (0, 1, 2, ...)
      midi_channel: 0             # MIDI channel for this layer
      program_change: null        # Program change for this layer
      cc_messages: {}             # CC messages for this layer
      sysex_messages: []          # SysEx for this layer
  
  # Per-round-robin-layer control (optional)
  roundrobin_midi_control:
    - roundrobin_layer: 0         # Layer index (0, 1, 2, ...)
      midi_channel: 0             # MIDI channel for this layer
      program_change: null        # Program change for this layer
      cc_messages: {}             # CC messages for this layer
      sysex_messages: []          # SysEx for this layer
```

### Common CC Numbers

| CC # | Parameter | Range |
|------|-----------|-------|
| 1 | Modulation Wheel | 0-127 |
| 7 | Volume | 0-127 |
| 10 | Pan | 0 (left) - 64 (center) - 127 (right) |
| 11 | Expression | 0-127 |
| 64 | Sustain Pedal | 0 (off) - 127 (on) |
| 71 | Resonance (Filter Q) | 0-127 |
| 74 | Filter Cutoff (Brightness) | 0-127 |
| 91 | Reverb Depth | 0-127 |
| 93 | Chorus Depth | 0-127 |

### Execution Order

1. **Global setup** (once at start):
   - SysEx messages
   - CC messages
   - Program Change

2. **For each note**:
   - **For each velocity layer**:
     - Send velocity layer SysEx (if defined)
     - Send velocity layer CC (if defined)
     - Send velocity layer Program Change (if defined)
     - Wait 100ms (for program change to settle)
     - **For each round-robin layer**:
       - Send round-robin layer SysEx (if defined)
       - Send round-robin layer CC (if defined)
       - Send round-robin layer Program Change (if defined)
       - Wait 100ms (for program change to settle)
       - **Sample the note**

### Priority Rules

When the same parameter is defined at multiple levels:
1. **Round-robin layer** settings (highest priority)
2. **Velocity layer** settings
3. **Global** settings (lowest priority)

---

## Tips and Best Practices

1. **Test with `--test_mode` first:**
   ```bash
   python autosamplerT.py --script conf/my_config.yaml --test_mode
   ```
   This shows MIDI messages without recording.

2. **Use delay between layers:** Complex synths may need time to respond. The default 100ms delay after Program Change is usually sufficient.

3. **Start simple:** Test with one velocity layer and one round-robin first, then expand.

4. **Document your CC mappings:** Different synths use different CC numbers. Keep notes in your YAML files.

5. **Backup your recordings:** Before processing, always backup with `--backup`:
   ```bash
   python autosamplerT.py --process "MySynth" --patch_normalize --backup
   ```

6. **Monitor the first note:** Watch the first note being sampled to verify MIDI messages are working correctly.

7. **Use descriptive multisample names:**
   ```yaml
   multisample_name: "MoogSub37_FilterSweep_4vel_2rr"
   ```

---

## Troubleshooting

**Problem:** MIDI messages not sent
- Check MIDI output device is configured: `python autosamplerT.py --setup`
- Verify synth is receiving MIDI (check its display/LEDs)
- Try test mode to see logged MIDI messages

**Problem:** Program Change not switching patches
- Ensure synth is in the correct mode (some need "Program Change Enable")
- Check program number range (some synths use 0-127, others 1-128)
- Increase pause time: `pause_time: 1.0` in sampling section

**Problem:** CC messages not working
- Verify CC numbers are correct for your synth (check manual)
- Some CCs require specific value ranges
- Try sending CC manually via MIDI monitor tool first

**Problem:** SysEx not working
- Verify exact hex format from synth manual
- Check manufacturer ID is correct
- Ensure synth is in mode that accepts SysEx
- Add longer delays after SysEx: increase `pause_time`

---

## Examples Repository

Find more example configurations in `conf/examples/`:
- `basic_cc.yaml` - Simple CC message example
- `velocity_filter_sweep.yaml` - Filter per velocity layer
- `roundrobin_patches.yaml` - Multiple patches per layer
- `combined_advanced.yaml` - Complex multi-layer setup
- `multitimbral_drums.yaml` - Multi-channel drum sampling

---

For more information, see:
- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [IMPLEMENTATION.md](IMPLEMENTATION.md) - Technical details
- [autosamplerT_script.yaml](conf/autosamplerT_script.yaml) - Full config template
