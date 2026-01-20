# Waldorf Sample Map (.map) Format Documentation

The Waldorf Sample Map (.map) format is used by Waldorf Quantum and Iridium synthesizers for multisample definition. Unlike the QPAT format, this is a plain text file with no binary header.

## File Structure

The .map file consists of one sample definition per line, where each line contains 16 tab-separated columns representing sample mapping and playback parameters.

## Column Layout

Each line in the .map file contains exactly 16 tab-separated columns:

| Column | Name (Official) | Data Type | Range/Format | Known Values | Description |
|--------|-----------------|-----------|--------------|-------------|-------------|
| 1 | Sample Location | String | `"N:path/file.wav"` | 2: (SD), 3: (Internal), 4: (USB) | Quoted path with location prefix |
| 2 | Pitch | Float | 0.0 - 127.0 | MIDI note numbers | Root note/pitch center (pitch_keycenter) |
| 3 | From Note | Integer | 0 - 127 | MIDI note numbers | Lowest key for sample (lokey) |
| 4 | To Note | Integer | 0 - 127 | MIDI note numbers | Highest key for sample (hikey) |
| 5 | Sample Gain | Float | ? | Usually 1.0 | Sample gain/volume multiplier |
| 6 | From Velo | Integer | 1 - 127 | MIDI velocity | Lowest velocity for sample (lovel) |
| 7 | To Velo | Integer | 1 - 127 | MIDI velocity | Highest velocity for sample (hivel) |
| 8 | ??? (Unknown) | Float | ? | Column 8 purpose unknown | Unknown field - purpose not documented |
| 9 | Sample Start | Float | 0.0 - 1.0 | Normalized position | Start position in sample (0.0 = beginning) |
| 10 | Sample End | Float | 0.0 - 1.0 | Normalized position | End position in sample (1.0 = full) |
| 11 | Loop Mode | Integer | 0, 1, 2 | 0=off, 1=forward, 2=ping-pong | Loop type |
| 12 | Loop Start | Float | 0.0 - 1.0 | Normalized position | Loop start point (from WAV SMPL chunk) |
| 13 | Loop End | Float | 0.0 - 1.0 | Normalized position | Loop end point (from WAV SMPL chunk) |
| 14 | Direction | Integer | 0, 1 | 0=forward, 1=reverse | Playback direction |
| 15 | X-Fade | Float | 0.0 - 1.0 | Usually 0.0 | Crossfade amount |
| 16 | Track Pitch | Integer | 0, 1 | 0=off, 1=on | Key tracking enable/disable |

## Location Prefixes

The Sample Location field (Column 1) uses a location prefix to specify where samples are stored:

- **2:** SD Card (default, recommended)
- **3:** Internal Memory  
- **4:** USB Storage

Example: `"2:samples/prophet6-test/samples/prophet6-test_C4_v127_rr1.wav"`

## Loop Points

Columns 12 and 13 contain normalized loop points (0.0-1.0) that are read from the WAV file's SMPL chunk:
- **Column 12:** Loop Start (normalized position where loop begins)
- **Column 13:** Loop End (normalized position where loop ends)  
- **Column 11:** Loop Mode determines how looping behaves

If the WAV file contains no loop points, loop mode is set to 0 (off) and loop positions default to 0.0 and 1.0.

## Example Line

```
"2:samples/prophet6-test/samples/prophet6-test_C4_v127_rr1.wav"	60.00000000	59	60	1.00000000	1	127	0.50000000	0.00000000	1.00000000	2	0.00000000	0.99958333	0	0.50020833	1
```

This represents:
- Sample from SD card location (Column 1: Sample Location)
- Root key C4 (Column 2: Pitch = 60.0)
- Key range C4-C4 (Columns 3-4: From Note=59, To Note=60)
- Full velocity range (Columns 6-7: From Velo=1, To Velo=127)
- Ping-pong loop mode (Column 11=2) with loop points from WAV SMPL chunk
- Key tracking enabled (Column 16: Track Pitch=1)

## Implementation Status Analysis

Based on the corrected field names, here's the current AutosamplerT implementation status:

### ✅ Correctly Implemented
- **Column 1:** Sample Location - ✅ Full path with location prefix (2:/3:/4:)
- **Column 2:** Pitch - ✅ Root key from pitch_keycenter + tune
- **Column 3:** From Note - ✅ Key range low (lokey)
- **Column 4:** To Note - ✅ Key range high (hikey)  
- **Column 6:** From Velo - ✅ Velocity range low (lovel)
- **Column 7:** To Velo - ✅ Velocity range high (hivel)
- **Column 9:** Sample Start - ✅ Always 0.0 (full sample)
- **Column 10:** Sample End - ✅ Always 1.0 (full sample)
- **Column 11:** Loop Mode - ✅ From constructor parameter (0/1/2)
- **Column 12:** Loop Start - ✅ From WAV SMPL chunk
- **Column 13:** Loop End - ✅ From WAV SMPL chunk
- **Column 16:** Track Pitch - ✅ Always 1 (key tracking on)

### ❌ Incorrectly Implemented
- **Column 5:** Sample Gain - ❌ Currently outputs `1.0` but should be linear gain from SFZ volume
- **Column 8:** Unknown Field - ❌ Currently outputs pan but field 8 purpose unknown
- **Column 14:** Direction - ❌ Currently outputs `0` (loop end random) instead of playback direction
- **Column 15:** X-Fade - ❌ Currently outputs loop start again instead of crossfade value

### 🔍 Needs Investigation
- **Column 8:** Purpose completely unknown - current pan implementation may be wrong placement
- Pan positioning might belong in a different column or be calculated differently

## Implementation Notes

- All floating-point values are formatted with 8 decimal places
- Loop points are automatically read from WAV SMPL chunks when available
- Location prefix 2: (SD card) is recommended as default
- Files must use tab characters (\\t) as separators, not spaces
- Sample paths must be quoted strings
- The .map format is purely text-based (no binary header unlike QPAT)

## Related Formats

This format is the text-only version of Waldorf's sample mapping system. For binary format with additional features, see QPAT format documentation.

---
*Generated by AutosamplerT - Last updated: January 10, 2026*