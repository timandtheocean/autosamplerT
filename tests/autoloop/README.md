# Auto-Loop Testing

This directory contains comprehensive tests for the auto-loop functionality.

## Directory Structure

```
tests/autoloop/
├── README.md              # This file
├── test_autoloop.py       # Main test script
├── samples/               # Test sample files (you create these)
│   ├── short_sustain.wav
│   ├── medium_sustain.wav
│   ├── long_sustain.wav
│   ├── percussive.wav
│   └── noisy_sustain.wav
└── output/                # Test results (created automatically)
    ├── basic_autoloop/
    ├── min_duration_percent_50/
    └── ...
```

## Setup

### 1. Create Test Samples

You need to create test samples first. You have three options:

#### Option A: Automated (using autosamplerT)

```bash
# From workspace root
python autosamplerT.py --note_range_start C4 --note_range_end C4 \
                       --hold_time 2 --release_time 0.5 \
                       --multisample_name short_sustain

# Copy the WAV file
copy output\short_sustain\samples\*.wav tests\autoloop\samples\short_sustain.wav

# Repeat for other durations
python autosamplerT.py --note_range_start C4 --note_range_end C4 \
                       --hold_time 5 --release_time 0.5 \
                       --multisample_name medium_sustain

python autosamplerT.py --note_range_start C4 --note_range_end C4 \
                       --hold_time 10 --release_time 1 \
                       --multisample_name long_sustain
```

#### Option B: Use Existing Samples

```bash
# Copy from your existing prophet6 samples
copy output\prophet6_long_test\samples\prophet6_long_test_C4_v127_backup.wav ^
     tests\autoloop\samples\long_sustain.wav
```

#### Option C: Show Instructions

```bash
python tests\autoloop\test_autoloop.py --create-samples
```

### 2. Recommended Test Samples

| Filename | Description | Duration |
|----------|-------------|----------|
| `short_sustain.wav` | Sustained note | 1-2s |
| `medium_sustain.wav` | Sustained note | 4-5s |
| `long_sustain.wav` | Sustained note | 10-15s |
| `percussive.wav` | Short attack, quick decay | <1s |
| `noisy_sustain.wav` | Sustained with background noise | 4-5s |

## Running Tests

### Run All Tests

```bash
python tests\autoloop\test_autoloop.py
```

### Run Specific Test Group

```bash
python tests\autoloop\test_autoloop.py --test basic
python tests\autoloop\test_autoloop.py --test min_duration
python tests\autoloop\test_autoloop.py --test fixed_points
python tests\autoloop\test_autoloop.py --test combined
python tests\autoloop\test_autoloop.py --test edge_cases
```

### Run Quick Tests Only

```bash
python tests\autoloop\test_autoloop.py --quick
```

### Quiet Mode

```bash
python tests\autoloop\test_autoloop.py --quiet
```

## Test Groups

### 1. Basic Tests
- Default auto-loop behavior
- Tests: 1

### 2. Minimum Duration Tests
- `--loop_min_duration "50%"` - 50% of sample length
- `--loop_min_duration "80%"` - 80% of sample length
- `--loop_min_duration "2.0"` - 2.0 seconds minimum
- `--loop_min_duration "5.0"` - 5.0 seconds minimum
- Tests: 4

### 3. Fixed Points Tests
- `--loop_start_time 2.0` - Fixed start time
- `--loop_end_time 10.0` - Fixed end time
- Both fixed start and end
- Tests: 3

### 4. Combined Tests
- Min duration + fixed start
- Min duration + fixed end
- Fixed start + fixed end + min duration
- Tests: 3

### 5. Edge Cases
- Very short percussive samples
- Noisy samples
- Tests: 2

**Total: 13 tests**

## Test Output

Results are saved in `tests/autoloop/output/`:
- Each test creates a subdirectory
- Processed samples saved with loop metadata
- Check WAV files with a sampler to verify loops

## Expected Results

### Successful Test Output

```
======================================================================
TEST SUMMARY
======================================================================

Total tests: 13
   Passed:   13
  Failed:   0
  ⚠️  Warned:   0
  ⏭️  Skipped:  0
  Errors:   0
  ⏱️  Timeouts: 0
```

### Verifying Loop Quality

Load the processed WAV files in a sampler (Sforzando, Kontakt, etc.) and:
1. Hold a note indefinitely - should sustain smoothly
2. Listen for clicks or pops at the loop point
3. Verify loop respects minimum duration requirements

**Note:** Loop points are stored in the WAV file's RIFF 'smpl' chunk. The sampler application is responsible for applying crossfade or interpolation at the loop point.

## Troubleshooting

### No Test Samples

```
⚠️  WARNING: No test samples found!

To create test samples:
  1. Run: python test_autoloop.py --create-samples
  2. Or manually place WAV files in tests/autoloop/samples/
```

**Solution**: Create test samples using one of the methods above.

### Test Timeouts

If tests timeout (>30s), check:
- Sample file size (very large files take longer)
- System performance
- Audio file corruption

### Tests Skip

Tests skip when:
- Required sample file doesn't exist
- Specific sample mentioned in test config not found

**Solution**: Create the missing sample files.

## Manual Verification

After running tests, manually verify loop quality:

```bash
# Load in Sforzando or your preferred sampler
# Check: tests/autoloop/output/basic_autoloop/*.wav
```

Good loop indicators:
- Seamless transition (no click/pop)
- Natural sustain when held
- Appropriate loop duration
- Smooth crossfade applied by the sampler

## Integration with Main Test Suite

These tests are separate from the main integration tests in `tests/test_all.py`.

To add to main suite:
1. Create samples first
2. Run: `python tests\autoloop\test_autoloop.py --quick`
3. Verify all pass before committing changes

## Future Enhancements

Potential additions:
- Automated loop quality analysis (FFT, click detection)
- Generate test samples automatically (sine waves)
- Compare before/after audio visually
- Benchmark loop-finding performance
- Test with various sample rates and bit depths
