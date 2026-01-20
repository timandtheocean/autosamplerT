"""
Shared utilities for Waldorf exports (QPAT and MAP formats).
Contains common functionality to avoid code duplication.
"""

import struct
import logging
from typing import Tuple


def read_wav_loop_points(wav_path: str) -> Tuple[float, float, bool]:
    """
    Read loop points from WAV file RIFF SMPL chunk.
    
    This function properly handles both mono and stereo samples by reading
    the actual audio format from the fmt chunk.
    
    Args:
        wav_path: Path to WAV file
        
    Returns:
        Tuple of (loop_start_normalized, loop_end_normalized, has_loop)
        - loop_start_normalized: Loop start as fraction of total length (0.0-1.0)
        - loop_end_normalized: Loop end as fraction of total length (0.0-1.0) 
        - has_loop: True if valid loop points found
    """
    try:
        with open(wav_path, 'rb') as f:
            # Read RIFF header
            riff = f.read(4)
            if riff != b'RIFF':
                return 0.0, 1.0, False

            file_size = struct.unpack('<I', f.read(4))[0]
            wave_tag = f.read(4)
            if wave_tag != b'WAVE':
                return 0.0, 1.0, False

            # Initialize format info
            total_frames = 0
            sample_rate = 0
            channels = 1
            bits_per_sample = 16
            block_align = 0
            loop_start = 0
            loop_end = 0
            has_loop = False

            # Read all chunks
            while f.tell() < file_size + 8:
                try:
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4:
                        break

                    chunk_size = struct.unpack('<I', f.read(4))[0]
                    chunk_pos = f.tell()

                    if chunk_id == b'fmt ':
                        # Parse format chunk to get audio format info
                        if chunk_size >= 16:
                            chunk_data = f.read(16)
                            fmt = struct.unpack('<HHIIHH', chunk_data)
                            format_tag = fmt[0]      # PCM = 1
                            channels = fmt[1]        # 1=mono, 2=stereo
                            sample_rate = fmt[2]     # Sample rate
                            bytes_per_sec = fmt[3]   # Bytes per second
                            block_align = fmt[4]     # Bytes per sample frame
                            bits_per_sample = fmt[5] # Bits per sample
                            
                            logging.debug(f"WAV format: {channels}ch, {sample_rate}Hz, "
                                        f"{bits_per_sample}bit, block_align={block_align}")

                    elif chunk_id == b'data':
                        # Calculate total frames using block_align from fmt chunk
                        if block_align > 0:
                            total_frames = chunk_size // block_align
                        else:
                            # Fallback calculation
                            bytes_per_sample = bits_per_sample // 8
                            bytes_per_frame = bytes_per_sample * channels
                            total_frames = chunk_size // bytes_per_frame
                            
                        logging.debug(f"Data chunk: {chunk_size} bytes, {total_frames} frames")

                    elif chunk_id == b'smpl':
                        # Parse SMPL chunk for loop information
                        if chunk_size >= 36:
                            smpl_data = f.read(min(chunk_size, 60))  # Header + 1 loop
                            
                            # SMPL header (36 bytes)
                            if len(smpl_data) >= 36:
                                smpl_header = struct.unpack('<9I', smpl_data[:36])
                                num_loops = smpl_header[7]  # Number of loops
                                
                                # Read first loop (24 bytes)
                                if num_loops > 0 and len(smpl_data) >= 60:
                                    loop_data = struct.unpack('<6I', smpl_data[36:60])
                                    loop_start = loop_data[2]  # Start sample offset
                                    loop_end = loop_data[3]    # End sample offset
                                    has_loop = True
                                    
                                    logging.debug(f"Loop points: start={loop_start}, end={loop_end}, "
                                                f"total_frames={total_frames}")

                    # Move to next chunk
                    f.seek(chunk_pos + chunk_size)
                    
                    # Handle odd-sized chunks (RIFF alignment)
                    if chunk_size % 2:
                        f.seek(1, 1)

                except Exception as e:
                    logging.debug(f"Error reading chunk: {e}")
                    break

            # Normalize loop points
            if has_loop and total_frames > 0:
                loop_start_norm = loop_start / total_frames
                loop_end_norm = loop_end / total_frames
                
                # Clamp to valid range
                loop_start_norm = max(0.0, min(1.0, loop_start_norm))
                loop_end_norm = max(0.0, min(1.0, loop_end_norm))
                
                # Validate loop points
                if loop_start_norm < loop_end_norm:
                    return loop_start_norm, loop_end_norm, True
                else:
                    logging.warning(f"Invalid loop points in {wav_path}: "
                                  f"start={loop_start_norm:.6f} >= end={loop_end_norm:.6f}")
                    return 0.0, 1.0, False
            else:
                return 0.0, 1.0, False

    except Exception as e:
        logging.debug(f"Error reading WAV loop points from {wav_path}: {e}")
        return 0.0, 1.0, False


def format_double_value(value: float) -> str:
    """
    Format floating point value for Waldorf files.
    
    Args:
        value: Float value to format
        
    Returns:
        String with 8 decimal places
    """
    return f'{value:.8f}'


def calculate_crossfade_value(crossfade_ms: float, sample_rate: float = 44100.0) -> float:
    """
    Calculate crossfade value as fraction of sample length.
    
    Args:
        crossfade_ms: Crossfade time in milliseconds
        sample_rate: Sample rate in Hz
        
    Returns:
        Crossfade as fraction (0.0 = no crossfade, 0.1 = 10% of sample)
    """
    if crossfade_ms <= 0:
        return 0.0
    
    # Convert milliseconds to samples, then to fraction
    crossfade_samples = (crossfade_ms / 1000.0) * sample_rate
    # For now, assume a default sample length - this could be improved
    # by passing actual sample length
    default_sample_length = sample_rate  # 1 second default
    return min(0.1, crossfade_samples / default_sample_length)  # Cap at 10%