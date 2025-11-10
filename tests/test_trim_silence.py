#!/usr/bin/env python3
"""
Test: Trim silence functionality

This test:
1. Creates a WAV file with added silence at start and end
2. Applies trim_silence postprocessing
3. Verifies that silence was correctly removed
"""

import sys
import os
import wave
import struct
import numpy as np
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.postprocess import PostProcessor


def create_test_wav_with_silence(output_path, duration=1.0, silence_start=0.5, silence_end=0.5, 
                                  samplerate=44100, frequency=440.0):
    """
    Create a test WAV file with silence at start and end.
    
    Args:
        output_path: Path to save the WAV file
        duration: Duration of actual audio content in seconds
        silence_start: Duration of silence at start in seconds
        silence_end: Duration of silence at end in seconds
        samplerate: Sample rate in Hz
        frequency: Frequency of the test tone in Hz
    """
    # Calculate samples
    audio_samples = int(duration * samplerate)
    silence_start_samples = int(silence_start * samplerate)
    silence_end_samples = int(silence_end * samplerate)
    total_samples = silence_start_samples + audio_samples + silence_end_samples
    
    # Generate test tone (sine wave)
    t = np.linspace(0, duration, audio_samples, False)
    audio_data = np.sin(2 * np.pi * frequency * t)
    
    # Add some amplitude variation to make it more realistic
    envelope = np.linspace(0.8, 0.3, audio_samples)
    audio_data = audio_data * envelope
    
    # Create silence arrays
    silence_start_array = np.zeros(silence_start_samples)
    silence_end_array = np.zeros(silence_end_samples)
    
    # Combine: silence + audio + silence
    full_audio = np.concatenate([silence_start_array, audio_data, silence_end_array])
    
    # Convert to stereo (duplicate mono to both channels)
    stereo_audio = np.column_stack([full_audio, full_audio])
    
    # Normalize to 16-bit range
    audio_int16 = (stereo_audio * 32767).astype(np.int16)
    
    # Write WAV file
    with wave.open(str(output_path), 'wb') as wav:
        wav.setnchannels(2)  # Stereo
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(samplerate)
        wav.writeframes(audio_int16.tobytes())
    
    return {
        'total_duration': total_samples / samplerate,
        'audio_duration': audio_samples / samplerate,
        'silence_start': silence_start,
        'silence_end': silence_end,
        'expected_trimmed_duration': audio_samples / samplerate
    }


def get_wav_info(wav_path):
    """Get WAV file information."""
    with wave.open(str(wav_path), 'rb') as wav:
        return {
            'channels': wav.getnchannels(),
            'samplerate': wav.getframerate(),
            'frames': wav.getnframes(),
            'duration': wav.getnframes() / wav.getframerate(),
            'sampwidth': wav.getsampwidth()
        }


def analyze_silence(wav_path, threshold_db=-40.0):
    """
    Analyze silence at start and end of WAV file.
    
    Returns dict with silence_start and silence_end in seconds.
    """
    with wave.open(str(wav_path), 'rb') as wav:
        frames = wav.readframes(wav.getnframes())
        samplerate = wav.getframerate()
        channels = wav.getnchannels()
        sampwidth = wav.getsampwidth()
        
        # Convert to numpy array
        if sampwidth == 2:  # 16-bit
            audio_data = np.frombuffer(frames, dtype=np.int16)
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth}")
        
        # Reshape to channels
        audio_data = audio_data.reshape(-1, channels)
        
        # Convert to mono for analysis (average channels)
        if channels > 1:
            audio_mono = np.mean(audio_data, axis=1)
        else:
            audio_mono = audio_data[:, 0]
        
        # Calculate RMS amplitude in dB
        frame_size = int(0.01 * samplerate)  # 10ms frames
        num_frames = len(audio_mono) // frame_size
        
        threshold_linear = 10 ** (threshold_db / 20.0)
        
        # Find first non-silent frame
        silence_start_frames = 0
        for i in range(num_frames):
            start_idx = i * frame_size
            end_idx = start_idx + frame_size
            frame = audio_mono[start_idx:end_idx]
            rms = np.sqrt(np.mean(frame ** 2)) / 32768.0  # Normalize to [0, 1]
            
            if rms > threshold_linear:
                silence_start_frames = i
                break
        
        # Find last non-silent frame
        silence_end_frames = 0
        for i in range(num_frames - 1, -1, -1):
            start_idx = i * frame_size
            end_idx = start_idx + frame_size
            frame = audio_mono[start_idx:end_idx]
            rms = np.sqrt(np.mean(frame ** 2)) / 32768.0
            
            if rms > threshold_linear:
                silence_end_frames = num_frames - i - 1
                break
        
        silence_start_sec = (silence_start_frames * frame_size) / samplerate
        silence_end_sec = (silence_end_frames * frame_size) / samplerate
        
        return {
            'silence_start': silence_start_sec,
            'silence_end': silence_end_sec
        }


def main():
    print("\n" + "="*60)
    print("TEST: Trim Silence Functionality")
    print("="*60)
    
    # Setup test directory
    test_dir = Path("output") / "test_trim_silence"
    test_dir.mkdir(parents=True, exist_ok=True)
    
    original_file = test_dir / "test_with_silence.wav"
    trimmed_file = test_dir / "test_with_silence.wav"  # Will be overwritten
    
    # Test parameters
    audio_duration = 1.0  # 1 second of actual audio
    silence_start = 0.5   # 500ms silence at start
    silence_end = 0.5     # 500ms silence at end
    
    print(f"\nTest setup:")
    print(f"  - Audio duration: {audio_duration}s")
    print(f"  - Silence at start: {silence_start}s")
    print(f"  - Silence at end: {silence_end}s")
    print(f"  - Expected total duration: {audio_duration + silence_start + silence_end}s")
    print(f"  - Expected trimmed duration: {audio_duration}s")
    
    # Step 1: Create test WAV with silence
    print(f"\n{'='*60}")
    print("STEP 1: Create test WAV file with added silence")
    print(f"{'='*60}")
    
    test_info = create_test_wav_with_silence(
        original_file,
        duration=audio_duration,
        silence_start=silence_start,
        silence_end=silence_end,
        frequency=440.0  # A4 note
    )
    
    original_info = get_wav_info(original_file)
    print(f"\n[CREATED] {original_file.name}")
    print(f"  Channels: {original_info['channels']}")
    print(f"  Sample rate: {original_info['samplerate']} Hz")
    print(f"  Duration: {original_info['duration']:.3f}s")
    print(f"  Frames: {original_info['frames']}")
    
    # Analyze original silence
    original_silence = analyze_silence(original_file)
    print(f"\n[ANALYSIS] Original file silence:")
    print(f"  Start: {original_silence['silence_start']:.3f}s")
    print(f"  End: {original_silence['silence_end']:.3f}s")
    
    # Step 2: Apply trim_silence postprocessing
    print(f"\n{'='*60}")
    print("STEP 2: Apply trim_silence postprocessing")
    print(f"{'='*60}")
    
    processor = PostProcessor()
    operations = {
        'trim_silence': {'threshold_db': -40.0}
    }
    
    success = processor.process_samples([original_file], operations)
    
    if not success:
        print("[ERROR] Postprocessing failed")
        sys.exit(1)
    
    print("\n[SUCCESS] Trim silence applied")
    
    # Step 3: Verify silence was trimmed
    print(f"\n{'='*60}")
    print("STEP 3: Verify silence was trimmed")
    print(f"{'='*60}")
    
    trimmed_info = get_wav_info(trimmed_file)
    print(f"\n[INFO] Trimmed file:")
    print(f"  Channels: {trimmed_info['channels']}")
    print(f"  Sample rate: {trimmed_info['samplerate']} Hz")
    print(f"  Duration: {trimmed_info['duration']:.3f}s")
    print(f"  Frames: {trimmed_info['frames']}")
    
    # Analyze trimmed silence
    trimmed_silence = analyze_silence(trimmed_file)
    print(f"\n[ANALYSIS] Trimmed file silence:")
    print(f"  Start: {trimmed_silence['silence_start']:.3f}s")
    print(f"  End: {trimmed_silence['silence_end']:.3f}s")
    
    # Calculate duration reduction
    duration_reduction = original_info['duration'] - trimmed_info['duration']
    expected_reduction = silence_start + silence_end
    
    print(f"\n[COMPARISON]")
    print(f"  Original duration: {original_info['duration']:.3f}s")
    print(f"  Trimmed duration: {trimmed_info['duration']:.3f}s")
    print(f"  Duration reduction: {duration_reduction:.3f}s")
    print(f"  Expected reduction: {expected_reduction:.3f}s")
    print(f"  Difference: {abs(duration_reduction - expected_reduction):.3f}s")
    
    # Verify results
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")
    
    passed = True
    tolerance = 0.05  # 50ms tolerance
    
    # Check that duration was reduced
    if duration_reduction < expected_reduction * 0.8:  # At least 80% of expected
        print(f"[FAIL] Duration not reduced enough")
        print(f"  Expected at least {expected_reduction * 0.8:.3f}s reduction")
        print(f"  Got {duration_reduction:.3f}s reduction")
        passed = False
    else:
        print(f"[PASS] Duration reduced by {duration_reduction:.3f}s")
    
    # Check that trimmed file has minimal silence at start
    if trimmed_silence['silence_start'] > tolerance:
        print(f"[FAIL] Too much silence at start: {trimmed_silence['silence_start']:.3f}s")
        passed = False
    else:
        print(f"[PASS] Minimal silence at start: {trimmed_silence['silence_start']:.3f}s")
    
    # Check that trimmed file has minimal silence at end
    if trimmed_silence['silence_end'] > tolerance:
        print(f"[FAIL] Too much silence at end: {trimmed_silence['silence_end']:.3f}s")
        passed = False
    else:
        print(f"[PASS] Minimal silence at end: {trimmed_silence['silence_end']:.3f}s")
    
    # Check that audio content is preserved
    expected_trimmed_duration = audio_duration
    duration_diff = abs(trimmed_info['duration'] - expected_trimmed_duration)
    
    if duration_diff > tolerance:
        print(f"[FAIL] Trimmed duration differs from expected")
        print(f"  Expected: ~{expected_trimmed_duration:.3f}s")
        print(f"  Got: {trimmed_info['duration']:.3f}s")
        print(f"  Difference: {duration_diff:.3f}s")
        passed = False
    else:
        print(f"[PASS] Audio content preserved: {trimmed_info['duration']:.3f}s")
    
    # Final result
    print(f"\n{'='*60}")
    if passed:
        print("[SUCCESS] All trim silence tests passed!")
    else:
        print("[FAIL] Some tests failed")
    print(f"{'='*60}")
    
    print(f"\nOutput folder: {test_dir}")
    
    if not passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
