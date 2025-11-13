# Interactive Sampling

Interactive sampling allows you to pause the sampling process at specific intervals for manual intervention, such as adjusting synth parameters, changing patches, or working around hardware limitations.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Configuration Parameters](#configuration-parameters)
- [Use Cases](#use-cases)
  - [Fixed Interval Pausing](#fixed-interval-pausing)
  - [MIDI Range Mapping](#midi-range-mapping-for-limited-key-hardware)
- [Examples](#examples)

## Basic Usage

Interactive sampling is configured in the `interactive_sampling` section of your YAML script:

```yaml
interactive_sampling:
  pause_interval: 12  # Pause every 12 notes
  auto_resume: 5  # Auto-resume after 5 seconds
  prompt: "Check levels, press Enter..."
```

## Configuration Parameters

### pause_interval

- **Type:** Integer
- **Default:** 0 (disabled)
- **Description:** Pause after every N notes have been sampled
- **Previous name:** `every` (still supported for backward compatibility)

Example:
```yaml
interactive_sampling:
  pause_interval: 12  # Pause every octave
```

### auto_resume

- **Type:** Number (seconds)
- **Default:** 0 (wait for Enter key)
- **Description:** Automatically resume sampling after N seconds
  - If `0`: Wait indefinitely for user to press Enter
  - If `> 0`: Show countdown timer, resume automatically after N seconds (user can press any key to skip)
- **Previous name:** `continue` (still supported for backward compatibility)

Example:
```yaml
interactive_sampling:
  auto_resume: 10  # Auto-resume after 10 seconds
```

### midi_range

- **Type:** Dictionary with `start` and `end` keys
- **Default:** null (disabled)
- **Description:** Define the MIDI note range that your hardware can play. If this range is smaller than `note_range`, AutosamplerT will automatically repeat the MIDI notes to cover the full SFZ range.

Example:
```yaml
interactive_sampling:
  midi_range: {start: 36, end: 67}  # Hardware has 32 keys (C1-G3)
```

### pause_after_range

- **Type:** Boolean
- **Default:** false
- **Description:** When `midi_range` is enabled, pause after each complete cycle through the MIDI range. This allows you to manually adjust transpose/octave settings on hardware before continuing.

Example:
```yaml
interactive_sampling:
  midi_range: {start: 36, end: 67}
  pause_after_range: true  # Pause after each 32-note cycle
```

### prompt

- **Type:** String
- **Default:** "Paused for user intervention. Press Enter to continue..."
- **Description:** Custom message displayed during pause

Example:
```yaml
interactive_sampling:
  prompt: "Adjust filter cutoff, then press Enter..."
```

## Use Cases

### Fixed Interval Pausing

Use `pause_interval` to pause at regular intervals for checking levels, adjusting parameters, or taking breaks.

```yaml
sampling_midi:
  note_range: {start: 36, end: 96, interval: 1}  # 61 notes
  velocity_layers: 3
  roundrobin_layers: 1

interactive_sampling:
  pause_interval: 12  # Pause every octave
  auto_resume: 10  # Auto-resume after 10 seconds
  prompt: "Check levels and EQ settings..."

sampling:
  hold_time: 2.0
  release_time: 1.5
```

**Behavior:**
- Samples notes 36-47 (12 notes) → PAUSE (10 seconds)
- Samples notes 48-59 (12 notes) → PAUSE (10 seconds)
- Samples notes 60-71 (12 notes) → PAUSE (10 seconds)
- Continues until all 61 notes completed

### MIDI Range Mapping for Limited-Key Hardware

Some hardware samplers (e.g., Casio SK-1) have limited key ranges. Use `midi_range` to automatically repeat a small MIDI range across a larger SFZ range.

#### Example: Casio SK-1 (32 keys)

```yaml
sampling_midi:
  note_range: {start: 36, end: 99, interval: 1}  # 64 notes to sample
  velocity_layers: 1
  roundrobin_layers: 1

interactive_sampling:
  # SK-1 has 32 keys (C1-G3)
  midi_range: {start: 36, end: 67}
  
  # Pause after each 32-note cycle
  pause_after_range: true
  auto_resume: 0  # Wait for Enter (user needs time to adjust)
  
  prompt: "Adjust SK-1 octave up (+12 semitones), then press Enter..."

sampling:
  hold_time: 1.5
  release_time: 1.0
```

**Behavior:**
1. **Cycle 1:** Samples MIDI notes 36-67 → Records as SFZ notes 36-67
2. **PAUSE:** "Adjust SK-1 octave up (+12 semitones), then press Enter..."
3. **Cycle 2:** Samples MIDI notes 36-67 → Records as SFZ notes 68-99
4. **Done:** 64 samples using only 32 MIDI keys

#### How MIDI Range Mapping Works

When `midi_range` is defined and smaller than `note_range`:

1. AutosamplerT calculates how many times to repeat the MIDI range
2. For each SFZ note, it maps to a MIDI note using modulo arithmetic:
   ```
   midi_note = midi_range_start + (sfz_note_index % midi_range_size)
   ```
3. The display shows both MIDI and SFZ notes:
   ```
   Note ON: MIDI C1 (36) → SFZ E3 (68), Vel=127
   ```

## Examples

### Example 1: Manual Filter Sweeps

Sample with pauses to manually adjust filter cutoff at different ranges:

```yaml
sampling_midi:
  note_range: {start: 24, end: 96, interval: 2}  # 37 notes (2 notes per octave)

interactive_sampling:
  pause_interval: 12  # Pause every octave
  auto_resume: 0  # Wait for manual adjustment
  prompt: "Adjust filter cutoff, press Enter..."

sampling:
  hold_time: 3.0
  release_time: 2.0
```

### Example 2: Quick Level Checks

Sample with auto-resume for quick monitoring:

```yaml
interactive_sampling:
  pause_interval: 6  # Pause every 6 notes
  auto_resume: 3  # Auto-resume after 3 seconds
  prompt: "Checking levels..."
```

### Example 3: Akai S950 (Limited Keys)

Sample an Akai S950 that only has 12 keys assigned to samples:

```yaml
sampling_midi:
  note_range: {start: 36, end: 95, interval: 1}  # 60 notes total

interactive_sampling:
  midi_range: {start: 36, end: 47}  # S950 has 12 keys
  pause_after_range: true
  prompt: "Load next bank on S950, press Enter..."

sampling:
  hold_time: 2.0
  release_time: 1.5
```

**Result:** Samples 60 notes by cycling through the 12-key range 5 times, pausing between each cycle.

### Example 4: Combining Both Features

You can combine `pause_interval` and `midi_range`, but `pause_after_range` takes precedence:

```yaml
sampling_midi:
  note_range: {start: 36, end: 99, interval: 1}

interactive_sampling:
  # MIDI range mapping is active
  midi_range: {start: 36, end: 67}
  pause_after_range: true  # This will trigger pauses
  
  # pause_interval is ignored when midi_range is active
  pause_interval: 10
  
  auto_resume: 0
  prompt: "Adjust hardware, press Enter..."
```

## Display Information

During interactive pauses, the main sampling display shows:

- Pause message
- Progress bar (if `auto_resume > 0`)
- Remaining time countdown (if `auto_resume > 0`)
- Last 10 log messages

When MIDI range mapping is active, the display shows:

```
MIDI Note: C1 (36) → SFZ Note: E3 (68)
Velocity: 127 (Layer 1/1), RR: 1/1, Channel: 0
```

## Backward Compatibility

The old parameter names are still supported:

- `every` → use `pause_interval` instead
- `continue` → use `auto_resume` instead

```yaml
# Old format (still works)
interactive_sampling:
  every: 12
  continue: 5

# New format (recommended)
interactive_sampling:
  pause_interval: 12
  auto_resume: 5
```

## Tips

1. **For manual adjustments:** Set `auto_resume: 0` to wait indefinitely
2. **For quick checks:** Use `auto_resume: 3-5` seconds
3. **MIDI mapping:** Always use `pause_after_range: true` with `midi_range`
4. **Test mode:** Use `test_mode: true` to verify timing without recording
5. **Log output:** The last 10 log messages are visible during pauses

## Troubleshooting

**Pause not triggering:**
- Check that `pause_interval > 0` or `pause_after_range: true`
- Verify `interactive_sampling` section exists in YAML

**MIDI mapping not working:**
- Ensure `midi_range` has both `start` and `end` keys
- `midi_range` must be smaller than `note_range` to activate
- Check log output for "MIDI range mapping enabled" message

**Auto-resume not working:**
- Verify `auto_resume > 0`
- Press any key to skip countdown
- Check terminal for display updates

---

Last updated: November 13, 2025
