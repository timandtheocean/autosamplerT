# AutosamplerT - Quick Start Guide

## First Time Setup

### 1. Install Dependencies

```bash
pip install sounddevice numpy scipy mido python-rtmidi pyyaml
```

### 2. Configure Audio and MIDI

```bash
python autosamplerT.py --setup
```

Follow the prompts to:
- Select your audio input/output devices
- Choose sample rate (44100, 48000, 96000, etc.)
- Choose bit depth (16, 24, or 32)
- Select MIDI input/output devices

Configuration is saved to `conf/autosamplerT_config.yaml`

## Quick Test Run

Test your setup without recording (5 notes, test mode):

```bash
python autosamplerT.py --test_mode --note_range_start C4 --note_range_end E4 --note_range_interval 1 --hold_time 0.5
```

You should see:
- Audio devices loaded
- MIDI devices connected
- Test MIDI notes sent (no actual recording)

## Basic Sampling

Sample one octave (C3 to C4) with default settings:

```bash
python autosamplerT.py --note_range_start C3 --note_range_end C4 --note_range_interval 1
```

This will:
- Sample notes C3 to C4 (chromatic)
- Use default 2s hold time, 1s release
- Save to `./output/` folder
- Create an SFZ file

## Common Use Cases

### 1. Full Keyboard, Chromatic

Sample entire keyboard range (C2 to C7):

```bash
python autosamplerT.py --note_range_start C2 --note_range_end C7 --note_range_interval 1 --multisample_name "MyFullSynth"
```

### 2. Every 3rd Note (Minor Third Intervals)

Faster sampling for long sounds:

```bash
python autosamplerT.py --note_range_start C2 --note_range_end C7 --note_range_interval 3 --hold_time 3.0 --release_time 2.0
```

### 3. Velocity Layers

Sample 4 velocity layers:

```bash
python autosamplerT.py --velocity_layers 4 --note_range_start C3 --note_range_end C5 --note_range_interval 1
```

### 4. Round-Robin Layers

Sample with 3 round-robin variations:

```bash
python autosamplerT.py --roundrobin_layers 3 --note_range_start C3 --note_range_end C5 --note_range_interval 1
```

### 5. Drum Machine (No Pitch)

Sample percussion sounds:

```bash
python autosamplerT.py --note_range_start C2 --note_range_end D#3 --note_range_interval 1 --hold_time 1.0 --release_time 0.5 --multisample_name "DrumKit"
```

### 6. High Quality Settings

96kHz, 24-bit, normalized:

```bash
python autosamplerT.py --samplerate 96000 --bitdepth 24 --patch_normalize --silence_detection
```

## Using Script Files

Edit `conf/autosamplerT_script.yaml` with your settings, then run:

```bash
python autosamplerT.py --script conf/autosamplerT_script.yaml
```

## Output Files

After sampling, check the `./output/` folder:

```
output/
├── MySynth_C3_v127.wav
├── MySynth_C#3_v127.wav
├── MySynth_D3_v127.wav
├── ...
└── MySynth.sfz
```

Load the `.sfz` file in your sampler (SFZ Player, etc.)

## Troubleshooting

**"No audio devices found"**
- Run `python src/audio_interface_manager.py` to list devices
- Check your audio interface is connected

**"No MIDI devices found"**
- Run `python src/midi_interface_manager.py` to list devices
- Check MIDI interface drivers are installed

**Samples are too quiet**
- Use `--gain 1.5` to boost input
- Or use `--patch_normalize` for automatic leveling

**Samples are clipping**
- Use `--gain 0.8` to reduce input
- Enable `--patch_normalize`

**Note starts are cut off**
- Increase `--latency_compensation 50` (milliseconds)
- Or disable `--no_silence_detection`

## Advanced Options

### MIDI Control

#### Basic MIDI Messages

Send Program Change and CC messages before sampling:

```bash
python autosamplerT.py --program_change 10 --cc_messages '{"7":127,"74":64}'
```

#### Per-Velocity-Layer MIDI Control

Use script YAML to send different MIDI messages per velocity layer:

```yaml
sampling_midi:
  note_range: {start: 36, end: 96, interval: 1}
  velocity_layers: 3
  
  velocity_midi_control:
    - velocity_layer: 0  # Soft layer
      cc_messages: {74: 30}  # Filter closed
    - velocity_layer: 1  # Medium layer
      cc_messages: {74: 80}  # Filter half open
    - velocity_layer: 2  # Loud layer
      cc_messages: {74: 127}  # Filter wide open
```

#### Per-Round-Robin MIDI Control

Sample different programs or patches per round-robin:

```yaml
sampling_midi:
  note_range: {start: 36, end: 96, interval: 1}
  roundrobin_layers: 3
  
  roundrobin_midi_control:
    - roundrobin_layer: 0
      program_change: 10
      cc_messages: {7: 127}
    - roundrobin_layer: 1
      program_change: 11
      cc_messages: {7: 120}
    - roundrobin_layer: 2
      program_change: 12
      cc_messages: {7: 115}
```

#### SysEx Messages

Send SysEx messages to configure your synth:

```yaml
sampling_midi:
  sysex_messages:
    - "F0 43 10 7F 1C 00 00 00 01 F7"  # Yamaha example
    - "F0 41 10 00 00 00 20 12 F7"     # Roland example
```

Then run with your script:

```bash
python autosamplerT.py --script conf/my_midi_config.yaml
```

### Custom Output Folder

```bash
python autosamplerT.py --output_folder "C:/Samples/MySynth"
```

### Mono Recording

```bash
python autosamplerT.py --mono_stereo mono
```

## Post-Processing Samples

Post-processing operates on already-recorded samples in your output folder.

### Process by Multisample Name

```bash
python autosamplerT.py --process "MySynth" --patch_normalize --trim_silence
```

### Process Custom Folder

```bash
python autosamplerT.py --process_folder "C:/Samples/MySynth" --patch_normalize
```

### Normalize Entire Patch

Normalize all samples to consistent peak level:

```bash
python autosamplerT.py --process "MySynth" --patch_normalize
```

### Trim Silence

Remove silence from start/end of samples:

```bash
python autosamplerT.py --process "MySynth" --trim_silence
```

### Auto-Looping

Find and set loop points (for sustained sounds):

```bash
python autosamplerT.py --process "MySynth" --auto_loop
```

### DC Offset Removal

Remove DC bias:

```bash
python autosamplerT.py --process "MySynth" --dc_offset_removal
```

### Crossfade Loops

Create smooth loops:

```bash
python autosamplerT.py --process "MySynth" --auto_loop --crossfade_loop 20
```

### Convert Bit Depth

Convert with dithering:

```bash
python autosamplerT.py --process "MySynth" --convert_bitdepth 16 --dither
```

### Combined Post-Processing

```bash
python autosamplerT.py --process "MySynth" --trim_silence --patch_normalize --dc_offset_removal --auto_loop --backup
```

## Get Help

View all available options:

```bash
python autosamplerT.py --help
python autosamplerT.py --help audio
python autosamplerT.py --help midi
python autosamplerT.py --help sampling
python autosamplerT.py --help postprocessing
```

## Tips

1. **Always test first**: Use `--test_mode` to verify your setup
2. **Start small**: Sample a few notes first, then scale up
3. **Monitor levels**: Check input gain during test mode
4. **Save configs**: Use script files for repeatable sampling sessions
5. **Backup samples**: Copy the output folder after successful sampling

## Next Steps

- Explore velocity layers for expressive instruments
- Try round-robin for more realistic sounds
- Experiment with CC, sysex messages for sound variations
- Load your SFZ in a sampler and play!

Enjoy sampling! 🎹🎵
