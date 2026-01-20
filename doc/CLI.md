# Command Line Interface (CLI)

Complete reference for AutosamplerT command-line usage.

## Overview

AutosamplerT is a command-line application that provides various modes for setup, sampling, and testing. All operations are initiated via the `python autosamplerT.py` command with different arguments.

## What It's Used For

- **Device Setup**: Configure audio and MIDI devices
- **Script Execution**: Run YAML-based sampling scripts
- **Interactive Sampling**: Perform guided sampling sessions
- **Testing**: Verify configuration and MIDI messages

## Basic Syntax

```bash
python autosamplerT.py [OPTIONS]
```

## Command-Line Arguments

### `--setup <mode>`

Configure audio and/or MIDI devices interactively.

**Syntax:**
```bash
python autosamplerT.py --setup {audio|midi|all}
```

**Modes:**
- `audio` - Configure only audio input/output devices
- `midi` - Configure only MIDI input/output ports
- `all` - Configure both audio and MIDI (default)

**Examples:**
```bash
# Setup everything (first-time setup)
python autosamplerT.py --setup all

# Setup only audio devices
python autosamplerT.py --setup audio

# Setup only MIDI devices
python autosamplerT.py --setup midi
```

**What it does:**
1. Lists available devices/ports
2. Prompts for device selection (supports fuzzy matching for MIDI)
3. Validates selections
4. Saves configuration to `conf/autosamplerT_config.yaml`

**Output:**
```
=== Audio Device Setup ===
Available audio devices:
[0] Microsoft Sound Mapper - Input
[1] Focusrite USB (input)
...
Enter input device number (or 'skip'): 1
✓ Selected input device: Focusrite USB

Saved configuration to: conf/autosamplerT_config.yaml
```

---

### `--script <path>`

Execute a YAML sampling script.

**Syntax:**
```bash
python autosamplerT.py --script <path/to/script.yaml>
```

**Path:** Relative to workspace root or absolute path.

**Examples:**
```bash
# Run a test script
python autosamplerT.py --script conf/test/test_single_note.yaml

# Run production script
python autosamplerT.py --script conf/production/my_synth.yaml

# Absolute path
python autosamplerT.py --script C:\Users\me\scripts\test.yaml
```

**What it does:**
1. Loads script and config file
2. Merges configurations
3. Displays pre-sampling summary
4. Prompts for confirmation
5. Executes sampling session
6. Generates output files (WAV + SFZ)
7. Copies script file to multisample folder for documentation

**Script Auto-Copy:**

After successful sampling, the script YAML file is automatically copied to the multisample folder:

```
output/
  MySynth/
    my_synth.yaml         # Auto-copied script file
    MySynth.sfz           # Generated SFZ file
    samples/              # Sample folder
      MySynth_C4_v127.wav
      ...
```

This documents the exact parameters used to create the multisample.

---

### `--script-folder <path>`

Process all YAML files in a folder sequentially (batch processing).

**Syntax:**
```bash
python autosamplerT.py --script-folder <path/to/folder>
```

**Path:** Relative to workspace root or absolute path.

**Examples:**
```bash
# Process all test scripts
python autosamplerT.py --script-folder conf/test

# Process production scripts with custom export
python autosamplerT.py --script-folder conf/production --export_formats qpat,waldorf_map

# Process with custom output folder
python autosamplerT.py --script-folder C:\MyScripts --output_folder D:\Samples
```

**What it does:**
1. Finds all `.yaml` and `.yml` files in the folder
2. Processes them in alphabetical order
3. Each script runs as if you called `python autosamplerT.py --script <file.yaml>`
4. Preserves these arguments:
   - `--output_folder`
   - `--export_formats`
   - `--export_location`
   - `--export_loop_mode`
   - `--export_loop_crossfade`
5. Shows progress: "Processing 3/10: my_synth.yaml"
6. Asks to continue if a script fails
7. Copies each script to its multisample folder
8. Reports final summary

**Output:**
```
=== AutosamplerT - Batch Processing ===
Found 3 YAML file(s) in: conf/test

================================================================================
Processing 1/3: test_synth_a.yaml
================================================================================

[... sampling output ...]

[SUCCESS] Script test_synth_a.yaml completed successfully

================================================================================
Processing 2/3: test_synth_b.yaml
================================================================================

[... sampling output ...]

[SUCCESS] Script test_synth_b.yaml completed successfully

================================================================================
Processing 3/3: test_synth_c.yaml
================================================================================

[... sampling output ...]

[SUCCESS] Script test_synth_c.yaml completed successfully

================================================================================
Batch processing complete: 3 file(s) processed
================================================================================
```

**Error Handling:**

If a script fails, you'll be prompted:
```
[WARNING] Script test_synth_b.yaml failed with return code 1
Continue with remaining scripts? (y/n):
```

**Use Cases:**
- Sample multiple patches overnight
- Process all test configurations
- Batch export multiple multisamples to different formats
- Run regression tests

**Output:**
```
Loading script: conf/test/test_single_note.yaml
Loading configuration from: conf/autosamplerT_config.yaml

=== Sampling Configuration Summary ===
Multisample: TestSingleNote
Total Samples: 1
Estimated Duration: ~3 seconds
Estimated Disk Space: ~2.5 MB

Proceed with sampling? (y/n): y

Starting sampling session...
Sampling note 60 (C4) at velocity 100, RR layer 1...
✓ Recorded sample: C4_v100_rr1.wav

Sampling complete!
Output: output/TestSingleNote/
```

---

### No Arguments (Interactive Mode)

Run without arguments for interactive sampling configuration.

**Syntax:**
```bash
python autosamplerT.py
```

**What it does:**
1. Loads configuration
2. Prompts for sampling parameters
3. Executes sampling session

**Note:** This mode does not support MIDI control features. Use `--script` for MIDI control.

---

## Common Workflows

### First-Time Setup Workflow

```bash
# 1. Setup devices
python autosamplerT.py --setup all

# 2. Test with single note
python autosamplerT.py --script conf/test/test_single_note.yaml

# 3. Verify output files
ls output/TestSingleNote/
```

### Production Sampling Workflow

```bash
# 1. Verify MIDI setup (if using MIDI control)
python autosamplerT.py --setup midi

# 2. Run sampling script
python autosamplerT.py --script conf/production/synth_bass.yaml

# 3. Check output
ls output/synth_bass/
```

### Testing MIDI Messages Workflow

```bash
# 1. Setup virtual MIDI cable (loopMIDI on Windows)
# 2. Start MIDI monitor in separate terminal
receivemidi dev "loopMIDI Port 1"

# 3. Configure AutosamplerT to use virtual port
python autosamplerT.py --setup midi
# Select: loopMIDI Port 1 for output

# 4. Run test script
python autosamplerT.py --script conf/test/test_roundrobin_cc.yaml

# 5. Monitor MIDI messages in receivemidi terminal
```

### Quick Audio Test Workflow

```bash
# Test audio setup only (no sampling)
python autosamplerT.py --setup audio

# If devices work, proceed with sampling
python autosamplerT.py --script conf/test/test_single_note.yaml
```

### Change MIDI Device Workflow

```bash
# Setup new MIDI device (audio unchanged)
python autosamplerT.py --setup midi

# Enter new device name (fuzzy matching supported)
Enter MIDI output port: OP-1

# Test with script
python autosamplerT.py --script conf/test/test_program_change.yaml
```

## Interactive Prompts

### Pre-Sampling Summary

Before starting sampling, AutosamplerT displays a summary:

```
=== Sampling Configuration Summary ===

Multisample: MySynth_MultiSample
Output Directory: output/MySynth_MultiSample/samples/

Notes to Sample: 16 notes (C2 to C7, every 4 semitones)
Velocity Layers: 3 (40, 80, 120)
Round-Robin Layers: 4
Total Samples: 192

Estimated Duration: ~16 minutes
Estimated Disk Space: ~480 MB

Recording Parameters:
  Hold: 2.0s | Release: 2.0s | Pause: 0.5s | Total: 4.5s per sample

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

**Actions:**
- Type `y` or `yes` to proceed
- Type `n` or `no` to cancel
- Press Ctrl+C to abort

### Device Selection

During setup, you'll be prompted for device selection:

```
Available MIDI Output Ports:
[0] loopMIDI Port 1
[1] OP-1 Field 0
[2] Microsoft GS Wavetable Synth

Enter MIDI output port name or number (or 'skip' to keep current):
```

**Options:**
- Enter number: `1`
- Enter exact name: `OP-1 Field 0`
- Enter partial name: `op-1` (fuzzy matching)
- Skip: `skip` (keeps current device)

## Output Files

### Directory Structure

```
output/
  <multisample_name>/
    <multisample_name>.sfz
    samples/
      <multisample_name>_C2_v40_rr1.wav
      <multisample_name>_C2_v40_rr2.wav
      ...
```

### File Naming Convention

```
<multisample_name>_<note>_v<velocity>_rr<layer>.wav
```

Examples:
- `MySynth_C4_v100_rr1.wav` - C4, velocity 100, round-robin 1
- `MySynth_A#3_v80_rr2.wav` - A#3, velocity 80, round-robin 2

## Exit Codes

- `0` - Success
- `1` - Error (configuration, device not found, etc.)
- `130` - User interrupt (Ctrl+C)

## Error Handling

### Configuration Not Found

```
Error: Configuration file not found
```

**Solution:**
```bash
python autosamplerT.py --setup all
```

### Script Not Found

```
Error: Script file not found: conf/test/missing.yaml
```

**Solution:** Check file path and ensure file exists.

### Device Not Available

```
Error: MIDI output port not available
```

**Solution:**
```bash
python autosamplerT.py --setup midi
```

### YAML Syntax Error

```
Error: YAML parsing failed
```

**Solution:** Check script YAML syntax. Use YAML validator.

## Environment Variables

Currently, AutosamplerT does not use environment variables. All configuration is in `conf/autosamplerT_config.yaml`.

## Logging

AutosamplerT outputs to stdout with different log levels:

- **INFO**: Normal operations (MIDI messages, sampling progress)
- **WARNING**: Non-critical issues
- **ERROR**: Critical errors

**Example output:**
```
INFO: MIDI Controller initialized
INFO: Sending CC: controller=74, value=30
INFO: Sending Program Change: program=0
INFO: Sampling note 60 (C4) at velocity 40, RR layer 1...
INFO: Recorded sample: MySynth_C4_v40_rr1.wav
```

## Best Practices

1. **Always setup first**: Run `--setup` before first use
2. **Test with single note**: Use `test_single_note.yaml` to verify setup
3. **Use virtual MIDI for testing**: Test MIDI messages without hardware
4. **Review summary**: Always review pre-sampling summary before proceeding
5. **Monitor disk space**: Check estimated disk space in summary
6. **Use absolute paths carefully**: Prefer relative paths from workspace root

## Tips & Tricks

### Quick Device Check
```bash
# List devices without changing configuration
python -m mido.ports
python -m sounddevice
```

### Skip All Audio Setup
```bash
# Setup only MIDI, leave audio untouched
python autosamplerT.py --setup midi
```

### Test MIDI Without Sampling
```bash
# Use receivemidi to monitor MIDI output
receivemidi dev "loopMIDI Port 1"

# In another terminal
python autosamplerT.py --script conf/test/test_roundrobin_cc.yaml
```

### Batch Multiple Scripts

**Recommended: Use --script-folder**
```bash
# Process all scripts in folder
python autosamplerT.py --script-folder conf/production

# With export options
python autosamplerT.py --script-folder conf/test --export_formats qpat,waldorf_map --export_loop_crossfade 12.5
```

**Alternative: Shell loops**
```bash
# Windows PowerShell
Get-ChildItem conf\production\*.yaml | ForEach-Object {
    python autosamplerT.py --script $_.FullName
}

# Linux/Mac
for script in conf/production/*.yaml; do
    python autosamplerT.py --script "$script"
done
```

## Related Documentation

- [Setup & Configuration](SETUP.md) - Device configuration details
- [Scripting System](SCRIPTING.md) - YAML script reference
- [MIDI Control](MIDI_CONTROL_FEATURE.md) - MIDI message configuration

---

*Last updated: November 11, 2025*
