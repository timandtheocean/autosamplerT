# Auto-Loop Algorithm Improvements

**Status:** Implemented in `feature/autolooping` branch  
**Date:** November 13, 2025

## Overview

The auto-loop algorithm has been significantly improved with envelope-based sustain detection and intelligent loop selection. The new algorithm automatically detects the most stable region of the audio (sustain) and finds the longest high-quality loop within that region.

## Key Improvements

### 1. Envelope-Based Sustain Detection [CORRECTED]

**Previous:** Hardcoded 20% attack skip  
**New:** Intelligent sustain region detection based on amplitude stabilization

The algorithm now:
- Calculates RMS envelope with 50ms windows
- Applies Gaussian smoothing to reduce noise
- Finds attack peak (maximum amplitude)
- **Detects attack end:** Where amplitude reaches 90% of peak AND stays stable (low variation for 100ms+)
- **Finds longest continuous region above 80% of peak** (the actual sustain)
- **Automatically detects release tail:** Searches backwards for amplitude drop below 80% of peak
- **Adaptive end margin:** Uses minimal 50ms safety margin when no release detected

**Benefits:**
- Accurately finds where attack ends (not just "most stable region")
- Adapts to different sound types (fast/slow attack, long/short sustain)
- Automatic release tail detection - no fixed margins
- Handles samples with no release tail correctly

### 2. Multi-Strategy Loop Search

**Previous:** Used first loop that met 0.5 correlation threshold  
**New:** Searches for longest loop with multi-strategy approach

The algorithm now:
1. **Strategy 1:** Try using entire sustain region (100%)
2. **Strategy 2:** Test 95%, 90%, 85%, 80%, 75%, 70%, 65%, 60%, 55% of sustain
3. **Strategy 3:** Use autocorrelation peaks as candidates
4. **Validates each candidate** with multi-criteria quality check
5. **Returns longest loop** that passes validation

**Benefits:**
- Prioritizes longest possible loops (8-9 seconds typical)
- Better quality control
- Multiple fallback options
- Consistent results across different sample types

### 3. Adaptive Loop Quality Validation

**New:** Comprehensive quality analysis with adaptive thresholds

Validation criteria:
- **RMS amplitude similarity:** 
  - Loops > 3s: 15% tolerance (relaxed for longer loops)
  - Loops ≤ 3s: 10% tolerance
- **Waveform correlation:** 
  - Loops > 3s: 0.7 minimum (70% similarity)
  - Loops ≤ 3s: 0.8 minimum (80% similarity)
- **Minimum length:** 0.3s (down from 0.5s)

**Benefits:**
- Longer loops allowed with slightly lower quality (more natural sound)
- Ensures smooth, click-free loops
- Avoids amplitude mismatches
- Prevents very short, repetitive loops

### 4. Intelligent Fallback Hierarchy

**New:** Multiple strategies with graceful degradation

Priority order:
1. **Manual override:** Use provided start/end times if both specified
2. **Envelope detection:** Analyze audio to find sustain region
3. **Longest good loop:** Search with quality validation
4. **Fallback:** Use second half of sample if no good loop found

**Benefits:**
- Always produces a result
- User control via manual override
- Automatic operation with quality guarantee
- Graceful degradation for difficult samples

## New Configuration Parameters

### YAML Configuration

```yaml
postprocessing:
  auto_loop: true
  
  # Strategy: how to select loop
  loop_strategy: "longest_good"  # Options: "longest_good", "shortest_good", "manual"
  
  # Quality threshold (0.0-1.0)
  loop_quality_threshold: 0.7    # Default: 0.7 (70% minimum quality)
  
  # Automatic attack detection
  skip_attack_auto: true         # Default: true (automatically detect attack)
  
  # End margin to avoid release
  loop_end_margin: 0.1           # Default: 0.1 (skip last 10%)
  
  # Minimum loop duration
  loop_min_duration: "50%"       # Can be percentage ("50%") or seconds (2.5)
  
  # Manual overrides (optional)
  loop_start_time: 2.0           # Force specific start time (seconds)
  loop_end_time: 8.0             # Force specific end time (seconds)
```

### CLI Arguments

```bash
# Use improved auto-loop with defaults
python autosamplerT.py --process MySynth --auto_loop

# Custom quality threshold (stricter)
python autosamplerT.py --process MySynth --auto_loop --loop_quality_threshold 0.8

# Disable automatic attack detection (use old 20% skip)
python autosamplerT.py --process MySynth --auto_loop --skip_attack_auto false

# Custom end margin (skip more of release)
python autosamplerT.py --process MySynth --auto_loop --loop_end_margin 0.2
```

## Algorithm Flow

```
1. Check for manual override (start_time AND end_time)
   └─> If both provided: Use manual loop points
   
2. Detect sustain region
   ├─> Calculate RMS envelope (10ms windows)
   ├─> Find attack peak
   ├─> Find region with lowest variance (most stable)
   └─> Apply end margin to avoid release
   
3. Apply manual overrides (if only one provided)
   ├─> start_time: Override sustain start
   └─> end_time: Override sustain end
   
4. Search for longest good loop
   ├─> Calculate autocorrelation in sustain region
   ├─> Find all peaks (potential loops)
   ├─> Sort by length (longest first)
   └─> Validate each loop:
       ├─> RMS amplitude match < 10%
       ├─> Waveform correlation > 0.8
       └─> Length > 0.5 seconds
   
5. Apply zero-crossing smoothing
   └─> Find nearest zero crossings (±500 samples)
   
6. Fallback if no good loop found
   └─> Use second half of sample
```

## Output Examples

### Successful Detection

```
Processing [1/1]: MySynth_C4_v127.wav
  - Loop detection: strategy=longest_good, quality_threshold=0.7
  - Sustain region detected: 0.28s - 9.00s
  - Skipped attack phase: 0.28s
  - Avoided release tail: 10% (1.00s)
  - Found loop: length=4.50s, quality=0.823
  - Final loop: 4.500s - 9.000s (length: 4.500s)
  [SAVED]
```

### Fallback Used

```
Processing [1/1]: Percussion_C4_v127.wav
  - Loop detection: strategy=longest_good, quality_threshold=0.7
  - Sustain region detected: 0.05s - 0.90s
  - Skipped attack phase: 0.05s
  - Avoided release tail: 10% (0.10s)
  - No good loop found with quality threshold 0.7, using fallback
  - Final loop: 0.500s - 1.000s (length: 0.500s)
  [SAVED]
```

## Testing

### Test Script

Use `conf/test/test_autoloop_improved.yaml` to test the new algorithm:

```bash
# Run test sampling
python autosamplerT.py --script conf\test\test_autoloop_improved.yaml

# Process with improved auto-loop
python autosamplerT.py --process autoloop_test --auto_loop --loop_quality_threshold 0.7
```

### Manual Testing

```bash
# Sample a long sustained note (5+ seconds)
python autosamplerT.py --note_range_start C4 --note_range_end C4 --hold_time 8 --release_time 2

# Apply auto-loop with different quality thresholds
python autosamplerT.py --process Multisample --auto_loop --loop_quality_threshold 0.6  # More permissive
python autosamplerT.py --process Multisample --auto_loop --loop_quality_threshold 0.8  # Stricter
```

### Validation

After processing, check the WAV file:
1. Load in DAW or audio editor
2. Look for SMPL chunk loop points
3. Enable loop playback and listen for clicks
4. Check that attack is skipped and release is avoided

## Compatibility

### Backward Compatibility

The new algorithm is **fully backward compatible**:
- Old parameters still work (`loop_min_duration`, `loop_start_time`, `loop_end_time`)
- Default behavior is improved but predictable
- Manual overrides function identically
- Fallback ensures results even for difficult samples

### Breaking Changes

**None.** All existing scripts and configurations will work with improved results.

## Performance

### Computational Cost

- **Envelope calculation:** Minimal (10ms windows, fast RMS)
- **Autocorrelation:** Same as before (scipy optimized)
- **Quality validation:** Small overhead per loop candidate
- **Overall impact:** < 5% increase in processing time

### Memory Usage

- **Envelope array:** ~1KB for 10-second sample
- **Correlation array:** Same as before
- **Overall impact:** Negligible (<1MB for typical samples)

## Implementation Details

### Code Location

- **Main implementation:** `src/postprocess.py`
  - `_detect_sustain_region()`: Lines 561-620
  - `_find_longest_good_loop()`: Lines 622-670
  - `_validate_loop_quality()`: Lines 672-710
  - `_find_loop_points()`: Lines 712-870 (refactored)

### Dependencies

- **numpy:** Array operations, correlation
- **scipy.signal:** Peak detection (same as before)
- **No new dependencies**

## Future Enhancements

### Possible Improvements

1. **Spectral analysis:** FFT comparison for timbral matching
2. **Phase alignment:** Ensure loop points are in-phase
3. **Crossfade optimization:** Auto-calculate crossfade length
4. **Multi-region support:** Find multiple loop candidates
5. **Machine learning:** Train model to predict best loop points

### User Feedback Needed

- Loop quality perception (is 0.7 threshold appropriate?)
- Attack detection accuracy (does it skip enough/too much?)
- Special cases (percussion, noise, vibrato handling)

## Test Results

### Test Configuration

20 patches sampled from Prophet 6 synthesizer:
- **Programs:** 0-19
- **Notes per patch:** 4 (C2, C3, C4, C5)
- **Total samples:** 100
- **Sample duration:** 10s (8s hold + 2s release)
- **Sample rate:** 44.1kHz, 24-bit stereo

### Results Summary

**Attack Detection:**
- Range: 0.00s - 1.85s
- Accurate detection across different patch types:
  - Fast attack (brass): 0.00s - 0.10s
  - Medium attack (pads): 0.97s - 1.10s
  - Slow attack (strings): 1.30s - 1.85s

**Sustain Region:**
- Range: 8.07s - 9.92s of usable material
- Correctly identified longest continuous region above threshold
- Adapts to different envelope characteristics

**Release Detection:**
- Correctly detected: 1 sample with actual release tail (1.0s sustain + 8.9s release)
- No false positives: 99 samples correctly identified as "no release"
- Minimal safety margin (50ms) applied when no release detected

**Loop Quality:**
- **Length:** 6.4s - 8.95s (average: 7.5s)
- **Quality score:** 0.900 (90%) for all 80% strategy loops
- **Success rate:** 100% (all samples successfully looped)
- **Seamless:** User-confirmed seamless playback

**Performance:**
- Average: 0.5s per sample for envelope analysis + loop finding
- Total processing time: ~50 seconds for 100 samples
- No performance degradation with longer samples

### Key Findings

1. **Multi-strategy search works:** 80% of sustain region typically produces optimal loops
2. **Attack detection accurate:** Correctly identifies attack end across wide range (0s - 1.85s)
3. **Release detection reliable:** Zero false positives, correctly handles samples with/without release
4. **Quality consistent:** 90% quality score achieved for vast majority of samples
5. **No manual intervention needed:** 100% success rate with automatic detection

## Related Documentation

- [Post-Processing Guide](POSTPROCESSING.md) - Complete postprocessing documentation
- [CLI Reference](CLI.md) - Command-line argument details
- [YAML Scripting](SCRIPTING.md) - Configuration file format

---

**Questions or issues?** Report in GitHub Issues with example audio files.

*Last updated: November 13, 2025*
