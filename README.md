# AutosamplerT

Python-based autosampler to create SFZ multisample libraries from hardware synths and instruments.

A cross-platform program that samples hardware synthesizers by sending MIDI notes (and optionally CC and SysEx messages) to a hardware device, captures the audio, and creates an SFZ multisample.

This is the initial commit and development just started. 
things are probably not fully working.

## Features

### Audio Configuration
- Select audio device, bit depth (16/24/32), and sample rate
- Support for mono (left/right channel selection) and stereo inputs
- Audio latency compensation
- Input gain control
- Built-in silence detection for automatic trimming

### MIDI Configuration
- MIDI input for testing and audition
- MIDI output for playback during sampling
- Support for SysEx, Program Change, and CC messages
- Multiple MIDI channels for capturing multiple instruments
- MIDI latency adjustment for sample start correction

### Sampling Options
- Configurable note hold time
- Configurable release time
- Pause between samples
- Note range and interval (chromatic, whole-tone, etc.)
- Multiple velocity layers
- Multiple round-robin layers
- Test mode for quick setup verification

### Output
- WAV file export with metadata (note, velocity, MIDI channel in RIFF chunk)
- SFZ mapping file generation with velocity layers and round-robin support
- Customizable sample naming

### Postprocessing
- Patch normalize: automatically gain all samples to consistent peak level
- Sample normalize: gain each sample to maximum volume independently
- Silence trimming: remove silence from start/end of samples
- DC offset removal: remove DC bias from recordings
- Auto-loop detection: find and set loop points for sustained sounds
- Crossfade looping: create smooth loop transitions
- Bit depth conversion: convert between 16/24/32-bit with optional dithering
- Backup creation: automatically backup samples before processing

## Installation

See [REQUIREMENTS.md](REQUIREMENTS.md) for platform-specific installation instructions.

Quick install (all platforms):
```bash
pip install sounddevice numpy scipy mido python-rtmidi pyyaml
```

## Usage

### 1. Initial Setup

Configure your audio and MIDI interfaces:

```bash
python autosamplerT.py --setup
```

This will guide you through selecting:
- Audio input/output devices
- Sample rate and bit depth
- MIDI input/output devices

Configuration is saved to `conf/autosamplerT_config.yaml`

### 2. Run Sampling

Basic sampling with config file:

```bash
python autosamplerT.py
```

Using a script file for batch sampling:

```bash
python autosamplerT.py --script conf/autosamplerT_script.yaml
```

### 3. Command-Line Options

View all options:
```bash
python autosamplerT.py --help
```

View category-specific help:
```bash
python autosamplerT.py --help audio
python autosamplerT.py --help midi
python autosamplerT.py --help sampling
python autosamplerT.py --help postprocessing
```

#### Audio Options Examples

```bash
# Set sample rate and bit depth
python autosamplerT.py --samplerate 96000 --bitdepth 24

# Record in mono using left channel
python autosamplerT.py --mono_stereo mono --mono_channel 0

# Record in mono using right channel
python autosamplerT.py --mono_stereo mono --mono_channel 1

# Enable normalization and silence detection
python autosamplerT.py --patch_normalize --silence_detection

# Set input gain
python autosamplerT.py --gain 1.5
```

#### MIDI Options Examples

**Note Ranges:**

```bash
# Set note range with note names (A#3 to C#5, chromatic)
python autosamplerT.py --note_range_start A#3 --note_range_end C#5 --note_range_interval 1

# Set note range with MIDI numbers (C2=36 to C7=96, chromatic)
python autosamplerT.py --note_range_start 36 --note_range_end 96 --note_range_interval 1

# Sample every octave (C4 to C7)
python autosamplerT.py --note_range_start C4 --note_range_end C7 --note_range_interval 12
```

**Velocity Layers:**

```bash
# 4 velocity layers with automatic logarithmic distribution (1, 43, 85, 127)
python autosamplerT.py --velocity_layers 4 --note_range_start C3 --note_range_end C5

# Start from velocity 45 instead of 1 (softer samples often not needed)
python autosamplerT.py --velocity_layers 4 --velocity_minimum 45 --note_range_start C3 --note_range_end C5

# Custom velocity split points for precise control
python autosamplerT.py --velocity_layers 4 --velocity_layers_split 32,64,96 --note_range_start C3 --note_range_end C5

# Single velocity layer with custom value
python autosamplerT.py --velocity_layers 1 --velocity_minimum 100 --note_range_start C3 --note_range_end C5
```

**Other MIDI Options:**

# Set velocity layers (automatic logarithmic distribution)
python autosamplerT.py --velocity_layers 4

# Set velocity layers with custom minimum velocity
python autosamplerT.py --velocity_layers 4 --velocity_minimum 45

# Set velocity layers with custom split points
python autosamplerT.py --velocity_layers 4 --velocity_layers_split 40,70,100

# Combine minimum velocity with custom splits
python autosamplerT.py --velocity_layers 3 --velocity_minimum 30 --velocity_layers_split 60,90

# Send program change before sampling
python autosamplerT.py --program_change 10

# Send CC messages
python autosamplerT.py --cc_messages '{"7":127,"10":64}'
```

#### Sampling Options Examples

```bash
# Set timing parameters
python autosamplerT.py --hold_time 2.0 --release_time 1.5 --pause_time 0.5

# Set output parameters
python autosamplerT.py --output_folder ./my_samples --multisample_name "My_Synth"

# Enable test mode (no actual recording)
python autosamplerT.py --test_mode

# Set round-robin layers
python autosamplerT.py --roundrobin_layers 3
```

#### Postprocessing Options Examples

**What's the difference between patch and sample normalize?**
- **Patch normalize** (`--patch_normalize`): Analyzes all samples in the multisample to find the loudest peak, then applies the same gain to ALL samples so they have consistent relative levels. Use this to maintain the natural dynamics between soft and loud samples.
- **Sample normalize** (`--sample_normalize`): Normalizes each sample independently to its maximum volume. This destroys the relative dynamics but ensures every sample is as loud as possible. Use for drum kits or when dynamics don't matter.

```bash
# Patch normalize: maintain relative dynamics between samples
python autosamplerT.py --process "MySynth" --patch_normalize --trim_silence

# Sample normalize: maximize each sample independently
python autosamplerT.py --process "DrumKit" --sample_normalize --trim_silence

# Process samples in a specific folder
python autosamplerT.py --process_folder ./output/MySynth --patch_normalize --auto_loop

# Normalize and trim with backup (recommended for safety)
python autosamplerT.py --process "MySynth" --patch_normalize --trim_silence --backup

# Auto-loop with crossfade for sustained sounds
python autosamplerT.py --process "MySynth" --auto_loop --crossfade_loop 50

# Convert bit depth with dithering
python autosamplerT.py --process "MySynth" --convert_bitdepth 16 --dither

# Full post-processing chain
python autosamplerT.py --process "MySynth" --dc_offset_removal --trim_silence --patch_normalize --auto_loop --crossfade_loop 30 --backup
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
  samplerate: 96000
  bitdepth: 24
  gain: 1.0
  silence_detection: true
  sample_normalize: true

midi_interface:
  program_change: 10
  note_range: {start: 36, end: 96, interval: 1}
  velocity_layers: 4
  
sampling:
  hold_time: 2.0
  release_time: 1.0
  pause_time: 0.5
  multisample_name: "MyInstrument"
  output_folder: "./output"
  output_format: "sfz"
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
- JSON metadata files (if `wav_meta` enabled)

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

```bash
# 3 layers with splits at 50 and 90
python autosamplerT.py --velocity_layers 3 --velocity_layers_split 50,90
# Samples at: 25, 70, 108 (midpoint of each range)
# Ranges: 0-50, 50-90, 90-127
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
