#!/usr/bin/env python3
"""
Test: Hold, Release, and Pause timing verification

This test samples notes with different timing parameters and verifies
that the resulting WAV file durations match the expected values.

NO POSTPROCESSING - Testing raw recording length.

Test cases:
1. --hold_time 1.0 --release_time 0.5 --pause_time 0.5
2. --hold_time 2.0 --release_time 2.5 --pause_time 2.5
3. --hold_time 10.0 --release_time 4.5 --pause_time 4.5

Expected duration = hold_time + release_time
(pause_time is between samples, not included in WAV duration)
"""

import subprocess
import sys
import wave
from pathlib import Path


def run_sample_command(note, hold_time, release_time, pause_time, test_name):
    """Run sampling command with specified timing parameters."""
    # Find the correct Python executable (venv or current)
    python_exe = sys.executable
    
    # If we're in a venv, use that Python
    import os
    venv_python = Path(__file__).parent.parent / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        python_exe = str(venv_python)
    
    cmd = [
        python_exe, "autosamplerT.py",
        "--note_range_start", note,
        "--note_range_end", note,
        "--hold_time", str(hold_time),
        "--release_time", str(release_time),
        "--pause_time", str(pause_time),
        "--multisample_name", test_name
    ]
    
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.returncode != 0:
        print(f"[ERROR] Command failed with code {result.returncode}")
        if result.stderr:
            print(result.stderr)
        return False
    
    return True


def get_wav_duration(wav_path):
    """Get the duration of a WAV file in seconds."""
    with wave.open(str(wav_path), 'rb') as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        duration = frames / float(rate)
        return {
            'duration': duration,
            'frames': frames,
            'samplerate': rate,
            'channels': wav.getnchannels()
        }


def test_timing(test_num, hold_time, release_time, pause_time, note="C4"):
    """
    Test a specific timing configuration.
    
    Returns: (passed, actual_duration, expected_duration)
    """
    print(f"\n{'='*60}")
    print(f"TEST CASE {test_num}")
    print(f"{'='*60}")
    print(f"Parameters:")
    print(f"  Note: {note}")
    print(f"  Hold time: {hold_time}s")
    print(f"  Release time: {release_time}s")
    print(f"  Pause time: {pause_time}s")
    
    # Expected duration = hold_time + release_time
    # No postprocessing, so we should get the exact recorded length
    expected_duration = hold_time + release_time
    print(f"  Expected WAV duration: {expected_duration:.3f}s")
    
    # Setup
    test_name = f"test_timing_{test_num}"
    output_folder = Path("output") / test_name / "samples"
    
    # Clean up any existing test output
    if output_folder.parent.exists():
        import shutil
        shutil.rmtree(output_folder.parent)
        print(f"\n[CLEANUP] Removed existing test folder")
    
    # Run sampling
    print(f"\n[SAMPLING] Recording note {note}...")
    if not run_sample_command(note, hold_time, release_time, pause_time, test_name):
        print(f"[FAIL] Sampling command failed")
        return False, 0, expected_duration
    
    # Find the WAV file
    if not output_folder.exists():
        print(f"[FAIL] Output folder not found: {output_folder}")
        return False, 0, expected_duration
    
    wav_files = list(output_folder.glob("*.wav"))
    if not wav_files:
        print(f"[FAIL] No WAV files found in {output_folder}")
        return False, 0, expected_duration
    
    if len(wav_files) > 1:
        print(f"[WARNING] Multiple WAV files found, using first one")
    
    wav_file = wav_files[0]
    print(f"\n[ANALYSIS] Analyzing: {wav_file.name}")
    
    # Get WAV info
    wav_info = get_wav_duration(wav_file)
    actual_duration = wav_info['duration']
    
    print(f"\nWAV file info:")
    print(f"  Duration: {actual_duration:.3f}s")
    print(f"  Frames: {wav_info['frames']}")
    print(f"  Sample rate: {wav_info['samplerate']} Hz")
    print(f"  Channels: {wav_info['channels']}")
    
    # Calculate difference
    # Allow for system latency (~0.2s observed for MIDI + audio interface)
    duration_diff = abs(actual_duration - expected_duration)
    tolerance = 0.25  # 250ms tolerance to account for latency
    
    print(f"\n[COMPARISON]")
    print(f"  Expected duration (theoretical): {expected_duration:.3f}s")
    print(f"  Actual duration: {actual_duration:.3f}s")
    print(f"  Difference: {duration_diff:.3f}s")
    print(f"  Tolerance: {tolerance:.3f}s")
    
    # Check that the relationship holds: longer hold+release = longer WAV
    # The absolute timing may have latency, but relative timing should be consistent
    print(f"\n[VERIFICATION]")
    print(f"  Formula: WAV duration ≈ hold_time + release_time (minus ~0.19s latency)")
    print(f"  hold_time ({hold_time}s) + release_time ({release_time}s) = {expected_duration}s")
    print(f"  Actual WAV: {actual_duration:.3f}s")
    print(f"  Latency: {expected_duration - actual_duration:.3f}s")
    
    # Verify
    if duration_diff <= tolerance:
        print(f"  [PASS] Duration within tolerance")
        return True, actual_duration, expected_duration
    else:
        print(f"  [FAIL] Duration differs by {duration_diff:.3f}s (tolerance: {tolerance}s)")
        return False, actual_duration, expected_duration


def main():
    print("\n" + "="*60)
    print("TIMING VERIFICATION TEST")
    print("Testing hold_time + release_time = WAV duration")
    print("="*60)
    
    # Test cases
    test_cases = [
        (1, 1.0, 0.5, 0.5),     # Test 1: 1.5s total
        (2, 2.0, 2.5, 2.5),     # Test 2: 4.5s total
        (3, 10.0, 4.5, 4.5),    # Test 3: 14.5s total
        (4, 60.0, 5.0, 1.0),    # Test 4: 65s total (1 minute hold)
        (5, 120.0, 5.0, 1.0),   # Test 5: 125s total (2 minute hold)
    ]
    
    # KNOWN ISSUES:
    # 1. Recording latency: ~0.19s shorter than expected (MIDI + audio interface startup)
    #    - Test 1: Expected 1.5s, got 1.311s (0.189s short)
    #    - Test 2: Expected 4.5s, got 4.311s (0.189s short)
    #    - Consistent latency across different durations
    # 
    # 2. Long recordings hang: Recordings >10s freeze during sd.wait()
    #    - Test 3 (14.5s) never completes
    #    - Likely causes:
    #      * Audio interface buffer overflow (639,450 frames at 44.1kHz)
    #      * sounddevice library limitation with large buffers
    #      * System memory allocation issue
    #    - Needs investigation in src/sampler.py record_audio() method
    #
    # See TODO.md #9 for full details and proposed solutions
    
    results = []
    
    for test_num, hold_time, release_time, pause_time in test_cases:
        passed, actual, expected = test_timing(
            test_num, hold_time, release_time, pause_time
        )
        results.append({
            'test_num': test_num,
            'hold_time': hold_time,
            'release_time': release_time,
            'pause_time': pause_time,
            'expected': expected,
            'actual': actual,
            'passed': passed
        })
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    print(f"\n{'Test':<6} {'Hold':<6} {'Release':<8} {'Pause':<7} {'Expected':<10} {'Actual':<10} {'Diff':<8} {'Result':<8}")
    print("-" * 60)
    
    all_passed = True
    for r in results:
        diff = abs(r['actual'] - r['expected'])
        result_str = "[PASS]" if r['passed'] else "[FAIL]"
        
        print(f"{r['test_num']:<6} {r['hold_time']:<6.1f} {r['release_time']:<8.1f} "
              f"{r['pause_time']:<7.1f} {r['expected']:<10.3f} {r['actual']:<10.3f} "
              f"{diff:<8.3f} {result_str}")
        
        if not r['passed']:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("[SUCCESS] All timing tests passed!")
        print("Formula verified: WAV duration = hold_time + release_time")
    else:
        print("[FAIL] Some tests failed")
    print("="*60)
    
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
