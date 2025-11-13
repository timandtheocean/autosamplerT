# Post-Processing

Guide to audio processing performed after sample capture in AutosamplerT.

## Overview

AutosamplerT performs automatic post-processing on recorded samples to improve quality and consistency:
- Silence detection and trimming
- Patch normalization
- Quality validation
- File optimization

## What It's Used For

- **File size reduction**: Remove unnecessary silence (via trimming)
- **Consistent levels**: Normalize volume across patches
- **Better loops**: Clean start/end points
- **Professional quality**: Optimized samples for samplers
- **Faster loading**: Smaller files load quicker

## Silence Detection and Trimming

[NOTE] As of v3.0, silence trimming is **only performed during postprocessing**, not during recording. This ensures complete capture of the full hold + release duration for debugging and quality control.

### How It Works

Silence trimming detects and removes silence from the beginning and end of each recorded sample.

**Process:**
1. **Scan from start**: Find first sample above threshold
2. **Scan from end**: Find last sample above threshold
3. **Add safety margin**: Keep small buffer before attack (10ms) and after release (100ms)
4. **Trim audio**: Remove silence outside detected range
5. **Save trimmed file**: Overwrite with optimized version

### Usage

**Postprocessing existing samples:**
```bash
python autosamplerT.py --process MySynth --trim_silence
```

**YAML script:**
```yaml
postprocessing:
  trim_silence: true
  silence_threshold: -60  # dB threshold (optional)
```

### Benefits

- **Smaller files**: 30-70% size reduction typical
- **Clean attacks**: No leading silence before sound
- **Clean releases**: No trailing silence after decay
- **Better timing**: Samples start immediately when triggered
- **Looping**: Cleaner loop points for sustained sounds

### Threshold Configuration

**Default threshold:**
```python
silence_threshold = 0.001  # ~-60dB below full scale
```

**Interpretation:**
- Any sample with absolute amplitude < 0.001 is considered silence
- Catches quiet noise floors while preserving subtle releases
- Can be adjusted in postprocessing scripts

### Safety Margins

Buffers preserved around the audio:

```python
pre_attack = 10ms    # Before first sound (prevents cutting transients)
post_release = 100ms # After last sound (preserves natural decay)
```

**Purpose:**
- Ensure no attack transient is cut
- Preserve natural release characteristics
- Preserve any pre-attack artifacts
- Account for detection threshold

### Visual Example

```
Before trimming:
[silence...silence...ATTACK---SUSTAIN---RELEASE...silence...silence]

After trimming:
[buffer][ATTACK---SUSTAIN---RELEASE][buffer]
```

### What Gets Trimmed

**Leading silence:**
- Room noise before note starts
- MIDI transmission delay
- Hardware envelope delay

**Trailing silence:**
- Room noise after release
- Unnecessary recording buffer
- Post-release silence

**What's preserved:**
- Full attack transient
- Complete sustain phase
- Full release tail
- Small safety margins

## Patch Normalization

### What It Is

Patch normalization adjusts the volume of all samples in a multi-sample patch to a consistent peak level while preserving relative dynamics.

### Why It's Important

**Without normalization:**
```
C2 velocity 40:  Peak = -18dB  (too quiet)
C2 velocity 80:  Peak = -8dB   (medium)
C2 velocity 120: Peak = -3dB   (loud)
```
Result: Inconsistent volumes, velocity layer jumps

**With normalization:**
```
C2 velocity 40:  Peak = -3dB  (gain +15dB)
C2 velocity 80:  Peak = -3dB  (gain +5dB)
C2 velocity 120: Peak = -3dB  (gain 0dB)
```
Result: Smooth velocity curve, consistent levels

### How It Works

**Two-pass process:**

**Pass 1: Analysis**
```python
1. Scan all samples in patch
2. Find maximum peak across all samples
3. Calculate required gain to reach target
```

**Pass 2: Processing**
```python
1. Apply same gain to all samples
2. Preserve relative dynamics
3. Save normalized files
```

### Target Level

```python
# src/sampler.py
target_level_db = -3.0  # Peak at -3dB
```

**Why -3dB?**
- **Headroom**: Prevents clipping in samplers
- **Mixing headroom**: Room for effects and processing
- **Industry standard**: Common mastering level
- **Safety margin**: Accounts for interpolation artifacts

### Configuration

```python
# src/sampler.py
normalize_patch = True       # Enable/disable normalization
target_level_db = -3.0      # Target peak level
```

**Disable normalization:**
```python
normalize_patch = False
```
Use when:
- Source already normalized
- Preserving original levels critical
- Manual level adjustment preferred

### Dynamic Range Preservation

**Critical:** Normalization preserves relative dynamics.

**Example:**
```
Original:
  Velocity 40:  -18dB peak
  Velocity 80:  -8dB peak
  Velocity 120: -3dB peak
  Dynamic range: 15dB

Normalized (target -3dB):
  Velocity 40:  -3dB peak  (+15dB gain)
  Velocity 80:  -3dB peak  (+5dB gain)
  Velocity 120: -3dB peak  (0dB gain)
  Dynamic range: Still 15dB (preserved)
```

The **relationship** between velocity layers is maintained.

## Processing Pipeline

### Order of Operations

```
1. Record audio          → Raw capture
2. Silence detection     → Find audio boundaries
3. Trim silence          → Remove leading/trailing
4. Save trimmed file     → Individual sample optimization
5. [All samples complete]
6. Patch analysis        → Find maximum peak
7. Normalize patch       → Apply gain to all samples
8. Generate SFZ          → Create mapping file
```

### Per-Sample Processing

For each sample:
```python
1. record_sample()
   ↓
2. detect_silence_boundaries()
   ↓
3. trim_audio()
   ↓
4. save_wav()
```

### Batch Processing

After all samples:
```python
1. analyze_patch()
   ↓
2. calculate_gain()
   ↓
3. apply_gain_to_all_samples()
   ↓
4. generate_sfz()
```

## Quality Validation

### Automatic Checks

AutosamplerT performs quality validation during processing:

**Clipping detection:**
```python
if peak >= 0.99:
    log_warning("Sample may be clipping")
```

**Silence validation:**
```python
if audio_duration < expected_duration * 0.5:
    log_warning("Sample unusually short")
```

**Level validation:**
```python
if peak < 0.01:
    log_warning("Sample very quiet, check levels")
```

### Manual Validation

**After first sample:**
1. Check output file in `samples/` folder
2. Verify attack is present
3. Verify release tail captured
4. Check for clipping or distortion
5. If good, continue; if not, adjust and restart

**Spot check during sampling:**
- Monitor levels in real-time
- Listen to recorded samples
- Verify MIDI messages sent correctly

## File Optimization

### Compression

AutosamplerT uses **uncompressed WAV** files:
- PCM encoding (no lossy compression)
- Preserves full audio quality
- Compatible with all samplers

**External compression (optional):**
```bash
# Compress entire patch folder
zip -r MySynth_Pad.zip output/MySynth_Pad/

# Or use 7-Zip for better compression
7z a -t7z -mx9 MySynth_Pad.7z output/MySynth_Pad/
```

### Bit Depth Optimization

**24-bit recording:**
- Use when source has high dynamic range
- Analog synthesizers, acoustic instruments
- Professional quality

**16-bit recording:**
- Sufficient for most digital sources
- Smaller files (33% reduction)
- Compatible with all samplers

**Convert 24-bit to 16-bit (optional):**
```bash
# Using sox
sox input_24bit.wav -b 16 output_16bit.wav

# Using ffmpeg
ffmpeg -i input_24bit.wav -sample_fmt s16 output_16bit.wav
```

## Examples

### Example 1: Trimming Impact

**Before trimming:**
```
File: MySynth_C4_v100_rr1.wav
Size: 504 KB
Duration: 3.5s (including 0.5s leading + 0.8s trailing silence)
Actual sound: 2.2s
```

**After trimming:**
```
File: MySynth_C4_v100_rr1.wav
Size: 330 KB (35% reduction)
Duration: 2.3s (2.2s sound + 0.1s margins)
Actual sound: 2.2s (preserved)
```

### Example 2: Normalization Impact

**Original recordings:**
```
MySynth_C4_v40_rr1.wav:   Peak = -15dB
MySynth_C4_v80_rr1.wav:   Peak = -8dB
MySynth_C4_v120_rr1.wav:  Peak = -2dB
```

**After normalization (target -3dB):**
```
MySynth_C4_v40_rr1.wav:   Peak = -3dB  (gain +12dB)
MySynth_C4_v80_rr1.wav:   Peak = -3dB  (gain +5dB)
MySynth_C4_v120_rr1.wav:  Peak = -3dB  (gain -1dB, slight reduction)
```

**Result:**
- Consistent peak levels
- Smooth velocity response
- Professional quality

### Example 3: Full Patch Processing

**Patch:** 48 samples (4 notes × 3 velocities × 4 RR)

**Before processing:**
```
Total size: 1,200 MB
Average duration: 3.8s per sample
Peak levels: -25dB to -2dB
File format: 24-bit, 48kHz, stereo
```

**After processing:**
```
Total size: 720 MB (40% reduction)
Average duration: 2.4s per sample
Peak levels: All -3dB
File format: 24-bit, 48kHz, stereo (unchanged)
Processing time: ~15 seconds
```

## Advanced Topics

### Custom Threshold

To modify silence threshold, edit source:

```python
# src/sampler.py
class Sampler:
    def __init__(self, ...):
        self.silence_threshold = 0.001  # Adjust this
```

**Lower threshold (0.0001):**
- More conservative
- Keeps quieter sections
- Longer samples

**Higher threshold (0.01):**
- More aggressive
- Removes more silence
- Shorter samples

### Fade In/Out

AutosamplerT does not currently apply fades, but you can add them:

```python
# Add to src/sampler.py after trimming
fade_samples = int(0.005 * sample_rate)  # 5ms fade

# Fade in
audio[:fade_samples] *= np.linspace(0, 1, fade_samples)

# Fade out
audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
```

**Use when:**
- Preventing clicks from sharp cuts
- Smoothing loop points
- Processing percussive sounds

### Batch Reprocessing

Reprocess existing samples:

```python
# Script to reprocess samples
import os
import numpy as np
import soundfile as sf

def normalize_existing_patch(patch_dir, target_db=-3.0):
    samples = []
    files = []
    
    # Load all samples
    for filename in os.listdir(patch_dir):
        if filename.endswith('.wav'):
            path = os.path.join(patch_dir, filename)
            audio, sr = sf.read(path)
            samples.append(audio)
            files.append(path)
    
    # Find max peak
    max_peak = max(np.abs(sample).max() for sample in samples)
    
    # Calculate gain
    target_linear = 10 ** (target_db / 20)
    gain = target_linear / max_peak
    
    # Apply gain and save
    for audio, path in zip(samples, files):
        normalized = audio * gain
        sf.write(path, normalized, sr)
    
    print(f"Normalized {len(files)} files to {target_db}dB")

# Usage
normalize_existing_patch('output/MySynth_Pad/samples/')
```

## Best Practices

### 1. Monitor First Sample
Always check the first sample:
```bash
# After first sample is recorded
# Listen to: output/<multisample_name>/samples/<first_file>.wav
```

### 2. Appropriate Recording Times
Set recording times to capture full sound:
```yaml
# For sustained sounds
hold: 3.0        # Capture full sustain
release: 2.0     # Capture full decay

# For percussive sounds
hold: 0.5        # Short hit
release: 2.0     # Long tail
```

### 3. Check Normalization Results
After sampling, verify levels:
```bash
# Check peak levels (using sox or ffmpeg)
soxi output/MySynth_Pad/samples/*.wav | grep "Maximum amplitude"
```

### 4. Balance File Size vs Quality
```yaml
# Smaller files
sample_rate: 44100
sample_width: 16

# Higher quality
sample_rate: 48000
sample_width: 24
```

### 5. Preserve Originals
Consider keeping pre-processed versions:
```bash
# Before running AutosamplerT, set output to temp folder
# Then copy and rename if satisfied
```

## Troubleshooting

### Attack Cut Off
**Problem:** Sample starts mid-attack

**Solutions:**
- Lower `silence_threshold` in code
- Increase pre-attack buffer
- Check hardware latency

### Release Cut Short
**Problem:** Release tail trimmed too early

**Solutions:**
- Lower `silence_threshold`
- Increase `release` time in YAML
- Check room noise level

### Inconsistent Levels After Normalization
**Problem:** Some samples still quieter than others

**Solutions:**
- Check source instrument output
- Verify MIDI velocity response
- Check for clipping in source

### Files Too Large
**Problem:** Disk space filling up quickly

**Solutions:**
- Use 16-bit instead of 24-bit
- Use 44.1kHz instead of 48kHz
- Reduce `release` time if possible
- Compress archives when complete

### Processing Takes Too Long
**Problem:** Normalization slow for large patches

**Solutions:**
- Process smaller batches
- Use faster disk (SSD)
- Disable normalization if not needed

## Performance Considerations

### Processing Speed

**Typical speeds:**
- Silence detection: ~0.1s per sample
- Trimming: ~0.1s per sample
- Normalization: ~0.2s per sample

**Large patch (192 samples):**
- Silence detection: ~20s
- Trimming: ~20s
- Normalization: ~40s
- **Total post-processing: ~80s (~1.5 minutes)**

### Memory Usage

AutosamplerT processes samples in memory:
- ~10 MB per sample (24-bit, 48kHz, 3s, stereo)
- Normalization loads all samples simultaneously
- Large patches (500+ samples) may use >5 GB RAM

**If memory constrained:**
- Process in smaller batches
- Use 16-bit audio
- Reduce sample duration

## Related Documentation

- [Sampling Engine](SAMPLING.md) - Recording parameters
- [Output Formats](OUTPUT.md) - File organization
- [MIDI Control](MIDI_CONTROL_FEATURE.md) - Per-layer control

---

*Last updated: November 11, 2025*
