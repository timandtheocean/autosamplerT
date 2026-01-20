"""
Audio recording and processing engine.

This module provides AudioEngine class that handles:
- Audio device configuration
- Recording with ASIO multi-channel support
- Silence detection and trimming
- Audio normalization (per-sample and patch-level)
"""

import logging
from typing import Optional, Tuple, List, Dict
import numpy as np
import sounddevice as sd


class AudioEngine:
    """
    Handles all audio recording and processing operations.

    Supports:
    - ASIO multi-channel device selection
    - Stereo and mono recording
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

        self.input_device = audio_config.get('input_device_index')
        self.output_device = audio_config.get('output_device_index')

        self.silence_detection = audio_config.get('silence_detection', True)
        self.sample_normalize = audio_config.get('sample_normalize', True)
        self.gain = audio_config.get('gain', 1.0)

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
            device_info = sd.query_devices(self.input_device)
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
            logging.info(f"Starting recording: {frames} frames ({duration:.1f}s), "
                        f"{record_channels} channels")

            # Explicitly pass device and extra_settings for ASIO compatibility
            recording = sd.rec(
                frames,
                samplerate=self.samplerate,
                channels=record_channels,
                dtype='float32',
                device=self.input_device,
                extra_settings=extra_settings,
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
                sd.stop()  # Stop the stream on abort
                return None
            except Exception as e:
                logging.error(f"Recording wait failed: {e}")
                sd.stop()  # Stop the stream on error
                return None
            finally:
                # Always stop the stream to ensure clean closure and prevent clicks
                sd.stop()

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

    def normalize(self, audio: np.ndarray, target_level: float = 0.95) -> np.ndarray:
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
