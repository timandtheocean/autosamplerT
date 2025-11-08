#!/usr/bin/env python3
"""
Verify WAV RIFF Metadata

This script reads WAV files and displays all RIFF chunks,
including custom 'note' chunks with MIDI data.
"""

import struct
import sys
from pathlib import Path


def read_riff_chunks(filepath):
    """
    Read and display all RIFF chunks from a WAV file.
    
    Args:
        filepath: Path to WAV file
    """
    with open(filepath, 'rb') as f:
        # Read RIFF header
        riff_id = f.read(4)
        if riff_id != b'RIFF':
            print(f"Error: Not a valid RIFF file (got {riff_id})")
            return
        
        riff_size = struct.unpack('<I', f.read(4))[0]
        wave_id = f.read(4)
        if wave_id != b'WAVE':
            print(f"Error: Not a WAVE file (got {wave_id})")
            return
        
        print(f"=== WAV File: {filepath.name} ===")
        print(f"RIFF size: {riff_size} bytes")
        print(f"\nChunks:")
        
        # Read all chunks
        bytes_read = 4  # Already read 'WAVE'
        while bytes_read < riff_size:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                break
            
            chunk_size = struct.unpack('<I', f.read(4))[0]
            chunk_data = f.read(chunk_size)
            
            # Pad to even boundary
            if chunk_size % 2:
                f.read(1)
                bytes_read += 1
            
            bytes_read += 8 + chunk_size
            
            # Display chunk info
            print(f"\n  [{chunk_id.decode('latin1')}] size={chunk_size}")
            
            # Parse specific chunks
            if chunk_id == b'fmt ':
                parse_fmt_chunk(chunk_data)
            elif chunk_id == b'data':
                print(f"    Audio data: {chunk_size} bytes")
            elif chunk_id == b'note':
                parse_note_chunk(chunk_data)
            else:
                print(f"    Data: {chunk_data[:32]}" + ("..." if len(chunk_data) > 32 else ""))


def parse_fmt_chunk(data):
    """Parse the 'fmt ' chunk."""
    if len(data) < 16:
        return
    
    audio_format, channels, sample_rate, byte_rate, block_align, bits_per_sample = \
        struct.unpack('<HHIIHH', data[:16])
    
    format_names = {1: 'PCM', 3: 'IEEE Float', 6: 'A-law', 7: 'μ-law'}
    format_name = format_names.get(audio_format, f'Unknown({audio_format})')
    
    print(f"    Format: {format_name}")
    print(f"    Channels: {channels}")
    print(f"    Sample Rate: {sample_rate} Hz")
    print(f"    Bit Depth: {bits_per_sample} bits")
    print(f"    Byte Rate: {byte_rate} bytes/sec")


def parse_note_chunk(data):
    """Parse the custom 'note' chunk with MIDI data."""
    if len(data) < 4:
        print(f"    Invalid note chunk (size={len(data)})")
        return
    
    note, velocity, round_robin, channel = struct.unpack('BBBB', data[:4])
    
    # Convert MIDI note to name
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    note_name = note_names[note % 12]
    octave = (note // 12) - 1
    
    print(f"    *** MIDI Metadata ***")
    print(f"    Note: {note} ({note_name}{octave})")
    print(f"    Velocity: {velocity}")
    print(f"    Round-Robin: {round_robin}")
    print(f"    Channel: {channel}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_wav_metadata.py <wav_file> [wav_file2 ...]")
        sys.exit(1)
    
    for filepath in sys.argv[1:]:
        path = Path(filepath)
        if not path.exists():
            print(f"Error: File not found: {filepath}")
            continue
        
        read_riff_chunks(path)
        print()


if __name__ == '__main__':
    main()
