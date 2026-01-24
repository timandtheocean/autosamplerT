"""
Test patches for verifying Waldorf Column 5 fix.

This script creates SFZ files with different volume settings to test
that Column 5 now correctly outputs gain (linear) instead of tune (cents).
"""

import os
import math
from pathlib import Path

def db_to_linear(db_value):
    """Convert decibel value to linear multiplier."""
    return math.pow(10, db_value / 20.0)

def create_test_sfz_patches():
    """Create test SFZ files with different volume settings."""
    
    test_dir = Path("conf/test_column_fix")
    test_dir.mkdir(exist_ok=True)
    
    # Test cases for Column 5 (gain) verification
    test_cases = [
        {
            'name': 'test_col5_gain_negative12db',
            'description': 'Test -12dB volume (should output 0.251 in column 5)',
            'volume_db': -12.0,
            'expected_linear': 0.251189,
            'note': 60
        },
        {
            'name': 'test_col5_gain_0db',
            'description': 'Test 0dB volume (should output 1.0 in column 5)',
            'volume_db': 0.0,
            'expected_linear': 1.0,
            'note': 61
        },
        {
            'name': 'test_col5_gain_plus6db',
            'description': 'Test +6dB volume (should output 1.995 in column 5)',
            'volume_db': 6.0,
            'expected_linear': 1.995262,
            'note': 62
        },
        {
            'name': 'test_col5_gain_plus12db',
            'description': 'Test +12dB volume (should output 3.981 in column 5)',
            'volume_db': 12.0,
            'expected_linear': 3.981071,
            'note': 63
        }
    ]
    
    for test in test_cases:
        # Create SFZ file
        sfz_path = test_dir / f"{test['name']}.yaml"
        
        with open(sfz_path, 'w', encoding='utf-8') as f:
            f.write(f"""# Test patch: {test['description']}
# Expected Column 5 output: {test['expected_linear']:.6f}

name: "{test['name']}"
description: "{test['description']}"

# Audio settings
audio:
  samplerate: 48000
  bitdepth: 24

# MIDI interface (no MIDI needed for this test)
midi_interface:
  output_port_name: null

# Sampling configuration
sampling:
  note_range_start: {test['note']}
  note_range_end: {test['note']}
  velocity_layers: 1
  roundrobin_layers: 1
  hold_time: 2.0
  release_time: 0.5

# Post-processing
postprocessing:
  normalize: false
  trim_silence: false
  volume: {test['volume_db']:.1f}  # This is the key test parameter

# Export formats
export:
  formats:
    - map
""")
        
        # Also create a simple SFZ for direct testing
        sfz_direct_path = test_dir / f"{test['name']}.sfz"
        with open(sfz_direct_path, 'w', encoding='utf-8') as f:
            f.write(f"""// Test SFZ: {test['description']}
// Volume: {test['volume_db']}dB -> Expected linear: {test['expected_linear']:.6f}

<group>
lovel=1 hivel=127
volume={test['volume_db']:.1f}

<region>
sample=test_sample.wav
key={test['note']}
lokey={test['note']} hikey={test['note']}
""")

    # Create README for the test patches
    readme_path = test_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(f"""# Waldorf Column 5 Fix Test Patches

These test patches verify that Column 5 now correctly outputs **gain** (linear) instead of **tune** (cents).

## Test Cases

| File | Volume (dB) | Expected Linear | Test Note |
|------|------------|----------------|-----------|
| `test_col5_gain_negative12db` | -12.0 dB | 0.251189 | C4 (60) |
| `test_col5_gain_0db` | 0.0 dB | 1.000000 | C#4 (61) |
| `test_col5_gain_plus6db` | +6.0 dB | 1.995262 | D4 (62) |
| `test_col5_gain_plus12db` | +12.0 dB | 3.981071 | D#4 (63) |

## Testing Instructions

### Method 1: Using AutosamplerT Scripts
```bash
# Test each patch (requires MIDI/audio setup)
python autosamplerT.py --script conf/test_column_fix/test_col5_gain_0db.yaml --test_mode

# Export to map format
python autosamplerT.py --script conf/test_column_fix/test_col5_gain_0db.yaml --export_formats map
```

### Method 2: Direct SFZ Testing
```bash
# Test direct SFZ export (no sampling needed)
python -c "
from src.export.export_waldorf_sample_map import WaldorfSampleMapExporter
exporter = WaldorfSampleMapExporter(location=2)
exporter.export('output/test_col5', 'test_col5_gain_0db', 'conf/test_column_fix/test_col5_gain_0db.sfz', 'samples')
"
```

## What to Verify

1. **Column 5 values**: Should match expected linear values, not 1.0 (old tune behavior)
2. **dB to Linear conversion**: -12dB ≈ 0.251, 0dB = 1.0, +6dB ≈ 1.995, +12dB ≈ 3.981
3. **No regression**: Other columns should remain unchanged

## Expected Output Format

Before fix (WRONG):
```
"2:samples/test_sample.wav"	60.0	60	60	1.0	1	127	...
```

After fix (CORRECT):
```
"2:samples/test_sample.wav"	60.0	60	60	0.251189	1	127	...
                                        ^^^^^^^ 
                                     Column 5: Gain (linear)
```

## Formula Verification

The conversion formula used: `linear = 10^(dB/20)`

| dB | Formula | Result |
|----|---------|--------|
| -12 | 10^(-12/20) | 0.251189 |
| 0 | 10^(0/20) | 1.000000 |
| +6 | 10^(6/20) | 1.995262 |
| +12 | 10^(12/20) | 3.981071 |

---
*Generated by: test_waldorf_column_fix.py*
*Date: January 16, 2026*
""")

    print(f"Created test patches in: {test_dir}")
    print(f"Files created:")
    for test in test_cases:
        print(f"  - {test['name']}.yaml (AutosamplerT script)")
        print(f"  - {test['name']}.sfz (Direct SFZ test)")
    print(f"  - README.md (Test documentation)")

if __name__ == "__main__":
    create_test_sfz_patches()