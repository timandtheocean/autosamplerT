# AutosamplerT Tools

Utility scripts for development, debugging, and batch operations.

## Audio/ASIO Tools

| Script | Description |
|--------|-------------|
| `analyze_audio.py` | Analyze audio files for levels, frequency content |
| `check_asio_devices.py` | List and test ASIO devices |
| `check_devices_wavetable.py` | Check device compatibility for wavetable recording |
| `debug_device_selection.py` | Debug audio device selection issues |
| `debug_noise_floor.py` | Analyze noise floor of recordings |

## Prophet 6 Script Generators

| Script | Description |
|--------|-------------|
| `create_prophet_scripts.py` | Generate Prophet 6 sampling scripts |
| `create_prophet_programs_20_99.py` | Generate scripts for programs 20-99 |
| `create_prophet_programs_extended.py` | Extended program script generator |
| `optimize_prophet_programs.py` | Optimize Prophet program configs |
| `optimize_prophet_programs_single_rr.py` | Single round-robin optimization |
| `update_prophet_programs.py` | Update existing Prophet scripts |
| `update_prophet_programs_0_19.py` | Update programs 0-19 |
| `update_roundrobin_to_3.py` | Update scripts to use 3 round-robins |

## Sample/Export Tools

| Script | Description |
|--------|-------------|
| `fix_g3_sample.py` | Fix specific sample issues |
| `fix_sample_paths.py` | Fix sample path references |
| `re_export_qpat_files.py` | Re-export samples to QPAT format |
| `send_program_change.py` | Send MIDI program change messages |

## Waldorf Tools

| Script | Description |
|--------|-------------|
| `WALDORF_COLUMN_FIX_PROPOSAL.py` | Waldorf column alignment fix utility |

## Usage

Most tools can be run directly:

```bash
python tools/check_asio_devices.py
python tools/analyze_audio.py path/to/sample.wav
```

For Prophet script generators:

```bash
python tools/create_prophet_scripts.py
python tools/update_prophet_programs.py
```
