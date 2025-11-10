# AutosamplerT - TODO List

## Critical Issues - Not Implemented

### 1. Postprocessing Arguments - COMPLETELY NOT IMPLEMENTED
**Status:** Arguments defined but NO CODE EXECUTION PATH
- All `--process` and `--process_*` arguments are parsed but never executed
- No integration between `autosamplerT.py` main() and `postprocess.py`
- **Impact:** Users cannot use ANY postprocessing features from CLI

**Arguments affected:**
- `--process NAME` - Process existing multisample by name
- `--process_folder PATH` - Process samples in folder
- `--patch_normalize` - Normalize patch (postprocessing mode)
- `--sample_normalize` - Normalize samples (postprocessing mode)
- `--trim_silence` - Trim silence (postprocessing mode)
- `--auto_loop` - Find loop points (postprocessing mode)
- `--dc_offset_removal` - Remove DC offset (postprocessing mode)
- `--crossfade_loop MS` - Crossfade loop points
- `--convert_bitdepth BITS` - Convert bit depth
- `--dither` - Apply dithering
- `--backup` - Create backup before processing

**Required Fix:**
```python
# In autosamplerT.py main(), need to add before "Run sampling":
if args.process or args.process_folder:
    # Import PostProcessor
    from src.postprocess import PostProcessor
    
    # Build operations dict from args
    # Get sample paths from process_folder or construct from process name
    # Execute PostProcessor.process_samples()
    sys.exit(0)
```

---

## Major Issues - Not Implemented

### 2. `--note_range` JSON PARSING ISSUE ON WINDOWS POWERSHELL
**Status:** Argument works with YAML files but fails with CLI on PowerShell
- PowerShell escaping of JSON strings doesn't work: `--note_range '{\"start\":60,\"end\":60,\"interval\":1}'`
- **Impact:** Users on Windows cannot use `--note_range` from command line
- **Workaround:** Use `--script` with YAML file instead

**Testing Results:**
- ❌ Failed: `--note_range '{\"start\":60,\"end\":60,\"interval\":1}'` (ignored, uses default 36-96)
- ✅ Works: Script YAML with `note_range: {start: 60, end: 60, interval: 1}`

**Possible Solutions:**
1. Add `--start_note`, `--end_note`, `--interval` as separate arguments
2. Improve JSON parsing/error handling with better shell escaping docs
3. Detect shell and provide platform-specific escaping hints

---

### 3. `--audio_inputs` - NOT IMPLEMENTED
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

### 3. `--midi_latency_adjust` - NOT IMPLEMENTED
**Status:** Argument defined but never used
- **Impact:** Cannot compensate for MIDI interface latency
- Could cause timing issues with sample start points

**Required Fix:**
- Add to sampler.py: `self.midi_latency = self.midi_config.get('midi_latency_adjust', 0.0)`
- Apply delay before `sd.rec()` or adjust recording trim

---

### 4. `--script_mode` - NOT IMPLEMENTED
**Status:** Argument defined but never checked
- Unclear what behavior difference this should have
- **Impact:** Unknown - needs clarification

**Required Clarification:**
- What should `--script_mode` do differently from normal mode?
- Should it suppress prompts? Change output format? Batch process?

---

### 5. `--debug` - PARTIALLY IMPLEMENTED
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

### 6. ⚠️ `--latency_compensation` - NEEDS TESTING
**Status:** Implemented but untested
- Code exists in sampler.py line 454
- Trims samples based on latency value
- **Impact:** May not work correctly with all interfaces

**Testing Required:**
- Test with known latency values
- Verify samples start at correct point
- Test with different audio interfaces

---

### 7. ⚠️ `--mono_channel` - NEWLY ADDED, NEEDS TESTING
**Status:** Just implemented
- Allows selecting left (0) or right (1) channel for mono recording
- **Testing Required:**
  - Test with stereo interface
  - Verify correct channel is extracted
  - Test in combination with `--mono_stereo mono`

---

### 8. ⚠️ `--sample_name` - PARTIALLY IMPLEMENTED, NEEDS TESTING
**Status:** Used as template but unclear how it works
- Code: `base_name = self.sampling_config.get('sample_name', self.multisample_name)`
- **Testing Required:**
  - What template variables are supported?
  - Can you use `{note}`, `{velocity}`, etc.?
  - Is this documented?

---

### 9. ⚠️ MIDI Control Arguments - NEEDS COMPREHENSIVE TESTING
**Status:** Implemented but complex, needs validation
- `--sysex_messages` - SysEx message parsing and sending
- `--program_change` - Program change before sampling
- `--cc_messages` - JSON CC message parsing
- `--midi_channels` - Multi-channel support

**Testing Required:**
- Test with real hardware synths
- Verify SysEx message format and execution
- Test multi-channel MIDI routing
- Validate CC message parsing from JSON
- Test per-layer MIDI control (velocity_midi_control, roundrobin_midi_control)

---

### 10. ⚠️ SFZ Generation - NEEDS VALIDATION
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

### 11. 📝 Missing Documentation
- `--sample_name` template syntax not documented
- `--audio_inputs` is documented but doesn't work (REMOVE from docs!)
- MIDI latency compensation workflow not explained
- Multi-channel recording workflow not documented

---

## Configuration File Issues

### 12. ⚠️ YAML Config Validation
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

### 🔴 HIGH PRIORITY - BROKEN FEATURES
1. **Postprocessing not working at all** - All CLI args ignored
2. **`--audio_inputs` broken** - Misleading users, doesn't work
3. **`--debug` doesn't enable debug logs** - Confusing behavior

### 🟡 MEDIUM PRIORITY - MISSING FEATURES
4. **`--midi_latency_adjust`** - Could affect timing accuracy
5. **`--script_mode`** - Purpose unclear, needs definition
6. **Config validation** - Could prevent crashes

### 🟢 LOW PRIORITY - NEEDS TESTING
7. **MIDI control features** - Complex but likely working
8. **SFZ generation** - Likely working but needs validation
9. **`--latency_compensation`** - Implemented but untested
10. **`--mono_channel`** - Just added, needs testing
11. **`--sample_name` templates** - Unclear documentation

---

## Testing Checklist

### Audio Recording
- [ ] Test mono recording with `--mono_channel 0` (left)
- [ ] Test mono recording with `--mono_channel 1` (right)
- [ ] Test stereo recording
- [ ] Test `--latency_compensation` with different values
- [ ] Test `--gain` parameter
- [ ] Test different sample rates (44100, 48000, 96000)
- [ ] Test different bit depths (16, 24, 32)

### MIDI Control
- [ ] Test `--program_change` with hardware synth
- [ ] Test `--cc_messages` JSON parsing and sending
- [ ] Test `--sysex_messages` hex string parsing
- [ ] Test per-velocity-layer MIDI control
- [ ] Test per-round-robin-layer MIDI control
- [ ] Test multi-channel MIDI routing

### Sampling
- [ ] Test velocity layers (1, 2, 3, 4)
- [ ] Test round-robin layers (1, 2, 3)
- [ ] Test combined velocity + round-robin
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
- [ ] Test SFZ loads in Kontakt
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

### 13. 🐌 Potential Performance Concerns
- **Auto-looping algorithm** - Autocorrelation may be slow for long samples
- **Patch normalization** - Loads all samples into memory
- **Multi-channel recording** - May cause buffer underruns

**Testing Required:**
- Profile with large sample sets (100+ samples)
- Test with long samples (10+ seconds)
- Monitor memory usage during patch normalize

---

## Future Enhancements (Not Bugs)

### 14. 💡 Nice-to-Have Features
- [ ] Add `--preview` mode to hear samples before saving
- [ ] Add `--metadata` flag to embed more info in WAV files
- [ ] Add `--parallel` processing for postprocessing
- [ ] Add progress bars for long operations
- [ ] Add `--resume` to continue interrupted sampling
- [ ] Add `--export` formats beyond WAV/SFZ (EXS24, Kontakt)
- [ ] Add spectrum analyzer for noise floor detection
- [ ] Add automatic gain staging for consistent levels

---

## Code Quality Issues

### 15. 🧹 Code Cleanup Needed
- [ ] Remove unused imports
- [ ] Add type hints consistently
- [ ] Improve error messages (more user-friendly)
- [ ] Add input validation for all arguments
- [ ] Separate concerns better (large functions)
- [ ] Add unit tests for core functions
- [ ] Add integration tests for full workflows

---

## End of TODO List

Last Updated: 2025-11-09
Version: 1.0
