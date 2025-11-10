#!/usr/bin/env python3
"""
Integration test: Sample a note and apply autolooping

This test:
1. Samples a single note (C4)
2. Applies autolooping with crossfade
3. Verifies loop points are written to WAV RIFF header
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
    print("INTEGRATION TEST: Sample and Autoloop")
    print("="*60)
    
    # Test parameters
    test_name = "test_autoloop_integration"
    output_folder = Path("output") / test_name
    samples_folder = output_folder / "samples"
    
    # Clean up any existing test output
    if output_folder.exists():
        import shutil
        shutil.rmtree(output_folder)
        print(f"\nCleaned up existing test folder: {output_folder}")
    
    # Step 1: Sample a single note
    sample_cmd = [
        sys.executable, "autosamplerT.py",
        "--note_range_start", "C4",
        "--note_range_end", "C4",
        "--note_range_interval", "1",
        "--hold_time", "2.0",
        "--release_time", "0.5",
        "--pause_time", "0.5",
        "--multisample_name", test_name
    ]
    
    if not run_command(sample_cmd, "STEP 1: Sample single note (C4)"):
        sys.exit(1)
    
    # Check that sample was created
    if not samples_folder.exists():
        print(f"[ERROR] Samples folder not found: {samples_folder}")
        sys.exit(1)
    
    wav_files = list(samples_folder.glob("*.wav"))
    if not wav_files:
        print(f"[ERROR] No WAV files found in {samples_folder}")
        sys.exit(1)
    
    sample_file = wav_files[0]
    print(f"\n[SUCCESS] Sample created: {sample_file.name}")
    
    # Get WAV info
    wav_info = get_wav_info(sample_file)
    print(f"  Channels: {wav_info['channels']}")
    print(f"  Sample rate: {wav_info['samplerate']} Hz")
    print(f"  Duration: {wav_info['duration']:.3f} seconds")
    print(f"  Frames: {wav_info['frames']}")
    
    # Step 2: Apply autolooping with crossfade
    autoloop_cmd = [
        sys.executable, "autosamplerT.py",
        "--process", test_name,
        "--auto_loop",
        "--loop_min_duration", "0.3",
        "--crossfade_loop", "30"
    ]
    
    if not run_command(autoloop_cmd, "STEP 2: Apply autolooping with 30ms crossfade"):
        sys.exit(1)
    
    # Step 3: Verify loop points in RIFF header
    print(f"\n{'='*60}")
    print("STEP 3: Verify loop points in WAV RIFF header")
    print(f"{'='*60}")
    
    smpl_data = read_smpl_chunk(sample_file)
    
    if smpl_data is None:
        print("[ERROR] No 'smpl' chunk found in WAV file")
        sys.exit(1)
    
    print(f"[SUCCESS] Found 'smpl' chunk with loop data:")
    print(f"  Number of loops: {smpl_data['num_loops']}")
    print(f"  Loop type: {smpl_data['loop_type']} (0=forward)")
    print(f"  Loop start: {smpl_data['loop_start']} samples ({smpl_data['loop_start']/wav_info['samplerate']:.3f}s)")
    print(f"  Loop end: {smpl_data['loop_end']} samples ({smpl_data['loop_end']/wav_info['samplerate']:.3f}s)")
    
    loop_duration_samples = smpl_data['loop_end'] - smpl_data['loop_start']
    loop_duration_seconds = loop_duration_samples / wav_info['samplerate']
    print(f"  Loop duration: {loop_duration_seconds:.3f} seconds")
    
    # Verify loop points are valid
    if smpl_data['loop_start'] >= smpl_data['loop_end']:
        print("[ERROR] Invalid loop points: start >= end")
        sys.exit(1)
    
    if smpl_data['loop_end'] > wav_info['frames']:
        print("[ERROR] Loop end point beyond audio data")
        sys.exit(1)
    
    if loop_duration_seconds < 0.3:
        print(f"[WARNING] Loop duration ({loop_duration_seconds:.3f}s) less than requested minimum (0.3s)")
    
    print("\n" + "="*60)
    print("[SUCCESS] All tests passed!")
    print("="*60)
    print("\nSummary:")
    print(f"  - Sampled note: C4")
    print(f"  - Audio format: {wav_info['channels']} channel(s), {wav_info['samplerate']} Hz")
    print(f"  - Total duration: {wav_info['duration']:.3f}s")
    print(f"  - Loop region: {smpl_data['loop_start']/wav_info['samplerate']:.3f}s - {smpl_data['loop_end']/wav_info['samplerate']:.3f}s")
    print(f"  - Loop duration: {loop_duration_seconds:.3f}s")
    print(f"  - Crossfade: 30ms equal-power")
    print(f"  - Output: {sample_file}")


if __name__ == "__main__":
    main()
