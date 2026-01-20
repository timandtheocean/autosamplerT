# Wavetable Creation - AutosamplerT

## Overview

AutosamplerT's wavetable creation feature allows you to sample hardware synthesizers while sweeping control parameters to create wavetables with various curve types. This is perfect for capturing filter sweeps, oscillator morphing, or any parameter that creates interesting timbral changes.

## Recent Implementation (January 2026)

The wavetable creation system has been implemented as a complete feature with:

### **Core Features**
- **Automatic note calculation:** Optimal frequency selection for clean wave periods
- **MIDI learn system:** Learn any CC, NRPN, or CC14 control parameter
- **Multiple sweep curves:** Linear, logarithmic, exponential, log-linear, and linear-log
- **Flexible wavetable sizes:** 128, 512, 1024, 2048, or 4096 samples per waveform
- **Configurable wave counts:** Up to 256 waves (217 for 4096 samples)
- **Perfect timing synchronization:** MIDI sweep aligned with audio capture

### **Supported Formats**
- **Audio:** 8-bit, 16-bit, or 24-bit WAV files
- **Sample rates:** Any supported by your audio interface (44.1kHz recommended)
- **Channels:** Stereo capture with mono/stereo output options

## Usage

### **Basic Command**
```bash
python autosamplerT.py --wavetable
```

This launches the interactive wavetable creation wizard.

### **Workflow Steps**

#### **1. Configuration Setup**
The system will prompt for:
- **Wavetable name:** Base name for output files
- **Samples per waveform:** 128, 512, 1024, 2048, or 4096
- **Number of waves:** 2 to 256 (max 217 for 4096 samples)
- **Output folder:** Where to save wavetable files

#### **2. MIDI Learn Process**
```
MIDI Learn: Move the control you want to learn...
✓ Learned: CC74 (Channel 1)

Step 1: Move control to MINIMUM position and hold...
✓ MINIMUM position: 0

Step 2: Move control to MAXIMUM position and hold...  
✓ MAXIMUM position: 127

✓ Range learned: 0 to 127
```

#### **3. Automatic Note Calculation**
The system automatically calculates the optimal note frequency:
```
Optimal wavetable note: C3 (MIDI 48, 130.81 Hz)
Wave period: 337.0 samples (target: 337)
```

#### **4. Wavetable Creation**
Five separate wavetables are created with different sweep curves:
- `wavetable-lin-2048.wav` - Linear sweep
- `wavetable-log-2048.wav` - Logarithmic sweep  
- `wavetable-exp-2048.wav` - Exponential sweep
- `wavetable-log-lin-2048.wav` - Log-linear hybrid
- `wavetable-lin-log-2048.wav` - Linear-log hybrid

## Technical Details

### **Wave Period Calculation**
The system automatically selects the optimal MIDI note to ensure clean wave periods:

```python
ideal_frequency = sample_rate / samples_per_waveform
midi_note = 69 + 12 * log2(ideal_frequency / 440.0)
```

For 2048 samples at 44.1kHz: ~21.5Hz (approximately E0)

### **Sweep Timing**
- **Total length:** `samples_per_waveform × number_of_waves`
- **Sweep length:** Total length minus 1 wave period
- **Perfect alignment:** MIDI parameter changes synchronized with audio capture

### **Curve Mathematics**

#### **Linear**
```
value = min + (max - min) × progress
```

#### **Logarithmic** 
```
log_value = log(min) + (log(max) - log(min)) × progress
value = exp(log_value)
```

#### **Exponential**
```
value = min + (max - min) × progress²
```

#### **Log-Linear**
First half logarithmic, second half linear

#### **Linear-Log**
First half linear, second half logarithmic

### **File Naming Convention**
```
{name}-wavetable-{curve}-{samples_per_waveform}.wav
```

Examples:
- `filter_sweep-wavetable-lin-2048.wav`
- `morphing_osc-wavetable-log-4096.wav`

## Configuration Files

### **Main Config (autosamplerT_config.yaml)**
Audio and MIDI interface settings are used from the main configuration.

### **Wavetable Config (conf/wavetable_config.yaml)**
```yaml
wavetable_defaults:
  bit_depth: 24
  samples_per_waveform: 2048
  number_of_waves: 64
  output_folder: "./output/wavetables"
  name_prefix: "wavetable"
  learn_timeout: 30.0
  range_timeout: 60.0
```

## Best Practices

### **Hardware Preparation**
1. **Set up your synthesizer** with an interesting sound
2. **Connect MIDI** for parameter control
3. **Connect audio** from synth to audio interface
4. **Test the control** you want to sweep manually

### **Parameter Selection**
- **Filter cutoff:** Classic wavetable source
- **Oscillator shape/pulse width:** Creates dramatic timbral changes  
- **Wave folding/distortion:** Adds harmonic content variation
- **LFO rate/depth:** For rhythmic wavetables
- **Envelope amounts:** For dynamic wavetables

### **Optimal Settings**
- **2048 samples:** Good balance of quality and file size
- **64-128 waves:** Smooth parameter sweeps
- **24-bit depth:** Professional quality
- **44.1kHz sample rate:** Standard for wavetables

### **Quality Tips**
- **Use sustained sounds** without natural decay
- **Avoid effects** like reverb or delay during capture
- **Monitor levels** to prevent clipping
- **Test MIDI timing** before long captures

## Troubleshooting

### **MIDI Learn Issues**
- **No control detected:** Check MIDI connections and device settings
- **Wrong parameter learned:** Move only the desired control during learn
- **Range too narrow:** Ensure full parameter sweep during range learning

### **Audio Issues**
- **Clipping:** Reduce synthesizer output level
- **Low signal:** Increase synthesizer level or audio interface gain
- **Noise:** Check audio connections and interface settings

### **Timing Issues**
- **MIDI lag:** Adjust audio interface buffer settings
- **Sweep alignment:** Test with shorter wavetables first
- **Parameter jumps:** Ensure smooth hardware control movement

## Advanced Usage

### **Custom Curve Development**
The sweep curve system is modular. New curves can be added to `src/wavetable/sweep_curves.py`.

### **Batch Processing**
For multiple wavetables, modify the wavetable_mode.py to accept configuration files.

### **Integration with Samplers**
The generated wavetables are compatible with:
- **Serum:** Load directly as wavetables
- **Massive X:** Import as user wavetables  
- **Pigments:** Wavetable import function
- **Phase Plant:** Custom wavetable loading

## File Organization

```
output/wavetables/
├── filter_sweep-wavetable-lin-2048.wav
├── filter_sweep-wavetable-log-2048.wav
├── filter_sweep-wavetable-exp-2048.wav
├── filter_sweep-wavetable-log-lin-2048.wav
└── filter_sweep-wavetable-lin-log-2048.wav
```

## Performance Considerations

### **Memory Usage**
- **4096 samples, 256 waves:** ~4MB per wavetable
- **2048 samples, 128 waves:** ~1MB per wavetable
- **System RAM:** 5 curves × file size during processing

### **Processing Time**
- **2048 samples, 64 waves:** ~8 seconds at 44.1kHz
- **4096 samples, 128 waves:** ~24 seconds at 44.1kHz
- **Plus MIDI learn time:** ~2-3 minutes total

### **Storage Requirements**
Each wavetable session creates 5 files, so plan storage accordingly.

---

The wavetable creation feature provides professional-quality wavetable generation directly from hardware synthesizers, with perfect timing synchronization and multiple curve options for maximum creative flexibility.

*Last updated: January 20, 2026*