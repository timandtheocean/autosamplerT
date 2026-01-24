# Export Formats

AutosamplerT supports exporting multisamples to various hardware and software sampler formats. This allows you to sample once and deploy to multiple samplers.

## Supported Formats

| Format | Status | Description | Features |
|--------|--------|-------------|----------|
| **SFZ** | Native | Native format, always created | Loop points |
| **QPAT** | Implemented | Waldorf Quantum/Iridium format | Loop points, crossfade |
| **Waldorf .map** | Implemented | Waldorf text-based sample map | Loop points, crossfade |
| **Ableton ADV** | Implemented | Ableton Live Sampler format | Velocity crossfade, round-robin, loops |
| **EXS24** | TODO | Logic Pro EXS24 format | - |
| **SXT** | TODO | Reason NN-XT format | - |

## Export Configuration

### Loop Mode and Crossfade Support

Both QPAT and Waldorf .map formats support configurable loop modes and crossfade:

**CLI Usage:**
```bash
python autosamplerT.py --export_formats qpat,waldorf_map \
  --export_loop_mode 1 --export_loop_crossfade 15.0
```

**YAML Configuration:**
```yaml
export:
  formats:
    - qpat
    - waldorf_map
  loop_crossfade_ms: 12.5  # Global crossfade setting
  qpat:
    location: 2
    loop_mode: 1  # 0=off, 1=forward, 2=ping-pong
```

**Loop Mode Values:**
- `0` = Loop disabled
- `1` = Forward loop (default) 
- `2` = Ping-pong/bidirectional loop

**Crossfade Time:**
- Default: `10.0` milliseconds
- Range: `0.0` (no crossfade) to any positive value
- Applied only when loop points exist
- Helps smooth loop transitions

**Important:** Loop mode is only applied if the WAV file contains loop points (from auto-looping). Files without loop points will have loop mode set to 0 (off) regardless of configuration.

### Loop Point Source

Loop points are read from WAV file RIFF SMPL chunks, not SFZ files. This ensures consistency across all export formats:

1. **Auto-looping** writes loop points to WAV metadata during sampling
2. **Exporters** read loop points from the SMPL chunk
3. **Compatibility** works with both mono and stereo samples
4. **Accuracy** correctly normalizes loop points for any sample rate/format

**Fixed Issues (v2026.01.15):**
- Loop points now work correctly for mono samples (was assuming stereo)
- Loop start/end values are properly normalized
- Shared loop reading logic eliminates code duplication  
3. **Loop ranges** are normalized to 0.0-1.0 for sampler compatibility

---

## SFZ Format (Native)

**Status:**  Always created during sampling

### Overview
SFZ is a text-based format that defines sample mappings. AutosamplerT uses this as the native format and generates it automatically during sampling.

### File Structure
```
output/
  MySynth/
    MySynth.sfz          # SFZ mapping file
    samples/
      MySynth_C3_v127_rr1.wav
      MySynth_C3_v127_rr2.wav
      ...
```

### Features Supported
-  Velocity layers
-  Round-robin layers
-  Key mapping
-  Loop points (stored in WAV SMPL chunk)
-  Volume/pan control
-  Pitch tuning
-  ADSR envelopes
-  Filters

### Compatibility
- Compatible with any SFZ-supporting sampler:
  - Sforzando (free)
  - ARIA Engine
  - Plogue Sforzando
  - Many DAW samplers

### Usage
No export needed - SFZ is created automatically during sampling.

---

## Waldorf Quantum/Iridium QPAT Format

**Status:**  Fully Implemented

### Overview
The QPAT format is the native patch format for Waldorf Quantum and Iridium synthesizers. QPAT files are **text files** with a 512-byte binary header followed by plain text sections containing tab-separated sample maps and synth parameters.

### File Structure
```
output/
  MySynth/
    MySynth.qpat         # Text file with binary header (512 bytes) + text sections
    samples/
      MySynth/
        MySynth_C3_v127_rr1.wav
        MySynth_C3_v127_rr2.wav
        ...
```

### Format Specification

#### Binary Header (512 bytes)
- **Magic Number:** `3402932` (identifies QPAT format)
- **Preset Version:** `14` (current format version)
- **Name:** 32 bytes (patch name, ASCII)
- **Creator:** 32 bytes (creator name, ASCII)
- **Description:** 32 bytes (patch description, ASCII)
- **Categories:** 4 × 32 bytes (category + 3 keywords)
- **Parameter Count:** uint16 (number of synth parameters)
- **Resource Headers:** Up to 3 sample map headers
- **Padding:** To 512 bytes total

#### Parameters Section
Synth engine parameters for oscillators, filters, envelopes:
- Oscillator settings (type, pitch, volume, pan)
- Filter parameters (cutoff, resonance, type)
- Envelope generators (ADSR for amp and filter)
- Modulation matrix routing

#### Sample Maps (Tab-Separated Text)
Up to 3 sample maps (one per velocity layer or round-robin group).

**Format:** 16 columns, tab-separated
```
"LOCATION:path"  pitch  fromNote  toNote  gain  fromVelo  toVelo  pan  start  end  loopMode  loopStart  loopEnd  direction  crossfade  trackPitch
```

**Column Details:**

| Column | Type | Description | Range/Values |
|--------|------|-------------|--------------|
| **path** | string | Sample path with location prefix | `"4:samples/file.wav"` |
| **pitch** | float | Root note with tuning | 0.0-127.0 |
| **fromNote** | int | Key range start | 0-127 |
| **toNote** | int | Key range end | 0-127 |
| **gain** | float | Linear gain | 0.0-10.0+ |
| **fromVelo** | int | Velocity range start | 0-127 |
| **toVelo** | int | Velocity range end | 0-127 |
| **pan** | float | Panorama | 0.0-1.0 (0.5=center) |
| **start** | float | Sample start | 0.0-1.0 (fraction) |
| **end** | float | Sample end | 0.0-1.0 (fraction) |
| **loopMode** | int | Loop type | 0=off, 1=forward, 2=ping-pong |
| **loopStart** | float | Loop start | 0.0-1.0 (fraction) |
| **loopEnd** | float | Loop end | 0.0-1.0 (fraction) |
| **direction** | int | Playback direction | 0=forward, 1=reverse |
| **crossfade** | float | Loop crossfade | 0.0-1.0 |
| **trackPitch** | int | Key tracking | 0=off, 1=on |

### Sample Location Prefixes

The path column uses a location prefix to specify where samples are stored:

- **`2:`** - SD card (recommended - default)
- **`3:`** - Internal memory
- **`4:`** - USB drive (triggers auto-import to internal memory)

**Example (SD card):**
```
"2:samples/MySynth/MySynth_C3_v127.wav"	60.00000000	48	72	1.00000000	0	127	0.50000000	0.00000000	1.00000000	1	0.20000000	0.80000000	0	0.00000000	1
```

### Waldorf-Specific Constraints

1. **Maximum 3 Sample Maps**
   - One map per velocity layer or round-robin group
   - If >3 groups exist, extras are merged into 3rd map
   
2. **Maximum 128 Samples Per Map**
   - Hardware limitation

3. **Sample RAM Limit**
   - ~360MB total (converted to 32-bit float internally)
   
4. **Audio Format**
   - Sample rate: 44.1 kHz (native - recommended) or 48 kHz
   - Bit depth: 24-bit (recommended) or 32-bit float
   - Quantum/Iridium converts to 32-bit float internally
   - Supports WAV and AIFF

5. **Auto-Mapping Requirements**
   - Only works with no key range overlap
   - Single velocity layer, no round-robin
   - Manual maps support multiple velocity + round-robin

### Usage

#### Export from Existing SFZ
```bash
# Basic export (SD card, keep original audio format)
python autosamplerT.py --process MySynth --export_formats qpat

# SD card with audio optimization (convert to 44.1kHz 32-bit float)
python autosamplerT.py --process MySynth --export_formats qpat --export_optimize_audio

# USB location (triggers auto-import to internal memory)
python autosamplerT.py --process MySynth --export_formats qpat --export_location 4
```

#### Export During Sampling
```bash
# Sample and export to QPAT
python autosamplerT.py --script conf/my_synth.yaml
```

#### YAML Configuration
```yaml
export:
  formats:
    - qpat
  qpat:
    location: 2              # 2=SD card (default), 3=internal, 4=USB
    optimize_audio: false    # false=keep original (44.1kHz 24-bit), true=convert to 44.1kHz 32-bit float
```

**Audio Optimization Options:**
- **`optimize_audio: false`** (recommended)
  - Keeps original sample rate and bit depth (e.g., 44.1kHz 24-bit)
  - Smaller file sizes
  - No quality loss from conversion
  - Waldorf converts to 32-bit internally anyway

- **`optimize_audio: true`**
  - Converts all samples to 44.1kHz 32-bit float
  - Larger file sizes
  - Use if source samples have varying sample rates
  - Use if experiencing compatibility issues

### Importing to Quantum/Iridium

#### Option 1: SD Card (Recommended)
1. **Export to SD card location** (default):
   ```bash
   python autosamplerT.py --process MySynth --export_formats qpat
   ```
2. **Copy output folder** to SD card root or organized folder
3. **Insert SD card** into Quantum/Iridium
4. **Load patch** from SD card location
5. Samples play directly from SD card (no internal memory used)

#### Option 2: USB Auto-Import
1. **Export with USB location**:
   ```bash
   python autosamplerT.py --process MySynth --export_formats qpat --export_location 4
   ```
2. **Copy output folder** to USB drive
3. **Connect USB drive** to Quantum/Iridium USB port
4. **Load patch** - synth auto-imports samples to internal memory
5. Can disconnect USB after import completes

### Features Supported
-  Velocity layers (up to 3)
-  Round-robin layers (up to 3)
-  Key mapping with ranges
-  Loop points (forward and ping-pong)
-  Gain control
-  Pan positioning
-  Pitch/tuning
-  Key tracking
- ⚠️ Filters (basic support, limited modulation)
- ⚠️ Envelopes (ADSR only, simplified curves)

### Known Limitations
- Maximum 3 groups (velocity or round-robin)
- No LFO modulation export
- Simplified envelope curves
- Basic filter support only
- No wavetable/kernel support (Particle mode only)

### Troubleshooting

**Problem:** Samples don't load from SD card
- **Solution:** Verify SD card is properly formatted and inserted. Check file paths are correct.

**Problem:** USB auto-import not working
- **Solution:** Use `--export_location 4` to enable USB auto-import trigger

**Problem:** "Out of memory" error
- **Solution:** Use SD card (location 2) instead of internal memory, or reduce number of samples

**Problem:** Velocity layers don't switch
- **Solution:** Check velocity ranges in SFZ don't overlap, ensure `fromVelo`/`toVelo` are correct

**Problem:** Loop points incorrect
- **Solution:** Verify loop points in source WAV files (SMPL chunk), use `--auto_loop` during sampling

---

## Ableton Live Sampler Format

**Status:** Implemented

### Overview
The ADV format is Ableton Live's Sampler instrument preset format. ADV files are **GZIP-compressed XML files** containing sample mappings, loop points, and all Sampler parameters. This export creates multisamples that load directly in Ableton Live's Sampler device.

### File Structure
```
output/
  MySynth/
    MySynth.adv          # GZIP-compressed XML preset
    samples/
      MySynth_C3_v127_rr1.wav
      MySynth_C3_v127_rr2.wav
      ...
```

### Format Specification

#### File Format
- **Container:** GZIP-compressed XML
- **Extension:** `.adv`
- **Encoding:** UTF-8
- **Schema Version:** 5.11 (Ableton Live 11 compatible)

#### XML Structure
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="5" MinorVersion="11.0_11300" 
         SchemaChangeCount="3" Creator="AutosamplerT">
    <MultiSampler>
        <Player>
            <MultiSampleMap>
                <SampleParts>
                    <MultiSamplePart Id="0">
                        <!-- Sample zone definition -->
                    </MultiSamplePart>
                </SampleParts>
            </MultiSampleMap>
        </Player>
        <!-- Sampler engine parameters -->
    </MultiSampler>
</Ableton>
```

### Sample Zone Mapping

Each sample has a `MultiSamplePart` element defining its key range, velocity range, and selector range (for round-robin):

#### KeyRange - Note Mapping with Crossfade
```xml
<KeyRange>
    <Min Value="48" />           <!-- Lowest MIDI note -->
    <Max Value="72" />           <!-- Highest MIDI note -->
    <CrossfadeMin Value="48" />  <!-- Start of crossfade in -->
    <CrossfadeMax Value="72" />  <!-- End of crossfade out -->
</KeyRange>
```
- **CrossfadeMin/CrossfadeMax** define the soft crossfade boundaries
- Enables smooth blending between adjacent key zones

#### VelocityRange - Velocity Layers with Crossfade
```xml
<VelocityRange>
    <Min Value="1" />            <!-- Lowest velocity -->
    <Max Value="64" />           <!-- Highest velocity -->
    <CrossfadeMin Value="1" />   <!-- Crossfade start (soft) -->
    <CrossfadeMax Value="64" />  <!-- Crossfade end (soft) -->
</VelocityRange>
```

**Velocity Crossfade Calculation:**
For velocity layers, crossfade zones are calculated for smooth transitions:
- Layer 1 (bottom): CrossfadeMin=1, CrossfadeMax=CrossfadeWidth
- Middle layers: Overlap with adjacent layers
- Layer N (top): CrossfadeMin=Max-CrossfadeWidth, CrossfadeMax=127

**Default Crossfade:** 15 velocity units (~12% of range)

#### SelectorRange - Round-Robin via Selector
```xml
<SelectorRange>
    <Min Value="0" />
    <Max Value="63" />
    <CrossfadeMin Value="0" />
    <CrossfadeMax Value="63" />
</SelectorRange>
```

**Round-Robin Implementation:**
- Ableton Sampler uses the "Selector" parameter (0-127) for round-robin
- The 0-127 range is divided equally among round-robin samples
- Example with 2 RR layers: Sample 1 = 0-63, Sample 2 = 64-127
- Example with 4 RR layers: 0-31, 32-63, 64-95, 96-127

**Setting Up Round-Robin in Ableton:**
1. Load the .adv preset
2. In Sampler, find the "Selector" knob in the Zone tab
3. Map Selector to a MIDI CC or use a Max for Live device
4. Automate or use a Random LFO to cycle through values

#### Loop Points
```xml
<SustainLoop>
    <Start Value="22050" />      <!-- Loop start (sample frames) -->
    <End Value="44100" />        <!-- Loop end (sample frames) -->
    <Mode Value="1" />           <!-- 0=off, 1=forward, 2=alternating -->
    <Crossfade Value="441" />    <!-- Crossfade in samples (10ms @44.1kHz) -->
    <Detune Value="0" />
</SustainLoop>
```

**Loop Mode Values:**
- `0` = Loop disabled
- `1` = Forward loop (standard)
- `2` = Alternating (ping-pong) loop
- `3` = Release loop (for ReleaseLoop element)

### Features Supported

- **Key Mapping** - Full keyboard support with configurable ranges
- **Key Crossfade** - Smooth blending between adjacent key zones
- **Velocity Layers** - Multiple velocity layers with crossfade
- **Velocity Crossfade** - Soft transitions between velocity layers
- **Round-Robin** - Via SelectorRange parameter
- **Loop Points** - Forward and ping-pong loops from WAV SMPL chunk
- **Loop Crossfade** - Smooth loop transitions
- **Root Key/Pitch** - Correct pitch mapping
- **Volume/Pan** - Per-sample gain and pan

### Usage

#### Export from Existing SFZ
```bash
# Basic export
python autosamplerT.py --process MySynth --export_formats ableton

# Combined export (QPAT + Ableton)
python autosamplerT.py --process MySynth --export_formats qpat,ableton
```

#### Export During Sampling
```bash
python autosamplerT.py --script conf/my_synth.yaml --export_formats ableton
```

#### YAML Configuration
```yaml
export:
  formats:
    - ableton
  # Velocity crossfade is automatic based on number of layers
```

### Importing to Ableton Live

1. **Locate the ADV file** in your output folder
2. **Copy to User Library** (optional):
   - macOS: `~/Music/Ableton/User Library/Presets/Instruments/Sampler/`
   - Windows: `\Users\[username]\Documents\Ableton\User Library\Presets\Instruments\Sampler\`
3. **Open Ableton Live**
4. **Drag the .adv file** onto a MIDI track, or
5. **Browse in Live's browser** under User Library > Presets > Instruments > Sampler

**Important:** Keep the `samples/` folder in the same location as the .adv file, or collect and save after loading.

### Ableton-Specific Constraints

1. **Sample Paths**
   - Relative paths from the .adv file location
   - Samples must be in a `samples/` subfolder
   - Use "Collect All and Save" in Ableton to consolidate

2. **Round-Robin Requires Setup**
   - Selector must be modulated for RR to work
   - Use Max for Live Round Robin device, or
   - Map Selector to MIDI CC with cycling values

3. **Velocity Crossfade**
   - Enabled by default with 15-unit crossfade
   - Creates smooth transitions between velocity layers

### Known Limitations
- Round-robin requires manual Selector modulation setup
- No filter/envelope export (uses Sampler defaults)
- No modulation routing export
- Maximum tested: 128 samples per preset

### Troubleshooting

**Problem:** Samples don't load
- **Solution:** Ensure samples folder is in same directory as .adv file. Use "Collect All and Save" to consolidate.

**Problem:** Round-robin not cycling
- **Solution:** Selector parameter needs external modulation. Use a Max for Live device or MIDI CC mapping.

**Problem:** Velocity crossfade too abrupt/smooth
- **Solution:** Currently fixed at 15 units. Edit XML manually for custom crossfade.

**Problem:** Loop points not correct
- **Solution:** Verify loop points in source WAV files (SMPL chunk). Run auto-loop during sampling.

---

## Logic Pro EXS24 Format

**Status:**  TODO - Planned for future release

### Overview
Export format for Logic Pro's EXS24 sampler.

### Planned Features
- EXS instrument file (.exs)
- Sample folder structure
- Velocity layers
- Key mapping

### Implementation Notes
- Research `.exs` binary format
- Analyze ConvertWithMoss EXS export
- Support zones and groups

---

## Native Instruments Kontakt SXT Format

**Status:**  TODO - Planned for future release

### Overview
Export format for Native Instruments Kontakt sampler.

### Planned Features
- SXT preset format
- Multi-sample support
- Velocity layers
- Round-robin groups

### Implementation Notes
- Research `.nki` and sample folder structure
- Analyze ConvertWithMoss SXT export

---

## Export Workflow

### Single Format Export
```bash
# Export to QPAT only
python autosamplerT.py --process MySynth --export_formats qpat
```

### Multiple Format Export
```bash
# Export to multiple formats (shares samples folder)
python autosamplerT.py --process MySynth --export_formats qpat,ableton,exs
```

### Export with Optimization
```bash
# Convert samples during export
python autosamplerT.py --process MySynth --export_formats qpat --export_optimize_audio
```

### Export During Sampling
```bash
# Sample and auto-export to all formats
python autosamplerT.py --script conf/my_synth.yaml --export_formats qpat,ableton,exs
```

---

## Best Practices

### Sample Once, Export Many
1. **Sample with highest quality settings:**
   - High sample rate (96kHz)
   - 32-bit depth
   - Low noise floor
   
2. **Keep master SFZ + samples:**
   - Source of truth for all exports
   - Can re-export anytime
   
3. **Export to target formats:**
   - Each sampler gets optimized format
   - Shared samples folder (no duplication)

### Organizing Exports
```
output/
  MySynth/
    MySynth.sfz              # Master SFZ
    MySynth.qpat             # Waldorf export
    MySynth.adg              # Ableton export (TODO)
    MySynth.exs              # Logic export (TODO)
    samples/
      MySynth/               # Shared samples folder
        MySynth_C3_v127.wav
        ...
```

### Format-Specific Optimization

**Waldorf QPAT:**
- Use `--export_optimize_audio` for 44.1kHz 32-bit
- Limit to 3 velocity/round-robin groups
- Keep total samples <128 per map

**SFZ:**
- Keep original sample quality
- Use for archival and re-export

**Future formats:**
- Check sampler-specific requirements
- Optimize per target platform

---

## API Reference

### Command-Line Arguments

```bash
--export_formats FORMAT[,FORMAT...]
```
Comma-separated list of export formats: `qpat`, `ableton`, `exs`, `sxt`

```bash
--export_location 2|3|4
```
Waldorf sample location (QPAT only):
- `2` = SD card
- `3` = Internal memory
```bash
--export_location 2|3|4
```
Waldorf sample location (QPAT only):
- `2` = SD card (default, recommended)
- `3` = Internal memory
- `4` = USB drive (triggers auto-import to internal)

```bash
--export_optimize_audio
```
Convert samples to target-optimal format (currently 44.1kHz 32-bit float for QPAT)

### YAML Configuration

```yaml
export:
  formats:
    - qpat
    - ableton
    - exs
  qpat:
    location: 2              # Sample location (2=SD default, 3=internal, 4=USB)
    optimize_audio: true     # Convert to 44.1kHz 32-bit
```

### Python API

```python
from src.export.export_qpat import export_to_qpat

# Export to QPAT
success = export_to_qpat(
    output_folder='output/MySynth',
    multisample_name='MySynth',
    sfz_file='output/MySynth/MySynth.sfz',
    samples_folder='output/MySynth/samples',
    location=4,
    optimize_audio=True
)
```

---

## Technical Implementation

### SFZ Parser
The export system includes a lightweight SFZ parser that extracts:
- Groups (velocity layers, round-robin)
- Zones (individual samples)
- Key ranges (`lokey`, `hikey`)
- Velocity ranges (`lovel`, `hivel`)
- Loop points (`loop_mode`, `loop_start`, `loop_end`)
- Pitch/tuning (`pitch_keycenter`, `tune`)
- Volume/pan (`volume`, `pan`)

### Sample Path Resolution
- Reads sample paths from SFZ `sample=` opcodes
- Resolves relative paths from SFZ location
- Copies samples to format-specific output folder
- Preserves original samples (non-destructive)

### Format Writers
Each format has a dedicated writer class:
- `WaldorfQpatExporter` - QPAT format writer
- `AbletonExporter` - TODO
- `ExsExporter` - TODO
- `SxtExporter` - TODO

---

## Future Enhancements

### Planned Features
- [ ] Ableton Live export (.adg, .adv)
- [ ] Logic Pro EXS24 export (.exs)
- [ ] Kontakt SXT export
- [ ] Sample format conversion pipeline
- [ ] Batch export to multiple formats
- [ ] Format validation/testing

### Community Contributions
Want to add support for your favorite sampler format?
1. Check `TODO.md` for planned formats
2. Review `src/export/export_qpat.py` as reference
3. Analyze target format specification
4. Submit pull request with new exporter

---

## See Also

- [OUTPUT.md](OUTPUT.md) - Native SFZ output format
- [POSTPROCESSING.md](POSTPROCESSING.md) - Sample processing before export
- [TODO.md](../TODO.md) - Roadmap for future export formats

---

*Last updated: November 13, 2025*
