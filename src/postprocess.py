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
                    loop_strategy = operations.get('loop_strategy', 'longest_good')
                    quality_threshold = operations.get('loop_quality_threshold', 0.7)
                    skip_attack_auto = operations.get('skip_attack_auto', True)
                    loop_end_margin = operations.get('loop_end_margin', 0.1)
                    
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
                        end_time=end_time,
                        loop_strategy=loop_strategy,
                        quality_threshold=quality_threshold,
                        skip_attack_auto=skip_attack_auto,
                        loop_end_margin=loop_end_margin
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
    
    def _detect_sustain_region(self, audio_data: np.ndarray, samplerate: int) -> Tuple[int, int]:
        """
        Detect the sustain region by finding where attack ends and where release begins.
        Automatically determines if there's a release tail.
        
        Args:
            audio_data: Mono audio data as float32
            samplerate: Sample rate in Hz
        
        Returns:
            (sustain_start, sustain_end) in samples
        """
        # Calculate RMS envelope with 50ms windows
        window_size = int(0.05 * samplerate)  # 50ms windows
        hop_size = window_size // 2
        
        envelope = []
        for i in range(0, len(audio_data) - window_size, hop_size):
            window = audio_data[i:i + window_size]
            rms = np.sqrt(np.mean(window ** 2))
            envelope.append(rms)
        
        envelope = np.array(envelope)
        
        if len(envelope) < 10:
            # Too short for analysis
            start_idx = int(len(audio_data) * 0.2)
            end_idx = int(len(audio_data) * 0.95)
            return (start_idx, end_idx)
        
        # Smooth envelope to reduce noise
        if len(envelope) > 5:
            from scipy.ndimage import gaussian_filter1d
            envelope = gaussian_filter1d(envelope, sigma=2)
        
        # Find peak (attack maximum)
        peak_idx = np.argmax(envelope)
        peak_level = envelope[peak_idx]
        
        # Find where attack ends: look for where envelope reaches 90% of peak and stays stable
        search_start = max(1, len(envelope) // 10)
        sustain_start_idx = peak_idx
        
        sustain_threshold = 0.90 * peak_level
        
        for i in range(search_start, len(envelope)):
            if envelope[i] >= sustain_threshold:
                # Check stability ahead (100-250ms)
                stability_window = min(5, len(envelope) - i - 1)
                if stability_window > 0:
                    future_region = envelope[i:i + stability_window]
                    variation = np.std(future_region) / np.mean(future_region) if np.mean(future_region) > 0 else 1.0
                    
                    if variation < 0.15:
                        sustain_start_idx = i
                        break
        
        # Find where release begins: search backwards for where level drops below 80% of peak
        release_threshold = 0.80 * peak_level
        sustain_end_idx = len(envelope) - 1
        
        # Look backwards from end to find where sustained level ends
        # We want the LAST continuous region above threshold (the sustain)
        # not the first point we encounter (which could be in the release tail)
        
        # First, find all regions above threshold
        above_threshold = envelope >= release_threshold
        
        # Find the longest continuous region above threshold after attack
        in_region = False
        region_start = sustain_start_idx
        best_region_start = sustain_start_idx
        best_region_end = sustain_start_idx
        best_region_length = 0
        
        for i in range(sustain_start_idx, len(envelope)):
            if above_threshold[i]:
                if not in_region:
                    region_start = i
                    in_region = True
            else:
                if in_region:
                    # Region ended
                    region_length = i - region_start
                    if region_length > best_region_length:
                        best_region_start = region_start
                        best_region_end = i
                        best_region_length = region_length
                    in_region = False
        
        # Check if we're still in a region at the end
        if in_region:
            region_length = len(envelope) - region_start
            if region_length > best_region_length:
                best_region_start = region_start
                best_region_end = len(envelope) - 1
                best_region_length = region_length
        
        # Use the end of the best (longest) region as sustain end
        if best_region_length > 0:
            sustain_end_idx = best_region_end
        else:
            # Fallback: no clear region found
            sustain_end_idx = len(envelope) - 1
        
        # Check if there's actually a release tail
        has_release = False
        if sustain_end_idx < len(envelope) - 3:  # At least 150ms before end
            # Check if level drops significantly after sustain
            remaining_envelope = envelope[sustain_end_idx:]
            if len(remaining_envelope) > 2:
                sustain_level = np.mean(envelope[max(sustain_start_idx, sustain_end_idx - 5):sustain_end_idx])
                release_level = np.mean(remaining_envelope)
                if release_level < 0.7 * sustain_level:  # 30% drop
                    has_release = True
        
        # If no clear release, use almost entire sample (leave 50ms safety margin)
        if not has_release:
            safety_margin = max(1, int(0.05 * samplerate / hop_size))  # 50ms
            sustain_end_idx = len(envelope) - safety_margin
        
        # Convert envelope indices to sample indices
        sustain_start = sustain_start_idx * hop_size
        sustain_end = sustain_end_idx * hop_size
        
        # Ensure reasonable bounds
        sustain_start = max(0, min(sustain_start, len(audio_data) - 1))
        sustain_end = max(sustain_start + samplerate, min(sustain_end, len(audio_data) - 1))
        
        # Report findings
        attack_duration = sustain_start / samplerate
        sustain_duration = (sustain_end - sustain_start) / samplerate
        release_duration = (len(audio_data) - sustain_end) / samplerate
        
        print(f"  - Attack phase: 0.00s - {attack_duration:.2f}s ({sustain_start} samples)")
        print(f"  - Sustain region: {attack_duration:.2f}s - {sustain_end/samplerate:.2f}s ({sustain_duration:.2f}s)")
        if has_release:
            print(f"  - Release tail detected: {sustain_end/samplerate:.2f}s - {len(audio_data)/samplerate:.2f}s ({release_duration:.2f}s)")
        else:
            print(f"  - No release tail detected (using {release_duration:.2f}s safety margin)")
        
        return (sustain_start, sustain_end)
        
        # Ensure reasonable range
        sustain_start = max(0, min(sustain_start, len(audio_data) - 1))
        sustain_end = max(sustain_start + int(0.5 * samplerate), sustain_end)  # At least 0.5 seconds
        sustain_end = min(sustain_end, len(audio_data) - 1)
        
        print(f"  - Sustain region detected: {sustain_start/samplerate:.2f}s - {sustain_end/samplerate:.2f}s")
        print(f"  - Attack phase ends at: {sustain_start/samplerate:.2f}s (sample {sustain_start})")
        if end_margin > 0:
            print(f"  - End margin: {end_margin*100:.0f}% ({(len(audio_data)-sustain_end)/samplerate:.2f}s)")
        
        return (sustain_start, sustain_end)
    
    def _find_longest_good_loop(self, audio_region: np.ndarray, samplerate: int,
                                min_loop_length: float, quality_threshold: float = 0.7) -> Optional[Tuple[int, float]]:
        """
        Find the longest loop with acceptable quality within the sustain region.
        Optimizes for maximum loop length while maintaining quality standards.
        
        Args:
            audio_region: Audio data within sustain region
            samplerate: Sample rate in Hz
            min_loop_length: Minimum acceptable loop length in seconds
            quality_threshold: Minimum quality score (0.0-1.0, default 0.7)
        
        Returns:
            (loop_length_samples, quality_score) or None if no good loop found
        """
        # Try to use as much of the sustain region as possible
        # Start with longest possible loop (entire sustain region) and work down
        max_loop_length = len(audio_region)
        min_loop_samples = int(min_loop_length * samplerate)
        
        print(f"  - Searching for longest loop: max={max_loop_length/samplerate:.2f}s, min={min_loop_length:.2f}s")
        
        # Strategy 1: Try longest possible loop first (entire sustain region)
        if max_loop_length >= min_loop_samples:
            if self._validate_loop_quality(audio_region, max_loop_length, samplerate):
                quality = 1.0  # Perfect loop of entire region
                print(f"  - Optimal: Using entire sustain region as loop ({max_loop_length/samplerate:.2f}s)")
                return (max_loop_length, quality)
        
        # Strategy 2: Use autocorrelation to find repeating patterns
        # Search from 90% down to min_length in 5% steps for longer loops
        max_lag = len(audio_region) // 2
        
        if min_loop_samples >= max_lag:
            return None
        
        # Compute autocorrelation
        correlation = np.correlate(audio_region[:max_lag], 
                                   audio_region[:max_lag], 
                                   mode='full')
        correlation = correlation[len(correlation)//2:]  # Only positive lags
        
        # Normalize correlation
        if np.max(np.abs(correlation)) > 0:
            correlation = correlation / np.max(np.abs(correlation))
        
        # Strategy 3: Test specific loop lengths from longest to shortest
        # Try 90%, 80%, 70%, 60% of sustain region first
        test_percentages = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55]
        for pct in test_percentages:
            test_length = int(len(audio_region) * pct)
            if test_length >= min_loop_samples:
                if self._validate_loop_quality(audio_region, test_length, samplerate):
                    quality = correlation[test_length] if test_length < len(correlation) else 0.9
                    print(f"  - Found {pct*100:.0f}% loop: length={test_length/samplerate:.2f}s, quality={quality:.3f}")
                    return (test_length, quality)
        
        # Strategy 4: Use autocorrelation peaks (original method)
        # Find peaks with relaxed threshold to get more candidates
        peaks, properties = signal.find_peaks(correlation[min_loop_samples:], 
                                             height=0.5,  # Lower threshold to find more candidates
                                             distance=min_loop_samples//4)
        
        if len(peaks) == 0:
            # Try even lower threshold
            peaks, properties = signal.find_peaks(correlation[min_loop_samples:], 
                                                 height=0.3,
                                                 distance=min_loop_samples//4)
        
        if len(peaks) > 0:
            # Adjust peak indices (they're relative to min_lag offset)
            peaks = peaks + min_loop_samples
            peak_qualities = properties['peak_heights']
            
            # Sort by length (longest first)
            sorted_indices = np.argsort(peaks)[::-1]
            
            # Find the longest loop that meets quality threshold
            for idx in sorted_indices:
                loop_length = peaks[idx]
                quality = peak_qualities[idx]
                
                # Validate loop quality with multi-scale analysis
                if self._validate_loop_quality(audio_region, loop_length, samplerate):
                    print(f"  - Found loop from autocorrelation: length={loop_length/samplerate:.2f}s, quality={quality:.3f}")
                    return (loop_length, quality)
        
        return None
    
    def _validate_loop_quality(self, audio_region: np.ndarray, loop_length: int, 
                               samplerate: int) -> bool:
        """
        Validate loop quality using multiple criteria.
        Optimized to accept longer loops more easily.
        Ensures both loop segments are in stable regions.
        
        Args:
            audio_region: Audio data (should be sustain region)
            loop_length: Loop length in samples
            samplerate: Sample rate in Hz
        
        Returns:
            True if loop meets quality criteria
        """
        if loop_length <= 0 or loop_length > len(audio_region):
            return False
        
        # For very long loops (>80% of region), we need to be more careful
        # Compare the MIDDLE section with the END section, not the start
        if loop_length > len(audio_region) * 0.8:
            # Use last 20% for comparison (most stable part of sustain)
            comparison_length = int(len(audio_region) * 0.2)
            if comparison_length < 0.3 * samplerate:  # At least 0.3s
                comparison_length = min(int(0.3 * samplerate), loop_length // 2)
            
            # Compare middle section with end section
            mid_point = len(audio_region) // 2
            loop_begin = audio_region[mid_point:mid_point + comparison_length]
            loop_end = audio_region[-comparison_length:]
        else:
            # Normal validation: compare start of loop with end
            loop_start = len(audio_region) - loop_length
            if loop_start < 0:
                return False
            
            loop_begin = audio_region[loop_start:loop_start + min(loop_length, len(audio_region) - loop_start)]
            loop_end = audio_region[-loop_length:]
        
        if len(loop_begin) < 100 or len(loop_end) < 100:
            return False
        
        # Criterion 1: RMS amplitude similarity
        # Relaxed for longer loops: 15% tolerance for loops > 3s, 10% for shorter
        rms_begin = np.sqrt(np.mean(loop_begin ** 2))
        rms_end = np.sqrt(np.mean(loop_end ** 2))
        
        if rms_end > 0:
            rms_diff = abs(rms_begin - rms_end) / rms_end
            max_diff = 0.15 if loop_length > 3 * samplerate else 0.10
            if rms_diff > max_diff:
                return False
        
        # Criterion 2: Waveform correlation
        # Relaxed for longer loops: 0.7 for loops > 3s, 0.8 for shorter
        min_len = min(len(loop_begin), len(loop_end))
        if min_len < 100:  # Need minimum samples for correlation
            return False
            
        correlation = np.corrcoef(loop_begin[:min_len], loop_end[:min_len])[0, 1]
        min_correlation = 0.7 if loop_length > 3 * samplerate else 0.8
        
        if correlation < min_correlation:
            return False
        
        # Criterion 3: Minimum loop length (very permissive)
        # Only reject extremely short loops (< 0.3s)
        if loop_length < 0.3 * samplerate:
            return False
        
        return True
    
    def _find_loop_points(self, audio_data: np.ndarray, samplerate: int,
                          min_loop_length: float = 0.1, start_time: float = None, 
                          end_time: float = None, loop_strategy: str = "longest_good",
                          quality_threshold: float = 0.7, skip_attack_auto: bool = True,
                          loop_end_margin: float = 0.1) -> Optional[Tuple[int, int]]:
        """
        Find optimal loop points using envelope-based sustain detection and longest-good-loop selection.
        
        Args:
            audio_data: Audio data as float32
            samplerate: Sample rate in Hz
            min_loop_length: Minimum loop length in seconds
            start_time: Optional fixed start time in seconds (manual override)
            end_time: Optional fixed end time in seconds (manual override)
            loop_strategy: "longest_good" (default), "shortest_good", or "manual"
            quality_threshold: Minimum quality for loop (0.0-1.0, default 0.7)
            skip_attack_auto: Automatically detect and skip attack phase (default True)
            loop_end_margin: Margin at end to avoid release (0.0-1.0, default 0.1 = 10%)
        
        Returns:
            (loop_start, loop_end) in samples, or None if no good loop found
        """
        # Use mono for analysis
        if audio_data.ndim > 1:
            mono = np.mean(audio_data, axis=1)
        else:
            mono = audio_data
        
        total_duration = len(mono) / samplerate
        print(f"  - Loop detection: strategy={loop_strategy}, quality_threshold={quality_threshold}")
        
        # Priority 1: Manual override - both start and end times provided
        if start_time is not None and end_time is not None:
            loop_start = int(start_time * samplerate)
            loop_end = int(end_time * samplerate)
            
            # Clamp to valid range
            loop_start = max(0, min(loop_start, len(mono) - 1))
            loop_end = max(loop_start + 1, min(loop_end, len(mono) - 1))
            
            # Find zero crossings for smooth transitions
            loop_start = self._find_zero_crossing(mono, loop_start, search_radius=500)
            loop_end = self._find_zero_crossing(mono, loop_end, search_radius=500)
            
            print(f"  - Manual override: {start_time:.2f}s - {end_time:.2f}s")
            return (loop_start, loop_end)
        
        # Priority 2: Envelope-based sustain region detection
        if skip_attack_auto:
            sustain_start, sustain_end = self._detect_sustain_region(mono, samplerate)
        else:
            # Use simple 20% skip if automatic detection disabled
            sustain_start = int(len(mono) * 0.2)
            sustain_end = int(len(mono) * (1.0 - loop_end_margin))
        
        # Apply manual start_time override if provided
        if start_time is not None:
            sustain_start = int(start_time * samplerate)
            sustain_start = max(0, min(sustain_start, len(mono) - 1))
            print(f"  - Manual start time override: {start_time:.2f}s")
        
        # Apply manual end_time override if provided
        if end_time is not None:
            sustain_end = int(end_time * samplerate)
            sustain_end = min(sustain_end, len(mono) - 1)
            print(f"  - Manual end time override: {end_time:.2f}s")
        
        # Extract sustain region for loop analysis
        sustain_region = mono[sustain_start:sustain_end]
        
        if len(sustain_region) < min_loop_length * samplerate:
            print(f"  - Sustain region too short for minimum loop length")
            # Fallback: use second half
            loop_start = len(mono) // 2
            loop_end = len(mono) - 1
            return (loop_start, loop_end)
        
        # Priority 3: Find longest good loop within sustain region
        result = self._find_longest_good_loop(sustain_region, samplerate, 
                                              min_loop_length, quality_threshold)
        
        if result is not None:
            loop_length, quality = result
            
            # IMPORTANT: loop_length is relative to sustain_region, so we need to
            # position the loop WITHIN the sustain region
            # Place loop at the end of sustain region, working backwards
            loop_end = sustain_end
            loop_start = sustain_end - loop_length
            
            # Ensure loop_start doesn't go before sustain_start
            if loop_start < sustain_start:
                # If the loop is too long for the sustain region, clip it
                loop_start = sustain_start
                print(f"  - Loop clipped to fit sustain region")
            
            # Find zero crossings for smooth transitions
            # But don't allow them to go before sustain_start
            loop_start_zc = self._find_zero_crossing(mono, loop_start, search_radius=500)
            if loop_start_zc < sustain_start:
                # Zero crossing would place us before sustain - use sustain_start instead
                loop_start = sustain_start
            else:
                loop_start = loop_start_zc
            
            loop_end = self._find_zero_crossing(mono, loop_end, search_radius=500)
            
            # Final validation - ensure loop is within sustain region
            if loop_start < sustain_start:
                print(f"  - Clamping loop start to sustain start ({sustain_start/samplerate:.2f}s)")
                loop_start = sustain_start
            
            # Validate final loop length
            final_length = (loop_end - loop_start) / samplerate
            print(f"  - Final loop: {loop_start/samplerate:.2f}s - {loop_end/samplerate:.2f}s (length: {final_length:.2f}s)")
            print(f"  - Sustain region: {sustain_start/samplerate:.2f}s - {sustain_end/samplerate:.2f}s")
            
            return (loop_start, loop_end)
        
        # Priority 4: Fallback - use second half of sample
        print(f"  - No good loop found with quality threshold {quality_threshold}, using fallback")
        loop_start = len(mono) // 2
        loop_end = len(mono) - 1
        
        # Find zero crossings
        loop_start = self._find_zero_crossing(mono, loop_start, search_radius=500)
        loop_end = self._find_zero_crossing(mono, loop_end, search_radius=500)
        
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
