# Sampling Engine

Guide to the core sampling functionality and recording parameters in AutosamplerT.

## Overview

The sampling engine is the heart of AutosamplerT, responsible for:
- Recording audio samples from hardware
- Managing velocity and round-robin layers
- Coordinating MIDI note-on/note-off with recording
- Detecting silence and trimming samples
- Organizing multi-sample output

## What It's Used For

- **Multi-sampling**: Capture multiple velocity and round-robin layers
- **Patch creation**: Generate complete instrument patches
- **Hardware capture**: Record external synthesizers and instruments
- **Layer management**: Automatically organize complex multi-layer samples
- **Batch processing**: Sample entire note ranges automatically

## Note Range Configuration

### Start Note and End Note

Define the range of MIDI notes to sample:

```yaml
sampling:
  startNote: 36    # C2
  endNote: 96      # C7
  noteInterval: 4  # Every 4 semitones
```

**MIDI Note Numbers:**
- C-1 = 0
- C0 = 12
- C1 = 24
- C2 = 36
- C3 = 48 (middle C is C4 = 60)
- C4 = 60
- C5 = 72
- C6 = 84
- C7 = 96
- C8 = 108
- G9 = 127 (max)

### Note Interval

Sample every N semitones:

```yaml
noteInterval: 1   # Every note (chromatic)
noteInterval: 2   # Every whole tone
noteInterval: 4   # Every major third
noteInterval: 12  # Every octave
```

**Examples:**

**Chromatic (every note):**
```yaml
startNote: 60      # C4
endNote: 72        # C5
noteInterval: 1
# Samples: C4, C#4, D4, D#4, E4, F4, F#4, G4, G#4, A4, A#4, B4, C5
# Total: 13 notes
```

**Octaves only:**
```yaml
startNote: 36      # C2
endNote: 96        # C7
noteInterval: 12
# Samples: C2, C3, C4, C5, C6, C7
# Total: 6 notes
```

**Major thirds:**
```yaml
startNote: 48      # C3
endNote: 72        # C5
noteInterval: 4
# Samples: C3, E3, G#3, C4, E4, G#4, C5
# Total: 7 notes
```

## Velocity Layers

### Configuration

Define velocity layers for dynamic sampling:

```yaml
sampling:
  velocities: [20, 40, 60, 80, 100, 120, 127]
```

**Common velocity mappings:**
- `[20, 40, 60, 80, 100, 120, 127]` - 7 layers (very detailed)
- `[40, 80, 120]` - 3 layers (ppp, mf, fff)
- `[64, 100, 127]` - 3 layers (mp, f, ff)
- `[100]` - Single velocity (no layers)

### Velocity with MIDI Control

Combine with per-velocity MIDI messages:

```yaml
sampling_midi:
  velocity_layers:
    - velocity: 40
      cc: [{controller: 74, value: 30}]    # Darker sound
    - velocity: 80
      cc: [{controller: 74, value: 70}]    # Medium brightness
    - velocity: 120
      cc: [{controller: 74, value: 110}]   # Bright sound

sampling:
  velocities: [40, 80, 120]
```

**Note:** When using `sampling_midi.velocity_layers`, the `velocities` in `sampling` section should match.

### Velocity Calculation

AutosamplerT automatically maps velocity layers to MIDI velocity ranges in the SFZ file:

**Example with 3 layers:**
```
Velocity 40:  lovel=0   hivel=59
Velocity 80:  lovel=60  hivel=99
Velocity 120: lovel=100 hivel=127
```

## Round-Robin Layers

### Configuration

Define number of round-robin alternations:

```yaml
sampling:
  rr_layers: 4
```

**Use cases:**
- **1 layer**: No alternation (single sample per note/velocity)
- **2-4 layers**: Subtle variations (most common)
- **5-8 layers**: Detailed variations (acoustic instruments)
- **10+ layers**: Extreme realism (large sample libraries)

### Round-Robin with MIDI Control

Use different MIDI settings per RR layer:

```yaml
sampling_midi:
  roundrobin_layers:
    - layer: 1
      cc: [{controller: 1, value: 10}]     # Slight modulation
    - layer: 2
      cc: [{controller: 1, value: 50}]     # Medium modulation
    - layer: 3
      cc: [{controller: 1, value: 90}]     # Heavy modulation
    - layer: 4
      cc: [{controller: 1, value: 127}]    # Maximum modulation

sampling:
  rr_layers: 4
```

### Sample Calculation

Total samples = Notes × Velocities × RR Layers

**Examples:**

**Single octave, 3 velocities, 4 RR:**
```yaml
startNote: 60
endNote: 72
noteInterval: 1
velocities: [40, 80, 120]
rr_layers: 4
# Total: 13 notes × 3 velocities × 4 RR = 156 samples
```

**Full keyboard, chromatic, single velocity:**
```yaml
startNote: 21      # A0
endNote: 108       # C8
noteInterval: 1
velocities: [100]
rr_layers: 1
# Total: 88 notes × 1 velocity × 1 RR = 88 samples
```

## Recording Parameters

### Hold Time

Duration to hold the note before releasing:

```yaml
sampling:
  hold: 2.0    # seconds
```

**Use cases:**
- **0.5-1.0s**: Short percussive sounds (piano, drums)
- **1.0-2.0s**: Medium sustain (strings, brass)
- **2.0-5.0s**: Long pads and drones
- **5.0+s**: Evolving textures

**Important:** Ensure hold time captures the full attack and sustain character.

### Release Time

Duration to record after note-off:

```yaml
sampling:
  release: 2.0    # seconds
```

**Use cases:**
- **0.1-0.5s**: Quick release (staccato)
- **0.5-1.0s**: Natural release (piano, plucked)
- **1.0-2.0s**: Medium release (strings with reverb)
- **2.0-5.0s**: Long tail (piano sustain pedal, reverb)

**Important:** Capture the full release tail including reverb and resonance.

### Pause Time

Delay between samples:

```yaml
sampling:
  pause: 0.5    # seconds
```

**Use cases:**
- **0.1-0.3s**: Fast sampling (no audio processing)
- **0.5-1.0s**: Normal sampling (standard)
- **1.0-2.0s**: Hardware with slow parameter changes
- **2.0+s**: Analog synth with slow envelope generators

**Important:** Increase pause time if:
- Hardware has slow envelope recovery
- MIDI messages need processing time
- Program changes are slow

### Note Duration

MIDI note-on duration (independent of recording):

```yaml
sampling:
  note_duration: 2.0    # seconds
```

**Note:** Should typically match `hold` time. Note-off is sent after `note_duration`.

### Total Time Per Sample

```
Total = Hold + Release + Pause
```

**Example:**
```yaml
hold: 2.0
release: 1.5
pause: 0.5
# Total per sample: 4.0 seconds
```

## MIDI Settings

### Note-On Velocity

Fixed velocity for note-on (when not using velocity layers):

```yaml
sampling:
  note_on_velocity: 100
```

**Range:** 1-127

**Use when:** Not using velocity layers or want consistent velocity.

### MIDI Channel

Target MIDI channel:

```yaml
sampling:
  midi_channel: 1
```

**Range:** 1-16

**Most hardware:** Channel 1 (default)

## Audio Processing During Recording

AutosamplerT records the full duration specified by `hold_time + release_time` without automatic silence trimming. This ensures:

- Complete capture of attack and release
- Full recording for debugging (e.g., verifying no clicks at end)
- Accurate timing for long recordings

### Optional Normalization

Individual sample normalization can be applied during recording:

```yaml
audio:
  sample_normalize: true  # Normalize each sample to peak level (default: true)
  patch_normalize: false  # Normalize entire patch together (default: false)
```

**Note:** Silence detection and trimming are now **postprocessing-only operations**. See [Post-Processing](POSTPROCESSING.md) for details.

## Pre-Sampling Summary

Before starting, AutosamplerT shows detailed estimates:

```
=== Sampling Configuration Summary ===

Multisample: MySynth_Pad
Output Directory: output/MySynth_Pad/samples/

Notes to Sample: 16 notes (C2 to C7, every 4 semitones)
Velocity Layers: 3 (40, 80, 120)
Round-Robin Layers: 4
Total Samples: 192

Estimated Duration: ~12.8 minutes
Estimated Disk Space: ~480 MB

Recording Parameters:
  Hold: 2.0s | Release: 1.5s | Pause: 0.5s | Total: 4.0s per sample

MIDI Configuration:
  [Details of MIDI messages per layer]

Proceed with sampling? (y/n):
```

### Duration Calculation

```
Duration = (Total Samples × Total Time Per Sample) / 60
```

**Example:**
```
192 samples × 4.0s = 768 seconds = 12.8 minutes
```

### Disk Space Calculation

```
File Size = Sample Rate × Bit Depth × Channels × Duration / 8
Total Size = File Size × Total Samples
```

**Example (48kHz, 24-bit, stereo, 3.5s average):**
```
File Size = 48000 × 24 × 2 × 3.5 / 8 = ~504 KB per sample
Total = 504 KB × 192 = ~94.5 MB
```

## Examples

### Example 1: Simple Piano Sampling

```yaml
multisample_name: "Piano_Bright"

sampling:
  startNote: 21      # A0
  endNote: 108       # C8
  noteInterval: 3    # Every minor third
  velocities: [40, 80, 120]
  rr_layers: 2
  hold: 1.0          # Short notes
  release: 3.0       # Capture sustain pedal
  pause: 0.5
  note_on_velocity: 100
  midi_channel: 1
  note_duration: 1.0
```

**Output:** ~90 notes × 3 velocities × 2 RR = ~540 samples

### Example 2: Synthesizer Pad

```yaml
multisample_name: "Synth_Ambient_Pad"

sampling:
  startNote: 36      # C2
  endNote: 96        # C7
  noteInterval: 4    # Every major third
  velocities: [100]  # Single velocity
  rr_layers: 1       # No RR
  hold: 5.0          # Long evolving sound
  release: 3.0       # Long tail
  pause: 1.0         # Let reverb settle
  note_on_velocity: 100
  midi_channel: 1
  note_duration: 5.0
```

**Output:** 16 notes × 1 velocity × 1 RR = 16 samples

### Example 3: Drum Kit

```yaml
multisample_name: "DrumKit_808"

sampling:
  startNote: 36      # Kick
  endNote: 60        # Hi-hat
  noteInterval: 1    # Chromatic
  velocities: [40, 80, 120]  # 3 dynamics
  rr_layers: 4       # 4 variations
  hold: 0.5          # Short hits
  release: 1.0       # Capture decay
  pause: 0.3         # Quick succession
  note_on_velocity: 100
  midi_channel: 10   # Drum channel
  note_duration: 0.5
```

**Output:** 25 notes × 3 velocities × 4 RR = 300 samples

### Example 4: Brass Section

```yaml
multisample_name: "Brass_Ensemble"

sampling:
  startNote: 48      # C3
  endNote: 84        # C6
  noteInterval: 2    # Whole tones
  velocities: [40, 70, 100, 127]
  rr_layers: 3
  hold: 2.5          # Long notes
  release: 1.5       # Natural release
  pause: 1.0         # Breath recovery
  note_on_velocity: 100
  midi_channel: 1
  note_duration: 2.5
```

**Output:** 19 notes × 4 velocities × 3 RR = 228 samples

### Example 5: Quick Test

```yaml
multisample_name: "Quick_Test"

sampling:
  startNote: 60      # C4
  endNote: 60        # C4 (single note)
  noteInterval: 1
  velocities: [100]
  rr_layers: 1
  hold: 1.0
  release: 0.5
  pause: 0.3
  note_on_velocity: 100
  midi_channel: 1
  note_duration: 1.0
```

**Output:** 1 sample (total time: ~2 seconds)

## Best Practices

### 1. Test First
Always test with single note before full sampling:
```yaml
startNote: 60
endNote: 60    # Same as start = single note
```

### 2. Optimize Note Interval
Don't oversample:
- **Synthesizers**: Every 4-6 semitones is often sufficient
- **Acoustic instruments**: Every 2-3 semitones
- **Percussive sounds**: Every 1-2 semitones

### 3. Match Recording Times to Sound
- **Attack time < hold time**: Capture full attack
- **Release time > natural release**: Capture full tail
- **Pause time > envelope recovery**: Prevent overlapping envelopes

### 4. Consider Disk Space
Check estimated disk space before sampling:
- **< 1 GB**: Safe for most systems
- **1-5 GB**: Consider splitting into multiple sessions
- **> 5 GB**: Plan disk space carefully

### 5. Monitor First Sample
Check the first sample quality before continuing:
1. Start sampling
2. After first sample, check output file
3. If quality is good, continue
4. If not, stop and adjust parameters

### 6. Use Appropriate Bit Depth
- **16-bit**: Sufficient for most uses, smaller files
- **24-bit**: Professional quality, larger files

### 7. Name Descriptively
```yaml
# Good
multisample_name: "Moog_Bass_FilterSweep"

# Bad
multisample_name: "test2"
```

## Troubleshooting

### Clipped Audio
**Problem:** Samples are distorted or clipping

**Solutions:**
- Lower hardware output volume
- Check input gain on audio interface
- Ensure levels stay below 0dB

### Missing Attack
**Problem:** Sample starts mid-attack

**Solutions:**
- Increase `hold` time
- Check silence detection threshold
- Verify MIDI timing

### Missing Release Tail
**Problem:** Sample cuts off before release ends

**Solutions:**
- Increase `release` time
- Check silence detection threshold
- Verify reverb/delay settings on hardware

### Overlapping Samples
**Problem:** Previous sample still playing when next starts

**Solutions:**
- Increase `pause` time
- Reduce `release` time
- Check hardware polyphony settings

### Silent Samples
**Problem:** Recorded files contain only silence

**Solutions:**
- Verify audio routing
- Check input device selection
- Ensure hardware is producing sound
- Verify MIDI connection

### Inconsistent Timing
**Problem:** Some samples have wrong duration

**Solutions:**
- Ensure stable audio buffer
- Check system load during sampling
- Use consistent sample rate

## Related Documentation

- [MIDI Control](MIDI_CONTROL_FEATURE.md) - Per-layer MIDI messages
- [Scripting System](SCRIPTING.md) - YAML configuration
- [Output Formats](OUTPUT.md) - File organization and SFZ
- [Post-Processing](POSTPROCESSING.md) - Silence trimming and normalization

---

*Last updated: November 11, 2025*
