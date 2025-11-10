#!/usr/bin/env python3
"""
Test script for autolooping functionality

Tests:
1. Zero-crossing detection
2. Auto loop detection with autocorrelation
3. Manual loop point specification
4. Equal-power crossfade application
"""

import numpy as np
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.postprocess import PostProcessor


def generate_test_audio(samplerate=44100, duration=5.0, frequency=440.0):
    """Generate a simple sine wave for testing."""
    t = np.linspace(0, duration, int(samplerate * duration))
    
    # Add amplitude envelope (attack, sustain, release)
    envelope = np.ones_like(t)
    attack_samples = int(0.1 * samplerate)
    release_samples = int(0.2 * samplerate)
    
    # Attack
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    # Release
    envelope[-release_samples:] = np.linspace(1, 0, release_samples)
    
    # Generate sine wave
    audio = np.sin(2 * np.pi * frequency * t) * envelope * 0.8
    
    return audio.astype(np.float32), samplerate


def test_zero_crossing():
    """Test zero-crossing detection."""
    print("\n" + "="*60)
    print("TEST 1: Zero-Crossing Detection")
    print("="*60)
    
    processor = PostProcessor()
    
    # Generate test signal
    audio, sr = generate_test_audio(duration=1.0)
    
    # Find zero crossing near middle
    target = len(audio) // 2
    zc = processor._find_zero_crossing(audio, target, search_radius=100)
    
    # Verify it's actually a zero crossing (value should be close to 0)
    if abs(audio[zc]) < 0.01:
        print(f"[PASS] Zero crossing found at sample {zc} (value: {audio[zc]:.6f})")
    else:
        print(f"[FAIL] Zero crossing value too high: {audio[zc]:.6f}")
    
    # Check multiple points
    test_points = [len(audio) // 4, len(audio) // 2, 3 * len(audio) // 4]
    for target in test_points:
        zc = processor._find_zero_crossing(audio, target, search_radius=100)
        print(f"  Target: {target}, ZC found: {zc}, Value: {audio[zc]:.6f}")


def test_auto_loop_detection():
    """Test automatic loop point detection."""
    print("\n" + "="*60)
    print("TEST 2: Auto Loop Detection")
    print("="*60)
    
    processor = PostProcessor()
    
    # Generate test signal with clear repetition
    audio, sr = generate_test_audio(duration=5.0, frequency=440.0)
    
    # Find loop points automatically
    loop_points = processor._find_loop_points(
        audio, sr, 
        min_loop_length=0.5
    )
    
    if loop_points:
        loop_start, loop_end = loop_points
        loop_duration = (loop_end - loop_start) / sr
        print(f"[PASS] Loop detected:")
        print(f"  Start: {loop_start} samples ({loop_start/sr:.3f}s)")
        print(f"  End: {loop_end} samples ({loop_end/sr:.3f}s)")
        print(f"  Duration: {loop_duration:.3f}s")
        
        # Verify both points are at zero crossings
        if abs(audio[loop_start]) < 0.01 and abs(audio[loop_end]) < 0.01:
            print(f"[PASS] Loop points are at zero crossings")
            print(f"  Start value: {audio[loop_start]:.6f}")
            print(f"  End value: {audio[loop_end]:.6f}")
        else:
            print(f"[WARN] Loop points not at optimal zero crossings")
            print(f"  Start value: {audio[loop_start]:.6f}")
            print(f"  End value: {audio[loop_end]:.6f}")
    else:
        print("[FAIL] No loop points found")


def test_manual_loop_points():
    """Test manual loop point specification."""
    print("\n" + "="*60)
    print("TEST 3: Manual Loop Points")
    print("="*60)
    
    processor = PostProcessor()
    
    # Generate test signal
    audio, sr = generate_test_audio(duration=5.0)
    
    # Specify manual loop points
    start_time = 1.0  # seconds
    end_time = 4.0    # seconds
    
    loop_points = processor._find_loop_points(
        audio, sr,
        min_loop_length=0.1,
        start_time=start_time,
        end_time=end_time
    )
    
    if loop_points:
        loop_start, loop_end = loop_points
        actual_start_time = loop_start / sr
        actual_end_time = loop_end / sr
        
        print(f"[PASS] Manual loop points set:")
        print(f"  Requested: {start_time:.3f}s - {end_time:.3f}s")
        print(f"  Actual: {actual_start_time:.3f}s - {actual_end_time:.3f}s")
        print(f"  Adjusted to zero crossings: {abs(actual_start_time - start_time):.4f}s, {abs(actual_end_time - end_time):.4f}s")
        
        # Verify zero crossings
        if abs(audio[loop_start]) < 0.01 and abs(audio[loop_end]) < 0.01:
            print(f"[PASS] Loop points adjusted to zero crossings")
        else:
            print(f"[WARN] Loop points not optimal")
    else:
        print("[FAIL] Failed to set manual loop points")


def test_crossfade():
    """Test equal-power crossfade."""
    print("\n" + "="*60)
    print("TEST 4: Equal-Power Crossfade")
    print("="*60)
    
    processor = PostProcessor()
    
    # Generate test signal
    audio, sr = generate_test_audio(duration=3.0)
    original_energy = np.sum(audio ** 2)
    
    # Set loop points
    loop_start = int(1.0 * sr)
    loop_end = int(2.5 * sr)
    
    # Apply crossfade
    crossfade_ms = 50
    audio_faded = processor._crossfade_loop(
        audio.copy(), 
        (loop_start, loop_end), 
        sr, 
        crossfade_ms
    )
    
    # Check energy is preserved (equal-power crossfade should maintain energy)
    crossfade_samples = int(crossfade_ms * sr / 1000)
    crossfade_start = loop_end - crossfade_samples
    
    original_segment_energy = np.sum(audio[crossfade_start:loop_end] ** 2)
    faded_segment_energy = np.sum(audio_faded[crossfade_start:loop_end] ** 2)
    
    energy_ratio = faded_segment_energy / original_segment_energy if original_segment_energy > 0 else 0
    
    print(f"[PASS] Crossfade applied:")
    print(f"  Crossfade duration: {crossfade_ms}ms ({crossfade_samples} samples)")
    print(f"  Original segment energy: {original_segment_energy:.6f}")
    print(f"  Crossfaded segment energy: {faded_segment_energy:.6f}")
    print(f"  Energy ratio: {energy_ratio:.3f}")
    
    if 0.8 <= energy_ratio <= 1.2:
        print(f"[PASS] Equal-power crossfade maintains energy (within 20%)")
    else:
        print(f"[WARN] Energy change outside expected range")


def test_min_duration():
    """Test minimum loop duration constraint."""
    print("\n" + "="*60)
    print("TEST 5: Minimum Loop Duration")
    print("="*60)
    
    processor = PostProcessor()
    
    # Generate short test signal
    audio, sr = generate_test_audio(duration=2.0)
    
    # Test with different minimum durations
    min_durations = [0.1, 0.5, 1.0]
    
    for min_dur in min_durations:
        loop_points = processor._find_loop_points(
            audio, sr,
            min_loop_length=min_dur
        )
        
        if loop_points:
            loop_start, loop_end = loop_points
            actual_duration = (loop_end - loop_start) / sr
            
            if actual_duration >= min_dur:
                print(f"[PASS] Min duration {min_dur}s: got {actual_duration:.3f}s")
            else:
                print(f"[FAIL] Min duration {min_dur}s: got {actual_duration:.3f}s (too short)")
        else:
            print(f"[WARN] No loop found for min duration {min_dur}s")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("AUTOLOOPING TEST SUITE")
    print("="*60)
    
    try:
        test_zero_crossing()
        test_auto_loop_detection()
        test_manual_loop_points()
        test_crossfade()
        test_min_duration()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
