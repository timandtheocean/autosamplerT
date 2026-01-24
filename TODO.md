# AutosamplerT - TODO List

Last Updated: January 24, 2026

---

## COMPLETED

### Ableton Live Sampler Format Export
**Status:** IMPLEMENTED - January 24, 2026

Features implemented:
- ADV file format (GZIP-compressed XML)
- Key range mapping with crossfade
- Velocity layers with crossfade (15-unit default)
- Round-robin via SelectorRange (0-127 divided by layer count)
- Loop points from WAV SMPL chunks (forward and ping-pong)
- Loop crossfade support
- Per-sample volume, pan, root key, detune

Documentation: [EXPORT_FORMATS.md](doc/EXPORT_FORMATS.md#ableton-live-sampler-format)

---

## HIGH PRIORITY - Critical Issues

### 1. Recording Latency Detection and Compensation
**Status:** NOT IMPLEMENTED - Critical timing issue
- Recordings are ~0.19s shorter than requested
- Very long recordings (10s+ hold time) cause the sampler to hang/freeze

**Observed Behavior:**
- `--hold_time 1.0 --release_time 0.5` → Expected 1.5s, Actual 1.311s
- Consistent ~190ms latency across different configurations

**Proposed Solutions:**
1. Auto-detect latency by recording silence and measuring startup time
2. Sample longer and trim in postprocessing (recommended by user)

### 2. `--audio_inputs` Not Implemented
**Status:** Argument defined but completely ignored
- Currently only records 1 (mono) or 2 (stereo) channels
- Multi-channel interface users cannot record more than stereo

### 3. `--midi_latency_adjust` Not Implemented
**Status:** Argument defined but never used
- Could cause timing issues with sample start points

### 4. `--debug` Partially Implemented
**Status:** Flag doesn't actually enable debug logging level

---

## MEDIUM PRIORITY - Testing Needed

### 5. MIDI Message Types Testing
All implemented but need comprehensive testing:
- CC Messages (7-bit) - CLI and YAML
- CC14 Messages (14-bit) - CLI and YAML
- NRPN Messages - CLI and YAML
- Program Change - CLI and YAML
- SysEx Messages - CLI and YAML
- Combined MIDI Messages in scripts

### 6. Auto-Loop Test Material
**Status:** Test framework exists, needs test samples
- Generate synthetic test samples (sine, square, sawtooth, noise)
- Test different `--loop_min_duration` values
- Test `--loop_start_time` / `--loop_end_time` parameters

---

## LOW PRIORITY - UI/UX Issues

### 9. Fix "Recent MIDI Messages" Display
**Status:** UI bug - shows duplicate lines
- Same message appears twice in display
- Should show all MIDI message types (NRPN, SysEx, CC, Program Change)

---

## LOW PRIORITY - New Feature Requests

### 10. Chord Mode for Sampling
**Status:** PLANNED
- Single file mode: entire chord into one WAV
- Multi-file mode: each note into separate files
- Chord selection by key and inversion

### 11. Simple GUI with Piano Roll
**Status:** CONCEPT
- Visual keyboard for note range selection
- YAML script generation
- HTML/JavaScript implementation

---

## LOW PRIORITY - Code Quality

### 12. Pending Code Improvements
- Improve error messages (more user-friendly)
- Add input validation for all arguments
- YAML config validation (type checking, valid values)
- Add unit tests with pytest (alongside existing integration tests)

---

## Testing Checklist

### Audio Recording
- [ ] Test `--latency_compensation` with different values
- [ ] Test `--gain` parameter
- [ ] Test different sample rates (44100, 48000, 96000)
- [ ] Test different bit depths (16, 24, 32)

### MIDI Control
- [ ] Test per-velocity-layer MIDI control
- [ ] Test per-round-robin-layer MIDI control
- [ ] Test multi-channel MIDI routing

### SFZ Output
- [ ] Test SFZ loads in Sforzando
- [ ] Test velocity switching works
- [ ] Test round-robin works
- [ ] Test loop points work

---

## Future Enhancements

- Add `--preview` mode to hear samples before saving
- Add `--parallel` processing for postprocessing
- Add progress bars for long operations
- Add `--resume` to continue interrupted sampling
- Add spectrum analyzer for noise floor detection
- Add automatic gain staging for consistent levels
