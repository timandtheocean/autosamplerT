"""
Post-processing functions for AutosamplerT
Handles normalization, trimming, looping, fades, and other audio processing operations.
"""

import wave
import struct
import os
import numpy as np
from scipy import signal
from typing import Tuple, Optional, List, Dict
import re
import shutil


class PostProcessor:
    """Main class for post-processing audio samples."""
    
    def __init__(self, backup=False):
        """
        Initialize PostProcessor.
        
        Args:
            backup: If True, create backup copies before processing
        """
        self.backup = backup
        
    def process_samples(self, sample_paths: List[str], operations: Dict):
        """
        Apply post-processing operations to a list of samples.
        
        Args:
            sample_paths: List of paths to WAV files
            operations: Dictionary of operations to apply with their parameters
                Example: {
                    'patch_normalize': True,
                    'sample_normalize': False,
                    'trim_silence': True,
                    'auto_loop': True,
                    'dc_offset_removal': True,
                    'convert_bitdepth': 16,
                    'dither': True,
                    'update_note_metadata': True  # Read note from filename and write to RIFF
                }
        """
        if not sample_paths:
            print("No samples to process")
            return
        
        print(f"\nProcessing {len(sample_paths)} samples...")
        
        # Create backups if requested
        if self.backup:
            self._create_backups(sample_paths)
        
        # Step 1: Patch normalization (analyze all files first)
        if operations.get('patch_normalize'):
            self._patch_normalize(sample_paths)
        
        # Step 2: Process each sample individually
        for i, path in enumerate(sample_paths):
            print(f"\nProcessing [{i+1}/{len(sample_paths)}]: {os.path.basename(path)}")
            
            try:
                # Read WAV file
                audio_data, samplerate, bitdepth, metadata = self._read_wav_with_metadata(path)
                original_bitdepth = bitdepth
                
                # Update note metadata from filename if requested
                if operations.get('update_note_metadata'):
                    note_info = self._extract_note_from_filename(os.path.basename(path))
                    if note_info:
                        metadata['note'] = note_info
                        print(f"  - Updated note metadata: {note_info}")
                
                # DC offset removal
                if operations.get('dc_offset_removal'):
                    audio_data = self._remove_dc_offset(audio_data)
                    print("  - Removed DC offset")
                
                # Trim silence
                if operations.get('trim_silence'):
                    audio_data = self._trim_silence(audio_data, samplerate)
                    print("  - Trimmed silence")
                
                # Sample normalization
                if operations.get('sample_normalize') and not operations.get('patch_normalize'):
                    audio_data = self._normalize_audio(audio_data)
                    print("  - Normalized sample")
                
                # Auto-looping
                if operations.get('auto_loop'):
                    min_duration_param = operations.get('loop_min_duration', 0.1)
                    start_time = operations.get('loop_start_time')
                    end_time = operations.get('loop_end_time')
                    
                    # Calculate sample duration
                    sample_duration = len(audio_data) / samplerate
                    
                    # Parse min_duration: support percentage (e.g., "55%") or seconds (e.g., 8.25)
                    if isinstance(min_duration_param, str) and min_duration_param.endswith('%'):
                        # Percentage of sample duration
                        percentage = float(min_duration_param.rstrip('%'))
                        min_duration = (percentage / 100.0) * sample_duration
                    else:
                        # Absolute duration in seconds
                        min_duration = float(min_duration_param)
                    
                    # Validate min_duration doesn't exceed sample length
                    if min_duration > sample_duration:
                        print(f"  [WARNING] Requested loop duration ({min_duration:.3f}s) exceeds sample length ({sample_duration:.3f}s)")
                        min_duration = sample_duration * 0.8  # Use 80% of sample as fallback
                        print(f"  [WARNING] Using {min_duration:.3f}s ({min_duration/sample_duration*100:.1f}%) instead")
                    
                    loop_points = self._find_loop_points(
                        audio_data, samplerate, 
                        min_loop_length=min_duration,
                        start_time=start_time,
                        end_time=end_time
                    )
                    
                    if loop_points:
                        metadata['loop_start'], metadata['loop_end'] = loop_points
                        loop_start_sec = loop_points[0] / samplerate
                        loop_end_sec = loop_points[1] / samplerate
                        loop_duration = loop_end_sec - loop_start_sec
                        print(f"  - Found loop points: {loop_start_sec:.3f}s - {loop_end_sec:.3f}s (duration: {loop_duration:.3f}s)")
                
                # Bit depth conversion
                target_bitdepth = operations.get('convert_bitdepth')
                if target_bitdepth and target_bitdepth != original_bitdepth:
                    use_dither = operations.get('dither', False)
                    audio_data = self._convert_bitdepth(audio_data, original_bitdepth, target_bitdepth, use_dither)
                    bitdepth = target_bitdepth
                    print(f"  - Converted to {target_bitdepth}-bit" + (" (dithered)" if use_dither else ""))
                
                # Write processed file
                self._write_wav_with_metadata(path, audio_data, samplerate, bitdepth, metadata)
                print(f"  [SAVED]")
                
            except Exception as e:
                print(f"  [ERROR] Error processing {path}: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        print(f"\n[SUCCESS] Processing complete!")
        return True
    
    def _create_backups(self, sample_paths: List[str]):
        """Create backup copies of samples before processing."""
        print("\nCreating backups...")
        for path in sample_paths:
            backup_path = path.replace('.wav', '_backup.wav')
            shutil.copy2(path, backup_path)
        print(f"[SUCCESS] Created {len(sample_paths)} backups")
    
    def _read_wav_with_metadata(self, path: str) -> Tuple[np.ndarray, int, int, Dict]:
        """
        Read WAV file and extract all metadata including custom RIFF chunks.
        
        Returns:
            (audio_data, samplerate, bitdepth, metadata)
            metadata dict contains: 'note', 'loop_start', 'loop_end', 'midi_note', 'velocity', 'round_robin', 'channel'
        """
        metadata = {}
        
        with open(path, 'rb') as f:
            # Read RIFF header
            riff = f.read(4)
            if riff != b'RIFF':
                raise ValueError("Not a valid WAV file")
            
            file_size = struct.unpack('<I', f.read(4))[0]
            wave_tag = f.read(4)
            if wave_tag != b'WAVE':
                raise ValueError("Not a valid WAV file")
            
            audio_data = None
            samplerate = None
            bitdepth = None
            channels = None
            
            # Read all chunks
            while f.tell() < file_size + 8:
                try:
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4:
                        break
                    
                    chunk_size = struct.unpack('<I', f.read(4))[0]
                    chunk_data = f.read(chunk_size)
                    
                    # Align to word boundary
                    if chunk_size % 2:
                        f.read(1)
                    
                    if chunk_id == b'fmt ':
                        # Parse format chunk
                        # Format: audio_format(2), channels(2), samplerate(4), byterate(4), blockalign(2), bitspersample(2)
                        fmt = struct.unpack('<HHIIHH', chunk_data[:16])
                        channels = fmt[1]
                        samplerate = fmt[2]
                        bitdepth = fmt[5]  # bits per sample is the last field
                    
                    elif chunk_id == b'data':
                        # Parse audio data
                        if bitdepth == 16:
                            dtype = np.int16
                        elif bitdepth == 24:
                            # 24-bit needs special handling
                            audio_data = np.frombuffer(chunk_data, dtype=np.uint8)
                            audio_data = audio_data.reshape(-1, 3)
                            audio_data = np.pad(audio_data, ((0, 0), (0, 1)), mode='constant')
                            audio_data = audio_data.view(np.int32)
                            audio_data = audio_data.astype(np.float32) / (2**23)
                            if channels == 2:
                                audio_data = audio_data.reshape(-1, 2)
                            continue
                        elif bitdepth == 32:
                            dtype = np.int32
                        else:
                            raise ValueError(f"Unsupported bit depth: {bitdepth}")
                        
                        audio_data = np.frombuffer(chunk_data, dtype=dtype)
                        if channels == 2:
                            audio_data = audio_data.reshape(-1, 2)
                        
                        # Convert to float32 [-1.0, 1.0]
                        audio_data = audio_data.astype(np.float32) / (2**(bitdepth-1))
                    
                    elif chunk_id == b'note':
                        # Custom note chunk with MIDI metadata
                        if len(chunk_data) >= 4:
                            metadata['midi_note'] = chunk_data[0]
                            metadata['velocity'] = chunk_data[1]
                            metadata['round_robin'] = chunk_data[2]
                            metadata['channel'] = chunk_data[3]
                    
                    elif chunk_id == b'smpl':
                        # Sample chunk with loop points
                        if len(chunk_data) >= 36:
                            smpl_data = struct.unpack('<9I', chunk_data[:36])
                            num_loops = smpl_data[7]
                            if num_loops > 0 and len(chunk_data) >= 60:
                                loop_data = struct.unpack('<6I', chunk_data[36:60])
                                metadata['loop_start'] = loop_data[2]
                                metadata['loop_end'] = loop_data[3]
                
                except Exception as e:
                    print(f"Warning: Error reading chunk: {e}")
                    break
            
            if audio_data is None:
                raise ValueError("No audio data found in WAV file")
            
            return audio_data, samplerate, bitdepth, metadata
    
    def _write_wav_with_metadata(self, path: str, audio_data: np.ndarray, samplerate: int, 
                                  bitdepth: int, metadata: Dict):
        """
        Write WAV file with metadata including custom RIFF chunks.
        
        Args:
            path: Output file path
            audio_data: Audio data as float32 [-1.0, 1.0]
            samplerate: Sample rate in Hz
            bitdepth: Bit depth (16, 24, or 32)
            metadata: Dictionary with optional keys: 'note', 'loop_start', 'loop_end', 
                     'midi_note', 'velocity', 'round_robin', 'channel'
        """
        # Determine channels
        if audio_data.ndim == 1:
            channels = 1
        else:
            channels = audio_data.shape[1]
        
        # Convert audio data to integer format
        if bitdepth == 16:
            max_val = 2**15 - 1
            audio_int = (audio_data * max_val).astype(np.int16)
            sample_width = 2
        elif bitdepth == 24:
            max_val = 2**23 - 1
            audio_int = (audio_data * max_val).astype(np.int32)
            sample_width = 3
        elif bitdepth == 32:
            max_val = 2**31 - 1
            audio_int = (audio_data * max_val).astype(np.int32)
            sample_width = 4
        else:
            raise ValueError(f"Unsupported bit depth: {bitdepth}")
        
        with wave.open(str(path), 'wb') as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(samplerate)
            
            # Write audio data
            if bitdepth == 24:
                # Convert 32-bit to 24-bit
                audio_bytes = audio_int.tobytes()
                audio_24bit = bytearray()
                for i in range(0, len(audio_bytes), 4):
                    audio_24bit.extend(audio_bytes[i:i+3])
                wav.writeframes(bytes(audio_24bit))
            else:
                wav.writeframes(audio_int.tobytes())
        
        # Now add custom chunks by rewriting the file
        with open(path, 'rb') as f:
            wav_data = f.read()
        
        # Find the data chunk end
        data_idx = wav_data.find(b'data')
        if data_idx == -1:
            return
        
        data_size = struct.unpack('<I', wav_data[data_idx+4:data_idx+8])[0]
        data_end = data_idx + 8 + data_size
        if data_size % 2:
            data_end += 1
        
        # Build custom chunks
        custom_chunks = bytearray()
        
        # Add 'note' chunk with MIDI metadata
        if 'midi_note' in metadata or 'note' in metadata:
            note_data = bytearray(4)
            note_info = metadata.get('note') or {}
            note_data[0] = metadata.get('midi_note', note_info.get('midi_note', 60))
            note_data[1] = metadata.get('velocity', note_info.get('velocity', 127))
            note_data[2] = metadata.get('round_robin', note_info.get('round_robin', 0))
            note_data[3] = metadata.get('channel', note_info.get('channel', 0))
            
            custom_chunks.extend(b'note')
            custom_chunks.extend(struct.pack('<I', 4))
            custom_chunks.extend(note_data)
        
        # Add 'smpl' chunk with loop points
        if 'loop_start' in metadata and 'loop_end' in metadata:
            loop_start = metadata['loop_start']
            loop_end = metadata['loop_end']
            
            # Build smpl chunk
            smpl_chunk = bytearray()
            smpl_chunk.extend(struct.pack('<I', 0))  # Manufacturer
            smpl_chunk.extend(struct.pack('<I', 0))  # Product
            smpl_chunk.extend(struct.pack('<I', int(1e9 / samplerate)))  # Sample period (nanoseconds)
            smpl_chunk.extend(struct.pack('<I', metadata.get('midi_note', 60)))  # MIDI unity note
            smpl_chunk.extend(struct.pack('<I', 0))  # MIDI pitch fraction
            smpl_chunk.extend(struct.pack('<I', 0))  # SMPTE format
            smpl_chunk.extend(struct.pack('<I', 0))  # SMPTE offset
            smpl_chunk.extend(struct.pack('<I', 1))  # Number of loops
            smpl_chunk.extend(struct.pack('<I', 0))  # Sampler data
            
            # Loop data
            smpl_chunk.extend(struct.pack('<I', 0))  # Cue point ID
            smpl_chunk.extend(struct.pack('<I', 0))  # Type (0 = forward loop)
            smpl_chunk.extend(struct.pack('<I', loop_start))  # Start
            smpl_chunk.extend(struct.pack('<I', loop_end))  # End
            smpl_chunk.extend(struct.pack('<I', 0))  # Fraction
            smpl_chunk.extend(struct.pack('<I', 0))  # Play count (0 = infinite)
            
            custom_chunks.extend(b'smpl')
            custom_chunks.extend(struct.pack('<I', len(smpl_chunk)))
            custom_chunks.extend(smpl_chunk)
        
        # Write updated file
        if len(custom_chunks) > 0:
            with open(path, 'wb') as f:
                # Write everything up to and including data chunk
                f.write(wav_data[:data_end])
                # Write custom chunks
                f.write(custom_chunks)
                # Update RIFF size
                f.seek(4)
                new_size = data_end - 8 + len(custom_chunks)
                f.write(struct.pack('<I', new_size))
    
    def _extract_note_from_filename(self, filename: str) -> Optional[Dict]:
        """
        Extract note information from filename.
        Expected format: "Name_C3_v127_rr0.wav" or similar
        
        Returns:
            Dictionary with 'midi_note', 'velocity', 'round_robin', 'channel' or None
        """
        # Pattern to match note names (C, C#, Db, etc.) followed by octave
        note_pattern = r'([A-G][#b]?)(-?\d+)'
        velocity_pattern = r'v(\d+)'
        rr_pattern = r'rr(\d+)'
        
        note_info = {}
        
        # Extract note and octave
        note_match = re.search(note_pattern, filename)
        if note_match:
            note_name = note_match.group(1)
            octave = int(note_match.group(2))
            
            # Convert to MIDI note number
            note_map = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 
                       'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 
                       'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
            
            if note_name in note_map:
                midi_note = (octave + 1) * 12 + note_map[note_name]
                note_info['midi_note'] = midi_note
        
        # Extract velocity
        vel_match = re.search(velocity_pattern, filename)
        if vel_match:
            note_info['velocity'] = int(vel_match.group(1))
        else:
            note_info['velocity'] = 127
        
        # Extract round-robin
        rr_match = re.search(rr_pattern, filename)
        if rr_match:
            note_info['round_robin'] = int(rr_match.group(1))
        else:
            note_info['round_robin'] = 0
        
        note_info['channel'] = 0
        
        return note_info if 'midi_note' in note_info else None
    
    def _patch_normalize(self, sample_paths: List[str]):
        """
        Normalize all samples to the same peak level.
        Finds the maximum peak across all samples and normalizes to that level.
        """
        print("\nAnalyzing patch for normalization...")
        
        # Find global maximum peak
        global_max = 0.0
        for path in sample_paths:
            try:
                audio_data, _, _, _ = self._read_wav_with_metadata(path)
                peak = np.abs(audio_data).max()
                global_max = max(global_max, peak)
            except Exception as e:
                print(f"Warning: Could not read {path}: {e}")
        
        if global_max == 0:
            print("Warning: All samples are silent")
            return
        
        # Calculate normalization factor (target 0.95 to leave headroom)
        norm_factor = 0.95 / global_max
        print(f"Global peak: {global_max:.3f}, normalization factor: {norm_factor:.3f}")
        
        # Apply normalization to all samples
        for path in sample_paths:
            try:
                audio_data, samplerate, bitdepth, metadata = self._read_wav_with_metadata(path)
                audio_data = audio_data * norm_factor
                self._write_wav_with_metadata(path, audio_data, samplerate, bitdepth, metadata)
            except Exception as e:
                print(f"Warning: Could not normalize {path}: {e}")
        
        print("[SUCCESS] Patch normalization complete")
    
    def _normalize_audio(self, audio_data: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
        """Normalize audio to target peak level."""
        peak = np.abs(audio_data).max()
        if peak > 0:
            return audio_data * (target_peak / peak)
        return audio_data
    
    def _remove_dc_offset(self, audio_data: np.ndarray) -> np.ndarray:
        """Remove DC offset by subtracting the mean."""
        if audio_data.ndim == 1:
            return audio_data - np.mean(audio_data)
        else:
            # Process each channel separately
            return audio_data - np.mean(audio_data, axis=0)
    
    def _trim_silence(self, audio_data: np.ndarray, samplerate: int, 
                      threshold_db: float = -40.0, margin_ms: float = 10.0) -> np.ndarray:
        """
        Trim silence from start and end of audio.
        Uses silence detection to find actual audio onset/offset.
        
        Args:
            audio_data: Audio data as float32
            samplerate: Sample rate in Hz
            threshold_db: Silence threshold in dB
            margin_ms: Safety margin in milliseconds to keep before/after audio
        """
        # Convert threshold to linear
        threshold = 10 ** (threshold_db / 20)
        
        # Calculate RMS energy in small windows
        window_size = int(0.01 * samplerate)  # 10ms windows
        margin_samples = int(margin_ms * samplerate / 1000)
        
        # Get amplitude envelope
        if audio_data.ndim == 1:
            envelope = np.abs(audio_data)
        else:
            envelope = np.max(np.abs(audio_data), axis=1)
        
        # Smooth envelope
        envelope = signal.convolve(envelope, np.ones(window_size)/window_size, mode='same')
        
        # Find start and end points
        above_threshold = envelope > threshold
        if not np.any(above_threshold):
            # All silence, return a small chunk
            return audio_data[:window_size]
        
        start_idx = np.argmax(above_threshold)
        end_idx = len(envelope) - np.argmax(above_threshold[::-1])
        
        # Apply margin
        start_idx = max(0, start_idx - margin_samples)
        end_idx = min(len(audio_data), end_idx + margin_samples)
        
        return audio_data[start_idx:end_idx]
    
    def _find_zero_crossing(self, audio_data: np.ndarray, target_pos: int, 
                           search_radius: int = 500) -> int:
        """
        Find nearest zero crossing point near target position.
        
        Args:
            audio_data: Audio data (mono)
            target_pos: Target sample position
            search_radius: Maximum samples to search in each direction (default: 500)
        
        Returns:
            Sample position of nearest zero crossing
        """
        start = max(0, target_pos - search_radius)
        end = min(len(audio_data), target_pos + search_radius)
        
        # Find zero crossings in search window
        search_window = audio_data[start:end]
        
        # Detect sign changes (zero crossings)
        signs = np.sign(search_window)
        # Handle exact zeros by looking at neighbors
        signs[signs == 0] = 1
        zero_crossings = np.where(np.diff(signs) != 0)[0]
        
        if len(zero_crossings) == 0:
            # No zero crossing found, return closest to zero value
            abs_values = np.abs(search_window)
            min_idx = np.argmin(abs_values)
            return start + min_idx
        
        # Find closest zero crossing to target
        target_offset = target_pos - start
        distances = np.abs(zero_crossings - target_offset)
        closest_idx = zero_crossings[np.argmin(distances)]
        
        return start + closest_idx
    
    def _find_loop_points(self, audio_data: np.ndarray, samplerate: int,
                          min_loop_length: float = 0.1, start_time: float = None, 
                          end_time: float = None) -> Optional[Tuple[int, int]]:
        """
        Find optimal loop points using autocorrelation with zero-crossing detection.
        
        Args:
            audio_data: Audio data as float32
            samplerate: Sample rate in Hz
            min_loop_length: Minimum loop length in seconds
            start_time: Optional fixed start time in seconds
            end_time: Optional fixed end time in seconds
        
        Returns:
            (loop_start, loop_end) in samples, or None if no good loop found
        """
        # Use mono for analysis
        if audio_data.ndim > 1:
            mono = np.mean(audio_data, axis=1)
        else:
            mono = audio_data
        
        total_duration = len(mono) / samplerate
        
        # If both start and end times are provided, use them directly
        if start_time is not None and end_time is not None:
            loop_start = int(start_time * samplerate)
            loop_end = int(end_time * samplerate)
            
            # Clamp to valid range
            loop_start = max(0, min(loop_start, len(mono) - 1))
            loop_end = max(loop_start + 1, min(loop_end, len(mono) - 1))
            
            # Find zero crossings for smooth transitions
            loop_start = self._find_zero_crossing(mono, loop_start, search_radius=500)
            loop_end = self._find_zero_crossing(mono, loop_end, search_radius=500)
            
            print(f"  - Using provided loop points: {start_time:.2f}s - {end_time:.2f}s")
            return (loop_start, loop_end)
        
        # Auto-detect loop points
        # Focus on the sustained part (skip attack, use last 80%)
        start_search = int(len(mono) * 0.2)
        
        # If start_time provided, use it as starting point
        if start_time is not None:
            start_search = int(start_time * samplerate)
            start_search = max(0, min(start_search, len(mono) - 1))
        
        search_region = mono[start_search:]
        
        if len(search_region) < min_loop_length * samplerate:
            return None
        
        # Calculate autocorrelation for loop detection
        # This finds repeating patterns in the audio
        max_lag = min(len(search_region) // 2, int(10 * samplerate))  # Max 10 second loops
        correlation = np.correlate(search_region[:max_lag], 
                                   search_region[:max_lag], 
                                   mode='full')
        correlation = correlation[len(correlation)//2:]  # Only positive lags
        
        # Find peaks in autocorrelation (potential loop lengths)
        min_samples = int(min_loop_length * samplerate)
        if min_samples >= len(correlation):
            # Fallback to simple loop
            loop_start = start_search
            loop_end = len(mono) - 1
            return (loop_start, loop_end)
        
        correlation_search = correlation[min_samples:]
        
        # Normalize correlation
        if len(correlation_search) > 0 and np.max(np.abs(correlation_search)) > 0:
            correlation_search = correlation_search / np.max(np.abs(correlation_search))
        else:
            # No good loop found
            loop_start = len(mono) // 2
            loop_end = len(mono) - 1
            return (loop_start, loop_end)
        
        # Find the first strong peak (threshold 0.5 for good similarity)
        peaks, properties = signal.find_peaks(correlation_search, 
                                             height=0.5, 
                                             distance=min_samples//2)
        
        if len(peaks) == 0:
            # Try lower threshold
            peaks, properties = signal.find_peaks(correlation_search, 
                                                 height=0.3,
                                                 distance=min_samples//2)
        
        if len(peaks) == 0:
            # No good loop found, use second half as loop
            loop_start = len(mono) // 2
            loop_end = len(mono) - 1
        else:
            # Use the first strong peak as loop length
            loop_length = peaks[0] + min_samples
            
            # Set loop points
            if end_time is not None:
                loop_end = int(end_time * samplerate)
                loop_end = min(loop_end, len(mono) - 1)
            else:
                loop_end = len(mono) - 1
            
            loop_start = loop_end - loop_length
            
            # Make sure loop_start is positive
            if loop_start < 0:
                loop_start = start_search
        
        # Find zero crossings for smoother loop points
        loop_start = self._find_zero_crossing(mono, loop_start, search_radius=500)
        loop_end = self._find_zero_crossing(mono, loop_end, search_radius=500)
        
        # Ensure loop is still at least min_loop_length
        if loop_end - loop_start < min_loop_length * samplerate:
            loop_end = loop_start + int(min_loop_length * samplerate)
            if loop_end >= len(mono):
                loop_end = len(mono) - 1
                loop_start = loop_end - int(min_loop_length * samplerate)
        
        return (loop_start, loop_end)
    
    def _convert_bitdepth(self, audio_data: np.ndarray, current_depth: int, 
                         target_depth: int, use_dither: bool = False) -> np.ndarray:
        """
        Convert audio to different bit depth.
        
        Args:
            audio_data: Audio data as float32 [-1.0, 1.0]
            current_depth: Current bit depth
            target_depth: Target bit depth
            use_dither: Apply dithering when reducing bit depth
        """
        if current_depth == target_depth:
            return audio_data
        
        # When reducing bit depth, apply dither
        if use_dither and target_depth < current_depth:
            # Calculate noise amplitude for TPDF dither
            # Dither amplitude should be 1 LSB of target bit depth
            lsb = 1.0 / (2 ** (target_depth - 1))
            
            # TPDF (Triangular Probability Density Function) dither
            dither1 = np.random.uniform(-lsb/2, lsb/2, audio_data.shape)
            dither2 = np.random.uniform(-lsb/2, lsb/2, audio_data.shape)
            dither = dither1 + dither2  # Sum creates triangular distribution
            
            audio_data = audio_data + dither
        
        # Clip to valid range
        return np.clip(audio_data, -1.0, 1.0)


def process_multisample(multisample_name: str, output_folder: str, operations: Dict):
    """
    Process all samples in a multisample by name.
    
    Args:
        multisample_name: Name of the multisample (looks in output_folder/multisample_name/)
        output_folder: Base output folder (default: 'output')
        operations: Dictionary of operations to apply
    """
    # Find sample folder
    sample_folder = os.path.join(output_folder, multisample_name, 'samples')
    if not os.path.exists(sample_folder):
        # Try without samples subfolder
        sample_folder = os.path.join(output_folder, multisample_name)
    
    if not os.path.exists(sample_folder):
        print(f"Error: Could not find samples folder: {sample_folder}")
        return
    
    # Get all WAV files
    sample_paths = []
    for file in os.listdir(sample_folder):
        if file.lower().endswith('.wav'):
            sample_paths.append(os.path.join(sample_folder, file))
    
    if not sample_paths:
        print(f"Error: No WAV files found in {sample_folder}")
        return
    
    print(f"Found {len(sample_paths)} samples in {sample_folder}")
    
    # Process samples
    processor = PostProcessor(backup=operations.get('backup', False))
    processor.process_samples(sample_paths, operations)


def process_folder(folder_path: str, operations: Dict):
    """
    Process all WAV files in a specific folder.
    
    Args:
        folder_path: Path to folder containing WAV files
        operations: Dictionary of operations to apply
    """
    if not os.path.exists(folder_path):
        print(f"Error: Folder not found: {folder_path}")
        return
    
    # Get all WAV files
    sample_paths = []
    for file in os.listdir(folder_path):
        if file.lower().endswith('.wav'):
            sample_paths.append(os.path.join(folder_path, file))
    
    if not sample_paths:
        print(f"Error: No WAV files found in {folder_path}")
        return
    
    print(f"Found {len(sample_paths)} samples in {folder_path}")
    
    # Process samples
    processor = PostProcessor(backup=operations.get('backup', False))
    processor.process_samples(sample_paths, operations)
