# AutosamplerT - TODO List

---

## Recently Completed Features ✅

### 1. [COMPLETED] Postprocessing - FULLY IMPLEMENTED
**Status:** Complete with all CLI arguments working
- All `--process` and `--process_*` arguments now execute correctly
- Full integration between `autosamplerT.py` main() and `postprocess.py`
- **Features Working:**
  - `--process NAME` - Process existing multisample by name
  - `--process_folder PATH` - Process samples in folder
  - `--patch_normalize` - Normalize patch (maintains relative dynamics)
  - `--sample_normalize` - Normalize individual samples
  - `--trim_silence` - Trim silence from start/end
  - `--auto_loop` - Find loop points using autocorrelation
  - `--dc_offset_removal` - Remove DC offset
  - `--crossfade_loop MS` - Crossfade loop points
  - `--convert_bitdepth BITS` - Convert bit depth
  - `--dither` - Apply dithering when converting
  - `--backup` - Create backup before processing

### 2. [COMPLETED] Help System - REORGANIZED AND ENHANCED
**Status:** Complete with practical examples and clean organization
- Main help shows common workflows and links to detailed help
- New `--help examples` with 11 practical sampling examples
- Separate help sections: audio, midi, sampling, postprocessing, examples
- No longer cluttered with all arguments in main view

### 3. [COMPLETED] SysEx Format - SIMPLIFIED
**Status:** Complete with user-friendly format
- Users provide data bytes WITHOUT F0/F7 (auto-added by code)
- Semicolon separates multiple messages: `"43 10 7F 1C 00;41 10 00 20 12"`
- Works correctly with PowerShell (no JSON escaping issues)
- CLI and YAML documentation updated

### 4. [COMPLETED] `--note_range` JSON PARSING - FIXED AND TESTED
**Status:** FIXED - Replaced with separate arguments, fully tested
- **Old (broken):** `--note_range '{\"start\":60,\"end\":60,\"interval\":1}'`
- **New (working):** `--note_range_start C4 --note_range_end C4 --note_range_interval 1`

**Solution Implemented:**
- Added `--note_range_start NOTE` - Accepts MIDI numbers (0-127) or note names (C2, A#4, Bb3)
- Added `--note_range_end NOTE` - Accepts MIDI numbers or note names
- Added `--note_range_interval N` - Interval between notes (1=chromatic, 12=octaves)
- Includes `note_name_to_midi()` function for parsing note names with sharp/flat support

**Testing Results:**
- [PASS] Works: `--note_range_start C4 --note_range_end C4 --note_range_interval 1`
- [PASS] Works: `--note_range_start 60 --note_range_end 60 --note_range_interval 1`
- [PASS] Works: `--note_range_start A#3 --note_range_end C#5 --note_range_interval 3`
- [PASS] Tested in regression suite (basic group, 4 tests passing)

### 5. [COMPLETED] VELOCITY LAYERS - FULLY IMPLEMENTED AND TESTED
**Status:** Complete with logarithmic distribution, custom splits, and minimum velocity
- **Features:**
  - Automatic logarithmic distribution (more density at higher velocities)
  - Custom split points: `--velocity_layers_split 50,90` for precise control
  - Minimum velocity: `--velocity_minimum 45` to skip very soft samples
  - Single velocity layer support
  
**Implementation Details:**
- Logarithmic curve: `math.pow(2.0, position)` for musical velocity distribution
- Validation: split count = layers - 1, ascending order, range 1-127
- SFZ generation: proper lovel/hivel ranges calculated from split points
- WAV metadata: velocity stored in RIFF 'note' chunk (3-byte format)

**Testing Results:**
- [PASS] 4 layers automatic: samples at 1, 33, 75, 127
- [PASS] 4 layers with min 45: samples at 45, 66, 93, 127
- [PASS] 3 layers custom splits 50,90: samples at 25, 70, 108
- [PASS] Single layer with velocity 100
- [PASS] Multiple notes × velocity layers
- [PASS] Added to regression suite (velocity group, 5 tests passing)

### 6. [COMPLETED] ROUND-ROBIN LAYERS - FULLY IMPLEMENTED AND TESTED
**Status:** Complete with proper SFZ seq_length/seq_position
- **Features:**
  - Multiple round-robin layers: `--roundrobin_layers 3`
  - Proper SFZ formatting with seq_length and seq_position
  - WAV metadata removed (was in RIFF chunk, removed per user request)
  
**Testing Results:**
- [PASS] 2 RR layers, single note
- [PASS] 2 RR layers × multiple notes
- [PASS] Combined with velocity layers (3 vel × 2 RR = 6 samples)
- [PASS] Added to regression suite (roundrobin group, 2 tests; combined group, 2 tests)

### 7. [COMPLETED] MONO/STEREO RECORDING - FULLY IMPLEMENTED AND TESTED
**Status:** Complete with channel selection
- **Features:**
  - Stereo recording (default): `--mono_stereo stereo`
  - Mono left channel: `--mono_stereo mono --mono_channel 0`
  - Mono right channel: `--mono_stereo mono --mono_channel 1`
  
**Testing Results:**
- [PASS] Mono left: creates 1-channel WAV
- [PASS] Mono right: creates 1-channel WAV
- [PASS] Stereo: creates 2-channel WAV
- [PASS] Added to regression suite (audio group, 3 tests passing)

### 8. [COMPLETED] WAV METADATA - IMPLEMENTED (3-BYTE FORMAT)
**Status:** Custom RIFF 'note' chunk with note, velocity, channel
- **Format:** 3 bytes per chunk (note, velocity, MIDI channel)
- **Round-robin removed:** Per user request, RR metadata not stored in WAV
- **Tool:** `verify_wav_metadata.py` to inspect RIFF chunks
  
**Testing Results:**
- [PASS] Verified with `verify_wav_metadata.py`
- [PASS] Added to regression suite (metadata group, 1 test)

### 9. [COMPLETED] COMPREHENSIVE REGRESSION TEST SUITE - CREATED
**Status:** Complete with 17 tests across 6 groups
- **Test Script:** `test_all.py` (Python) and `test_all.ps1` (PowerShell)
- **Groups:** basic (4), velocity (5), roundrobin (2), combined (2), audio (3), metadata (1)
- **Features:**
  - Automatic cleanup of existing test directories
  - Sample count verification
  - WAV metadata validation
  - Quick mode for faster testing
  - Group-specific testing
  - Detailed pass/fail reporting with timing
  
**Usage:**
```bash
python test_all.py              # Run all 17 tests
python test_all.py --quick      # Run 11 quick tests
python test_all.py --group velocity  # Run velocity tests only
```

**Testing Results:**
- [PASS] All 17 tests passing
- [PASS] Quick mode: 11 tests in ~150s
- [PASS] Documentation updated in README.md

---

## Major Issues - Not Implemented

### 8. `--audio_inputs` - NOT IMPLEMENTED
**Status:** Argument defined but completely ignored by sampler
- Currently: Only records 1 (mono) or 2 (stereo) channels
- Expected: Should support 1, 2, 4, or 8 channel recording
- **Impact:** Multi-channel interface users cannot record more than stereo

**Current code:**
```python
# autosamplerT.py defines it
audio.add_argument('--audio_inputs', type=int, choices=[1, 2, 4, 8])

# But sampler.py completely ignores it:
self.channels = 2 if self.mono_stereo == 'stereo' else 1  # WRONG!
```

**Required Fix:**
- Read `audio_inputs` from config in sampler.py
- Use it to set recording channels
- Handle multi-channel WAV file writing
- Update SFZ generation for multi-channel samples

---

### 9. [HIGH PRIORITY] RECORDING LATENCY DETECTION AND COMPENSATION - NOT IMPLEMENTED
**Status:** Critical timing issue - recordings are ~0.19s shorter than requested
- **Observed Behavior:**
  - `--hold_time 1.0 --release_time 0.5` → Expected 1.5s, Actual 1.311s (0.189s short)
  - `--hold_time 2.0 --release_time 2.5` → Expected 4.5s, Actual 4.311s (0.189s short)
  - Consistent ~190ms latency across different timing configurations
  - Very long recordings (10s+ hold time) cause the sampler to hang/freeze
- **Root Causes:**
  - MIDI → audio interface startup latency
  - Audio interface buffer latency
  - MIDI note-on processing delay
  - Recording buffer startup time
- **Impact:** 
  - Hold times are NOT exact as requested
  - Long recordings (>10s) freeze/hang
  - Users cannot get precise sample durations
  - Sustain portions may be cut too short

**Proposed Solutions:**
1. **Auto-detect latency** (RECOMMENDED):
   - Record silent audio with no MIDI note
   - Measure time until first non-zero sample
   - Store latency value and add to requested durations
   - Run calibration on first use or when config changes
   
2. **Sample longer and trim** (ALTERNATIVE):
   - Always record `hold_time + release_time + latency_buffer`
   - Add extra 0.5s buffer to all recordings
   - Trim to exact length in postprocessing
   - Use amplitude envelope detection to find note start
   - Pros: More reliable, handles variable latency
   - Cons: Requires postprocessing step

3. **Fix hanging on long recordings**:
   - Investigate why >10s recordings freeze
   - May be audio buffer overflow
   - May be MIDI timeout issue
   - Add timeout handling and error recovery

**Required Implementation:**
```python
# In sampler.py - Auto-detect latency method:
def _calibrate_latency(self):
    """Measure system recording latency."""
    # Record 1 second of silence (no MIDI)
    # Find first non-zero sample
    # Calculate latency = first_sample_index / samplerate
    # Store in config for future use
    
# Apply latency compensation:
def record_sample(...):
    actual_duration = hold_time + release_time + self.latency_compensation
    recording = sd.rec(actual_duration, ...)
```

**Testing Required:**
- Verify latency is consistent across multiple runs
- Test with different audio interfaces
- Test with different buffer sizes
- Verify long recordings (10s+) don't hang
- Validate trimmed samples have exact requested duration

**User Request:** "The hold times must be exact. Probably better to sample longer and cut it right after sampling?"

### 10. `--midi_latency_adjust` - NOT IMPLEMENTED
**Status:** Argument defined but never used
- **Impact:** Cannot compensate for MIDI interface latency
- Could cause timing issues with sample start points

**Required Fix:**
- Add to sampler.py: `self.midi_latency = self.midi_config.get('midi_latency_adjust', 0.0)`
- Apply delay before `sd.rec()` or adjust recording trim

---



### 11. `--debug` - PARTIALLY IMPLEMENTED
**Status:** Argument defined but doesn't control logging level
- Code uses `logging.debug()` throughout
- But `--debug` flag doesn't actually enable debug logging
- **Impact:** Debug messages never show even with `--debug`

**Current State:**
```python
# Logging statements exist:
logging.debug(f"Recording {duration}s...")

# But --debug flag isn't used to set log level
```

**Required Fix:**
```python
# In autosamplerT.py or sampler.py:
if config['audio_interface'].get('debug'):
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
```

---

## Minor Issues - Needs Testing

---

### 12. [WARNING] `--latency_compensation` - NEEDS TESTING
**Status:** Implemented but untested
- Code exists in sampler.py line 454
- Trims samples based on latency value
- **Impact:** May not work correctly with all interfaces

**Testing Required:**
- Test with known latency values
- Verify samples start at correct point
- Test with different audio interfaces

---

### 13. [WARNING] `--sample_name` - PARTIALLY IMPLEMENTED, NEEDS TESTING
**Status:** Fully implemented and tested
- Allows selecting left (0) or right (1) channel for mono recording
- **Testing Results:**
  - [PASS] Works with `--mono_stereo mono --mono_channel 0` (left channel)
  - [PASS] Works with `--mono_stereo mono --mono_channel 1` (right channel)
  - [PASS] Verified WAV files have correct channel count (1 for mono, 2 for stereo)
  - [PASS] Added to regression suite (audio group, 3 tests passing)
  - [PASS] Logging correctly shows "Channels: 1 (mono, using left/right channel)"

**Status:** Used as template but unclear how it works
- Code: `base_name = self.sampling_config.get('sample_name', self.multisample_name)`
- **Testing Required:**
  - What template variables are supported?
  - Can you use `{note}`, `{velocity}`, etc.?
  - Is this documented?

---

### 14. [WARNING] MIDI Control Arguments - NEEDS COMPREHENSIVE TESTING
**Status:** Implemented but complex, needs validation
- `--sysex_messages` - SysEx message parsing and sending (space-separated hex strings)
- `--program_change` - Program change before sampling
- `--cc_messages` - CC message parsing (format: "cc,value;cc,value")
- `--cc14_messages` - 14-bit CC message parsing (format: "cc,msb,lsb;cc,msb,lsb")
- `--midi_channels` - Multi-channel support

**Testing Required:**
- Test with real hardware synths
- Verify SysEx message format and execution
- Test multi-channel MIDI routing
- Validate CC message parsing from JSON
- Test per-layer MIDI control (velocity_midi_control, roundrobin_midi_control)

---

### 15. [WARNING] SFZ Generation - NEEDS VALIDATION
**Status:** Implemented but complex
- `--lowest_note` and `--highest_note` - Key mapping range
- Multi-velocity layer support
- Round-robin layer support
- Loop points stored in WAV RIFF 'smpl' chunk (not in SFZ file)

**Testing Required:**
- Test generated SFZ files load correctly in samplers
- Verify velocity layer crossfading
- Test round-robin triggering
- Validate loop points read from WAV RIFF 'smpl' chunk by samplers

---

## Documentation Issues

### 16. [DOCS] Missing Documentation
- `--sample_name` template syntax not documented
- `--audio_inputs` is documented but doesn't work (REMOVE from docs!)
- MIDI latency compensation workflow not explained
- Multi-channel recording workflow not documented

---

## Configuration File Issues

### 17. [WARNING] YAML Config Validation
**Status:** Config files loaded but not validated
- Missing keys might cause crashes
- Type validation not performed
- Invalid values not caught early

**Example Issues:**
```yaml
audio_interface:
  bitdepth: 99  # Should be 16, 24, or 32 - NOT VALIDATED
  samplerate: "fast"  # Should be integer - NOT VALIDATED
```

---

## Summary by Priority

### COMPLETED FEATURES
1. **Note range parsing** - Works with note names and MIDI numbers
2. **Velocity layers** - Logarithmic distribution, custom splits, minimum velocity
3. **Round-robin layers** - Full SFZ support with seq_length/seq_position
4. **Mono/stereo recording** - Channel selection working
5. **WAV metadata** - 3-byte RIFF chunk (note, velocity, channel)
6. **Regression test suite** - 17 tests across 6 groups, all passing
7. **Documentation** - Updated README and QUICKSTART with examples

###  HIGH PRIORITY - BROKEN FEATURES
1. **Postprocessing not working at all** - All CLI args ignored
2. **`--audio_inputs` broken** - Misleading users, doesn't work
3. **`--debug` doesn't enable debug logs** - Confusing behavior

###  MEDIUM PRIORITY - MISSING FEATURES
4. **`--midi_latency_adjust`** - Could affect timing accuracy
5. **Config validation** - Could prevent crashes

###  LOW PRIORITY - NEEDS TESTING
7. **MIDI control features** - Complex but likely working
8. **SFZ generation** - Likely working but needs validation with real samplers
9. **`--latency_compensation`** - Implemented but untested
10. **`--sample_name` templates** - Unclear documentation

---

## Testing Checklist

### Audio Recording
- [x] Test mono recording with `--mono_channel 0` (left) 
- [x] Test mono recording with `--mono_channel 1` (right) 
- [x] Test stereo recording 
- [ ] Test `--latency_compensation` with different values
- [ ] Test `--gain` parameter
- [ ] Test different sample rates (44100, 48000, 96000)
- [ ] Test different bit depths (16, 24, 32)

### MIDI Control
- [ ] Test `--program_change` with hardware synth
- [ ] Test `--cc_messages` semicolon-separated format parsing and sending
- [ ] Test `--cc14_messages` 14-bit CC format parsing and sending
- [ ] Test `--sysex_messages` space-separated hex string parsing
- [ ] Test per-velocity-layer MIDI control
- [ ] Test per-round-robin-layer MIDI control
- [ ] Test multi-channel MIDI routing

### Sampling
- [x] Test velocity layers (1, 2, 3, 4) 
- [x] Test round-robin layers (1, 2, 3) 
- [x] Test combined velocity + round-robin 
- [ ] Test `--test_mode` (no recording)
- [ ] Test note range with different intervals
- [ ] Test `--hold_time`, `--release_time`, `--pause_time`

### Postprocessing (AFTER FIX)
- [ ] Test `--process` by name
- [ ] Test `--process_folder` by path
- [ ] Test `--patch_normalize`
- [ ] Test `--sample_normalize`
- [ ] Test `--trim_silence`
- [ ] Test `--auto_loop`
- [ ] Test `--crossfade_loop`
- [ ] Test `--dc_offset_removal`
- [ ] Test `--convert_bitdepth` with dithering
- [ ] Test `--backup` creates backups

### SFZ Output
- [ ] Test SFZ loads in Sforzando
- [ ] Test velocity switching works
- [ ] Test round-robin works
- [ ] Test loop points work
- [ ] Test `--lowest_note` and `--highest_note` mapping

### Configuration Files
- [ ] Test loading `autosamplerT_config.yaml`
- [ ] Test loading `autosamplerT_script.yaml`
- [ ] Test CLI args override config file
- [ ] Test script YAML overrides config YAML
- [ ] Test all example configs in `conf/examples/`

---

## Performance Issues

### 18. Potential Performance Concerns
- **Auto-looping algorithm** - Autocorrelation may be slow for long samples
- **Patch normalization** - Loads all samples into memory
- **Multi-channel recording** - May cause buffer underruns

**Testing Required:**
- Profile with large sample sets (100+ samples)
- Test with long samples (10+ seconds)
- Monitor memory usage during patch normalize

---

## Future Enhancements (Not Bugs)

### 19.  Nice-to-Have Features
- [ ] Add `--preview` mode to hear samples before saving
- [ ] Add `--parallel` processing for postprocessing
- [ ] Add progress bars for long operations
- [ ] Add `--resume` to continue interrupted sampling
- [ ] Add `--export` formats beyond WAV/SFZ (EXS24, Ableton)
- [ ] Add spectrum analyzer for noise floor detection
- [ ] Add automatic gain staging for consistent levels

---

## Code Quality Issues

### 20.  Code Cleanup Needed
- [x] Remove unused imports - COMPLETED (removed wavfile, parse_cc_messages, parse_cc14_messages from sampler.py)
- [x] Add type hints consistently - COMPLETED (added to autosamplerT.py, sampler.py, audio_interface_manager.py, midi_interface_manager.py)
- [ ] Improve error messages (more user-friendly)
- [ ] Add input validation for all arguments
- [ ] Separate concerns better (large functions)
- [ ] Add unit tests for core functions
- [ ] Add integration tests for full workflows

---

## Testing Infrastructure

### 21. 📋 Add pytest for Unit Tests (WHILE keeping integration tests)
**Status:** Planned - complement existing integration tests
- **Current State:**
  - ✅ Integration tests working well (`tests/test_all.py` - 17 tests, 6 groups)
  - ❌ No unit tests for individual functions
  
**Goal:** Add pytest-based unit tests alongside existing integration tests

**Proposed Structure:**
```
tests/
├── integration/          # Move existing tests here
│   ├── test_all.py      # Current integration test suite
│   ├── test_all.ps1
│   ├── test_autoloop.py
│   └── ...
├── unit/                # New unit tests
│   ├── test_velocity_calculation.py
│   ├── test_midi_parsing.py
│   ├── test_sfz_generation.py
│   ├── test_note_name_parsing.py
│   └── test_audio_processing.py
├── conftest.py          # Shared pytest fixtures
└── pytest.ini           # Pytest configuration
```

**Unit Test Targets:**
1. **autosamplerT.py:**
   - `note_name_to_midi()` - Test note name parsing (C4, A#3, Bb5, etc.)
   - Argument validation logic
   - Config merging logic

2. **sampler_velocity.py:**
   - `calculate_velocity_values()` - Test logarithmic distribution
   - `parse_velocity_split()` - Test split point parsing
   - Velocity validation logic

3. **sampler_midicontrol.py:**
   - `parse_cc_messages()` - Test semicolon-separated format
   - `parse_cc14_messages()` - Test MSB/LSB parsing
   - `parse_sysex_messages()` - Test hex string parsing

4. **SFZ generation:**
   - Region generation logic
   - Velocity layer mapping
   - Round-robin seq_position logic

5. **Audio processing:**
   - Trim silence detection
   - Auto-loop point finding
   - Normalization calculations

**Benefits:**
- ✅ Fast feedback (unit tests run in milliseconds)
- ✅ Precise error location (know exact function failing)
- ✅ Test edge cases easily (invalid inputs, boundary conditions)
- ✅ Code coverage metrics
- ✅ Mocking support (test without audio hardware)
- ✅ Parallel test execution
- ✅ CI/CD integration ready
- ✅ Keep existing integration tests for end-to-end validation

**Implementation Steps:**
1. Install pytest: `pip install pytest pytest-cov`
2. Create `tests/conftest.py` with shared fixtures
3. Create `tests/pytest.ini` for configuration
4. Move existing tests to `tests/integration/`
5. Create `tests/unit/` with initial unit tests
6. Add pytest commands to documentation
7. Optional: Add GitHub Actions for CI

**Example Unit Test:**
```python
# tests/unit/test_note_name_parsing.py
import pytest
from autosamplerT import note_name_to_midi

def test_note_name_to_midi_basic():
    assert note_name_to_midi("C4") == 60
    assert note_name_to_midi("A4") == 69

def test_note_name_to_midi_sharps():
    assert note_name_to_midi("C#4") == 61
    assert note_name_to_midi("A#3") == 58

def test_note_name_to_midi_flats():
    assert note_name_to_midi("Db4") == 61
    assert note_name_to_midi("Bb3") == 58

def test_note_name_to_midi_invalid():
    assert note_name_to_midi("X4") is None
    assert note_name_to_midi("C99") is None
```

**Running Tests:**
```bash
# Run all tests (unit + integration)
pytest

# Run only unit tests (fast)
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=src --cov-report=html

# Run in parallel
pytest -n auto
```

---

## End of TODO List

Last Updated: 2025-11-10
Version: 2.0 - Major features implemented (velocity layers, round-robin, mono/stereo, regression tests)
