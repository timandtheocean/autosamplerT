# AutosamplerT

Python-based autosampler to create SFZ multisample libraries from hardware synths and instruments.

A cross-platform program that samples hardware synthesizers by sending MIDI notes (and optionally MIDI messages like CC, NRPN, program changes, and SysEx) to a hardware device, captures the audio, and creates an SFZ multisample with export options for various sampler formats.



## Features

### Audio Configuration
- Select audio device, bit depth (16/24/32-bit), and sample rate (44.1kHz, 48kHz, 96kHz, etc.)
- Support for mono (left/right channel selection) and stereo inputs
- **ASIO multi-channel support**: Select specific stereo pairs on multi-channel interfaces (Ch A, Ch B, etc.)
- ASIO, WASAPI, MME, WDM-KS, and DirectSound audio APIs supported (Windows)
- JACK, ALSA support (Linux)
- CoreAudio support (macOS)
- Audio latency compensation
- Input gain control
- Built-in silence detection for automatic trimming

### MIDI Configuration
- MIDI input for testing and audition
- MIDI output for playback during sampling
- **CC (7-bit)**: Standard Control Change messages (0-127)
- **CC14 (14-bit)**: High-resolution Control Change messages (0-16383)
- **NRPN**: Non-Registered Parameter Number messages
- **Program Change**: Switch patches/programs (0-127)
- **SysEx**: System Exclusive messages (hex format)
- **Per-layer MIDI control**: Different MIDI messages per velocity/round-robin layer
- Configurable MIDI message delays
- Multiple MIDI channels for capturing multiple instruments
- MIDI latency adjustment for sample start correction

### Sampling Options
- Configurable note hold time, release time, and pause between samples
- Note range and interval (chromatic, whole-tone, octaves, etc.)
- **Multiple velocity layers** with automatic logarithmic distribution or custom split points
- **Velocity minimum**: Start velocity distribution from higher values (e.g., skip very soft layers)
- **Multiple round-robin layers** (up to 4+ variations per note/velocity)
- **Interactive sampling**: Pause at intervals for manual intervention
  - Fixed interval pausing (every N notes)
  - **MIDI range mapping**: Repeat limited MIDI range across wider SFZ range (for hardware samplers with limited keys)
  - Auto-resume with countdown timer or wait for keypress
  - Perfect for: Casio SK-1, Akai S950, acoustic instruments, vocals
- **Patch iteration**: Automatically sample multiple patches with program changes
- Test mode for quick setup verification without recording
- Pre-sampling summary with sample count and timing estimates

### Output & Export Formats
- **SFZ format**: Native format, always created with velocity layers and round-robin support
- **Waldorf QPAT**: Export to Waldorf Quantum/Iridium format (SD card, internal, or USB storage)
- **Ableton Live**: Planned
- **Logic Pro EXS24**: Planned
- **Kontakt SXT**: Planned
- WAV file export with metadata (MIDI note, velocity, channel, loop points in RIFF chunks)
- Customizable sample naming and folder organization
- Optional JSON sidecar files for debugging (disabled by default)

### Post-Processing
- **Patch normalize**: Gain all samples to consistent peak level (maintains relative dynamics)
- **Sample normalize**: Gain each sample to maximum volume independently (destroys dynamics)
- **Silence trimming**: Remove silence from start/end of samples with configurable threshold
- **DC offset removal**: Remove DC bias from recordings
- **Auto-loop detection**: Find and set loop points using autocorrelation algorithm
  - Zero-crossing detection for smooth, click-free loop points
  - Automatic loop detection or manual start/end time specification
  - Configurable minimum loop duration (percentage or absolute: `55%` or `8.5` seconds)
  - Loop points stored in WAV RIFF 'smpl' chunk (sampler handles crossfading)
- **Bit depth conversion**: Convert between 16/24/32-bit with optional dithering
- **Backup creation**: Automatically backup samples before processing
- **Debug mode**: Optional JSON sidecar files for detailed metadata

### Scripting & Automation
- **YAML-based scripting system**: Define complete sampling workflows in human-readable format
- **Command-line interface**: Full CLI support for automation and batch processing
- **Config file**: Store audio/MIDI device settings separately from scripts
- **Script templates**: Pre-made templates for common workflows
- **Test scripts**: Comprehensive test suite in `conf/test/` directory## Installation



## Quick StartSee [REQUIREMENTS.md](REQUIREMENTS.md) for platform-specific installation instructions.



### InstallationQuick install (all platforms):

```bash

See [INSTALL.md](INSTALL.md) for platform-specific automated installation scripts.pip install sounddevice numpy scipy mido python-rtmidi pyyaml

```

Quick install (all platforms):

```bash## Usage

pip install sounddevice numpy scipy mido python-rtmidi pyyaml

```### 1. Initial Setup



### Basic UsageConfigure your audio and MIDI interfaces:



**1. Initial Setup**```bash

python autosamplerT.py --setup

Configure your audio and MIDI interfaces:```

```bash

python autosamplerT.py --setup allThis will guide you through selecting:

```- Audio input/output devices

- Sample rate and bit depth

**2. Run Sampling**- MIDI input/output devices



Using a script file:Configuration is saved to `conf/autosamplerT_config.yaml`

```bash

python autosamplerT.py --script conf/my_synth.yaml### 2. Run Sampling

```

Basic sampling with config file:

Basic command-line sampling:

```bash```bash

python autosamplerT.py --note_range_start C3 --note_range_end C5 --note_range_interval 1python autosamplerT.py

``````



**3. Post-Process Samples**Using a script file for batch sampling:



Normalize and trim silence:```bash

```bashpython autosamplerT.py --script conf/autosamplerT_script.yaml

python autosamplerT.py --process "MySynth" --patch_normalize --trim_silence```

```

### 3. Command-Line Options

Auto-loop detection:

```bash**Important: CLI vs Script Syntax Differences**

python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 55%

```When using command-line arguments, note range uses **three separate flags**:

```bash

**4. Export to Sampler Formats**# CLI syntax (three separate flags)

python autosamplerT.py --note_range_start 36 --note_range_end 96 --note_range_interval 1

Export to Waldorf Quantum/Iridium:```

```bash

python autosamplerT.py --process "MySynth" --export_formats qpatWhen using script files (YAML), note range uses a **dict with start/end/interval keys**:

``````yaml

# Script syntax (dict format)

### Example: Sample with MIDI Controlsampling_midi:

  note_range: {start: 36, end: 96, interval: 1}

Create a YAML script (`conf/my_synth.yaml`):```

```yaml

name: "My Synth Sampling"The same applies to velocity layer splits:

- **CLI**: `--velocity_layers_split 50,90` (comma-separated string)

audio:- **Script**: `velocity_layers_split: [50, 90]` or `velocity_layers_split: null` (YAML list or null)

  samplerate: 48000

  bitdepth: 24View all options:

```bash

midi_interface:python autosamplerT.py --help

  output_port_name: "Prophet 6"```

  program_change: 10

View category-specific help:

sampling:```bash

  note_range_start: 36python autosamplerT.py --help audio

  note_range_end: 96python autosamplerT.py --help midi

  note_range_interval: 1python autosamplerT.py --help sampling

  velocity_layers: 3python autosamplerT.py --help postprocessing

  hold_time: 3.0```

  release_time: 1.5

#### Audio Options Examples

sampling_midi:

  velocity_midi_control:```bash

    - layer: 0# Set sample rate and bit depth

      cc_messages: {7: 32}python autosamplerT.py --samplerate 96000 --bitdepth 24

    - layer: 1

      cc_messages: {7: 80}# Record in mono using left channel

    - layer: 2python autosamplerT.py --mono_stereo mono --mono_channel 0

      cc_messages: {7: 127}

# Record in mono using right channel

postprocessing:python autosamplerT.py --mono_stereo mono --mono_channel 1

  patch_normalize: true

  trim_silence: true# ASIO multi-channel: Record from Ch A (channels 0-1)

  auto_loop: truepython autosamplerT.py --channel_offset 0

  loop_min_duration: "55%"

# ASIO multi-channel: Record from Ch B (channels 2-3)

export:python autosamplerT.py --channel_offset 2

  formats:

    - qpat# ASIO multi-channel: Record mono from Ch B left (channel 2)

  qpat:python autosamplerT.py --channel_offset 2 --mono_stereo mono --mono_channel 0

    location: 2  # SD card

```# Enable normalization and silence detection

python autosamplerT.py --patch_normalize --silence_detection

Run the script:

```bash# Set input gain

python autosamplerT.py --script conf/my_synth.yamlpython autosamplerT.py --gain 1.5

``````



## Documentation#### MIDI Options Examples



**Complete documentation is available in [doc/DOCUMENTATION.md](doc/DOCUMENTATION.md)****Note Ranges:**



### Quick Links```bash

- [Setup & Configuration](doc/SETUP.md) - Audio and MIDI device configuration# Set note range with note names (A#3 to C#5, chromatic)

- [MIDI Control](doc/MIDI_CONTROL.md) - Per-layer MIDI messages, CC, SysEx, Program Changepython autosamplerT.py --note_range_start A#3 --note_range_end C#5 --note_range_interval 1

- [Scripting System](doc/SCRIPTING.md) - YAML scripts for automated workflows

- [Command Line Interface](doc/CLI.md) - Complete CLI reference# Set note range with MIDI numbers (C2=36 to C7=96, chromatic)

- [Sampling Engine](doc/SAMPLING.md) - Velocity layers, round-robin, note rangespython autosamplerT.py --note_range_start 36 --note_range_end 96 --note_range_interval 1

- [Output Formats](doc/OUTPUT.md) - SFZ file generation and organization

- [Export Formats](doc/EXPORT_FORMATS.md) - QPAT, Ableton, EXS24, SXT export# Sample every octave (C4 to C7)

- [Post-Processing](doc/POSTPROCESSING.md) - Normalize, trim, auto-looppython autosamplerT.py --note_range_start C4 --note_range_end C7 --note_range_interval 12

- [ASIO Multi-Channel](doc/ASIO_MULTICHANNEL.md) - Multi-channel interface configuration```

- [Quick Start Guide](doc/QUICKSTART.md) - 5-minute setup guide

**Velocity Layers:**

### Help & Examples

```bash

```bash# 4 velocity layers with automatic logarithmic distribution (1, 43, 85, 127)

# View all optionspython autosamplerT.py --velocity_layers 4 --note_range_start C3 --note_range_end C5

python autosamplerT.py --help

# Start from velocity 45 instead of 1 (softer samples often not needed)

# View category-specific helppython autosamplerT.py --velocity_layers 4 --velocity_minimum 45 --note_range_start C3 --note_range_end C5

python autosamplerT.py --help audio

python autosamplerT.py --help midi# Custom velocity split points for precise control

python autosamplerT.py --help samplingpython autosamplerT.py --velocity_layers 4 --velocity_layers_split 32,64,96 --note_range_start C3 --note_range_end C5

python autosamplerT.py --help postprocessing

# Single velocity layer with custom value

# Browse test examplespython autosamplerT.py --velocity_layers 1 --velocity_minimum 100 --note_range_start C3 --note_range_end C5

ls conf/test/```

```

**Other MIDI Options:**

## Common Workflows

# Set velocity layers (automatic logarithmic distribution)

### Sample a Hardware Synthpython autosamplerT.py --velocity_layers 4

```bash

# 1. Setup devices# Set velocity layers with custom minimum velocity

python autosamplerT.py --setup allpython autosamplerT.py --velocity_layers 4 --velocity_minimum 45



# 2. Create a script with MIDI control# Set velocity layers with custom split points

# See doc/MIDI_CONTROL.md for examplespython autosamplerT.py --velocity_layers 4 --velocity_layers_split 40,70,100



# 3. Run sampling# Combine minimum velocity with custom splits

python autosamplerT.py --script conf/my_synth.yamlpython autosamplerT.py --velocity_layers 3 --velocity_minimum 30 --velocity_layers_split 60,90



# 4. Export to your sampler# Send program change before sampling

python autosamplerT.py --process "MySynth" --export_formats qpatpython autosamplerT.py --program_change 10

```

# Send 7-bit CC messages (volume=127, pan=center)

### Multi-Patch Samplingpython autosamplerT.py --cc_messages "7,127;10,64"

```yaml

# Use program changes to sample multiple patches# Send 14-bit CC messages (modulation=8192 center, expression=16383 max)

sampling_midi:python autosamplerT.py --cc14_messages "1,8192;11,16383"

  velocity_midi_control:

    - layer: 0# Combine both 7-bit and 14-bit CC

      program_change: 0python autosamplerT.py --cc_messages "7,127" --cc14_messages "1,8192"

      cc_messages: {7: 64}```

    - layer: 1

      program_change: 5**Understanding CC Messages:**

      cc_messages: {7: 100}

```**7-bit CC (Control Change):**

- Range: 0-127 (128 values)

### Velocity Layers with CC Control- Format: `"controller,value;controller,value"` (CLI) or `{controller: value}` (YAML)

```yaml- Common controllers:

# Different CC values per velocity layer  - CC 1: Modulation Wheel (0-127)

sampling_midi:  - CC 7: Volume (0-127)

  velocity_midi_control:  - CC 10: Pan (0=left, 64=center, 127=right)

    - layer: 0  # Soft  - CC 11: Expression (0-127)

      cc_messages: {7: 32, 74: 40}  - CC 74: Filter Cutoff (0-127)

    - layer: 1  # Medium  - CC 71: Filter Resonance (0-127)

      cc_messages: {7: 80, 74: 80}

    - layer: 2  # Hard**14-bit CC (High Resolution):**

      cc_messages: {7: 127, 74: 120}- Range: 0-16383 (16,384 values)

```- Format: `"controller,value;controller,value"` (CLI) or `{controller: value}` (YAML)

- Uses two messages automatically: MSB (controller N) + LSB (controller N+32)

### Round-Robin with NRPN- Controllers: Any CC 0-127 can be 14-bit (uses CC N and CC N+32)

```yaml- Example: CC45 (14-bit) sends CC45 (MSB) + CC77 (LSB)

# Use NRPN or CC14 for round-robin variations- Common uses:

sampling_midi:  - CC 1: Modulation Wheel (0-16383, center=8192)

  roundrobin_midi_control:  - CC 11: Expression (0-16383)

    - layer: 0  - CC 45: User parameter (common for round-robin layer switching)

      nrpn_messages: {45: 0}  - High-resolution filter sweeps

    - layer: 1

      nrpn_messages: {45: 55}```

    - layer: 2

      nrpn_messages: {45: 110}#### Sampling Options Examples

```

```bash

## Troubleshooting# Set timing parameters

python autosamplerT.py --hold_time 2.0 --release_time 1.5 --pause_time 0.5

**No audio devices found:**

- Ensure PortAudio is installed (see [REQUIREMENTS.md](REQUIREMENTS.md))# Set output parameters

- Check that your audio interface is connected and recognized by the OSpython autosamplerT.py --output_folder ./my_samples --multisample_name "My_Synth"



**MIDI devices not showing:**# Enable test mode (no actual recording)

- Verify MIDI interface drivers are installedpython autosamplerT.py --test_mode

- Check OS MIDI settings/permissions

# Set round-robin layers

**Samples are clipping:**python autosamplerT.py --roundrobin_layers 3

- Reduce input gain: `--gain 0.8````

- Enable normalization: `--patch_normalize`

#### Postprocessing Options Examples

**Silence detection trimming too much:**

- Adjust by editing threshold in `src/sampler.py` (default: 0.001)**What's the difference between patch and sample normalize?**

- **Patch normalize** (`--patch_normalize`): Analyzes all samples in the multisample to find the loudest peak, then applies the same gain to ALL samples so they have consistent relative levels. Use this to maintain the natural dynamics between soft and loud samples.

**Program changes not working:**- **Sample normalize** (`--sample_normalize`): Normalizes each sample independently to its maximum volume. This destroys the relative dynamics but ensures every sample is as loud as possible. Use for drum kits or when dynamics don't matter.

- Check synth MIDI settings (some require enabling program change receive)

- Prophet 6 uses 0-indexed: Program Change 0 = Patch 0**Basic Postprocessing:**

```bash

## Requirements# Patch normalize: maintain relative dynamics between samples

python autosamplerT.py --process "MySynth" --patch_normalize --trim_silence

- Python 3.8+

- sounddevice, numpy, scipy, mido, python-rtmidi, pyyaml# Sample normalize: maximize each sample independently

- PortAudio (ASIO/WASAPI on Windows, JACK/ALSA on Linux, CoreAudio on macOS)python autosamplerT.py --process "DrumKit" --sample_normalize --trim_silence



See [REQUIREMENTS.md](REQUIREMENTS.md) for detailed platform-specific instructions.# Process samples in a specific folder

python autosamplerT.py --process_folder ./output/MySynth --patch_normalize --auto_loop

## License

# Normalize and trim with backup (recommended for safety)

GPL3python autosamplerT.py --process "MySynth" --patch_normalize --trim_silence --backup



## Credits# Remove DC offset (recommended for all recordings)

python autosamplerT.py --process "MySynth" --dc_offset_removal

AutosamplerT - Cross-platform hardware synth autosampler```



---**Auto-Loop Detection:**



For complete documentation, see [doc/DOCUMENTATION.md](doc/DOCUMENTATION.md)AutosamplerT uses advanced autocorrelation analysis with zero-crossing detection to find perfect loop points.


```bash
# Auto-loop with percentage-based minimum duration (55% of sample length)
python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 55%

# Auto-loop with absolute minimum duration (8.5 seconds)
python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 8.5

# Auto-loop with manual start/end times (for precise control)
python autosamplerT.py --process "MySynth" --auto_loop --loop_start_time 1.5 --loop_end_time 3.2
```

**Bit Depth Conversion:**
```bash
# Convert to 16-bit for OP-1/tape machines
python autosamplerT.py --process "MySynth" --convert_bitdepth 16 --dither

# Convert to 24-bit without dithering
python autosamplerT.py --process "MySynth" --convert_bitdepth 24
```

**Complete Postprocessing Chain Examples:**
```bash
# Standard workflow: clean, normalize, loop
python autosamplerT.py --process "MySynth" \
  --dc_offset_removal \
  --trim_silence \
  --patch_normalize \
  --auto_loop --loop_min_duration 50% \
  --backup

# Aggressive processing for maximum quality
python autosamplerT.py --process "MySynth" \
  --dc_offset_removal \
  --trim_silence \
  --patch_normalize \
  --auto_loop --loop_min_duration 8.0 \
  --convert_bitdepth 16 --dither \
  --backup
```

### 4. Configuration Files

#### Config File (`conf/autosamplerT_config.yaml`)

Stores your audio/MIDI device settings. Created by `--setup` or manually edited:

```yaml
audio_interface:
  input_device_index: 4
  output_device_index: 3
  samplerate: 44100
  bitdepth: 24
  
midi_interface:
  midi_input_name: "MIDI IN"
  midi_output_name: "MIDI OUT"
```

#### Script File (`conf/autosamplerT_script.yaml`)

Full sampling script with all parameters:

```yaml
audio_interface:
  input_device_index: 0            # Audio input device
  output_device_index: 3           # Audio output device (for monitoring)
  samplerate: 96000                # 44100, 48000, 96000
  bitdepth: 24                     # 16, 24, 32
  mono_stereo: stereo              # mono or stereo
  gain: 1.0                        # Input gain multiplier
  latency_compensation: 0.0        # Latency compensation in milliseconds
  audio_inputs: 2                  # Number of input channels
  debug: false                     # Enable JSON sidecar files

midi_interface:
  midi_input_name: "MIDI IN"       # MIDI input device name
  midi_output_name: "MIDI OUT"     # MIDI output device name
  midi_latency_adjust: 0.0         # MIDI latency adjustment in milliseconds

sampling_midi:
  # Default MIDI settings (sent once at start of sampling)
  midi_channels: [0]               # MIDI channels to sample (0-15)
  program_change: 10               # Program change 0-127, or null
  cc_messages: {7: 127, 10: 64}    # 7-bit CC messages: {controller: value} (0-127)
  cc14_messages: {1: 8192}         # 14-bit CC messages: {controller: value} (0-16383)
  sysex_messages: []               # SysEx messages as hex strings
  
  # Note range and layers - use dict syntax
  note_range: {start: 36, end: 96, interval: 1}  # C2 to C7, chromatic
  velocity_layers: 4               # Number of velocity layers
  velocity_minimum: 1              # Minimum velocity (1-127)
  velocity_layers_split: null      # Custom splits: "50,90" or null for automatic
  roundrobin_layers: 1             # Number of round-robin variations
  
  # Per-velocity-layer MIDI control (optional)
  velocity_midi_control:
    - velocity_layer: 0            # First velocity layer (softest)
      midi_channel: 0
      program_change: null
      cc_messages: {74: 20}        # 7-bit: Filter cutoff low
      cc14_messages: {1: 2048}     # 14-bit: Modulation low
      sysex_messages: []
    
    - velocity_layer: 1            # Second velocity layer
      midi_channel: 0
      cc_messages: {74: 60}        # 7-bit: Filter cutoff medium
      cc14_messages: {1: 8192}     # 14-bit: Modulation center
  
  # Per-round-robin-layer MIDI control (optional)
  roundrobin_midi_control:
    - roundrobin_layer: 0          # First round-robin
      midi_channel: 0
      program_change: 10
      cc_messages: {7: 127}

sampling:
  hold_time: 2.0                   # Note hold time in seconds
  release_time: 1.0                # Release time in seconds
  pause_time: 0.5                  # Pause between samples in seconds
  sample_name: "MySample"          # Individual sample name prefix
  multisample_name: "MyInstrument" # Multisample folder/SFZ name
  test_mode: false                 # Quick test (only first note)
  output_format: "sfz"             # Output format: sfz, soundfont, kontakt
  output_folder: "./output"        # Output directory
  lowest_note: 0                   # SFZ lowest note mapping
  highest_note: 127                # SFZ highest note mapping

## Round-Robin Layers with CC14 (14-bit MIDI)

For instruments that use 14-bit CC messages to switch between round-robin layers:

### YAML Configuration

```yaml
sampling:
  multisample_name: "synth_cc14_rr"
  roundrobin_layers: 4
  note_range:
    start: 36  # C1
    end: 96    # C7
    interval: 1

midi_interface:
  midi_channels: 0

sampling_midi:
  # Per-round-robin-layer MIDI control
  roundrobin_midi_control:
    - roundrobin_layer: 0
      midi_channel: 0
      cc14_messages: {45: 0}        # Layer 1: CC45=0
    - roundrobin_layer: 1
      midi_channel: 0
      cc14_messages: {45: 5461}     # Layer 2: CC45=5461
    - roundrobin_layer: 2
      midi_channel: 0
      cc14_messages: {45: 10922}    # Layer 3: CC45=10922
    - roundrobin_layer: 3
      midi_channel: 0
      cc14_messages: {45: 16383}    # Layer 4: CC45=16383
```

**Key Points:**
- Each `roundrobin_layer` index (0-3) corresponds to a round-robin layer
- `cc14_messages` uses 14-bit values (0-16383) 
- CC45 is common for round-robin control, but any CC 0-127 works
- AutosamplerT automatically sends MSB and LSB messages (e.g., CC45 + CC77)
- Also supports: `cc_messages`, `program_change`, `sysex_messages` per layer

### Command-Line (with YAML script)

```bash
python autosamplerT.py --script conf/my_cc14_roundrobin.yaml
```

### Calculating CC14 Values

Distribute 14-bit range (0-16383) evenly across layers:

**4 layers:**
- Layer 0: 0 (0%)
- Layer 1: 5461 (33.3%)
- Layer 2: 10922 (66.6%)
- Layer 3: 16383 (100%)

**8 layers:**
- Layer 0: 0
- Layer 1: 2340
- Layer 2: 4681
- Layer 3: 7021
- Layer 4: 9362
- Layer 5: 11702
- Layer 6: 14043
- Layer 7: 16383

Formula: `value = (16383 * layer_index) / (num_layers - 1)`
```

## Sample Naming Convention

Samples are automatically named with the format:

```
{name}_{note}_{velocity}_rr{layer}.wav
```

Examples:
- `MySynth_C3_v127_rr1.wav`
- `MySynth_A#4_v064_rr2.wav`

## Output Files

After sampling, you'll find:
- Individual WAV files for each sample
- SFZ mapping file (`{multisample_name}.sfz`)
- JSON metadata files (only if `debug: true` in config)

**Note:** MIDI metadata (note, velocity, channel) and loop points are stored in WAV RIFF chunks. JSON files are only created when debug mode is enabled.

## Velocity Layer Distribution

AutosamplerT uses **logarithmic distribution** for automatic velocity layer calculation, providing more density at higher velocities (where most playing dynamics occur).

### Automatic Distribution Examples

**4 layers (default, 1-127):**
- Layer 1: velocity 1 (range 0-21)
- Layer 2: velocity 43 (range 21-64)
- Layer 3: velocity 85 (range 64-106)
- Layer 4: velocity 127 (range 106-127)

**4 layers with minimum 45:**
- Layer 1: velocity 45 (range 0-55)
- Layer 2: velocity 66 (range 55-79)
- Layer 3: velocity 93 (range 79-110)
- Layer 4: velocity 127 (range 110-127)

### Custom Split Points

Specify exact velocity boundaries between layers:

**CLI syntax:**
```bash
# 3 layers with splits at 50 and 90 (CLI uses comma-separated string)
python autosamplerT.py --velocity_layers 3 --velocity_layers_split 50,90
# Samples at: 25, 70, 108 (midpoint of each range)
# Ranges: 0-50, 50-90, 90-127

# 4 layers with splits at 32, 64, 96
python autosamplerT.py --velocity_layers 4 --velocity_layers_split 32,64,96
# Samples at: 16, 48, 80, 111
# Ranges: 0-32, 32-64, 64-96, 96-127
```

**Script syntax:**
```yaml
sampling_midi:
  velocity_layers: 3
  velocity_layers_split: [50, 90]  # YAML list format
  # OR
  velocity_layers_split: null      # Use automatic logarithmic distribution
```

Split points must:
- Match number of layers minus 1 (3 layers = 2 splits)
- Be in ascending order
- Be within range 1-127

## Workflow Example

1. **Setup**: `python autosamplerT.py --setup`
2. **Test**: `python autosamplerT.py --test_mode --note_range_start C4 --note_range_end C5 --note_range_interval 12`
3. **Sample**: `python autosamplerT.py --velocity_layers 3 --velocity_minimum 40 --note_range_start C2 --note_range_end C7 --note_range_interval 3`
4. **Output**: Check `./output/` folder for WAV files and SFZ

## Platform Support

- Windows
- Linux  
- macOS

## Testing

### Regression Test Suite

Run comprehensive tests after code changes to verify all features still work:

**Python script (cross-platform):**
```bash
# Run all tests
python test_all.py

# Run quick tests only (faster)
python test_all.py --quick

# Run specific test group
python test_all.py --group basic
python test_all.py --group velocity
python test_all.py --group roundrobin
```

**PowerShell script (Windows):**
```powershell
# Run all tests
.\test_all.ps1

# Run quick tests only
.\test_all.ps1 -Quick

# Run specific test group
.\test_all.ps1 -Group velocity
```

Test groups:
- **basic**: Single note and note range tests
- **velocity**: Velocity layer tests (automatic, minimum, custom splits)
- **roundrobin**: Round-robin layer tests
- **combined**: Velocity + round-robin combined
- **audio**: Audio configuration (mono left/right, stereo)
- **metadata**: WAV RIFF chunk verification

The test suite will:
- Run each test scenario
- Verify sample counts match expected values
- Check WAV metadata format
- Display pass/fail status for each test
- Print summary with timing information

## Complete Workflow Examples

### Production Sampling: Analog Synth with Auto-Looping

This example shows a complete workflow for sampling an analog synthesizer with automatic loop detection.

**Step 1: Sample the instrument (12 second hold, 2 notes per octave, C2 to C6)**
```bash
python autosamplerT.py --name "op1-pipedream" \
  --note_range 36 84 \
  --interval 6 \
  --hold_time 12.0 \
  --release_time 3.0
```

Output: 9 samples recorded (C2, F#2, C3, F#3, C4, F#4, C5, F#5, C6)

**Step 2: Postprocess with percentage-based auto-looping (55% minimum loop)**
```bash
python autosamplerT.py --process "op1-pipedream" \
  --dc_offset_removal \
  --trim_silence \
  --patch_normalize \
  --auto_loop --loop_min_duration 55%
```

This will:
- Remove DC offset from recordings
- Trim silence from start/end (typically ~1 second)
- Normalize all samples together to maintain relative dynamics
- Find loop points for each sample (minimum 55% of trimmed sample length)
- Embed loop points in WAV 'smpl' chunk for sampler compatibility

**Expected Results:**
- Sample duration after trimming: ~14.8 seconds
- Minimum loop duration (55%): ~8.1 seconds
- Detected loop duration: ~11.8 seconds (exceeds minimum, perfect!)
- Loop points stored in WAV RIFF headers, no JSON files created

### Debug Mode: Enabling JSON Sidecar Files

By default, autosamplerT stores all metadata in WAV RIFF chunks ('note' and 'smpl'). To create JSON sidecar files with detailed metadata, enable debug mode in your config:

**conf/autosamplerT_config.yaml:**
```yaml
audio:
  debug: true  # Creates JSON files with detailed metadata
```

**With debug disabled (default):**
```bash
output/MySynth/samples/
  MySynth_036_v127.wav  # Contains note and loop metadata in RIFF chunks
  MySynth_042_v127.wav
  MySynth_048_v127.wav
```

**With debug enabled:**
```bash
output/MySynth/samples/
  MySynth_036_v127.wav   # WAV file with RIFF metadata
  MySynth_036_v127.json  # JSON with human-readable metadata
  MySynth_042_v127.wav
  MySynth_042_v127.json
```

JSON files are useful for debugging but unnecessary for production since samplers read WAV RIFF chunks directly.

### Percentage vs. Absolute Loop Duration

The `--loop_min_duration` parameter accepts both percentage and absolute time values:

**Percentage syntax (recommended for variable-length samples):**
```bash
# 55% of each sample's duration (adapts to different sample lengths)
python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 55%

# 80% of each sample's duration (very long loops)
python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 80%
```

**Absolute syntax (seconds):**
```bash
# Exactly 8.5 seconds minimum loop (same for all samples)
python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 8.5

# Short 2 second minimum loop
python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 2.0
```

**Validation behavior:**
If the requested loop duration exceeds the sample length, autosamplerT automatically falls back to 80% of the sample duration with a warning:
```
[WARNING] Requested loop duration (12.000s) exceeds sample length (10.5s) for MySynth_036_v127.wav
Using 80% of sample duration: 8.4s
```

### Advanced: Manual Loop Points

For precise control over loop points (e.g., syncing to musical phrases):

```bash
python autosamplerT.py --process "MySynth" \
  --auto_loop \
  --loop_start_time 1.5 \
  --loop_end_time 8.2
```

This creates a loop from 1.5 to 8.2 seconds, ignoring autocorrelation analysis. Loop points are embedded in the WAV file's RIFF 'smpl' chunk, and your sampler application will handle the crossfading.

## Troubleshooting

**No audio devices found:**
- Ensure PortAudio is installed (see REQUIREMENTS.md)
- Check that your audio interface is connected and recognized by the OS

**MIDI devices not showing:**
- Verify MIDI interface drivers are installed
- Check OS MIDI settings/permissions

**Samples are clipping:**
- Reduce input gain: `--gain 0.8`
- Enable normalization: `--patch_normalize`

**Silence detection trimming too much:**
- Adjust by editing threshold in `src/sampler.py` (default: 0.001)

## License

GPL3

## Credits

AutosamplerT - Cross-platform hardware synth autosampler
