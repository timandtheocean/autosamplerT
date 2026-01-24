# AutosamplerT Command Cheatsheet

Quick reference for common AutosamplerT commands.

---

## Setup

### Activate Virtual Environment
```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# Linux/macOS
source .venv/bin/activate
```

### List Audio Devices
```bash
python autosamplerT.py --list_audio_devices
```

### List MIDI Ports
```bash
python autosamplerT.py --list_midi_ports
```

### Interactive Setup (configure audio/MIDI)
```bash
python autosamplerT.py --setup
```

---

## Sampling

### Sample Using a Script File
```bash
# Basic script sampling
python autosamplerT.py --script conf/my_synth.yaml

# With export formats
python autosamplerT.py --script conf/my_synth.yaml --export_formats qpat,ableton

# Test mode (no actual recording)
python autosamplerT.py --script conf/my_synth.yaml --test_mode
```

### Sample Prophet 6 Programs
```bash
# Single program
python autosamplerT.py --script conf/prophet_programs/program_001.yaml

# All programs in folder
python autosamplerT.py --script-folder conf/prophet_programs --export_formats qpat
```

### Sample All Scripts in a Folder
```bash
python autosamplerT.py --script-folder conf/test --export_formats qpat,ableton
```

### Quick Single Note Test
```bash
python autosamplerT.py --script conf/single_C4_script.yaml --test_mode
```

---

## Export Formats

### Export Existing Multisample to QPAT (Waldorf)
```bash
# Basic export (SD card location)
python autosamplerT.py --process output/MySynth --export_formats qpat

# USB location (auto-import to internal)
python autosamplerT.py --process output/MySynth --export_formats qpat --export_location 4

# With audio optimization (convert to 44.1kHz 32-bit float)
python autosamplerT.py --process output/MySynth --export_formats qpat --export_optimize_audio
```

### Export to Waldorf MAP Format
```bash
python autosamplerT.py --process output/MySynth --export_formats waldorf_map
```

### Export to Ableton Live Sampler (ADV)
```bash
python autosamplerT.py --process output/MySynth --export_formats ableton
```

### Export to Multiple Formats
```bash
python autosamplerT.py --process output/MySynth --export_formats qpat,ableton,waldorf_map
```

### Export with Custom Output Location
```bash
python autosamplerT.py --process output/MySynth --export_formats qpat --export_location 2
# Location: 2=SD card (default), 3=internal, 4=USB
```

---

## Post-Processing

### Process Loops (Auto-Loop)
```bash
# Add loop points to existing samples
python autosamplerT.py --process output/MySynth --auto_loop

# With custom loop duration (minimum 50% of sample)
python autosamplerT.py --process output/MySynth --auto_loop --loop_min_duration 50%

# With specific loop time range
python autosamplerT.py --process output/MySynth --auto_loop --loop_start_time 0.5 --loop_end_time 2.0
```

### Normalize Samples
```bash
# Normalize to -1dB peak
python autosamplerT.py --process output/MySynth --normalize -1

# Normalize to 0dB (maximum without clipping)
python autosamplerT.py --process output/MySynth --normalize 0
```

### Boost Samples by 12dB
```bash
# Apply 12dB gain boost
python autosamplerT.py --process output/MySynth --gain 12

# Boost and normalize to prevent clipping
python autosamplerT.py --process output/MySynth --gain 12 --normalize -1
```

### Trim Silence
```bash
# Remove silence from start/end
python autosamplerT.py --process output/MySynth --trim_silence

# With custom threshold
python autosamplerT.py --process output/MySynth --trim_silence --silence_threshold -60
```

### Combined Post-Processing
```bash
# Trim, loop, normalize, then export
python autosamplerT.py --process output/MySynth \
  --trim_silence --auto_loop --normalize -1 \
  --export_formats qpat,ableton
```

---

## Loop Configuration

### Loop Mode Options
```bash
# Forward loop (default)
python autosamplerT.py --process output/MySynth --export_formats qpat --export_loop_mode 1

# Ping-pong loop
python autosamplerT.py --process output/MySynth --export_formats qpat --export_loop_mode 2

# No loop
python autosamplerT.py --process output/MySynth --export_formats qpat --export_loop_mode 0
```

### Loop Crossfade
```bash
# 15ms crossfade
python autosamplerT.py --process output/MySynth --export_formats qpat --export_loop_crossfade 15.0
```

---

## MIDI Control During Sampling

### Send Program Change Before Sampling
```bash
python autosamplerT.py --script conf/my_synth.yaml --program_change 10
```

### Send CC Messages
```bash
# Volume CC7 = 127
python autosamplerT.py --script conf/my_synth.yaml --cc_messages "7:127"

# Multiple CCs
python autosamplerT.py --script conf/my_synth.yaml --cc_messages "7:127,10:64,1:0"
```

---

## Common Workflows

### Full Sampling Session with Export
```bash
# 1. Sample synth
python autosamplerT.py --script conf/prophet_programs/strings.yaml

# 2. Add loops
python autosamplerT.py --process output/strings --auto_loop

# 3. Export to all formats
python autosamplerT.py --process output/strings --export_formats qpat,ableton
```

### Quick Test Run
```bash
python autosamplerT.py --script conf/single_C4_script.yaml --test_mode --export_formats ableton
```

### Batch Process Multiple Synth Patches
```bash
python autosamplerT.py --script-folder conf/prophet_programs \
  --export_formats qpat,ableton \
  --output_folder output/prophet_collection
```

### Re-Export with Different Settings
```bash
# Already sampled, just need different export
python autosamplerT.py --process output/MySynth \
  --export_formats qpat --export_location 4 --export_optimize_audio
```

---

## Troubleshooting

### Verbose/Debug Output
```bash
python autosamplerT.py --script conf/my_synth.yaml --debug
```

### Check Configuration
```bash
# Show current config without sampling
python autosamplerT.py --script conf/my_synth.yaml --dry_run
```

### Force Overwrite Existing Output
```bash
python autosamplerT.py --script conf/my_synth.yaml --overwrite
```

---

## File Locations

| Item | Location |
|------|----------|
| Config file | `conf/autosamplerT_config.yaml` |
| Script files | `conf/*.yaml` |
| Output samples | `output/<name>/samples/` |
| SFZ files | `output/<name>/<name>.sfz` |
| QPAT files | `output/<name>/<name>.qpat` |
| ADV files | `output/<name>/<name>.adv` |
| Documentation | `doc/` |

---

## YAML Script Template

```yaml
# conf/my_synth.yaml
name: "My Synth Patch"
description: "Full keyboard sampling"

sampling:
  note_range_start: C2      # or MIDI number: 36
  note_range_end: C6        # or MIDI number: 84
  note_range_interval: 3    # every 3 semitones
  velocity_layers: 3
  roundrobin_layers: 2
  hold_time: 2.0
  release_time: 1.0

midi_interface:
  output_port_name: "Prophet 6"
  program_change: 1
  cc_messages: {7: 127}

postprocessing:
  auto_loop: true
  trim_silence: true

export:
  formats:
    - qpat
    - ableton
```

---

*Last updated: January 24, 2026*
