# GitHub Copilot Instructions for AutosamplerT

## Project Overview
AutosamplerT is an advanced automatic sampler with MIDI control capabilities for sampling hardware synthesizers. It records audio samples across velocity layers and round-robin variations, generates SFZ files, and exports to various sampler formats.

## Core Technologies
- **Language:** Python 3.8+
- **Audio:** sounddevice, soundfile, scipy, numpy
- **MIDI:** mido, python-rtmidi
- **Configuration:** PyYAML
- **Testing:** pytest

## Code Style & Conventions

### Python Style
- Follow PEP 8 guidelines
- Use type hints for function parameters and returns
- Maximum line length: 100-120 characters
- Use docstrings for all classes and public methods
- Prefer descriptive variable names over abbreviations

### Naming Conventions
```python
# Classes: PascalCase
class WaldorfQpatExporter:
    pass

# Functions/Methods: snake_case
def calculate_velocity_value(layer, total_layers):
    pass

# Constants: UPPER_SNAKE_CASE
MAX_GROUPS = 3
MAGIC_NUMBER = 3402932

# Private methods: _leading_underscore
def _parse_sfz(self, sfz_file):
    pass

# File names: snake_case
# sampler_midicontrol.py, export_qpat.py
```

### Import Organization
```python
# 1. Standard library imports
import os
import struct
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 2. Third-party imports
import numpy as np
import sounddevice as sd
import mido
import yaml

# 3. Local application imports
from src.sampler import Sampler
from src.postprocess import PostProcessor
```

## Architecture Patterns

### Configuration Management
- Use YAML for all configuration files
- Store configs in `conf/` directory
- Separate concerns: `autosamplerT_config.yaml` (setup) vs script files (sampling)
- Configuration merging: script overrides config file
- Always validate configuration values before use

### MIDI Control
- All MIDI messages go through `MIDIController` class (`src/sampler_midicontrol.py`)
- Support message types: CC (7-bit), CC14 (14-bit), NRPN, Program Change, SysEx
- Per-layer MIDI control: `velocity_midi_control` and `roundrobin_midi_control`
- Always add configurable delays after MIDI messages
- Use channel 0-15 (convert to 1-16 for display)

### Audio Processing
- All audio data as `numpy.ndarray` with dtype `float32`, range [-1.0, 1.0]
- Use `sounddevice` for recording (supports ASIO on Windows)
- **Recording captures full duration** (hold_time + release_time) without automatic trimming
- Silence trimming is **postprocessing-only** via `--trim_silence` flag or YAML config
- Process audio in `src/postprocess.py` for normalization, trimming, looping
- Store metadata in WAV RIFF chunks (SMPL chunk for MIDI note and loop points)
- Always call `sd.stop()` in finally block after recording to prevent audio clicks

### File Organization
```
autosamplerT/
├── src/                  # Core modules
│   ├── sampler.py        # Main sampling engine
│   ├── sampler_midicontrol.py  # MIDI message handling
│   ├── postprocess.py    # Audio postprocessing
│   └── export_*.py       # Format exporters (qpat, etc.)
├── conf/                 # Configuration files
│   ├── autosamplerT_config.yaml  # Main config
│   └── test/             # Test scripts
├── doc/                  # Documentation
├── tests/                # Test suite
└── output/               # Generated samples and files
```

## MIDI Implementation Guidelines

### Message Format Patterns
```python
# CC Messages (7-bit)
cc_messages = {7: 127, 10: 64}  # Dict format

# CC14 Messages (14-bit)
cc14_messages = {45: 16383, 1: 8192}  # Dict format, 0-16383 range

# NRPN Messages (Non-Registered Parameter Number)
nrpn_messages = {45: 164, 100: 8192}  # Dict format, device-specific ranges
# Sends 4 CC messages: CC99 (NRPN MSB), CC98 (NRPN LSB), CC6 (Data MSB), CC38 (Data LSB)

# SysEx Messages
sysex_messages = ["43 10 7F 1C 00", "41 10 00 20 12"]  # List of hex strings (no F0/F7)

# Program Change
program_change = 10  # 0-127
```

### Per-Layer MIDI Control
```yaml
# In YAML scripts
sampling_midi:
  velocity_midi_control:
    - layer: 0
      cc_messages: {7: 0}
      program_change: 1
    - layer: 1
      cc_messages: {7: 64}
      program_change: 2
  
  roundrobin_midi_control:
    - layer: 0
      nrpn_messages: {45: 0}
    - layer: 1
      nrpn_messages: {45: 55}
```

## Export Format Guidelines

### Waldorf QPAT Format
- **File type:** Text file with 512-byte binary header + plain text sections
- Binary header: 512 bytes, big-endian format (magic: `3402932`, version: `14`)
- Text sections: Tab-separated sample maps (16 columns) and synth parameters
- Location prefixes: `2:` (SD card - default), `3:` (internal), `4:` (USB)
- **Important:** Location prefix (`4:`) only in QPAT text sections, NOT for filesystem operations
- Maximum 3 groups (velocity/round-robin layers)
- Maximum 128 samples per map

### Sample Map Format
```python
# Path handling - correct pattern
path_in_qpat = f'"{self.location}:{relative_sample_path}/{sample_name}"'  # For QPAT text
filesystem_path = os.path.join(samples_folder, sample_name)  # For file operations

# Never use location prefix in filesystem operations
```

### SFZ Format (Native)
- Text-based, human-readable
- Generate during sampling (always created)
- Store metadata in WAV files, not SFZ
- Support velocity layers, round-robin, key mapping

## Error Handling Patterns

### Graceful Degradation
```python
try:
    # Attempt operation
    result = risky_operation()
except SpecificException as e:
    logging.error(f"Operation failed: {e}")
    # Provide fallback or reasonable default
    result = default_value
```

### MIDI Port Handling
```python
if not self.midi_output_port:
    logging.warning("No MIDI output port - skipping MIDI messages")
    return
```

### Audio Device Validation
```python
device_info = sd.query_devices(device_index)
if device_info is None:
    raise ValueError(f"Invalid device index: {device_index}")
```

## Logging Guidelines

### Log Levels
- `DEBUG`: Detailed diagnostic information (MIDI bytes, device queries)
- `INFO`: Normal operation messages (sampling started, file saved)
- `WARNING`: Recoverable issues (missing MIDI port, using defaults)
- `ERROR`: Operation failures (cannot save file, MIDI send failed)

### Log Format
```python
# Good logging examples
logging.info(f"Sampling: Note={note}, Vel={velocity}, RR={rr_index}")
logging.debug(f"MIDI CC sent: cc={cc}, value={value}, channel={channel}")
logging.warning(f"Sample not found: {source}")
logging.error(f"Failed to save WAV file {filepath}: {e}")
```

## Testing Patterns

### Test Organization
```
tests/
├── test_silence_detection.py  # Unit tests for silence detection
├── autoloop/                   # Auto-loop feature tests
│   ├── test_autoloop.py
│   └── README.md
├── asio/                       # ASIO-specific tests
└── TEST_ORGANIZATION.md        # Test documentation
```

### Test Naming
```python
def test_silence_detection_finds_start():
    """Test that silence detection correctly identifies sample start."""
    pass

def test_velocity_calculation_single_layer():
    """Test velocity value for single velocity layer."""
    pass
```

### Test Coverage Requirements
- **Every feature must have dedicated test scripts** in `conf/test/` directory
- Test scripts should cover all feature variations and edge cases
- Name test scripts descriptively: `test_<feature>_<variation>.yaml`
- Include comments in test scripts explaining what is being tested
- Document test results and expected behavior

### Mock MIDI for Testing
```python
# Use test mode to skip actual MIDI/audio
python autosamplerT.py --test_mode --script conf/test_script.yaml
```

## Documentation Standards

### Docstring Format
```python
def export_to_qpat(output_folder: str, multisample_name: str,
                   sfz_file: str, samples_folder: str,
                   location: int = 4, optimize_audio: bool = True) -> bool:
    """
    Export multisample to Waldorf QPAT format.
    
    Args:
        output_folder: Destination folder for QPAT file
        multisample_name: Name of the multisample (used for filenames)
        sfz_file: Path to source SFZ file to parse
        samples_folder: Path to folder containing sample WAV files
        location: Sample location (2=SD, 3=internal, 4=USB)
        optimize_audio: If True, convert samples to 44.1kHz 32-bit float
        
    Returns:
        True if export successful, False otherwise
        
    Raises:
        ValueError: If SFZ file is invalid or cannot be parsed
        IOError: If sample files cannot be copied
    """
    pass
```

### Markdown Documentation
- Store in `doc/` directory
- Use clear section headers with anchors
- Include code examples with syntax highlighting
- Add troubleshooting sections
- Link between related documents
- Keep examples up-to-date with code
- **NEVER use icons or emojis** in documentation (✅ ❌ 🚧 ⚠️ etc.)
- Use plain text markers instead: `[DONE]`, `[TODO]`, `[WARNING]`, `[NOTE]`

## CLI Argument Patterns

### Argument Groups
```python
# Main options (config, script, setup, help)
main_group = parser.add_argument_group('main', 'Main options')

# Audio interface options
audio_group = parser.add_argument_group('audio', 'Audio interface options')

# MIDI options
midi_group = parser.add_argument_group('midi', 'MIDI interface options')

# Sampling options
sampling_group = parser.add_argument_group('sampling', 'Sampling options')

# Post-processing options
postprocessing_group = parser.add_argument_group('postprocessing', 'Post-processing options')
```

### Help Text Conventions
```python
parser.add_argument('--note_range_start', type=str, metavar='NOTE',
                   help='Starting note (MIDI number or name like C4, A#3)')
parser.add_argument('--export_formats', type=str, metavar='FORMAT[,FORMAT...]',
                   help='Comma-separated list of export formats: qpat, ableton, exs, sxt')
```

## YAML Configuration Patterns

### Script Structure
```yaml
# Metadata (optional)
name: "MySynth Sampling"
description: "Full keyboard with 3 velocity layers"

# Audio settings
audio:
  samplerate: 48000
  bitdepth: 24
  mono_stereo: stereo

# MIDI interface
midi_interface:
  output_port_name: "Prophet 6"
  cc_messages: {7: 127}
  program_change: 1

# Sampling configuration
sampling:
  note_range_start: 36
  note_range_end: 96
  note_range_interval: 1
  velocity_layers: 3
  roundrobin_layers: 1
  hold_time: 3.0
  release_time: 1.5
  
# Per-layer MIDI control
sampling_midi:
  velocity_midi_control:
    - layer: 0
      cc_messages: {7: 32}
    - layer: 1
      cc_messages: {7: 80}
    - layer: 2
      cc_messages: {7: 127}

# Post-processing
postprocessing:
  auto_loop: true
  loop_min_duration: "50%"
  trim_silence: true

# Export formats
export:
  formats:
    - qpat
  qpat:
    location: 4
    optimize_audio: true
```

## WAV Metadata Handling

### RIFF Chunk Format
```python
# SMPL chunk - standard format (loop points + MIDI note)
smpl_chunk = struct.pack('<9I',
    0,                          # Manufacturer
    0,                          # Product
    int(1e9 / samplerate),      # Sample period (nanoseconds)
    midi_note,                  # MIDI unity note (0-127)
    0,                          # Pitch fraction
    0,                          # SMPTE format
    0,                          # SMPTE offset
    1,                          # Number of loops
    0                           # Sampler data
)

# Loop data (if loop points exist)
loop_data = struct.pack('<6I',
    0,                          # Cue point ID
    0,                          # Type (0=forward, 2=ping-pong)
    loop_start,                 # Loop start (sample offset)
    loop_end,                   # Loop end (sample offset)
    0,                          # Fraction
    0                           # Play count (0=infinite)
)
```

### Metadata Dictionary
```python
metadata = {
    'note': 60,              # MIDI note number (0-127)
    'midi_note': 60,         # Same as note (for SMPL chunk)
    'velocity': 127,         # MIDI velocity (1-127)
    'round_robin': 0,        # Round-robin index
    'channel': 0,            # MIDI channel (0-15)
    'loop_start': 44100,     # Loop start (sample offset)
    'loop_end': 88200        # Loop end (sample offset)
}
```

## Common Pitfalls to Avoid

### 1. Path Separators
```python
# Good - works on Windows and Unix
path = os.path.join(folder, filename)
path = Path(folder) / filename

# Bad - breaks on Windows/Unix
path = folder + '/' + filename
```

### 2. MIDI Channel Confusion
```python
# Good - internal representation (0-15)
channel = 0  # MIDI channel 1

# Display to user (1-16)
print(f"MIDI channel: {channel + 1}")
```

### 3. Audio Data Range
```python
# Good - normalized to [-1.0, 1.0]
audio_float32 = audio_int16.astype(np.float32) / 32767

# Bad - unnormalized integer data
audio_data = audio_int16  # Don't pass raw int16 to processing
```

### 4. Git Commit Messages with Special Characters
```python
# Good - escape paths in commit messages
git commit -m "Feat: Export format" -m "Sample location: 4=USB"

# Bad - causes git path interpretation errors
git commit -m "Sample path: 4:/samples/file.wav"
```

### 5. Configuration Validation
```python
# Good - validate before use
if not 0 <= velocity <= 127:
    raise ValueError(f"Invalid velocity: {velocity}")

# Bad - assume valid input
velocity = config.get('velocity')  # Could be invalid
```

## Performance Considerations

### Audio Buffer Sizes
- Use appropriate buffer sizes for ASIO (256-1024 samples)
- Larger buffers = more latency, fewer dropouts
- Monitor CPU usage during recording

### Memory Management
- Process samples in batches for large multisamples
- Release audio data after saving to disk
- Limit QPAT exports to ~360MB total RAM

### File I/O
- Use binary mode for WAV files: `open(file, 'wb')`
- Buffer writes when possible
- Close file handles promptly in error cases

## Version Control

### Commit Message Format
```
Type: Brief description

Detailed explanation of changes
- Bullet points for features
- Technical details
- Breaking changes

FILES:
- List of modified files
- Brief description per file
```

### Types
- `Feat:` New feature
- `Fix:` Bug fix
- `Docs:` Documentation only
- `Refactor:` Code restructuring
- `Test:` Test additions/changes
- `Chore:` Maintenance tasks

## When Adding New Features

### Checklist
- [ ] Add CLI arguments (if needed)
- [ ] Add YAML configuration support
- [ ] Implement core functionality
- [ ] Add error handling and logging
- [ ] Write docstrings
- [ ] Add to documentation (`doc/` folder)
- [ ] **Create dedicated test scripts in `conf/test/`**
- [ ] **Test all variations and edge cases**
- [ ] Update TODO.md
- [ ] Test with real hardware (if MIDI/audio related)
- [ ] **Do not make changes to codebase without user confirmation**
- [ ] Commit with descriptive message

### Example: Adding New Export Format
1. Create `src/export_newformat.py` with exporter class
2. Add CLI arguments in `autosamplerT.py`
3. Add format-specific options (location, optimization)
4. Implement SFZ parser integration
5. Add sample copying logic
6. Create comprehensive documentation in `doc/EXPORT_FORMATS.md`
7. Add examples to README
8. Test export with real SFZ files
9. Update TODO.md with completed status

---

*Last updated: November 13, 2025*
