"""
AutosamplerT - Main Sampling Engine

This module handles the core autosampling functionality:
- MIDI note/CC message transmission
- Audio recording with configurable parameters
- Velocity layers and round-robin sampling
- Silence detection and auto-trimming
- Sample normalization
- WAV metadata writing
- SFZ export generation

Author: AutosamplerT
License: MIT
"""

import sounddevice as sd
import numpy as np
import mido
import time
import os
import logging
import wave
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import json

# For WAV file writing with metadata
from scipy.io import wavfile
import struct

# MIDI Control module
from src.sampler_midicontrol import MIDIController, parse_cc_messages, parse_cc14_messages, parse_sysex_messages

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')


class AutoSampler:
    """
    Main autosampling class that coordinates MIDI and audio operations.
    
    This class handles:
    - MIDI port management and message sending
    - Audio device configuration and recording
    - Sample processing (normalization, trimming)
    - File management and metadata
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the AutoSampler with configuration.
        
        Args:
            config: Dictionary containing audio_interface, midi_interface, and sampling settings
        """
        self.config = config
        self.audio_config = config.get('audio_interface', {})
        self.midi_config = config.get('midi_interface', {})
        self.sampling_midi_config = config.get('sampling_midi', {})
        self.sampling_config = config.get('sampling', {})
        
        # MIDI ports
        self.midi_input_port: Optional[mido.ports.BaseInput] = None
        self.midi_output_port: Optional[mido.ports.BaseOutput] = None
        self.midi_controller: Optional[MIDIController] = None
        
        # Audio settings
        self.samplerate = self.audio_config.get('samplerate', 44100)
        self.bitdepth = self.audio_config.get('bitdepth', 24)
        self.mono_stereo = self.audio_config.get('mono_stereo', 'stereo')
        self.channels = 2 if self.mono_stereo == 'stereo' else 1
        self.mono_channel = self.audio_config.get('mono_channel', 0)  # 0=left, 1=right
        self.input_device = self.audio_config.get('input_device_index')
        self.output_device = self.audio_config.get('output_device_index')
        
        # Sampling settings
        self.hold_time = self.sampling_config.get('hold_time', 2.0)
        self.release_time = self.sampling_config.get('release_time', 1.0)
        self.pause_time = self.sampling_config.get('pause_time', 0.5)
        self.velocity_layers = self.sampling_config.get('velocity_layers', 1)
        self.roundrobin_layers = self.sampling_config.get('roundrobin_layers', 1)
        
        # Velocity configuration
        self.velocity_minimum = self.midi_config.get('velocity_minimum', 1)
        self.velocity_layers_split = self.midi_config.get('velocity_layers_split', None)
        
        # MIDI message delay (time to wait after sending CC/PC/SysEx before note-on)
        self.midi_message_delay = self.midi_config.get('midi_message_delay', 0.0)
        
        # Processing settings
        self.silence_detection = self.audio_config.get('silence_detection', True)
        self.sample_normalize = self.audio_config.get('sample_normalize', True)
        self.patch_normalize = self.audio_config.get('patch_normalize', False)
        self.gain = self.audio_config.get('gain', 1.0)
        
        # Output settings
        self.base_output_folder = Path(self.sampling_config.get('output_folder', './output'))
        self.output_format = self.sampling_config.get('output_format', 'sfz')
        self.multisample_name = self.sampling_config.get('multisample_name', 'Multisample')
        
        # Create folder structure: output/multisample_name/samples/
        self.multisample_folder = self.base_output_folder / self.multisample_name
        self.output_folder = self.multisample_folder / 'samples'
        
        # SFZ key mapping range
        self.lowest_note = self.sampling_config.get('lowest_note', 0)
        self.highest_note = self.sampling_config.get('highest_note', 127)
        
        # Test mode flag
        self.test_mode = self.sampling_config.get('test_mode', False)
        
        # Storage for normalization
        self.recorded_samples: List[Tuple[np.ndarray, Dict]] = []
        
        logging.info("AutoSampler initialized")
    
    def setup_midi(self) -> bool:
        """
        Open MIDI input/output ports based on configuration.
        
        Returns:
            True if MIDI setup successful, False otherwise
        """
        try:
            midi_input_name = self.midi_config.get('midi_input_name')
            midi_output_name = self.midi_config.get('midi_output_name')
            
            if midi_input_name:
                self.midi_input_port = mido.open_input(midi_input_name)
                logging.info(f"MIDI input opened: {midi_input_name}")
            else:
                logging.warning("No MIDI input configured - MIDI input disabled")
            
            if midi_output_name:
                self.midi_output_port = mido.open_output(midi_output_name)
                logging.info(f"MIDI output opened: {midi_output_name}")
            else:
                logging.warning("No MIDI output configured - MIDI output disabled")
            
            # Initialize MIDI controller
            self.midi_controller = MIDIController(self.midi_output_port, self.test_mode)
            
            return True
        except Exception as e:
            logging.error(f"MIDI setup failed: {e}")
            return False
    
    def setup_audio(self) -> bool:
        """
        Configure audio devices and verify settings.
        
        Returns:
            True if audio setup successful, False otherwise
        """
        try:
            # Set default devices
            if self.input_device is not None and self.output_device is not None:
                sd.default.device = (self.input_device, self.output_device)
                logging.info(f"Audio devices set: IN={self.input_device}, OUT={self.output_device}")
            else:
                logging.warning("Audio devices not configured - using system defaults")
            
            # Set sample rate
            sd.default.samplerate = self.samplerate
            logging.info(f"Sample rate: {self.samplerate} Hz")
            
            # Verify bit depth
            if self.bitdepth not in [16, 24, 32]:
                logging.error(f"Invalid bit depth: {self.bitdepth}")
                return False
            
            logging.info(f"Bit depth: {self.bitdepth} bits")
            if self.channels == 2:
                logging.info(f"Channels: 2 (stereo)")
            else:
                channel_name = 'left' if self.mono_channel == 0 else 'right'
                logging.info(f"Channels: 1 (mono, using {channel_name} channel)")
            
            return True
        except Exception as e:
            logging.error(f"Audio setup failed: {e}")
            return False
    
    def send_midi_note(self, note: int, velocity: int, channel: int = 0, duration: float = None) -> None:
        """
        Send a MIDI note on/off sequence.
        
        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            channel: MIDI channel (0-15)
            duration: Note duration in seconds (if None, only sends note_on)
        """
        if not self.midi_output_port:
            logging.warning("No MIDI output port - skipping MIDI note")
            return
        
        if self.test_mode:
            logging.info(f"[TEST MODE] Would send: Note={note}, Vel={velocity}, Ch={channel}")
            return
        
        try:
            # Send note on
            note_on = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
            self.midi_output_port.send(note_on)
            logging.debug(f"MIDI Note ON: note={note}, velocity={velocity}, channel={channel}")
            
            # If duration specified, wait and send note off
            if duration is not None:
                time.sleep(duration)
                note_off = mido.Message('note_off', note=note, velocity=0, channel=channel)
                self.midi_output_port.send(note_off)
                logging.debug(f"MIDI Note OFF: note={note}")
        except Exception as e:
            logging.error(f"Failed to send MIDI note: {e}")
    
    def record_audio(self, duration: float) -> Optional[np.ndarray]:
        """
        Record audio for the specified duration.
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            NumPy array of recorded audio samples, or None if recording failed
        """
        if self.test_mode:
            channel_info = 'stereo' if self.mono_stereo == 'stereo' else f"mono ({['left', 'right'][self.mono_channel]})"
            logging.info(f"[TEST MODE] Recording {duration}s of silent audio ({channel_info})")
            # Create silent audio with correct shape
            num_samples = int(duration * self.samplerate)
            silent_audio = np.zeros((num_samples, self.channels), dtype='float32')
            return silent_audio
        
        try:
            logging.debug(f"Recording {duration}s at {self.samplerate}Hz, {self.channels} channels")
            
            # Always record in stereo if input has multiple channels
            # For mono output, we'll select the desired channel afterwards
            record_channels = 2 if self.mono_stereo == 'mono' else self.channels
            
            # Record audio
            frames = int(duration * self.samplerate)
            logging.info(f"Starting recording: {frames} frames ({duration:.1f}s)")
            
            recording = sd.rec(
                frames,
                samplerate=self.samplerate,
                channels=record_channels,
                dtype='float32',
                blocking=False
            )
            
            # Wait for recording to complete with timeout
            # Add extra buffer time (max of 10s or 50% of duration)
            timeout = duration + max(10.0, duration * 0.5)
            logging.debug(f"Waiting for recording to complete (timeout: {timeout:.1f}s)...")
            
            try:
                sd.wait(timeout)
                logging.info(f"Recording completed: {len(recording)} frames")
            except sd.CallbackAbort as e:
                logging.error(f"Recording aborted: {e}")
                return None
            except Exception as e:
                logging.error(f"Recording wait failed: {e}")
                return None
            
            # If mono output is requested, extract the specified channel
            if self.mono_stereo == 'mono' and record_channels == 2:
                channel_name = 'left' if self.mono_channel == 0 else 'right'
                recording = recording[:, self.mono_channel:self.mono_channel+1]
                logging.debug(f"Extracted {channel_name} channel for mono recording")
            
            # Apply gain
            if self.gain != 1.0:
                recording *= self.gain
                logging.debug(f"Applied gain: {self.gain}")
            
            return recording
        except Exception as e:
            logging.error(f"Audio recording failed: {e}")
            return None
    
    def detect_silence(self, audio: np.ndarray, threshold: float = 0.001) -> Tuple[int, int]:
        """
        Detect non-silent regions in audio and return trim points.
        
        Args:
            audio: Audio data as NumPy array
            threshold: Amplitude threshold for silence detection
            
        Returns:
            Tuple of (start_sample, end_sample) for trimming
        """
        if not self.silence_detection:
            return 0, len(audio)
        
        # Calculate RMS energy per sample
        if len(audio.shape) > 1:
            # Stereo: calculate mean across channels
            energy = np.sqrt(np.mean(audio ** 2, axis=1))
        else:
            # Mono
            energy = np.abs(audio)
        
        # Find first and last samples above threshold
        above_threshold = np.where(energy > threshold)[0]
        
        if len(above_threshold) == 0:
            logging.warning("No audio above silence threshold detected")
            return 0, len(audio)
        
        start = max(0, above_threshold[0] - int(0.01 * self.samplerate))  # 10ms pre-attack
        end = min(len(audio), above_threshold[-1] + int(0.1 * self.samplerate))  # 100ms tail
        
        logging.debug(f"Silence detection: trimmed from {len(audio)} to {end-start} samples")
        return start, end
    
    def normalize_audio(self, audio: np.ndarray, target_level: float = 0.95) -> np.ndarray:
        """
        Normalize audio to target peak level.
        
        Args:
            audio: Audio data as NumPy array
            target_level: Target peak amplitude (0.0-1.0)
            
        Returns:
            Normalized audio array
        """
        if not self.sample_normalize:
            return audio
        
        peak = np.abs(audio).max()
        if peak > 0:
            normalized = audio * (target_level / peak)
            logging.debug(f"Normalized audio: peak {peak:.3f} -> {target_level}")
            return normalized
        return audio
    
    def save_wav_file(self, audio: np.ndarray, filepath: Path, metadata: Dict = None) -> bool:
        """
        Save audio to WAV file with optional metadata in RIFF chunks.
        
        Args:
            audio: Audio data as NumPy array
            filepath: Output file path
            metadata: Optional dictionary of metadata (note, velocity, etc.)
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            logging.info(f"Saving WAV file: {filepath} ({len(audio)} frames)")
            
            # Convert float32 to appropriate bit depth
            if self.bitdepth == 16:
                audio_int = np.int16(audio * 32767)
                sampwidth = 2
            elif self.bitdepth == 24:
                audio_int = np.int32(audio * 8388607)
                sampwidth = 3
            elif self.bitdepth == 32:
                audio_int = np.int32(audio * 2147483647)
                sampwidth = 4
            else:
                audio_int = np.int16(audio * 32767)
                sampwidth = 2
            
            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Write WAV file using wave module for custom chunk support
            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(sampwidth)
                wav_file.setframerate(self.samplerate)
                
                # Convert audio to bytes
                if self.bitdepth == 24:
                    # Special handling for 24-bit - efficient method
                    # Convert to bytes and extract 3 bytes per sample
                    audio_32bit = audio_int.tobytes()
                    audio_bytes = bytearray()
                    # Each 32-bit sample is 4 bytes, we want the lower 3 bytes
                    for i in range(0, len(audio_32bit), 4):
                        audio_bytes.extend(audio_32bit[i:i+3])
                    audio_bytes = bytes(audio_bytes)
                else:
                    audio_bytes = audio_int.tobytes()
                
                wav_file.writeframes(audio_bytes)
            
            # Now reopen the file and add custom RIFF chunks for metadata
            if metadata:
                self._add_riff_metadata(filepath, metadata)
            
            logging.info(f"Saved: {filepath}")
            return True
        except Exception as e:
            logging.error(f"Failed to save WAV file {filepath}: {e}")
            return False
    
    def _add_riff_metadata(self, filepath: Path, metadata: Dict) -> None:
        """
        Add custom RIFF chunks containing MIDI metadata to WAV file.
        
        Args:
            filepath: Path to WAV file
            metadata: Dictionary with note, velocity, etc.
        """
        try:
            # Read the entire file
            with open(filepath, 'rb') as f:
                data = bytearray(f.read())
            
            # Create custom 'note' chunk with MIDI data
            # Format: note (1 byte), velocity (1 byte), channel (1 byte)
            note_data = struct.pack('BBB',
                                   metadata.get('note', 0),
                                   metadata.get('velocity', 127),
                                   metadata.get('channel', 0))
            
            # RIFF chunk format: chunk_id (4 bytes), size (4 bytes), data
            chunk_id = b'note'
            chunk_size = struct.pack('<I', len(note_data))  # Little-endian 32-bit
            note_chunk = chunk_id + chunk_size + note_data
            
            # Pad to even length (RIFF requirement)
            if len(note_chunk) % 2:
                note_chunk += b'\x00'
            
            # Insert chunk before the final 'data' chunk
            # Find the position just before the last chunk
            insert_pos = len(data) - 8  # Rough position, will refine
            
            # Actually, append after all chunks but update RIFF size
            data.extend(note_chunk)
            
            # Update RIFF chunk size (at bytes 4-7)
            new_size = len(data) - 8
            data[4:8] = struct.pack('<I', new_size)
            
            # Write back to file
            with open(filepath, 'wb') as f:
                f.write(data)
            
            logging.debug(f"RIFF metadata added: note={metadata.get('note')}, vel={metadata.get('velocity')}")
            
            # Also write sidecar JSON only if debug mode is enabled
            if self.audio_config.get('debug', False):
                meta_path = filepath.with_suffix('.json')
                with open(meta_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                logging.debug(f"Sidecar metadata written to {meta_path}")
                
        except Exception as e:
            logging.warning(f"Failed to add RIFF metadata: {e}")
    
    def sample_note(self, note: int, velocity: int, channel: int = 0, 
                    rr_index: int = 0) -> Optional[np.ndarray]:
        """
        Sample a single note: send MIDI, record audio, process.
        
        Args:
            note: MIDI note number
            velocity: MIDI velocity
            channel: MIDI channel
            rr_index: Round-robin layer index
            
        Returns:
            Processed audio array or None
        """
        logging.info(f"Sampling: Note={note}, Vel={velocity}, RR={rr_index}")
        
        # Calculate total recording duration
        total_duration = self.hold_time + self.release_time
        
        # Send MIDI note on
        self.send_midi_note(note, velocity, channel)
        
        # Start recording immediately (or after small latency compensation)
        latency_comp = self.audio_config.get('latency_compensation', 0.0) / 1000.0  # ms to seconds
        if latency_comp > 0 and not self.test_mode:
            time.sleep(latency_comp)
        
        # Start recording in a separate thread so we can send note-off during recording
        import threading
        recording_complete = threading.Event()
        audio_result = [None]
        
        def record_thread():
            audio_result[0] = self.record_audio(total_duration)
            recording_complete.set()
        
        if not self.test_mode:
            # Start recording thread
            record_thread_obj = threading.Thread(target=record_thread)
            record_thread_obj.start()
            
            # Wait for hold time, then send note off
            time.sleep(self.hold_time)
            note_off = mido.Message('note_off', note=note, velocity=0, channel=channel)
            if self.midi_output_port:
                self.midi_output_port.send(note_off)
            
            # Wait for recording to complete
            recording_complete.wait()
            audio = audio_result[0]
        else:
            # Test mode: just record without MIDI timing
            audio = self.record_audio(total_duration)
        
        if audio is None:
            logging.error("Audio recording returned None")
            return None
        
        logging.info(f"Processing audio: {len(audio)} frames, {audio.shape}")
        
        # Process audio: silence detection and trimming
        logging.debug("Detecting silence...")
        start, end = self.detect_silence(audio)
        logging.debug(f"Silence detection complete: trim from {start} to {end}")
        
        audio_trimmed = audio[start:end]
        logging.debug(f"Audio trimmed: {len(audio_trimmed)} frames")
        
        # Normalize individual sample
        logging.debug("Normalizing audio...")
        audio_processed = self.normalize_audio(audio_trimmed)
        logging.info(f"Audio processing complete: {len(audio_processed)} frames")
        
        return audio_processed
    
    def calculate_velocity_value(self, layer: int, total_layers: int) -> int:
        """
        Calculate MIDI velocity for a given velocity layer.
        
        Args:
            layer: Current layer index (0-based)
            total_layers: Total number of velocity layers
            
        Returns:
            MIDI velocity value (1-127)
        """
        # Use custom split points if provided
        if self.velocity_layers_split is not None:
            if layer < len(self.velocity_layers_split):
                return self.velocity_layers_split[layer]
            else:
                return 127  # Fallback
        
        # Default behavior: logarithmic distribution (more density at higher velocities)
        if total_layers == 1:
            return 127  # Full velocity for single layer
        
        min_vel = self.velocity_minimum
        max_vel = 127
        
        # Logarithmic curve: velocity feels more "musical"
        # Uses exponential mapping: velocity grows faster toward the end
        import math
        
        # Normalize layer position (0.0 to 1.0)
        position = layer / (total_layers - 1)
        
        # Apply exponential curve (base 2 works well for velocity)
        # This gives more samples at higher velocities
        curve_factor = 2.0
        curved_position = (math.pow(curve_factor, position) - 1) / (curve_factor - 1)
        
        # Map to velocity range
        velocity = int(min_vel + (max_vel - min_vel) * curved_position)
        return max(1, min(127, velocity))
    
    def generate_sample_filename(self, note: int, velocity: int, rr_index: int = 0) -> str:
        """
        Generate standardized sample filename.
        
        Args:
            note: MIDI note number
            velocity: MIDI velocity
            rr_index: Round-robin index
            
        Returns:
            Filename string
        """
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note // 12) - 1
        note_name = note_names[note % 12]
        
        base_name = self.sampling_config.get('sample_name', self.multisample_name)
        
        if self.roundrobin_layers > 1:
            filename = f"{base_name}_{note_name}{octave}_v{velocity:03d}_rr{rr_index+1}.wav"
        else:
            filename = f"{base_name}_{note_name}{octave}_v{velocity:03d}.wav"
        
        return filename
    
    def sample_range(self, start_note: int, end_note: int, interval: int = 1, 
                     channel: int = 0) -> List[Dict]:
        """
        Sample a range of notes with velocity layers and round-robin.
        
        Args:
            start_note: Starting MIDI note number
            end_note: Ending MIDI note number (inclusive)
            interval: Note interval (1=chromatic, 2=whole tone, etc.)
            channel: MIDI channel
            
        Returns:
            List of sample metadata dictionaries
        """
        sample_list = []
        
        # Get MIDI control configurations
        velocity_midi_config = self.sampling_midi_config.get('velocity_midi_control', [])
        roundrobin_midi_config = self.sampling_midi_config.get('roundrobin_midi_control', [])
        
        logging.info(f"Velocity MIDI config: {len(velocity_midi_config)} layers")
        logging.info(f"Round-robin MIDI config: {len(roundrobin_midi_config)} layers")
        
        # Send initial MIDI setup messages (from sampling_midi or fallback to midi_interface)
        initial_config = {}
        if self.sampling_midi_config:
            initial_config = self.sampling_midi_config
        else:
            # Fallback to old config structure
            initial_config = self.midi_config
        
        if self.midi_controller:
            self.midi_controller.send_midi_setup(initial_config, channel)
        
        # Iterate through notes
        for note in range(start_note, end_note + 1, interval):
            # Iterate through velocity layers
            for vel_layer in range(self.velocity_layers):
                velocity = self.calculate_velocity_value(vel_layer, self.velocity_layers)
                
                # Apply velocity layer MIDI settings
                if self.midi_controller and velocity_midi_config:
                    self.midi_controller.apply_velocity_layer_midi(
                        vel_layer, velocity_midi_config, channel, self.midi_message_delay
                    )
                
                # Iterate through round-robin layers
                for rr_layer in range(self.roundrobin_layers):
                    # Apply round-robin layer MIDI settings
                    if self.midi_controller and roundrobin_midi_config:
                        self.midi_controller.apply_roundrobin_layer_midi(
                            rr_layer, roundrobin_midi_config, channel, self.midi_message_delay
                        )
                    
                    # Determine which channel to use for this note
                    if self.midi_controller:
                        note_channel = self.midi_controller.get_layer_channel(
                            vel_layer, rr_layer, velocity_midi_config, 
                            roundrobin_midi_config, channel
                        )
                    else:
                        note_channel = channel
                    
                    # Sample the note
                    audio = self.sample_note(note, velocity, note_channel, rr_layer)
                    
                    # Generate filename
                    filename = self.generate_sample_filename(note, velocity, rr_layer)
                    filepath = self.output_folder / filename
                    
                    # Prepare metadata
                    metadata = {
                        'note': note,
                        'velocity': velocity,
                        'velocity_layer': vel_layer,
                        'roundrobin_layer': rr_layer,
                        'samplerate': self.samplerate,
                        'bitdepth': self.bitdepth,
                        'channels': self.channels,
                        'duration': (self.hold_time + self.release_time) if self.test_mode else (len(audio) / self.samplerate if audio is not None else 0)
                    }
                    
                    # In test mode, still add to sample list for SFZ generation
                    if self.test_mode:
                        sample_list.append({'file': str(filepath), **metadata})
                    elif audio is not None:
                        # Store for potential patch normalization
                        self.recorded_samples.append((audio, metadata))
                        
                        # Save immediately if not doing patch normalization
                        if not self.patch_normalize:
                            self.save_wav_file(audio, filepath, metadata)
                            sample_list.append({'file': str(filepath), **metadata})
                        else:
                            sample_list.append({'audio': audio, 'file': str(filepath), **metadata})
                    
                    # Pause between samples
                    if self.pause_time > 0:
                        time.sleep(self.pause_time)
        
        # Apply patch normalization if enabled
        if self.patch_normalize and self.recorded_samples:
            self.apply_patch_normalization()
            
            # Save all normalized samples
            for sample_info in sample_list:
                if 'audio' in sample_info:
                    audio = sample_info.pop('audio')
                    filepath = Path(sample_info['file'])
                    metadata = {k: v for k, v in sample_info.items() if k != 'file'}
                    self.save_wav_file(audio, filepath, metadata)
        
        return sample_list
    
    def apply_patch_normalization(self, target_level: float = 0.95) -> None:
        """
        Normalize all recorded samples to the same peak level.
        
        Args:
            target_level: Target peak amplitude (0.0-1.0)
        """
        if not self.recorded_samples:
            return
        
        # Find global peak across all samples
        global_peak = max(np.abs(audio).max() for audio, _ in self.recorded_samples)
        
        if global_peak > 0:
            scale_factor = target_level / global_peak
            
            # Apply normalization to all samples
            for i, (audio, metadata) in enumerate(self.recorded_samples):
                self.recorded_samples[i] = (audio * scale_factor, metadata)
            
            logging.info(f"Patch normalization applied: global peak {global_peak:.3f} -> {target_level}")
    
    def generate_sfz(self, sample_list: List[Dict], output_path: Path = None) -> bool:
        """
        Generate SFZ mapping file for the sampled instrument.
        
        Args:
            sample_list: List of sample metadata dictionaries
            output_path: Output SFZ file path
            
        Returns:
            True if successful, False otherwise
        """
        if output_path is None:
            # SFZ file goes in the multisample folder
            output_path = self.multisample_folder / f"{self.multisample_name}.sfz"
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w') as f:
                f.write(f"// {self.multisample_name} - Generated by AutosamplerT\n")
                f.write(f"// Sample Rate: {self.samplerate} Hz\n")
                f.write(f"// Bit Depth: {self.bitdepth} bits\n\n")
                
                # Group samples by note and velocity
                samples_by_note = {}
                for sample in sample_list:
                    note = sample['note']
                    if note not in samples_by_note:
                        samples_by_note[note] = []
                    samples_by_note[note].append(sample)
                
                # Get the note range for key mapping
                all_notes = sorted(samples_by_note.keys())
                if not all_notes:
                    logging.warning("No samples to write to SFZ")
                    return True
                
                lowest_note = all_notes[0]
                highest_note = all_notes[-1]
                
                # Write regions
                for i, note in enumerate(all_notes):
                    note_samples = samples_by_note[note]
                    
                    # Calculate key range for this sample
                    # If only one sample, it covers the configured keyboard range
                    if len(all_notes) == 1:
                        note_lokey = self.lowest_note
                        note_hikey = self.highest_note
                    else:
                        # Lowest sample extends down to configured lowest_note
                        if i == 0:
                            note_lokey = self.lowest_note
                            note_hikey = (note + all_notes[i + 1]) // 2
                        # Highest sample extends up to configured highest_note
                        elif i == len(all_notes) - 1:
                            note_lokey = (all_notes[i - 1] + note) // 2 + 1
                            note_hikey = self.highest_note
                        # Middle samples split the range
                        else:
                            note_lokey = (all_notes[i - 1] + note) // 2 + 1
                            note_hikey = (note + all_notes[i + 1]) // 2
                    
                    # Sort by velocity
                    note_samples.sort(key=lambda x: x['velocity'])
                    
                    for j, sample in enumerate(note_samples):
                        f.write(f"<region>\n")
                        # Reference sample with samples subfolder
                        sample_name = Path(sample['file']).name
                        f.write(f"sample=samples/{sample_name}\n")
                        f.write(f"pitch_keycenter={note}\n")
                        f.write(f"lokey={note_lokey}\n")
                        f.write(f"hikey={note_hikey}\n")
                        
                        # Velocity ranges
                        if len(note_samples) > 1:
                            # Use custom split points if available
                            if self.velocity_layers_split is not None:
                                if j == 0:
                                    lovel = self.velocity_minimum
                                else:
                                    lovel = self.velocity_layers_split[j-1] + 1
                                
                                hivel = self.velocity_layers_split[j]
                            else:
                                # Default behavior: calculate midpoints
                                if j == 0:
                                    lovel = 0
                                else:
                                    prev_vel = note_samples[j-1]['velocity']
                                    curr_vel = sample['velocity']
                                    lovel = (prev_vel + curr_vel) // 2
                                
                                if j == len(note_samples) - 1:
                                    hivel = 127
                                else:
                                    curr_vel = sample['velocity']
                                    next_vel = note_samples[j+1]['velocity']
                                    hivel = (curr_vel + next_vel) // 2
                            
                            f.write(f"lovel={lovel}\n")
                            f.write(f"hivel={hivel}\n")
                        
                        # Round-robin
                        if sample.get('roundrobin_layer', 0) > 0 or self.roundrobin_layers > 1:
                            f.write(f"seq_length={self.roundrobin_layers}\n")
                            f.write(f"seq_position={sample['roundrobin_layer'] + 1}\n")
                        
                        f.write(f"\n")
                
            logging.info(f"SFZ file generated: {output_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to generate SFZ: {e}")
            return False
    
    def cleanup(self) -> None:
        """Close MIDI ports and clean up resources."""
        if self.midi_input_port:
            self.midi_input_port.close()
            logging.debug("MIDI input port closed")
        
        if self.midi_output_port:
            self.midi_output_port.close()
            logging.debug("MIDI output port closed")
    
    def check_output_folder(self) -> bool:
        """
        Check if output folder exists and prompt user for action.
        
        Returns:
            True to continue, False to abort
        """
        if self.multisample_folder.exists():
            # In test mode, just warn
            if self.test_mode:
                logging.warning(f"Multisample folder already exists: {self.multisample_folder}")
                logging.info("Test mode: Will overwrite existing files")
                return True
            
            print(f"\nWARNING: Multisample folder already exists: {self.multisample_folder}")
            print("This folder may contain samples from a previous session.")
            print("\nOptions:")
            print("  1) Delete folder and continue")
            print("  2) Use different name")
            print("  3) Cancel")
            
            while True:
                choice = input("\nSelect option (1-3): ").strip()
                
                if choice == '1':
                    # Delete folder
                    import shutil
                    try:
                        shutil.rmtree(self.multisample_folder)
                        logging.info(f"Deleted existing folder: {self.multisample_folder}")
                        return True
                    except Exception as e:
                        logging.error(f"Failed to delete folder: {e}")
                        print(f"Error deleting folder: {e}")
                        return False
                
                elif choice == '2':
                    # Ask for new name
                    new_name = input("Enter new multisample name: ").strip()
                    if new_name:
                        self.multisample_name = new_name
                        self.multisample_folder = self.base_output_folder / self.multisample_name
                        self.output_folder = self.multisample_folder / 'samples'
                        logging.info(f"Changed multisample name to: {self.multisample_name}")
                        # Check again recursively
                        return self.check_output_folder()
                    else:
                        print("Invalid name. Please try again.")
                
                elif choice == '3':
                    print("Cancelled by user")
                    return False
                
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
        
        return True
    
    def run(self) -> bool:
        """
        Main sampling workflow: setup, sample, generate output files.
        
        Returns:
            True if sampling completed successfully, False otherwise
        """
        try:
            # Setup
            logging.info("=== AutosamplerT Starting ===")
            
            # Check output folder
            if not self.check_output_folder():
                logging.info("Sampling cancelled")
                return False
            
            if not self.setup_audio():
                logging.error("Audio setup failed - aborting")
                return False
            
            if not self.setup_midi():
                logging.warning("MIDI setup failed - continuing without MIDI")
            
            # Parse note range
            note_range = self.midi_config.get('note_range', {})
            if isinstance(note_range, str):
                try:
                    note_range = json.loads(note_range)
                except:
                    note_range = {}
            
            start_note = note_range.get('start', 36)  # C2
            end_note = note_range.get('end', 96)      # C7
            interval = note_range.get('interval', 1)  # Chromatic
            
            # Get MIDI channel
            channels = self.midi_config.get('midi_channels', [0])
            if isinstance(channels, list):
                channel = channels[0] if channels else 0
            else:
                channel = 0
            
            logging.info(f"Sampling range: Note {start_note}-{end_note}, interval {interval}")
            logging.info(f"Velocity layers: {self.velocity_layers}, Round-robin: {self.roundrobin_layers}")
            
            # Sample the range
            sample_list = self.sample_range(start_note, end_note, interval, channel)
            
            logging.info(f"Sampling complete: {len(sample_list)} samples recorded")
            
            # Generate output format
            if self.output_format == 'sfz':
                self.generate_sfz(sample_list)
            
            logging.info("=== AutosamplerT Complete ===")
            return True
            
        except KeyboardInterrupt:
            logging.info("Sampling interrupted by user")
            return False
        except Exception as e:
            logging.error(f"Sampling failed: {e}", exc_info=True)
            return False
        finally:
            self.cleanup()


def main():
    """Example usage of AutoSampler."""
    import yaml
    
    # Load config
    config_path = Path(__file__).parent.parent / 'conf' / 'autosamplerT_config.yaml'
    
    if not config_path.exists():
        logging.error(f"Config file not found: {config_path}")
        return
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Create and run sampler
    sampler = AutoSampler(config)
    success = sampler.run()
    
    if success:
        logging.info("Sampling completed successfully")
    else:
        logging.error("Sampling failed")


if __name__ == "__main__":
    main()
