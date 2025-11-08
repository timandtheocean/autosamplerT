# AutosamplerT

Python-based autosampler to create SFZ multisample libraries from hardware synths and instruments.

A cross-platform program that samples hardware synthesizers by sending MIDI notes (and optionally CC and SysEx messages) to a hardware device, captures the audio, and creates an SFZ multisample.

## Features

### Audio Configuration
- Select audio device, bit depth (16/24/32), and sample rate
- Support for mono and stereo inputs
- Audio latency compensation
- Input gain control
- Patch normalize: automatically gain all samples to consistent level
- Sample normalize: gain each sample to maximum volume
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
- WAV file export with metadata
- SFZ mapping file generation
- Customizable sample naming
- Loop point metadata (future)

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
```

#### Audio Options Examples

```bash
# Set sample rate and bit depth
python autosamplerT.py --samplerate 96000 --bitdepth 24

# Enable normalization and silence detection
python autosamplerT.py --patch_normalize --silence_detection

# Set input gain
python autosamplerT.py --gain 1.5
```

#### MIDI Options Examples

```bash
# Set note range (C2 to C7, chromatic)
python autosamplerT.py --note_range '{"start":36,"end":96,"interval":1}'

# Set velocity layers
python autosamplerT.py --velocity_layers 4

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

## Workflow Example

1. **Setup**: `python autosamplerT.py --setup`
2. **Test**: `python autosamplerT.py --test_mode --note_range '{"start":60,"end":72,"interval":12}'`
3. **Sample**: `python autosamplerT.py --velocity_layers 3 --note_range '{"start":36,"end":96,"interval":3}'`
4. **Output**: Check `./output/` folder for WAV files and SFZ

## Platform Support

- ✅ Windows
- ✅ Linux  
- ✅ macOS

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

MIT

## Credits

AutosamplerT - Cross-platform hardware synth autosampler