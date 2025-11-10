#!/usr/bin/env python3
"""
Integration test: Sample 8 notes and apply autolooping to all

This test:
1. Samples 8 notes (C3 to G3)
2. Applies autolooping with crossfade to all samples
3. Verifies loop points are written to all WAV RIFF headers
"""

import subprocess
import sys
import os
from pathlib import Path
import wave
import struct


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print(result.stdout)
    
    if result.returncode != 0:
        print(f"[ERROR] Command failed with code {result.returncode}")
        if result.stderr:
            print(result.stderr)
        return False
    
    return True


def read_smpl_chunk(wav_path):
    """Read and parse the 'smpl' chunk from a WAV file."""
    with open(wav_path, 'rb') as f:
        # Read RIFF header
        riff_id = f.read(4)
        if riff_id != b'RIFF':
            return None
        
        riff_size = struct.unpack('<I', f.read(4))[0]
        wave_id = f.read(4)
        if wave_id != b'WAVE':
            return None
        
        # Search for 'smpl' chunk
        bytes_read = 4  # Already read 'WAVE'
        while bytes_read < riff_size:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                break
            
            chunk_size = struct.unpack('<I', f.read(4))[0]
            
            if chunk_id == b'smpl':
                # Read smpl chunk data
                smpl_data = f.read(chunk_size)
                
                # Parse loop data (starts at byte 36 of smpl chunk)
                if len(smpl_data) >= 60:  # Minimum size with 1 loop
                    num_loops = struct.unpack('<I', smpl_data[28:32])[0]
                    
                    if num_loops > 0:
                        # Read first loop
                        loop_start_offset = 36
                        loop_type = struct.unpack('<I', smpl_data[loop_start_offset+4:loop_start_offset+8])[0]
                        loop_start = struct.unpack('<I', smpl_data[loop_start_offset+8:loop_start_offset+12])[0]
                        loop_end = struct.unpack('<I', smpl_data[loop_start_offset+12:loop_start_offset+16])[0]
                        
                        return {
                            'num_loops': num_loops,
                            'loop_type': loop_type,
                            'loop_start': loop_start,
                            'loop_end': loop_end
                        }
                
                return None
            
            # Skip to next chunk
            if chunk_size % 2:
                chunk_size += 1
            f.seek(chunk_size, 1)
            bytes_read += 8 + chunk_size
    
    return None


def get_wav_info(wav_path):
    """Get basic WAV file information."""
    with wave.open(str(wav_path), 'rb') as wav:
        return {
            'channels': wav.getnchannels(),
            'samplerate': wav.getframerate(),
            'frames': wav.getnframes(),
            'duration': wav.getnframes() / wav.getframerate()
        }


def main():
    print("\n" + "="*60)
    print("INTEGRATION TEST: Sample 8 Notes and Autoloop All")
    print("="*60)
    
    # Test parameters
    test_name = "test_8_samples_autoloop"
    output_folder = Path("output") / test_name
    samples_folder = output_folder / "samples"
    
    # Clean up any existing test output
    if output_folder.exists():
        import shutil
        shutil.rmtree(output_folder)
        print(f"\nCleaned up existing test folder: {output_folder}")
    
    # Step 1: Sample 8 notes (C3 to G3)
    sample_cmd = [
        sys.executable, "autosamplerT.py",
        "--note_range_start", "C3",
        "--note_range_end", "G3",
        "--note_range_interval", "1",  # Chromatic
        "--hold_time", "1.5",
        "--release_time", "0.5",
        "--pause_time", "0.3",
        "--multisample_name", test_name
    ]
    
    if not run_command(sample_cmd, "STEP 1: Sample 8 notes (C3 to G3, chromatic)"):
        sys.exit(1)
    
    # Check that samples were created
    if not samples_folder.exists():
        print(f"[ERROR] Samples folder not found: {samples_folder}")
        sys.exit(1)
    
    wav_files = sorted(list(samples_folder.glob("*.wav")))
    if not wav_files:
        print(f"[ERROR] No WAV files found in {samples_folder}")
        sys.exit(1)
    
    expected_count = 8  # C, C#, D, D#, E, F, F#, G
    if len(wav_files) != expected_count:
        print(f"[ERROR] Expected {expected_count} samples, found {len(wav_files)}")
        sys.exit(1)
    
    print(f"\n[SUCCESS] {len(wav_files)} samples created:")
    for wav_file in wav_files:
        wav_info = get_wav_info(wav_file)
        print(f"  - {wav_file.name}: {wav_info['channels']}ch, {wav_info['samplerate']}Hz, {wav_info['duration']:.3f}s")
    
    # Step 2: Apply autolooping with crossfade to all samples
    autoloop_cmd = [
        sys.executable, "autosamplerT.py",
        "--process", test_name,
        "--auto_loop",
        "--loop_min_duration", "0.4",
        "--crossfade_loop", "25",
        "--dc_offset_removal",
        "--trim_silence"
    ]
    
    if not run_command(autoloop_cmd, "STEP 2: Apply autolooping + DC removal + trim silence to all 8 samples"):
        sys.exit(1)
    
    # Step 3: Verify loop points in all WAV files
    print(f"\n{'='*60}")
    print("STEP 3: Verify loop points in all WAV RIFF headers")
    print(f"{'='*60}")
    
    processed_count = 0
    failed_count = 0
    loop_summary = []
    
    for wav_file in wav_files:
        print(f"\nVerifying: {wav_file.name}")
        
        # Get WAV info
        wav_info = get_wav_info(wav_file)
        
        # Read loop points
        smpl_data = read_smpl_chunk(wav_file)
        
        if smpl_data is None:
            print(f"  [ERROR] No 'smpl' chunk found")
            failed_count += 1
            continue
        
        loop_start_sec = smpl_data['loop_start'] / wav_info['samplerate']
        loop_end_sec = smpl_data['loop_end'] / wav_info['samplerate']
        loop_duration_sec = loop_end_sec - loop_start_sec
        
        print(f"  [PASS] Loop points found:")
        print(f"    Start: {smpl_data['loop_start']} samples ({loop_start_sec:.3f}s)")
        print(f"    End: {smpl_data['loop_end']} samples ({loop_end_sec:.3f}s)")
        print(f"    Duration: {loop_duration_sec:.3f}s")
        
        # Verify loop points are valid
        if smpl_data['loop_start'] >= smpl_data['loop_end']:
            print(f"  [ERROR] Invalid loop points: start >= end")
            failed_count += 1
            continue
        
        if smpl_data['loop_end'] > wav_info['frames']:
            print(f"  [ERROR] Loop end point beyond audio data")
            failed_count += 1
            continue
        
        if loop_duration_sec < 0.4:
            print(f"  [WARNING] Loop duration ({loop_duration_sec:.3f}s) less than requested minimum (0.4s)")
        
        processed_count += 1
        loop_summary.append({
            'name': wav_file.name,
            'duration': loop_duration_sec,
            'start': loop_start_sec,
            'end': loop_end_sec
        })
    
    # Print summary
    print("\n" + "="*60)
    if failed_count == 0 and processed_count == expected_count:
        print("[SUCCESS] All tests passed!")
    else:
        print(f"[PARTIAL] {processed_count}/{expected_count} samples processed successfully")
        if failed_count > 0:
            print(f"[ERROR] {failed_count} samples failed verification")
    print("="*60)
    
    print("\nSummary:")
    print(f"  - Total samples: {len(wav_files)}")
    print(f"  - Successfully processed: {processed_count}")
    print(f"  - Failed: {failed_count}")
    print(f"  - Note range: C3 to G3 (chromatic)")
    print(f"  - Postprocessing: DC removal, silence trim, autoloop, 25ms crossfade")
    
    print("\nLoop durations:")
    for item in loop_summary:
        print(f"  - {item['name']}: {item['duration']:.3f}s ({item['start']:.3f}s - {item['end']:.3f}s)")
    
    print(f"\nOutput folder: {samples_folder}")
    
    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
