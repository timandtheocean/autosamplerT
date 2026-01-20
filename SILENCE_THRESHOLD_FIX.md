# Silence Threshold Detection Fix

## Problem
The silence threshold detection was not working properly due to an incorrect method call in the `sample_noise_floor()` method. It was trying to access `self.sample_processor.audio_engine.record()` instead of using the directly available `self.audio_engine.record()`.

## Root Cause
1. **Incorrect audio engine access**: The method was trying to access the audio engine through `sample_processor`, which may not be initialized when `sample_noise_floor()` is called.
2. **Missing setup verification**: The method wasn't ensuring the audio engine was properly configured before attempting to record.

## Solution
### Changes Made

1. **Fixed audio engine access** in `src/sampler.py`:
   ```python
   # Before (incorrect):
   silence_audio = self.sample_processor.audio_engine.record(duration)
   
   # After (correct):
   silence_audio = self.audio_engine.record(duration)
   ```

2. **Added audio engine setup verification**:
   ```python
   # Ensure audio engine is properly set up before recording
   if not self.audio_engine.setup():
       logging.error("Audio engine setup failed")
       return -60.0
   ```

3. **Improved test mode simulation** in `src/sampling/audio_engine.py`:
   ```python
   # Before: Perfect silence (unrealistic -200dB)
   silent_audio = np.zeros((num_samples, self.channels), dtype='float32')
   
   # After: Realistic noise floor simulation (-70dB typical)
   noise_level = 10 ** (-70 / 20)  # -70dB in linear scale
   noise_audio = np.random.normal(0, noise_level, (num_samples, self.channels)).astype('float32')
   ```

## How It Works Now

### Automatic Silence Detection Process
1. **No MIDI sent**: When `trim_silence: true` and `silence_detection: auto` are configured, the system records silence WITHOUT sending any MIDI messages to the synthesizer.

2. **Noise floor analysis**: Records 2 seconds of ambient audio from your audio interface to measure the actual noise floor of your signal chain (synthesizer + audio interface + cables).

3. **Threshold calculation**: Calculates the noise floor in dB and adds a 6dB safety margin to create the silence trim threshold.

4. **Postprocessing application**: Uses this detected threshold during postprocessing to trim silence from recorded samples.

### Configuration Options

```yaml
postprocessing:
  trim_silence: true
  silence_detection: auto    # Automatically detect noise floor
  # OR
  silence_detection: manual  # Use manual threshold
  silence_threshold: -60.0   # Manual threshold in dB (only used with manual mode)
```

### Expected Results
- **Typical noise floors**: -70dB to -50dB (depending on audio interface quality)
- **Calculated thresholds**: -64dB to -44dB (noise floor + 6dB margin)
- **Log output example**:
  ```
  Recording 2.0s of silence to detect noise floor...
  Detected noise floor: -70.0dB
  Silence trim threshold: -64.0dB
  ```

## Benefits
1. **Adaptive to your setup**: Automatically adapts to your specific audio interface's noise characteristics
2. **No MIDI interference**: Records pure ambient noise without triggering the synthesizer
3. **Proper integration**: The detected threshold is correctly passed to the postprocessing pipeline
4. **Fallback safety**: Falls back to -60dB if detection fails

## Testing
Run the test to verify the fix:
```bash
python test_silence_threshold_fix.py
```

This test verifies:
- No MIDI messages are sent during detection
- Audio recording works properly  
- Threshold calculation produces reasonable results
- Integration with postprocessing configuration works