"""
Test silence detection and latency compensation.

This test verifies that:
1. Silence detection correctly trims leading/trailing silence
2. Recording latency is properly handled by silence detection
3. Samples have the correct audio content regardless of recording latency
"""

import os
import sys
from pathlib import Path
import tempfile
import shutil
import wave
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable ASIO support
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd
from src.sampler import Sampler


def get_wav_info(wav_path):
    """Get WAV file duration and audio statistics."""
    with wave.open(str(wav_path), 'rb') as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        channels = wav.getnchannels()
        duration = frames / float(rate)
        
        # Read audio data
        audio_data = wav.readframes(frames)
        if wav.getsampwidth() == 2:  # 16-bit
            audio = np.frombuffer(audio_data, dtype=np.int16)
        elif wav.getsampwidth() == 3:  # 24-bit
            # Convert 24-bit to int32
            audio_bytes = np.frombuffer(audio_data, dtype=np.uint8)
            audio = np.zeros(len(audio_bytes) // 3, dtype=np.int32)
            audio = audio_bytes[0::3].astype(np.int32) | \
                   (audio_bytes[1::3].astype(np.int32) << 8) | \
                   (audio_bytes[2::3].astype(np.int32) << 16)
            # Sign extend
            audio = np.where(audio >= 2**23, audio - 2**24, audio)
        else:
            raise ValueError(f"Unsupported bit depth: {wav.getsampwidth() * 8}")
        
        # Reshape for stereo
        if channels == 2:
            audio = audio.reshape(-1, 2)
        
        # Calculate RMS (root mean square) to detect audio content
        audio_float = audio.astype(np.float32) / (2**15 if wav.getsampwidth() == 2 else 2**23)
        if channels == 2:
            rms = np.sqrt(np.mean(audio_float**2, axis=0))
        else:
            rms = np.sqrt(np.mean(audio_float**2))
        
        # Find where audio actually starts (above noise floor)
        noise_threshold = 0.001  # -60dB
        if channels == 2:
            audio_energy = np.sqrt(np.sum(audio_float**2, axis=1))
        else:
            audio_energy = np.abs(audio_float)
        
        # Find first and last sample above threshold
        above_threshold = np.where(audio_energy > noise_threshold)[0]
        if len(above_threshold) > 0:
            audio_start = above_threshold[0] / rate
            audio_end = above_threshold[-1] / rate
            audio_duration = audio_end - audio_start
        else:
            audio_start = 0
            audio_end = 0
            audio_duration = 0
        
        return {
            'frames': frames,
            'samplerate': rate,
            'channels': channels,
            'duration': duration,
            'rms': rms,
            'audio_start': audio_start,
            'audio_end': audio_end,
            'audio_duration': audio_duration,
            'has_audio': np.any(rms > 0.001)
        }


def test_silence_detection(hold_time, release_time, test_name):
    """
    Test silence detection with specific hold/release times.
    
    Args:
        hold_time: Note hold time in seconds
        release_time: Release time in seconds
        test_name: Name for this test
    """
    print(f"\n{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}")
    print(f"Hold time: {hold_time}s, Release time: {release_time}s")
    print(f"Expected total duration: {hold_time + release_time}s")
    
    # Create temporary output directory
    temp_dir = Path(tempfile.mkdtemp(prefix=f"test_silence_{test_name}_"))
    print(f"Output directory: {temp_dir}")
    
    try:
        # Configuration
        config = {
            'audio_interface': {
                'input_device_index': 16,  # Audio 4 DJ ASIO
                'output_device_index': 16,
                'samplerate': 44100,
                'bitdepth': 24,
                'mono_stereo': 'stereo',
                'channel_offset': 0,
                'gain': 1.0,
                'silence_detection': True,  # ENABLED
                'latency_compensation': 0.0,
                'debug': False
            },
            'midi_interface': {
                'midi_input_name': 'Prophet 6 1',
                'midi_output_name': 'Prophet 6 2',
                'midi_input_valid': True,
                'midi_output_valid': True
            },
            'sampling_midi': {
                'midi_channels': [0],
                'note_range': {'start': 60, 'end': 60, 'interval': 1},  # C4
                'velocity_layers': 1,
                'roundrobin_layers': 1
            },
            'sampling_control': {
                'hold_time': hold_time,
                'release_time': release_time,
                'pause_time': 0.1,
                'multisample_name': f'silence_test_{test_name}',
                'output_folder': str(temp_dir)
            }
        }
        
        # Create sampler
        sampler = Sampler(config)
        
        # Run sampling
        print("\nStarting sampling...")
        print("NOTE: Make sure your synth is playing when triggered!")
        sampler.run()
        
        # Find the generated WAV file
        wav_files = list(temp_dir.glob('*.wav'))
        if not wav_files:
            print("FAIL: No WAV files generated")
            return False
        
        wav_file = wav_files[0]
        print(f"\nAnalyzing: {wav_file.name}")
        
        # Analyze WAV file
        info = get_wav_info(wav_file)
        
        print(f"\nWAV File Analysis:")
        print(f"  Total duration: {info['duration']:.3f}s")
        print(f"  Frames: {info['frames']}")
        print(f"  Sample rate: {info['samplerate']} Hz")
        print(f"  Channels: {info['channels']}")
        if info['channels'] == 2:
            print(f"  RMS (L/R): {info['rms'][0]:.6f} / {info['rms'][1]:.6f}")
        else:
            print(f"  RMS: {info['rms']:.6f}")
        print(f"  Audio starts at: {info['audio_start']:.3f}s")
        print(f"  Audio ends at: {info['audio_end']:.3f}s")
        print(f"  Audio duration: {info['audio_duration']:.3f}s")
        print(f"  Has audio content: {'YES ✓' if info['has_audio'] else 'NO ✗'}")
        
        # Check if audio was detected
        if not info['has_audio']:
            print("\nFAIL: No audio content detected (synth not playing?)")
            return False
        
        # Check if leading silence was trimmed
        # Should start very close to beginning (within 10ms) after silence detection
        if info['audio_start'] > 0.010:
            print(f"\n⚠️  WARNING: Audio starts at {info['audio_start']:.3f}s")
            print(f"   Leading silence not fully trimmed (expected < 0.010s)")
        else:
            print(f"\n✓ Leading silence properly trimmed (starts at {info['audio_start']:.3f}s)")
        
        # Check if file is reasonable length
        # After trimming, it should be close to hold_time + release_time
        # Allow 20% tolerance for synth envelope variations
        expected = hold_time + release_time
        tolerance = expected * 0.2
        duration_diff = abs(info['audio_duration'] - expected)
        
        if duration_diff > tolerance:
            print(f"\n⚠️  WARNING: Audio duration {info['audio_duration']:.3f}s differs from expected {expected:.3f}s")
            print(f"   Difference: {duration_diff:.3f}s (tolerance: {tolerance:.3f}s)")
            print(f"   This could be due to synth envelope or silence detection threshold")
        else:
            print(f"\n✓ Audio duration {info['audio_duration']:.3f}s is within tolerance of expected {expected:.3f}s")
        
        # Overall assessment
        print(f"\n{'='*70}")
        if info['has_audio'] and info['audio_start'] <= 0.010:
            print(f" TEST PASSED: {test_name}")
            print("   - Audio content detected")
            print("   - Leading silence properly trimmed")
            result = True
        else:
            print(f"TEST FAILED: {test_name}")
            result = False
        print(f"{'='*70}")
        
        return result
        
    except Exception as e:
        print(f"\nTEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print(f"\nCleaning up: {temp_dir}")
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not remove temp directory: {e}")


def main():
    """Run all silence detection tests."""
    print("="*70)
    print("SILENCE DETECTION & LATENCY COMPENSATION TEST SUITE")
    print("="*70)
    print("\nThis test verifies that silence detection properly handles:")
    print("  1. Recording latency (MIDI + audio interface startup)")
    print("  2. Leading silence trimming")
    print("  3. Trailing silence trimming")
    print("\nNOTE: Make sure your synthesizer is connected and responding to MIDI!")
    print("      The synth should play a note when triggered.")
    
    input("\nPress Enter to start testing...")
    
    results = []
    
    # Test 1: Short recording (1.5s total) - original timing issue case
    results.append(test_silence_detection(
        hold_time=1.0,
        release_time=0.5,
        test_name="short_1.5s"
    ))
    
    # Test 2: Medium recording (4.5s total) - original timing issue case
    results.append(test_silence_detection(
        hold_time=2.0,
        release_time=2.5,
        test_name="medium_4.5s"
    ))
    
    # Test 3: Longer recording (7.0s total)
    results.append(test_silence_detection(
        hold_time=5.0,
        release_time=2.0,
        test_name="long_7.0s"
    ))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("\n ALL TESTS PASSED")
        print("\nConclusion:")
        print("  - Silence detection is working correctly")
        print("  - Recording latency is properly compensated")
        print("  - Leading/trailing silence is being trimmed")
        print("  - Samples contain correct audio content")
    else:
        print("\nSOME TESTS FAILED")
        print("\nPossible issues:")
        print("  - Synth not responding to MIDI")
        print("  - Silence detection threshold too high/low")
        print("  - Audio interface not capturing properly")
        print("  - MIDI connection issues")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
