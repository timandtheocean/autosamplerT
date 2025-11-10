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
- Auto-loop detection: find and set loop points using autocorrelation algorithm
  - Zero-crossing detection for smooth, click-free loop points
  - Automatic loop detection or manual start/end time specification
  - Configurable minimum loop duration (percentage or seconds: `55%` or `8.5`)
- Crossfade looping: create smooth loop transitions with equal-power crossfade
- Bit depth conversion: convert between 16/24/32-bit with optional dithering
- Backup creation: automatically backup samples before processing
- Debug mode: optional JSON sidecar files for detailed metadata (disabled by default)

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

**Important: CLI vs Script Syntax Differences**

When using command-line arguments, note range uses **three separate flags**:
```bash
# CLI syntax (three separate flags)
python autosamplerT.py --note_range_start 36 --note_range_end 96 --note_range_interval 1
```

When using script files (YAML), note range uses a **dict with start/end/interval keys**:
```yaml
# Script syntax (dict format)
sampling_midi:
  note_range: {start: 36, end: 96, interval: 1}
```

The same applies to velocity layer splits:
- **CLI**: `--velocity_layers_split 50,90` (comma-separated string)
- **Script**: `velocity_layers_split: [50, 90]` or `velocity_layers_split: null` (YAML list or null)

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

# Send 7-bit CC messages (volume=127, pan=center)
python autosamplerT.py --cc_messages "7,127;10,64"

# Send 14-bit CC messages (modulation=8192 center, expression=16383 max)
python autosamplerT.py --cc14_messages "1,8192;11,16383"

# Combine both 7-bit and 14-bit CC
python autosamplerT.py --cc_messages "7,127" --cc14_messages "1,8192"
```

**Understanding CC Messages:**

**7-bit CC (Control Change):**
- Range: 0-127 (128 values)
- Format: `"controller,value;controller,value"` (CLI) or `{controller: value}` (YAML)
- Common controllers:
  - CC 1: Modulation Wheel (0-127)
  - CC 7: Volume (0-127)
  - CC 10: Pan (0=left, 64=center, 127=right)
  - CC 11: Expression (0-127)
  - CC 74: Filter Cutoff (0-127)
  - CC 71: Filter Resonance (0-127)

**14-bit CC (High Resolution):**
- Range: 0-16383 (16,384 values)
- Format: `"controller,value;controller,value"` (CLI) or `{controller: value}` (YAML)
- Uses two messages automatically: MSB (controller N) + LSB (controller N+32)
- Controllers: 0-31 only (14-bit CC uses pairs)
- Example: CC1 (14-bit) sends CC1 (MSB) + CC33 (LSB)
- Common uses:
  - CC 1: Modulation Wheel (0-16383, center=8192)
  - CC 11: Expression (0-16383)
  - Pitch Bend range extension
  - High-resolution filter sweeps

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

**Basic Postprocessing:**
```bash
# Patch normalize: maintain relative dynamics between samples
python autosamplerT.py --process "MySynth" --patch_normalize --trim_silence

# Sample normalize: maximize each sample independently
python autosamplerT.py --process "DrumKit" --sample_normalize --trim_silence

# Process samples in a specific folder
python autosamplerT.py --process_folder ./output/MySynth --patch_normalize --auto_loop

# Normalize and trim with backup (recommended for safety)
python autosamplerT.py --process "MySynth" --patch_normalize --trim_silence --backup

# Remove DC offset (recommended for all recordings)
python autosamplerT.py --process "MySynth" --dc_offset_removal
```

**Auto-Loop Detection:**

AutosamplerT uses advanced autocorrelation analysis with zero-crossing detection to find perfect loop points.

```bash
# Auto-loop with percentage-based minimum duration (55% of sample length)
python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 55%

# Auto-loop with absolute minimum duration (8.5 seconds)
python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 8.5

# Auto-loop with crossfade for smooth, click-free loops (30ms equal-power crossfade)
python autosamplerT.py --process "MySynth" --auto_loop --loop_min_duration 50% --crossfade_loop 30

# Auto-loop with manual start/end times (for precise control)
python autosamplerT.py --process "MySynth" --auto_loop --loop_start_time 1.5 --loop_end_time 3.2 --crossfade_loop 30
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
  --auto_loop --loop_min_duration 50% --crossfade_loop 30 \
  --backup

# Aggressive processing for maximum quality
python autosamplerT.py --process "MySynth" \
  --dc_offset_removal \
  --trim_silence \
  --patch_normalize \
  --auto_loop --loop_min_duration 8.0 --crossfade_loop 50 \
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
  --auto_loop --loop_min_duration 55% --crossfade_loop 30
```

This will:
- Remove DC offset from recordings
- Trim silence from start/end (typically ~1 second)
- Normalize all samples together to maintain relative dynamics
- Find loop points for each sample (minimum 55% of trimmed sample length)
- Apply 30ms equal-power crossfade at loop points
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

### Advanced: Manual Loop Points with Crossfade

For precise control over loop points (e.g., syncing to musical phrases):

```bash
python autosamplerT.py --process "MySynth" \
  --auto_loop \
  --loop_start_time 1.5 \
  --loop_end_time 8.2 \
  --crossfade_loop 50
```

This creates a loop from 1.5 to 8.2 seconds with a 50ms crossfade, ignoring autocorrelation analysis.

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
