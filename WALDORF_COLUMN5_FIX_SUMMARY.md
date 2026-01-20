# Waldorf Column 5 Fix - Implementation Summary

## Issue Identified
Based on hardware testing of Waldorf Quantum/Iridium, **Column 5** in the MAP format was incorrectly mapped:
- **Current code**: Output `tune` (tuning in cents)  
- **Hardware shows**: `sample_gain` (volume gain in dB, as linear multiplier)
- **Your observation**: `-12.4dB` gain values, not tune values

## Fix Implemented ✅

### 1. Column Mapping Correction
**File**: `src/export/export_waldorf_sample_map.py`

**Before** (WRONG):
```python
tune = float(region.get('tune', 1.0))  # Cents tuning
# ...
format_double_value(tune),              # Column 5: Tune/Gain
```

**After** (CORRECT):
```python
# FIXED: Column 5 - Convert SFZ volume (dB) to linear gain
volume_db = float(region.get('volume', 0.0))  # SFZ volume in dB
sample_gain = math.pow(10, volume_db / 20.0)  # Convert dB to linear gain
# ...
format_double_value(sample_gain),       # Column 5: GAIN (FIXED!) ✅
```

### 2. Added dB to Linear Conversion
- **Formula**: `linear = 10^(dB/20)`
- **Examples**:
  - `-12dB → 0.251189`
  - `0dB → 1.000000` 
  - `+6dB → 1.995262`
  - `+12dB → 3.981071`

### 3. Fixed SFZ Parsing Issue
The SFZ parser couldn't handle multiple parameters on one line (e.g., `lovel=1 hivel=127`).

**Added logic to handle**:
- Single parameters: `volume=0.0`
- Multiple parameters: `lovel=1 hivel=127`
- Mixed formats in same file

## Verification Tests ✅

Created comprehensive test suite in `conf/test_column_fix/`:

| Test File | Volume | Expected Linear | Verified |
|-----------|--------|----------------|----------|
| `test_col5_gain_negative12db` | -12dB | 0.251189 | ✅ |
| `test_col5_gain_0db` | 0dB | 1.000000 | ✅ |
| `test_col5_gain_plus6db` | +6dB | 1.995262 | ✅ |
| `test_col5_gain_plus12db` | +12dB | 3.981071 | ✅ |

## Updated Column Format Documentation ✅

**File**: `src/export/export_waldorf_sample_map.py`

Updated column format comments with verification status:
- ✅ = Verified correct
- ❓ = Needs hardware testing
- ❌ = Known issue (fixed)

```python
Waldorf .map format (16 tab-separated columns):
1. Sample Location (quoted path with location prefix) ✅
2. Pitch (root note + tuning) ✅
3. From Note (key range low) ✅
4. To Note (key range high) ✅
5. Sample Gain (linear multiplier from dB) ✅ FIXED
6. From Velo (velocity range low) ✅
7. To Velo (velocity range high) ✅
8. Unknown Field (pan/stereo width/filter?) ❓ MYSTERY
9. Sample Start (normalized 0.0-1.0) ✅
10. Sample End (normalized 0.0-1.0) ✅
11. Loop Mode (0=off, 1=forward, 2=ping-pong) ✅
12. Loop Start (normalized 0.0-1.0, from WAV SMPL chunk) ✅
13. Loop End (normalized 0.0-1.0, from WAV SMPL chunk) ✅
14. Direction (0=forward, 1=reverse) ❓ VERIFY
15. X-Fade (crossfade amount 0.0-1.0) ❓ VERIFY
16. Track Pitch (0=off, 1=on) ✅
```

## Testing Instructions

### Quick Test
```bash
python -c "
from src.export.export_waldorf_sample_map import WaldorfSampleMapExporter
exporter = WaldorfSampleMapExporter()
exporter.export('output/test', 'test', 'conf/test_column_fix/test_col5_gain_0db.sfz', 'samples')
"
```

### Full Test Suite
```bash
python test_waldorf_column_fix.py
```

## Impact

This fix resolves the critical Column 5 mismapping that was causing incorrect sample gain values in exported Waldorf MAP files. The hardware testing confirmed that Column 5 controls sample gain/volume, not tuning, which is now correctly implemented.

**Before**: Waldorf would receive tuning values where it expected gain
**After**: Waldorf receives proper gain values matching the SFZ volume parameter

---
*Fixed: January 16, 2026*  
*Verified: Hardware testing + automated tests*