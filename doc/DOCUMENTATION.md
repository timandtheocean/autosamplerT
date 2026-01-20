# AutosamplerT Documentation

Complete documentation for AutosamplerT - an advanced automatic sampler with MIDI control capabilities.

## Installation

**New to AutosamplerT? Start here!**

We provide automated installation scripts for all platforms:

- **[INSTALL.md](../INSTALL.md)** - Complete installation guide with automated and manual instructions
- **Windows:** Run `install.ps1` in PowerShell - handles Python installation via winget
- **Linux:** Run `install.sh` - supports Ubuntu, Fedora, Arch, openSUSE, and more
- **macOS:** Run `install-mac.sh` - includes Homebrew integration and audio libraries

All scripts automatically:
- [DONE] Detect and install Python 3.8+ if needed
- [DONE] Install system audio libraries (ALSA, JACK, PortAudio)
- [DONE] Create virtual environment
- [DONE] Install all Python dependencies
- [DONE] Verify installation and test functionality

## Quick Links

- [README](../README.md) - Project overview and quick start
- [REQUIREMENTS](../REQUIREMENTS.md) - Installation and dependencies
- [IMPLEMENTATION](../IMPLEMENTATION.md) - Technical implementation details
- [TODO](../TODO.md) - Roadmap and future plans

## Core Documentation

### 1. [Setup & Configuration](SETUP.md)
Learn how to configure audio and MIDI devices for sampling.

**Topics covered:**
- Audio device selection and configuration
- MIDI device selection with fuzzy matching
- Setup modes (audio/midi/all)
- Configuration file structure
- Device validation

**When to use:** First-time setup, changing audio/MIDI devices, troubleshooting device issues

---

### 2. [MIDI Control](MIDI_CONTROL.md)
Advanced MIDI control for per-layer message transmission.

**Topics covered:**
- Per-layer MIDI (velocity and round-robin)
- CC, CC14, Program Changes, SysEx messages
- Structured SysEx format with header reuse
- Configurable message delays
- Testing with virtual MIDI cables
- Practical use cases and examples
- Troubleshooting and best practices

**When to use:** Sampling hardware synths with different patches, CC sweeps, filter movements, program changes per layer

---

### 3. [Scripting System](SCRIPTING.md)
YAML-based scripting for automated sampling workflows.

**Topics covered:**
- Script vs config file distinction
- Script merging behavior
- YAML structure and sections
- sampling_midi configuration
- Script auto-copy to output folders
- Batch processing with --script-folder
- Best practices and examples

**When to use:** Creating reusable sampling configurations, batch sampling, testing different MIDI settings, documenting workflows

**Key features:**
- YAML-based configuration format
- Script auto-copy to output folders for documentation
- Batch processing with `--script-folder`
- Per-layer MIDI control (velocity and round-robin)
- Config file merging (script overrides config)
- Interactive sampling support
- Patch iteration (sample multiple patches sequentially)

---

### 4. [Command Line Interface](CLI.md)
Complete CLI reference and usage patterns.

**Topics covered:**
- Command-line arguments
- Setup modes
- Script execution
- Interactive prompts
- Common workflows

**When to use:** Running sampling sessions, setup configuration, understanding available options

---

### 5. [Sampling Engine](SAMPLING.md)
Core sampling functionality and parameters.

**Topics covered:**
- Velocity layers and calculation
- Round-robin layers
- Note ranges and intervals
- Recording parameters (hold, release, pause)
- Silence detection and processing
- Pre-sampling summary

**When to use:** Understanding sampling parameters, optimizing recording settings, troubleshooting audio issues

---

### 6. [Output Formats](OUTPUT.md)
Sample file organization and format generation.

**Topics covered:**
- SFZ file generation
- File naming conventions
- Sample organization structure
- Patch normalization
- Multi-sample export

**When to use:** Understanding output structure, customizing file organization, working with samplers

---

### 7. [Export Formats](EXPORT_FORMATS.md)
Convert and export to various sampler formats.

**Topics covered:**
- Waldorf Quantum/Iridium QPAT format [DONE]
- Ableton Live format [TODO]
- Logic Pro EXS24 format [TODO]
- Kontakt SXT format [TODO]
- QPAT format specification (binary header, parameters, sample maps)
- Sample location prefixes and import workflow
- Multi-format export workflow
- Format-specific constraints and best practices

**When to use:** Exporting to hardware samplers, converting between formats, deploying to multiple targets

---

### 8. [Post-Processing](POSTPROCESSING.md)
Audio processing after sample capture.

**Topics covered:**
- Silence detection and trimming
- Patch normalization
- Audio processing pipeline
- Quality control
- Batch processing

**When to use:** Improving sample quality, normalizing levels, trimming silent sections

---

## Advanced Documentation

### [ASIO Multi-Channel](ASIO_MULTICHANNEL.md)
ASIO interface configuration for multi-channel audio devices.

**Topics covered:**
- Channel offset configuration
- Stereo pair selection
- Multi-channel device setup

**When to use:** Using ASIO interfaces with multiple inputs

---

### [Quick Start Guide](QUICKSTART.md)
Fast track to getting started with AutosamplerT.

**Topics covered:**
- 5-minute setup
- First sampling session
- Basic workflow

**When to use:** New users wanting to get started quickly

---

## Test Examples

All test scripts are located in `conf/test/`:

- `test_roundrobin_cc.yaml` - Basic CC per round-robin layer
- `test_velocity_cc.yaml` - CC per velocity layer
- `test_sysex_structured.yaml` - SysEx structured format examples
- `test_program_change.yaml` - Program changes per layer
- `test_suite_full.yaml` - Comprehensive test (3 velocity × 4 round-robin)
- `test_cc1_sweep.yaml` - CC value sweep
- `test_cc1_with_delay.yaml` - MIDI message delay testing

## Workflow Examples

### Basic Sampling Workflow
```bash
# 1. First-time setup
python autosamplerT.py --setup all

# 2. Run a sampling script
python autosamplerT.py --script conf/my_script.yaml

# 3. Check output
# Files will be in output/<multisample_name>/samples/
```

### MIDI Control Workflow
```bash
# 1. Setup MIDI devices
python autosamplerT.py --setup midi

# 2. Test with example script
python autosamplerT.py --script conf/test/test_program_change.yaml

# 3. Verify MIDI messages (optional)
# Use receivemidi or MIDI monitor to verify messages
```

### Hardware Synth Sampling
```bash
# 1. Connect audio input from synth
# 2. Connect MIDI output to synth
# 3. Setup devices
python autosamplerT.py --setup all

# 4. Create custom script with MIDI control
# See doc/MIDI_CONTROL.md for examples

# 5. Run sampling
python autosamplerT.py --script conf/my_synth.yaml
```

## Getting Help

- **Issues**: Check [GitHub Issues](https://github.com/timandtheocean/autosamplerT/issues)
- **Configuration**: See `conf/autosamplerT_config.yaml` for current settings
- **Examples**: Browse `conf/test/` for working examples
- **Logs**: Check console output for INFO/WARNING/ERROR messages

## Contributing

See [IMPLEMENTATION.md](../IMPLEMENTATION.md) for technical details and contribution guidelines.

## Version Information

Current branch: `main`
Latest features: MIDI control, SysEx structured format, pre-sampling summary

---

*Last updated: November 11, 2025*
