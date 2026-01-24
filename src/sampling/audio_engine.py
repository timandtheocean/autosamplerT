"""
Audio recording and processing engine.

This module provides AudioEngine class that handles:
- Audio device configuration
- Recording with ASIO multi-channel support
- Silence detection and trimming
- Audio normalization (per-sample and patch-level)
"""

import os
# Enable ASIO support in sounddevice (must be set before importing sounddevice)
os.environ["SD_ENABLE_ASIO"] = "1"

import logging
from typing import Optional, Tuple, List, Dict
import numpy as np
import sounddevice as sd


def _update_visual_monitor(monitor: dict, indata: np.ndarray) -> None:
    """
    Update visual monitoring display with current audio levels and pitch.
    
    Args:
        monitor: Monitor state dictionary with pitch detector and display state
        indata: Audio input data (frames x channels)
    """
    import time
    
    # Update timestamp
    monitor['last_update'] = time.time()
    
    # Calculate levels for left and right channels
    if indata.shape[1] > 1:
        left_data = indata[:, 0]
        right_data = indata[:, 1]
        
        rms_l = np.sqrt(np.mean(left_data ** 2))
        rms_r = np.sqrt(np.mean(right_data ** 2))
        
        level_db_l = 20 * np.log10(rms_l) if rms_l > 0 else -100.0
        level_db_r = 20 * np.log10(rms_r) if rms_r > 0 else -100.0
        
        # Smooth levels
        monitor['current_level_db_l'] = (monitor['level_smoothing'] * monitor['current_level_db_l'] + 
                                         (1 - monitor['level_smoothing']) * level_db_l)
        monitor['current_level_db_r'] = (monitor['level_smoothing'] * monitor['current_level_db_r'] + 
                                         (1 - monitor['level_smoothing']) * level_db_r)
        
        # Use mono mix for pitch detection
        mono_data = np.mean(indata, axis=1)
    else:
        mono_data = indata[:, 0]
        rms = np.sqrt(np.mean(mono_data ** 2))
        level_db = 20 * np.log10(rms) if rms > 0 else -100.0
        monitor['current_level_db_l'] = monitor['current_level_db_r'] = (
            monitor['level_smoothing'] * monitor['current_level_db_l'] + 
            (1 - monitor['level_smoothing']) * level_db
        )
    
    # Pitch detection
    frequency = monitor['pitch_detector'].detect_pitch(mono_data)
    if frequency:
        note, midi_note, cents = monitor['pitch_detector'].frequency_to_note(frequency)
        monitor['current_frequency'] = frequency
        monitor['current_note'] = note
        monitor['current_cents'] = cents
    else:
        monitor['current_frequency'] = None
        monitor['current_note'] = None
        monitor['current_cents'] = 0.0
    
    # Build compact display string (single line, overwritten each update)
    bar_width = 20
    
    # Left channel bar
    level_l_normalized = max(0, min(1, (monitor['current_level_db_l'] + 60) / 60))
    filled_l = int(level_l_normalized * bar_width)
    bar_l = "█" * filled_l + "░" * (bar_width - filled_l)
    
    # Right channel bar
    level_r_normalized = max(0, min(1, (monitor['current_level_db_r'] + 60) / 60))
    filled_r = int(level_r_normalized * bar_width)
    bar_r = "█" * filled_r + "░" * (bar_width - filled_r)
    
    # Pitch display
    if monitor['current_note'] and monitor['current_frequency']:
        pitch_str = f"{monitor['current_note']:>3} {monitor['current_frequency']:5.1f}Hz {monitor['current_cents']:+4.0f}¢"
    else:
        pitch_str = " --  ---.-Hz   --¢"
    
    # Store display string for external use
    monitor['display_str'] = pitch_str
    monitor['display_ready'] = True


class AudioEngine:
    """
    Handles all audio recording and processing operations.

    Supports:
    - ASIO multi-channel device selection
    - Stereo and mono recording
    - Audio playback through selected output channels
    - Channel offset for multi-channel interfaces
    - Silence detection and trimming
    - Per-sample and patch-level normalization
    """

    def __init__(self, audio_config: Dict, test_mode: bool = False):
        """
        Initialize the audio engine.

        Args:
            audio_config: Audio configuration dictionary
            test_mode: If True, skip actual recording (for testing)
        """
        self.samplerate = audio_config.get('samplerate', 44100)
        self.bitdepth = audio_config.get('bitdepth', 24)
        self.mono_stereo = audio_config.get('mono_stereo', 'stereo')
        self.channels = 2 if self.mono_stereo == 'stereo' else 1
        self.mono_channel = audio_config.get('mono_channel', 0)  # 0=left, 1=right

        # Convert user-friendly input_channels (e.g., "3-4") to internal channel_offset
        input_channels = audio_config.get('input_channels', audio_config.get('channel_offset'))
        if isinstance(input_channels, str) and '-' in input_channels:
            # Parse "3-4" format to offset (e.g., "3-4" -> 2, "1-2" -> 0)
            first_channel = int(input_channels.split('-')[0])
            self.channel_offset = first_channel - 1
        elif isinstance(input_channels, int):
            # Direct offset value (backward compatibility)
            self.channel_offset = input_channels
        else:
            self.channel_offset = 0  # Default to channels 1-2

        # Convert user-friendly output_channels (e.g., "1-2") to internal output_channel_offset
        # If not specified, use same as input channels for monitoring
        output_channels = audio_config.get('output_channels', input_channels)
        if isinstance(output_channels, str) and '-' in output_channels:
            # Parse "1-2" format to offset
            first_channel = int(output_channels.split('-')[0])
            self.output_channel_offset = first_channel - 1
        elif isinstance(output_channels, int):
            # Direct offset value
            self.output_channel_offset = output_channels
        else:
            self.output_channel_offset = self.channel_offset  # Default to same as input

        # Convert user-friendly monitor_channels (e.g., "1-2") for real-time monitoring
        # If not specified, use output_channels
        monitor_channels = audio_config.get('monitor_channels', output_channels)
        if isinstance(monitor_channels, str) and '-' in monitor_channels:
            # Parse "1-2" format to offset
            first_channel = int(monitor_channels.split('-')[0])
            self.monitor_channel_offset = first_channel - 1
        elif isinstance(monitor_channels, int):
            # Direct offset value
            self.monitor_channel_offset = monitor_channels
        else:
            self.monitor_channel_offset = self.output_channel_offset  # Default to same as output

        self.input_device = audio_config.get('input_device_index')
        self.output_device = audio_config.get('output_device_index')

        self.silence_detection = audio_config.get('silence_detection', True)
        self.gain_db = audio_config.get('gain_db', 0.0)  # Gain in dB
        
        # Buffer size for ASIO streams (None = use driver default)
        # Common values: 128, 256, 512, 1024, 2048
        # Larger = more stable but higher latency
        self.blocksize = audio_config.get('blocksize', None)
        if self.blocksize is not None:
            logging.info(f"Audio blocksize set to {self.blocksize} samples")

        self.test_mode = test_mode

        # Storage for patch normalization
        self.recorded_samples: List[Tuple[np.ndarray, Dict]] = []

    def setup(self) -> bool:
        """
        Configure audio devices and verify settings.

        Returns:
            True if audio setup successful, False otherwise
        """
        try:
            # Note: We do NOT set sd.default.device here because it can conflict with
            # ASIO AsioSettings. Instead, we pass device explicitly to sd.rec()
            if self.input_device is not None and self.output_device is not None:
                logging.info(f"Audio devices configured: IN={self.input_device}, "
                           f"OUT={self.output_device}")
            else:
                logging.warning("Audio devices not configured - using system defaults")

            # Set default sample rate (this is safe)
            sd.default.samplerate = self.samplerate
            logging.info(f"Sample rate: {self.samplerate} Hz")

            # Verify bit depth
            if self.bitdepth not in [16, 24, 32]:
                logging.error(f"Invalid bit depth: {self.bitdepth}")
                return False

            logging.info(f"Bit depth: {self.bitdepth} bits")
            if self.channels == 2:
                if self.channel_offset > 0:
                    logging.info(f"Channels: 2 (stereo, offset {self.channel_offset}: "
                               f"channels {self.channel_offset}-{self.channel_offset+1})")
                else:
                    logging.info("Channels: 2 (stereo)")
            else:
                channel_name = 'left' if self.mono_channel == 0 else 'right'
                if self.channel_offset > 0:
                    actual_channel = self.channel_offset + self.mono_channel
                    logging.info(f"Channels: 1 (mono, using {channel_name} channel from "
                               f"offset {self.channel_offset}, actual channel {actual_channel})")
                else:
                    logging.info(f"Channels: 1 (mono, using {channel_name} channel)")

            return True
        except Exception as e:
            logging.error(f"Audio setup failed: {e}")
            return False

    def record(self, duration: float) -> Optional[np.ndarray]:
        """
        Record audio for the specified duration.

        Args:
            duration: Recording duration in seconds

        Returns:
            NumPy array of recorded audio samples, or None if recording failed
        """
        if self.test_mode:
            channel_info = ('stereo' if self.mono_stereo == 'stereo'
                          else f"mono ({['left', 'right'][self.mono_channel]})")
            logging.info(f"[TEST MODE] Recording {duration}s of silent audio ({channel_info})")
            # Create realistic noise floor simulation instead of perfect silence
            num_samples = int(duration * self.samplerate)
            # Simulate typical audio interface noise floor around -70dB
            noise_level = 10 ** (-70 / 20)  # -70dB in linear scale
            noise_audio = np.random.normal(0, noise_level, (num_samples, self.channels)).astype('float32')
            return noise_audio

        try:
            logging.debug(f"Recording {duration}s at {self.samplerate}Hz, {self.channels} channels")

            # Detect device channel count and host API
            if self.input_device is not None:
                device_info = sd.query_devices(self.input_device)
            else:
                # When input_device is None, get the default input device
                device_info = sd.query_devices(kind='input')
            
            device_channels = device_info['max_input_channels']
            host_apis = sd.query_hostapis()
            host_api_name = host_apis[device_info['hostapi']]['name']
            is_asio = 'ASIO' in host_api_name

            logging.debug(f"Device: {device_info['name']}, Host API: {host_api_name}")
            logging.debug(f"Device has {device_channels} input channels available")

            # Determine channel selection strategy
            extra_settings = None
            if is_asio and device_channels > 2:
                # ASIO multi-channel device: use AsioSettings for channel selection
                if self.mono_stereo == 'stereo':
                    # Select stereo pair based on channel_offset
                    channel_selectors = [self.channel_offset, self.channel_offset + 1]
                    record_channels = 2
                    logging.info(f"ASIO: Selecting channels {channel_selectors} (stereo pair)")
                else:
                    # Select single channel for mono
                    channel_selectors = [self.channel_offset + self.mono_channel]
                    record_channels = 1
                    logging.info(f"ASIO: Selecting channel {channel_selectors[0]} (mono)")

                extra_settings = sd.AsioSettings(channel_selectors=channel_selectors)
            elif self.mono_stereo == 'mono':
                # Non-ASIO in mono mode: record stereo then extract one channel
                record_channels = 2
            else:
                # Standard stereo recording
                record_channels = self.channels

            # Record audio
            frames = int(duration * self.samplerate)
            logging.info(f"Starting recording: {frames} samples ({duration:.1f}s), "
                        f"{record_channels} channels")

            # Explicitly pass device and extra_settings for ASIO compatibility
            recording = sd.rec(
                frames,
                samplerate=self.samplerate,
                channels=record_channels,
                dtype='float32',
                device=self.input_device,
                extra_settings=extra_settings,
                blocksize=self.blocksize
            )
            
            # Wait for recording to complete
            sd.wait()
            logging.info(f"Recording completed: {len(recording)} samples")

            # If mono output is requested, extract the specified channel
            if self.mono_stereo == 'mono' and record_channels == 2:
                channel_name = 'left' if self.mono_channel == 0 else 'right'
                recording = recording[:, self.mono_channel:self.mono_channel+1]
                logging.debug(f"Extracted {channel_name} channel for mono recording")

            # Gain is now applied in postprocessing, not during recording
            return recording
        except Exception as e:
            logging.error(f"Audio recording failed: {e}")
            return None

    def play(self, audio_data: np.ndarray, blocking: bool = True) -> bool:
        """
        Play audio through the configured output device and channels.

        Args:
            audio_data: Audio data to play (numpy array)
            blocking: If True, wait for playback to complete

        Returns:
            True if playback started successfully, False otherwise
        """
        if self.test_mode:
            logging.info(f"[TEST MODE] Would play {len(audio_data)} samples")
            return True

        try:
            # Ensure audio is in correct format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Get device info for ASIO detection
            device_info = sd.query_devices(self.output_device)
            device_channels = device_info['max_output_channels']
            host_apis = sd.query_hostapis()
            host_api_name = host_apis[device_info['hostapi']]['name']
            is_asio = 'ASIO' in host_api_name

            logging.debug(f"Playback device: {device_info['name']}, Host API: {host_api_name}")
            logging.debug(f"Device has {device_channels} output channels available")

            # Determine channel routing strategy
            extra_settings = None
            play_channels = audio_data.shape[1] if len(audio_data.shape) > 1 else 1

            if is_asio and device_channels > 2:
                # ASIO multi-channel device: use AsioSettings for channel selection
                if play_channels == 2:
                    # Stereo playback - route to selected channel pair
                    channel_selectors = [self.output_channel_offset, self.output_channel_offset + 1]
                    logging.info(f"ASIO: Playing stereo to channels {channel_selectors}")
                else:
                    # Mono playback - route to left channel of selected pair
                    channel_selectors = [self.output_channel_offset]
                    logging.info(f"ASIO: Playing mono to channel {channel_selectors[0]}")
                
                extra_settings = sd.AsioSettings(channel_selectors=channel_selectors)

            # Play audio
            logging.info(f"Playing {len(audio_data)} samples ({len(audio_data)/self.samplerate:.2f}s)")
            
            sd.play(
                audio_data,
                samplerate=self.samplerate,
                device=self.output_device,
                extra_settings=extra_settings,
                blocking=False
            )

            # Wait for playback if blocking
            if blocking:
                sd.wait()
                logging.debug("Playback complete")

            return True

        except Exception as e:
            logging.error(f"Playback failed: {e}")
            return False

    def stop_playback(self) -> None:
        """Stop any ongoing playback."""
        try:
            sd.stop()
            logging.debug("Playback stopped")
        except Exception as e:
            logging.warning(f"Failed to stop playback: {e}")
    
    def cleanup(self) -> None:
        """Clean up audio resources and release ASIO devices."""
        try:
            # Stop any ongoing audio operations
            sd.stop()
            
            # Reset default device settings (helps with ASIO)
            sd.default.reset()
            
            # Small delay to let ASIO driver release completely
            import time
            time.sleep(0.1)
            
            logging.debug("Audio engine cleanup completed - ASIO device should be released")
        except Exception as e:
            logging.warning(f"Audio engine cleanup failed: {e}")

    def record_with_monitoring(self, duration: float) -> Optional[np.ndarray]:
        """
        Record audio with real-time monitoring (duplex mode).
        Audio input is routed directly to output while recording.

        Args:
            duration: Recording duration in seconds

        Returns:
            NumPy array of recorded audio samples, or None if recording failed
        """
        if self.test_mode:
            logging.info(f"[TEST MODE] Recording with monitoring: {duration}s")
            num_samples = int(duration * self.samplerate)
            noise_level = 10 ** (-70 / 20)
            noise_audio = np.random.normal(0, noise_level, (num_samples, self.channels)).astype('float32')
            return noise_audio

        try:
            # Get device info for ASIO detection
            device_info = sd.query_devices(self.input_device)
            device_channels = device_info['max_input_channels']
            host_apis = sd.query_hostapis()
            host_api_name = host_apis[device_info['hostapi']]['name']
            is_asio = 'ASIO' in host_api_name

            logging.info(f"Recording with real-time monitoring: {duration}s")
            logging.debug(f"Device: {device_info['name']}, Host API: {host_api_name}")

            # Prepare for recording
            frames = int(duration * self.samplerate)
            recording = np.zeros((frames, self.channels), dtype='float32')
            current_frame = [0]
            current_frame = [0]

            # For ASIO with specific channel routing, we use a duplex stream approach
            # with separate channel selectors for input and output
            if is_asio and device_channels > 2:
                logging.info(f"ASIO monitoring: Input channels {self.channel_offset}-{self.channel_offset+1}, "
                           f"Monitor output channels {self.monitor_channel_offset}-{self.monitor_channel_offset+1}")
                
                # For ASIO duplex monitoring, we need proper channel setup
                if self.mono_stereo == 'stereo':
                    input_selectors = [self.channel_offset, self.channel_offset + 1]
                    output_selectors = [self.monitor_channel_offset, self.monitor_channel_offset + 1]
                    stream_channels = 2
                else:
                    input_selectors = [self.channel_offset + self.mono_channel]
                    output_selectors = [self.monitor_channel_offset]
                    stream_channels = 1
                
                # Create separate ASIO settings for input and output
                input_asio_settings = sd.AsioSettings(channel_selectors=input_selectors)
                output_asio_settings = sd.AsioSettings(channel_selectors=output_selectors)
                
                logging.debug(f"ASIO input channels: {input_selectors}, output channels: {output_selectors}")
                
                def callback(indata, outdata, frames, time_info, status):
                    if status:
                        logging.warning(f"Stream status: {status}")
                    
                    # Make a copy to prevent interference between input and output
                    audio_data = indata.copy()
                    
                    # Copy to recording buffer
                    chunksize = min(len(audio_data), len(recording) - current_frame[0])
                    if chunksize > 0:
                        recording[current_frame[0]:current_frame[0] + chunksize] = audio_data[:chunksize]
                        current_frame[0] += chunksize
                    
                    # Route to output for monitoring
                    outdata[:] = audio_data
                
                # Create duplex stream with separate input/output settings
                stream = sd.Stream(
                    samplerate=self.samplerate,
                    channels=(stream_channels, stream_channels),  # (input_channels, output_channels)
                    dtype='float32',
                    callback=callback,
                    device=(self.input_device, self.output_device),
                    extra_settings=(input_asio_settings, output_asio_settings),
                    blocksize=self.blocksize
                )
            else:
                # Standard (non-ASIO) duplex stream
                logging.info(f"Standard duplex monitoring: {self.channels} channels")
                
                def callback(indata, outdata, frames, time_info, status):
                    if status:
                        logging.warning(f"Stream status: {status}")
                    
                    # Make a copy to prevent interference between input and output
                    audio_data = indata.copy()
                    
                    # Copy to recording buffer
                    chunksize = min(len(audio_data), len(recording) - current_frame[0])
                    if chunksize > 0:
                        recording[current_frame[0]:current_frame[0] + chunksize] = audio_data[:chunksize]
                        current_frame[0] += chunksize
                    
                    # Route to output for monitoring
                    outdata[:] = audio_data
                
                stream = sd.Stream(
                    samplerate=self.samplerate,
                    channels=self.channels,
                    dtype='float32',
                    callback=callback,
                    device=(self.input_device, self.output_device),
                    blocksize=self.blocksize
                )

            with stream:
                sd.sleep(int(duration * 1000))  # Sleep in milliseconds

            logging.info(f"Recording complete: {current_frame[0]} samples captured")
            
            # Return the captured audio
            return recording[:current_frame[0]]

        except Exception as e:
            logging.error(f"Recording with monitoring failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def record_samples(self, duration: float, apply_postprocessing: bool = True) -> Optional[np.ndarray]:
        """
        Record audio samples with optional post-processing.
        This is the method called by wavetable sampler.

        Args:
            duration: Duration in seconds
            apply_postprocessing: Whether to apply silence detection and normalization

        Returns:
            Recorded audio data as numpy array, or None if failed
        """
        # Record the audio
        audio_data = self.record(duration)
        if audio_data is None:
            return None

        # Apply post-processing if requested
        if apply_postprocessing:
            if self.silence_detection:
                # Basic silence detection - find start and end of audio
                audio_data = self._trim_silence(audio_data)

            if self.sample_normalize:
                # Normalize to prevent clipping
                max_val = np.max(np.abs(audio_data))
                if max_val > 0:
                    audio_data = audio_data / max_val * 0.95  # Leave some headroom

        return audio_data

    def _trim_silence(self, audio_data: np.ndarray, threshold: float = 0.01) -> np.ndarray:
        """
        Trim silence from beginning and end of audio data.

        Args:
            audio_data: Audio data to trim
            threshold: Silence threshold (0.0 to 1.0)

        Returns:
            Trimmed audio data
        """
        if len(audio_data) == 0:
            return audio_data

        # Calculate RMS for each frame
        audio_abs = np.abs(audio_data)
        if len(audio_abs.shape) > 1:
            audio_abs = np.max(audio_abs, axis=1)  # Convert to mono for analysis

        # Find start and end of audio above threshold
        above_threshold = audio_abs > threshold
        if not np.any(above_threshold):
            # All silence, return a small portion from the middle
            mid_point = len(audio_data) // 2
            return audio_data[mid_point:mid_point + 1024]

        start_idx = np.argmax(above_threshold)
        end_idx = len(above_threshold) - np.argmax(above_threshold[::-1]) - 1

        # Add some padding
        padding = int(0.1 * self.samplerate)  # 100ms padding
        start_idx = max(0, start_idx - padding)
        end_idx = min(len(audio_data), end_idx + padding)

        return audio_data[start_idx:end_idx]

    def save_audio(self, audio_data: np.ndarray, filepath: str, metadata: Dict = None) -> bool:
        """
        Save audio data to WAV file with metadata.
        This is the method called by wavetable sampler.

        Args:
            audio_data: Audio data to save
            filepath: Output file path
            metadata: Optional metadata dictionary

        Returns:
            True if save successful, False otherwise
        """
        try:
            from pathlib import Path
            import soundfile as sf
            
            if self.test_mode:
                logging.info(f"[TEST MODE] Would save audio to {filepath}")
                return True

            # Ensure output directory exists
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)

            # Save using soundfile (supports metadata)
            sf.write(
                filepath,
                audio_data,
                samplerate=self.samplerate,
                subtype={
                    16: 'PCM_16',
                    24: 'PCM_24', 
                    32: 'PCM_32'
                }.get(self.bitdepth, 'PCM_24')
            )
            
            logging.info(f"Audio saved: {filepath}")
            return True

        except Exception as e:
            logging.error(f"Failed to save audio to {filepath}: {e}")
            return False

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

    def apply_gain(self, audio: np.ndarray, gain_db: float = 0.0) -> np.ndarray:
        """
        Apply gain to audio in dB.

        Args:
            audio: Audio data as NumPy array
            gain_db: Gain in dB (e.g., 10.0 for +10dB boost, -6.0 for -6dB reduction)

        Returns:
            Audio with gain applied
        """
        if gain_db == 0.0:
            return audio
        
        # Convert dB to linear gain (0 dB = 1.0, +6 dB = 2.0, -6 dB = 0.5)
        gain_linear = 10 ** (gain_db / 20.0)
        
        gained_audio = audio * gain_linear
        logging.debug(f"Applied gain: {gain_db:.1f}dB (linear: {gain_linear:.3f})")
        return gained_audio

    def normalize(self, audio: np.ndarray, target_db: float = -16.0) -> np.ndarray:
        """
        Apply gain to audio (normalization disabled - use gain parameter instead).

        Args:
            audio: Audio data as NumPy array
            target_db: Not used (kept for compatibility)

        Returns:
            Audio with gain applied
        """
        # Apply gain (gain_db is converted to linear multiplier)
        if self.gain_db != 0.0:
            gain_multiplier = 10 ** (self.gain_db / 20.0)
            gained = audio * gain_multiplier
            logging.debug(f"Applied gain: {self.gain_db:.1f}dB (multiplier: {gain_multiplier:.3f})")
            return gained
        return audio

    def apply_patch_normalization(self, samples: List[Tuple[np.ndarray, Dict]],
                                  target_level: float = 0.95) -> List[Tuple[np.ndarray, Dict]]:
        """
        Normalize all samples to the same peak level (patch-level normalization).

        Args:
            samples: List of (audio, metadata) tuples
            target_level: Target peak amplitude (0.0-1.0)

        Returns:
            List of normalized (audio, metadata) tuples
        """
        if not samples:
            return samples

        # Find global peak across all samples
        global_peak = max(np.abs(audio).max() for audio, _ in samples)

        if global_peak > 0:
            scale_factor = target_level / global_peak

            # Apply normalization to all samples
            normalized_samples = [(audio * scale_factor, metadata)
                                 for audio, metadata in samples]

            logging.info(f"Patch normalization applied: global peak {global_peak:.3f} "
                        f"-> {target_level}")
            return normalized_samples

        return samples
