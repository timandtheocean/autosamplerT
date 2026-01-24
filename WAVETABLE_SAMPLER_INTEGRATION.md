# Wavetable Sampler Integration with Main Sampler Infrastructure

## Problem Description

The original wavetable sampling implementation had several critical issues:

1. **Driver Locking**: Used separate audio recording logic instead of the proven `AudioEngine` from the main sampler
2. **Threading Issues**: Used complex threading without proper synchronization, leading to driver conflicts
3. **No Monitoring Support**: Lacked integration with the main sampler's monitoring capabilities
4. **Resource Management**: No proper cleanup of MIDI notes and audio resources
5. **ASIO Compatibility**: Different device handling approach that didn't leverage tested ASIO multi-channel logic

## Solution: Integration with Main Sampler Infrastructure

### Key Changes Made

#### 1. AudioEngine Integration
- **Before**: Wavetable sampler used `record_samples()` with custom threading
- **After**: Uses the same `audio_engine.record()` method as main sampler
- **Benefit**: Leverages tested ASIO device management and prevents driver conflicts

#### 2. Synchronized Recording and MIDI Sweep
```python
# NEW: _record_with_midi_sweep() method
def _record_with_midi_sweep(self, duration: float, control_values: List[int],
                           step_duration: float, control_info: Dict) -> Optional[np.ndarray]:
    """Record audio while performing synchronized MIDI parameter sweep."""
```

- Uses background threads for audio recording and MIDI sweep
- Proper synchronization with threading events
- Same recording pattern as main sampler to prevent conflicts

#### 3. Resource Management and Cleanup
```python
class WavetableSampler:
    def __init__(self, ...):
        self._active_note = None  # Track active notes for cleanup
    
    def cleanup(self):
        """Clean up resources and ensure all notes are off."""
        # Send note off for any active notes
        # Send All Notes Off (CC 123)
        # Stop audio operations with sd.stop()
    
    def __enter__(self) / __exit__(self):
        # Context manager support for automatic cleanup
```

#### 4. Improved Test Script
- Uses same audio configuration format as main sampler
- Proper MIDI port error handling
- Context manager usage for automatic cleanup
- Better device configuration (input_channels vs channel_offset)

### Technical Implementation Details

#### Audio Configuration Alignment
```yaml
# OLD wavetable config
audio_config = {
    'input_device_index': 37,
    'channel_offset': 2  # Inconsistent with main sampler
}

# NEW wavetable config (matches main sampler)
audio_config = {
    'input_device_index': 37,
    'output_device_index': 37,
    'input_channels': '3-4',  # User-friendly format
    'silence_detection': False,  # Appropriate for wavetables
    'gain_db': 0.0
}
```

#### Recording Method Improvements
```python
# OLD: Complex threading with record_samples()
def record_audio():
    recorded_audio = self.audio_engine.record_samples(
        duration=total_samples / self.audio_engine.samplerate,
        apply_postprocessing=False
    )

# NEW: Direct AudioEngine.record() like main sampler
def record_audio_thread():
    recorded_audio = self.audio_engine.record(duration)
```

#### MIDI Timing Precision
- Separated recording and MIDI sweep into synchronized threads
- Precise timing control with `target_time` calculations
- Better error handling and reporting
- Proper cleanup of hanging notes

### Files Modified

1. **`src/wavetable/wavetable_sampler.py`**
   - Added `cleanup()` method and context manager support
   - Replaced `_sample_curve()` method with new synchronized approach
   - Added `_record_with_midi_sweep()` method
   - Improved note tracking and MIDI cleanup
   - Better error handling throughout

2. **`test_wavetable_quick.py`**
   - Updated audio configuration to match main sampler format
   - Added proper MIDI port error handling
   - Added context manager usage for automatic cleanup
   - Added proper resource cleanup in finally block

3. **Created `WAVETABLE_SAMPLER_INTEGRATION.md`** (this document)
   - Comprehensive documentation of changes and rationale

### Benefits of the Integration

#### 1. Driver Stability
- **No more driver locking**: Uses the same proven AudioEngine that works reliably
- **ASIO compatibility**: Inherits all ASIO multi-channel device handling
- **Resource cleanup**: Proper cleanup prevents driver state issues

#### 2. Monitoring Support  
- **Potential for real-time monitoring**: Can now use `record_with_monitoring()` method
- **Consistent behavior**: Same monitoring capabilities as main sampler
- **Audio device sharing**: Proper device management allows monitoring integration

#### 3. Code Maintainability
- **Single audio path**: All recording goes through the same tested AudioEngine
- **Consistent patterns**: Same resource management as main sampler
- **Better error handling**: Inherits robust error handling from AudioEngine

#### 4. Configuration Consistency
- **Unified config format**: Uses same audio configuration as main sampler
- **Channel mapping**: Consistent input_channels format across project
- **Device management**: Same device selection logic

### Usage Example

```python
# Initialize audio engine exactly like main sampler
audio_config = {
    'input_device_index': 37,
    'output_device_index': 37,
    'samplerate': 44100,
    'bitdepth': 24,
    'mono_stereo': 'stereo',
    'input_channels': '3-4',
    'silence_detection': False
}

audio_engine = AudioEngine(audio_config, test_mode=False)
if not audio_engine.setup():
    raise Exception("Audio engine setup failed")

# Use context manager for automatic cleanup
with WavetableSampler(audio_engine, midi_controller) as sampler:
    success = sampler.create_wavetables(config)
    # Cleanup happens automatically
```

### Future Improvements

1. **Real-time monitoring**: Add support for visual monitoring during wavetable creation
2. **Batch processing**: Integrate with main sampler's batch processing capabilities  
3. **Export integration**: Use main sampler's export system for wavetable formats
4. **Configuration unification**: Move wavetable config into main autosamplerT config system

### Testing Recommendations

1. **Driver stability**: Test multiple consecutive wavetable runs without restarts
2. **MIDI cleanup**: Verify no hanging notes after interrupted sampling
3. **Audio device access**: Test switching between main sampling and wavetable creation
4. **Memory management**: Monitor for audio buffer leaks during long sessions
5. **ASIO multi-channel**: Test with various channel offsets and device configurations

---

This integration brings the wavetable sampling functionality in line with the proven, robust infrastructure of the main AutosamplerT sampler, resolving driver locking issues and laying the foundation for enhanced monitoring and other advanced features.