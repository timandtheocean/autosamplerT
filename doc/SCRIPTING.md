# Scripting System

Guide to YAML-based scripting for automated sampling workflows in AutosamplerT.

## Overview

AutosamplerT uses YAML scripts to define sampling sessions. Scripts allow you to:
- Define note ranges and intervals
- Configure velocity and round-robin layers
- Set recording parameters
- Configure per-layer MIDI messages
- Create reusable sampling templates
- Test different configurations

## What It's Used For

- **Automated sampling**: Define complex multi-layer sampling sessions
- **MIDI control**: Send different MIDI messages per layer
- **Testing**: Quickly test different configurations
- **Batch sampling**: Create multiple variations of a sampling session
- **Documentation**: Script files serve as documentation of sampling parameters

## Script vs Config

### Config File (`conf/autosamplerT_config.yaml`)
- Device configuration (audio/MIDI)
- System settings
- Persistent across sessions
- Modified by `--setup`

### Script File (`conf/*.yaml`)
- Sampling parameters
- MIDI messages
- Note ranges and layers
- Session-specific
- Executed with `--script`

## Script Structure

### Complete Example

```yaml
# Multisample name and output location
multisample_name: "MySynth_MultiSample"

# Audio interface settings (optional, merges with config)
audio_interface:
  input_device_idx: 1
  output_device_idx: 4
  sample_rate: 48000
  sample_width: 24

# MIDI interface settings (optional, merges with config)
midi_interface:
  input_port: "OP-1 0"
  output_port: "OP-1 1"

# MIDI messages for sampling (NEW - per-layer control)
sampling_midi:
  # Delay between MIDI message and note-on (seconds)
  midi_message_delay: 0.1
  
  # Velocity layers (different MIDI per velocity)
  velocity_layers:
    - velocity: 40
      cc: [{controller: 74, value: 30}]
      program_change: 0
    - velocity: 80
      cc: [{controller: 74, value: 70}]
      program_change: 0
    - velocity: 120
      cc: [{controller: 74, value: 110}]
      program_change: 0
  
  # Round-robin layers (different MIDI per RR layer)
  roundrobin_layers:
    - layer: 1
      cc: [{controller: 1, value: 10}]
    - layer: 2
      cc: [{controller: 1, value: 50}]
    - layer: 3
      cc: [{controller: 1, value: 90}]
    - layer: 4
      cc: [{controller: 1, value: 127}]

# Sampling configuration
sampling:
  # Note range
  startNote: 36  # C2
  endNote: 96    # C7
  noteInterval: 4  # Sample every 4 semitones
  
  # Velocity layers (if not using sampling_midi.velocity_layers)
  velocities: [40, 80, 120]  # ppp, mf, fff
  
  # Round-robin layers
  rr_layers: 4
  
  # Recording parameters
  hold: 2.0      # Hold note for 2 seconds
  release: 2.0   # Record release for 2 seconds
  pause: 0.5     # Pause between samples
  
  # MIDI settings
  note_on_velocity: 100
  midi_channel: 1
  note_duration: 2.0
```

## YAML Sections

### 1. Multisample Name

```yaml
multisample_name: "MySynth_Pad"
```

**Purpose:** Names the output folder and SFZ file.

**Output location:** `output/MySynth_Pad/`

**Files created:**
- `MySynth_Pad.sfz`
- `samples/MySynth_Pad_*.wav`

### 2. Audio Interface (Optional)

```yaml
audio_interface:
  input_device_idx: 1
  output_device_idx: 4
  sample_rate: 48000
  sample_width: 24
```

**Merge behavior:** Values override config file settings for this session only.

**Use cases:**
- Test with different audio interface
- Override sample rate for specific project
- Session-specific audio routing

### 3. MIDI Interface (Optional)

```yaml
midi_interface:
  input_port: "OP-1 0"
  output_port: "OP-1 1"
```

**Merge behavior:** Values override config file settings for this session only.

**Use cases:**
- Test with different MIDI device
- Use virtual MIDI for testing
- Session-specific MIDI routing

### 4. Sampling MIDI (Per-Layer Control)

```yaml
sampling_midi:
  midi_message_delay: 0.1
  velocity_layers:
    - velocity: 40
      cc: [{controller: 74, value: 30}]
      cc14: [{controller: 1, msb: 64, lsb: 0}]
      program_change: 0
      sysex:
        - {header: "43 10 7F", controller: "10", value: 64}
  roundrobin_layers:
    - layer: 1
      cc: [{controller: 1, value: 10}]
```

**See [MIDI Control Documentation](MIDI_CONTROL_FEATURE.md) for complete details.**

### 5. Sampling Configuration

```yaml
sampling:
  # Note selection
  startNote: 36        # MIDI note number
  endNote: 96          # MIDI note number
  noteInterval: 4      # Semitones between samples
  
  # Velocity layers
  velocities: [40, 80, 120]
  
  # Round-robin
  rr_layers: 4
  
  # Recording timing
  hold: 2.0           # Seconds
  release: 2.0        # Seconds
  pause: 0.5          # Seconds
  
  # MIDI behavior
  note_on_velocity: 100    # Fixed velocity (if not using velocity layers)
  midi_channel: 1          # MIDI channel (1-16)
  note_duration: 2.0       # Note duration in seconds
```

## Merge Behavior

When using a script with `--script`, values are merged with config file:

### Merging Sections
These sections from scripts **merge with** config file:
- `audio_interface`
- `midi_interface`
- `sampling_midi`

### Override Sections
These sections from scripts **replace** config file:
- `multisample_name`
- `sampling`

### Example Merge

**Config file:**
```yaml
audio_interface:
  input_device_idx: 1
  sample_rate: 44100
```

**Script file:**
```yaml
audio_interface:
  sample_rate: 48000
```

**Resulting configuration:**
```yaml
audio_interface:
  input_device_idx: 1      # From config
  sample_rate: 48000       # From script (overridden)
```

## Examples

### Example 1: Simple Single Note Test

```yaml
# conf/test/test_single_note.yaml
multisample_name: "TestSingleNote"

sampling:
  startNote: 60    # Middle C
  endNote: 60      # Middle C (same = single note)
  noteInterval: 1
  velocities: [100]
  rr_layers: 1
  hold: 1.0
  release: 1.0
  pause: 0.5
```

**Use:** Test audio setup with minimal sampling.

**Output:** 1 sample file (C4_v100_rr1.wav)

### Example 2: Velocity Layer Test

```yaml
# conf/test/test_velocity_cc.yaml
multisample_name: "VelocityTest"

sampling_midi:
  midi_message_delay: 0.05
  velocity_layers:
    - velocity: 20
      cc: [{controller: 74, value: 10}]
    - velocity: 50
      cc: [{controller: 74, value: 40}]
    - velocity: 80
      cc: [{controller: 74, value: 70}]
    - velocity: 110
      cc: [{controller: 74, value: 100}]
    - velocity: 127
      cc: [{controller: 74, value: 127}]

sampling:
  startNote: 60
  endNote: 60
  noteInterval: 1
  rr_layers: 1
  hold: 1.0
  release: 0.5
  pause: 0.5
```

**Use:** Test brightness filter (CC74) at different velocities.

**Output:** 5 sample files (one per velocity layer)

### Example 3: Round-Robin CC Sweep

```yaml
# conf/test/test_cc1_sweep.yaml
multisample_name: "CC1_Sweep"

sampling_midi:
  midi_message_delay: 0.1
  roundrobin_layers:
    - layer: 1
      cc: [{controller: 1, value: 1}]
    - layer: 2
      cc: [{controller: 1, value: 21}]
    - layer: 3
      cc: [{controller: 1, value: 41}]
    - layer: 4
      cc: [{controller: 1, value: 61}]
    - layer: 5
      cc: [{controller: 1, value: 81}]
    - layer: 6
      cc: [{controller: 1, value: 101}]
    - layer: 7
      cc: [{controller: 1, value: 121}]

sampling:
  startNote: 60
  endNote: 60
  noteInterval: 1
  velocities: [100]
  hold: 2.0
  release: 1.0
  pause: 0.5
```

**Use:** Sample modulation wheel sweep for single note.

**Output:** 7 sample files (CC1 from 1 to 121, step 20)

### Example 4: Program Change Multi-Layer

```yaml
# conf/test/test_program_change.yaml
multisample_name: "ProgramChanges"

sampling_midi:
  midi_message_delay: 0.2
  roundrobin_layers:
    - layer: 1
      program_change: 0    # Patch 0
    - layer: 2
      program_change: 24   # Patch 24
    - layer: 3
      program_change: 40   # Patch 40
    - layer: 4
      program_change: 80   # Patch 80

sampling:
  startNote: 48
  endNote: 72
  noteInterval: 12  # Sample C3, C4, C5, C6
  velocities: [100]
  hold: 2.0
  release: 1.0
  pause: 1.0  # Longer pause for patch switching
```

**Use:** Sample 4 different patches from same synth.

**Output:** 16 sample files (4 notes × 4 patches)

### Example 5: SysEx Structured Format

```yaml
# conf/test/test_sysex_structured.yaml
multisample_name: "SysEx_Test"

sampling_midi:
  midi_message_delay: 0.15
  roundrobin_layers:
    - layer: 1
      sysex:
        - {header: "43 10 7F", controller: "10", value: 0}
        - {header: "43 10 7F", controller: "11", value: 64}
    - layer: 2
      sysex:
        - {controller: "10", value: 32}  # Header reused
        - {controller: "11", value: 96}
    - layer: 3
      sysex:
        - {controller: "10", value: 64}
        - {controller: "11", value: 127}

sampling:
  startNote: 60
  endNote: 60
  noteInterval: 1
  velocities: [100]
  hold: 1.5
  release: 0.5
  pause: 0.5
```

**Use:** Send SysEx parameters per layer (header defined once, reused).

**Output:** 3 sample files with different SysEx settings

### Example 6: Comprehensive Multi-Layer

```yaml
# conf/test/test_suite_full.yaml
multisample_name: "FullTestSuite"

sampling_midi:
  midi_message_delay: 0.1
  velocity_layers:
    - velocity: 40
      cc: [{controller: 74, value: 30}]
      program_change: 0
    - velocity: 80
      cc: [{controller: 74, value: 70}]
      program_change: 0
    - velocity: 120
      cc: [{controller: 74, value: 110}]
      program_change: 0
  roundrobin_layers:
    - layer: 1
      cc: [{controller: 1, value: 10}]
    - layer: 2
      cc: [{controller: 1, value: 50}]
    - layer: 3
      cc: [{controller: 1, value: 90}]
    - layer: 4
      cc: [{controller: 1, value: 127}]

sampling:
  startNote: 48
  endNote: 72
  noteInterval: 12  # C3, C4, C5, C6
  rr_layers: 4
  hold: 1.5
  release: 1.0
  pause: 0.5
```

**Use:** Full test of velocity + round-robin + CC messages.

**Output:** 48 sample files (4 notes × 3 velocities × 4 RR layers)

## Best Practices

### 1. Descriptive Names
```yaml
# Good
multisample_name: "Prophet_Strings_Layer_A"

# Bad
multisample_name: "test"
```

### 2. Comment Your Scripts
```yaml
# Yamaha DX7 - SysEx parameter control
# Controller 10 = Algorithm (0-31)
# Controller 11 = Feedback (0-7, scaled to 0-127)
sampling_midi:
  roundrobin_layers:
    - layer: 1
      sysex:
        - {header: "43 10 7F", controller: "10", value: 0}   # Algorithm 0
```

### 3. Test Before Full Sampling
```yaml
# Start with single note
startNote: 60
endNote: 60

# Then expand to full range
# startNote: 36
# endNote: 96
```

### 4. Adjust Delays for Hardware
```yaml
# Fast digital synth
midi_message_delay: 0.05

# Analog synth with slow filter
midi_message_delay: 0.2

# Program change switching
midi_message_delay: 0.5
pause: 1.0
```

### 5. Organize Scripts by Purpose
```
conf/
  production/
    synth_bass.yaml
    synth_lead.yaml
  test/
    test_single_note.yaml
    test_velocity.yaml
```

## Script Validation

Before running a script, AutosamplerT shows a summary:

```
=== Sampling Configuration Summary ===

Multisample: FullTestSuite
Output Directory: output/FullTestSuite/samples/

Notes to Sample: 4 notes (C3, C4, C5, C6)
Velocity Layers: 3 (40, 80, 120)
Round-Robin Layers: 4
Total Samples: 48

Estimated Duration: ~4.8 minutes
Estimated Disk Space: ~120 MB

Recording Parameters:
  Hold: 1.5s | Release: 1.0s | Pause: 0.5s | Total: 3.0s per sample

MIDI Configuration:
  Velocity Layer 1 (vel=40): CC74=30, PC=0
  Velocity Layer 2 (vel=80): CC74=70, PC=0
  Velocity Layer 3 (vel=120): CC74=110, PC=0
  RR Layer 1: CC1=10
  RR Layer 2: CC1=50
  RR Layer 3: CC1=90
  RR Layer 4: CC1=127

Proceed with sampling? (y/n):
```

Review this carefully before proceeding.

## Troubleshooting

### Script Not Found
```
Error: Script file not found
```
**Solution:** Check path is relative to workspace root: `conf/test/script.yaml`

### YAML Syntax Error
```
Error: YAML parsing failed
```
**Solution:** Validate YAML syntax. Check indentation (use spaces, not tabs).

### Section Not Merging
```
Warning: sampling_midi section not found
```
**Solution:** Ensure `sampling_midi` is in merge list (already fixed in current version).

### MIDI Messages Not Sending
**Solution:** Check `sampling_midi` section exists and has valid syntax. Verify MIDI device setup.

## Related Documentation

- [MIDI Control](MIDI_CONTROL_FEATURE.md) - Complete MIDI message reference
- [CLI Documentation](CLI.md) - How to run scripts
- [Sampling Engine](SAMPLING.md) - Recording parameter details

---

*Last updated: November 11, 2025*
