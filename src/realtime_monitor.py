"""
Real-time Audio Monitoring System
Provides live signal level, clipping detection, and pitch analysis for AutosamplerT.

Features:
- Real-time signal level display with dB metering
- Clipping detection and warning
- Note detection with cents offset
- Console-based visualization
- Integration with sampling workflow
"""

import numpy as np
import sounddevice as sd
import threading
import time
import logging
from typing import Optional, Tuple, Callable
import math
from scipy import signal


class PitchDetector:
    """Autocorrelation-based pitch detection for musical note identification."""
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.min_freq = 80.0    # Lowest note to detect (E2)
        self.max_freq = 2000.0  # Highest fundamental to detect
        self.min_period = int(sample_rate / self.max_freq)
        self.max_period = int(sample_rate / self.min_freq)
        
        # Create high-pass filter to remove frequencies below 70 Hz
        # This prevents false subharmonic detections
        nyquist = sample_rate / 2
        cutoff = 70.0  # Hz
        self.highpass_b, self.highpass_a = signal.butter(4, cutoff / nyquist, btype='high')
        self.filter_state = None
        
        # Calibration: Adjust A4 reference to match professional tuners
        # Based on comparison with Korg tuner - if C4 shows -18¢, need to lower reference
        self.A4_calibration = 440.5  # Lowered from 443.3 to correct for -18¢ reading
    
    def detect_pitch(self, audio_chunk: np.ndarray) -> Optional[float]:
        """
        Detect fundamental frequency using simple FFT-based method.
        Based on the tuner algorithm - finds the dominant frequency directly.
        
        Args:
            audio_chunk: Audio samples (float32, mono)
            
        Returns:
            Detected frequency in Hz, or None if no pitch detected
        """
        if len(audio_chunk) < 512:
            return None
        
        # Use larger chunk size for better frequency resolution
        # For cents accuracy, we need good frequency resolution
        chunk_size = min(4096, len(audio_chunk))  # Increased from 2048 to 4096
        chunk = audio_chunk[:chunk_size]
        
        # Apply high-pass filter to remove problematic low frequencies
        try:
            if self.filter_state is None:
                # Initialize filter state
                chunk_filtered, self.filter_state = signal.lfilter(
                    self.highpass_b, self.highpass_a, chunk, zi=signal.lfilter_zi(self.highpass_b, self.highpass_a) * chunk[0])
            else:
                chunk_filtered, self.filter_state = signal.lfilter(
                    self.highpass_b, self.highpass_a, chunk, zi=self.filter_state)
        except:
            # If filtering fails, use original chunk
            chunk_filtered = chunk
        
        # Calculate RMS for signal strength check
        rms = np.sqrt(np.mean(chunk_filtered ** 2))
        if rms < 0.001:  # Too quiet - equivalent to about -60dB
            return None
        
        # Apply Hanning window to reduce spectral leakage  
        windowed_data = chunk_filtered * np.hanning(len(chunk_filtered))
        
        # Compute FFT - use real FFT for efficiency
        fft_result = np.fft.rfft(windowed_data)
        fft_magnitude = np.abs(fft_result)
        
        # Get frequency bins
        freqs = np.fft.rfftfreq(len(windowed_data), 1.0 / self.sample_rate)
        
        # Limit to musical frequency range (70-2000 Hz) to avoid false detections
        min_bin = max(1, int(70 * len(windowed_data) / self.sample_rate))  # Skip DC
        max_bin = min(len(fft_magnitude), int(2000 * len(windowed_data) / self.sample_rate))
        
        if max_bin <= min_bin:
            return None
        
        # Find the bin with maximum magnitude in the musical range
        musical_range = slice(min_bin, max_bin)
        peak_idx = np.argmax(fft_magnitude[musical_range])
        actual_peak_idx = peak_idx + min_bin
        
        # Get the dominant frequency
        dominant_freq = freqs[actual_peak_idx]
        peak_magnitude = fft_magnitude[actual_peak_idx]
        
        # Apply simple parabolic interpolation for sub-bin frequency resolution
        if 1 <= peak_idx < len(fft_magnitude[musical_range]) - 1:
            # Get neighboring bins for interpolation
            y_prev = fft_magnitude[actual_peak_idx - 1]
            y_curr = fft_magnitude[actual_peak_idx] 
            y_next = fft_magnitude[actual_peak_idx + 1]
            
            # Simple parabolic interpolation
            if y_prev > 0 and y_curr > 0 and y_next > 0:
                # Calculate offset using standard parabolic formula
                x_offset = 0.5 * (y_prev - y_next) / (y_prev - 2*y_curr + y_next)
                # Limit offset to reasonable range  
                x_offset = max(-0.5, min(0.5, x_offset))
                
                if abs(x_offset) > 0.01:  # Only apply if significant
                    # Calculate interpolated frequency
                    freq_resolution = freqs[1] - freqs[0] if len(freqs) > 1 else 1.0
                    interpolated_freq = dominant_freq + x_offset * freq_resolution
                    dominant_freq = interpolated_freq
        
        # Check signal strength - peak should be significant above noise floor
        noise_floor = np.median(fft_magnitude[musical_range])
        signal_strength = peak_magnitude / (noise_floor + 1e-10)
        
        if signal_strength < 3.0:  # Peak must be at least 3x above noise
            return None
        
        # Ensure frequency is in reasonable range
        if 70 <= dominant_freq <= 2000:
            return dominant_freq
        
        return None
    
    def frequency_to_note(self, frequency: float) -> Tuple[str, int, float]:
        """
        Convert frequency to musical note with cents offset.
        
        Args:
            frequency: Frequency in Hz
            
        Returns:
            Tuple of (note_name, midi_note_number, cents_offset)
        """
        # Use calibrated A4 reference - MIDI note 69
        A4_freq = self.A4_calibration
        A4_midi = 69
        
        # Calculate MIDI note number (float) - keep full precision
        # Use more precise calculation
        midi_float = A4_midi + (12.0 * math.log2(frequency / A4_freq))
        midi_note = round(midi_float)
        
        # Calculate cents offset with high precision
        cents = (midi_float - midi_note) * 100.0
        
        # Convert MIDI to note name
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note_name = note_names[midi_note % 12] + str(octave)
        
        # Calculate theoretical frequency for this MIDI note for comparison
        theoretical_freq = A4_freq * (2 ** ((midi_note - A4_midi) / 12.0))
        
        return note_name, midi_note, cents


class RealtimeAudioMonitor:
    """Real-time audio monitoring with level metering, clipping detection, and pitch analysis."""
    
    def __init__(self, device_index: int, sample_rate: int = 44100, 
                 channels: int = 1, chunk_size: int = 1024,
                 channel_offset: int = 0):
        """
        Initialize real-time audio monitor.
        
        Args:
            device_index: Audio input device index
            sample_rate: Audio sample rate in Hz
            channels: Number of input channels 
            chunk_size: Audio chunk size for processing
            channel_offset: Channel offset for multi-channel interfaces
        """
        self.device_index = device_index
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.channel_offset = channel_offset
        
        # Store channel selectors for display purposes
        self.channel_selectors = None
        self.is_asio = False
        
        self.pitch_detector = PitchDetector(sample_rate)
        
        # Monitoring state
        self.is_monitoring = False
        self.stream = None
        self.display_thread = None
        self.audio_thread = None
        self.stop_event = threading.Event()
        
        # Real-time data (thread-safe with simple assignment)
        self.current_level_db = -60.0
        self.current_frequency = None
        self.current_note = None
        self.current_cents = 0.0
        self.is_clipping = False
        self.peak_hold_db = -60.0
        self.peak_hold_time = 0
        
        # Stereo monitoring
        self.current_level_db_l = -60.0
        self.current_level_db_r = -60.0
        self.peak_hold_db_l = -60.0
        self.peak_hold_db_r = -60.0
        self.peak_hold_time_l = 0
        self.peak_hold_time_r = 0
        
        # Configuration
        self.clipping_threshold = 0.95  # -0.4dB
        self.peak_hold_duration = 30    # Frames to hold peak
        self.level_smoothing = 0.8      # Exponential smoothing factor
        
        # Frequency smoothing for stable cents display
        self.freq_smoothing = 0.7       # Exponential smoothing for frequency
        self.last_frequency = None      # For smoothing
        
    def calibrate_tuner(self, reference_note: str, reference_freq: float, expected_cents: float):
        """
        Calibrate the tuner based on a reference frequency.
        
        Args:
            reference_note: Note name (e.g., "A4", "C4")  
            reference_freq: Actual frequency being played
            expected_cents: What the cents should read (from your Korg tuner)
        """
        # Calculate what A4 frequency would give us the expected cents
        if reference_note == "A4":
            # For A4, adjust the calibration directly
            # If A4=440 shows +15¢ but should show +2¢, we need to lower the reference
            cents_error = expected_cents - self.frequency_to_note(reference_freq)[2]
            freq_correction = reference_freq * (2 ** (-cents_error / 1200))
            self.pitch_detector.A4_calibration = freq_correction
            logging.info(f"Calibrated A4 reference: {freq_correction:.3f}Hz (was 440.0Hz)")
        else:
            # For other notes, work backwards to find the A4 that would work
            current_cents = self.frequency_to_note(reference_freq)[2] 
            cents_error = current_cents - expected_cents
            # Adjust A4 reference to correct the error
            self.pitch_detector.A4_calibration += (cents_error / 1200) * 440.0
            logging.info(f"Calibrated for {reference_note}: A4 = {self.pitch_detector.A4_calibration:.3f}Hz")
        
    def _audio_callback(self, indata, frames, time, status):
        """Audio callback for processing incoming audio data."""
        if status:
            logging.warning(f"Audio callback status: {status}")
        

            
        # Process stereo channels separately for display
        if indata.shape[1] > 1:  # Multi-channel input
            left_data = indata[:, 0]
            right_data = indata[:, 1]
            
            # Calculate RMS levels for both channels
            rms_l = np.sqrt(np.mean(left_data ** 2))
            rms_r = np.sqrt(np.mean(right_data ** 2))
            
            level_db_l = 20 * np.log10(rms_l) if rms_l > 0 else -100.0
            level_db_r = 20 * np.log10(rms_r) if rms_r > 0 else -100.0
            
            # Smooth the level displays
            self.current_level_db_l = (self.level_smoothing * self.current_level_db_l + 
                                      (1 - self.level_smoothing) * level_db_l)
            self.current_level_db_r = (self.level_smoothing * self.current_level_db_r + 
                                      (1 - self.level_smoothing) * level_db_r)
            
            # Peak hold for both channels
            if level_db_l > self.peak_hold_db_l:
                self.peak_hold_db_l = level_db_l
                self.peak_hold_time_l = self.peak_hold_duration
            else:
                self.peak_hold_time_l -= 1
                if self.peak_hold_time_l <= 0:
                    self.peak_hold_db_l = max(self.peak_hold_db_l - 0.5, self.current_level_db_l)
            
            if level_db_r > self.peak_hold_db_r:
                self.peak_hold_db_r = level_db_r
                self.peak_hold_time_r = self.peak_hold_duration
            else:
                self.peak_hold_time_r -= 1
                if self.peak_hold_time_r <= 0:
                    self.peak_hold_db_r = max(self.peak_hold_db_r - 0.5, self.current_level_db_r)
            
            # Clipping detection for both channels
            max_sample_l = np.max(np.abs(left_data))
            max_sample_r = np.max(np.abs(right_data))
            self.is_clipping = (max_sample_l >= self.clipping_threshold or 
                               max_sample_r >= self.clipping_threshold)
            
            # Use primary channel (left) for pitch detection
            if self.channel_offset == 2:
                mono_data = left_data  # Use left channel for pitch
                rms = rms_l
                level_db = level_db_l
            else:
                mono_data = (left_data + right_data) / 2  # Mix for pitch
                rms = np.sqrt(np.mean(mono_data ** 2))
                level_db = 20 * np.log10(rms) if rms > 0 else -100.0
        else:
            # Mono input - duplicate to both channels for display
            mono_data = indata[:, 0]
            rms = np.sqrt(np.mean(mono_data ** 2))
            level_db = 20 * np.log10(rms) if rms > 0 else -100.0
            
            self.current_level_db_l = self.current_level_db_r = level_db
            self.peak_hold_db_l = self.peak_hold_db_r = level_db
            
            max_sample = np.max(np.abs(mono_data))
            self.is_clipping = max_sample >= self.clipping_threshold
        
        # Pitch detection (run on every callback for maximum responsiveness)
        if len(mono_data) >= 512:  # Reduced minimum sample requirement
            # Only detect if we have reasonable signal level (lowered threshold)
            if rms > 0.00001:  # Higher threshold for more stable detection (-100dB)
                frequency = self.pitch_detector.detect_pitch(mono_data)
                
                if frequency and 50 <= frequency <= 4000:  # Reasonable musical range
                    note_name, midi_note, cents = self.pitch_detector.frequency_to_note(frequency)
                    # Update more frequently and with wider cents range for responsiveness
                    if abs(cents) < 200:  # Allow wider cents range for display
                        # Always update - no smoothing to prevent real-time response
                        old_frequency = self.current_frequency
                        old_cents = self.current_cents
                        self.current_frequency = frequency
                        self.current_note = note_name
                        self.current_cents = cents
                else:
                    # Clear pitch detection if frequency is out of range
                    self.current_frequency = None
                    self.current_note = None
                    self.current_cents = 0
            elif level_db < -60:  # Clear detection for weak signals (raised from -80 to -60)
                self.current_frequency = None
                self.current_note = None
                self.current_cents = 0
    
    def _display_loop(self):
        """Display thread for updating the console visualization."""
        # Clear the terminal and set up the display area
        print("\033[2J\033[H", end="")  # Clear screen and move to top
        self._draw_header()
        
        frame_count = 0  # Track frames for whiteline spacing
        
        while not self.stop_event.is_set():
            # Move cursor to the display area and update
            print("\033[s", end="")  # Save cursor position
            print("\033[6;1H", end="")  # Move to line 6, column 1 (after header)
            self._update_bars()
            
            # Add whiteline every 2.5 seconds (125 frames at 50 Hz)
            frame_count += 1
            if frame_count >= 125:  # Every 2.5 seconds
                print()  # Add whiteline for spacing
                frame_count = 0
            
            print("\033[u", end="")  # Restore cursor position
            time.sleep(0.02)  # Increased to 50 Hz update rate for more responsive display
    
    def _draw_header(self):
        """Draw the static header information."""
        import sounddevice as sd
        try:
            device_info = sd.query_devices(self.device_index)
            device_name = device_info['name']
        except:
            device_name = f"Device {self.device_index}"
            
        print("Real-time Audio Monitor")
        print("======================")
        print("Optimal levels: -6dB to -3dB (yellow/red)")
        print()
        print("Commands:")
        print("  Press ENTER to continue sampling")
        print("  Type 'q' + ENTER to quit/cancel")
        print()
    
    def _update_bars(self):
        """Update only the dynamic bars without the header."""
    def _update_bars(self):
        """Update stereo level bars and pitch display."""
        bar_width = 40
        
        # Left channel bar
        level_normalized_l = max(0, min(1, (self.current_level_db_l + 60) / 60))
        filled_chars_l = int(level_normalized_l * bar_width)
        bar_l = "█" * filled_chars_l + "░" * (bar_width - filled_chars_l)
        
        # Left channel peak indicator
        peak_normalized_l = max(0, min(1, (self.peak_hold_db_l + 60) / 60))
        peak_pos_l = int(peak_normalized_l * bar_width)
        if peak_pos_l < bar_width and peak_pos_l >= filled_chars_l:
            bar_list_l = list(bar_l)
            bar_list_l[peak_pos_l] = "▌"
            bar_l = "".join(bar_list_l)
        
        # Right channel bar  
        level_normalized_r = max(0, min(1, (self.current_level_db_r + 60) / 60))
        filled_chars_r = int(level_normalized_r * bar_width)
        bar_r = "█" * filled_chars_r + "░" * (bar_width - filled_chars_r)
        
        # Right channel peak indicator
        peak_normalized_r = max(0, min(1, (self.peak_hold_db_r + 60) / 60))
        peak_pos_r = int(peak_normalized_r * bar_width)
        if peak_pos_r < bar_width and peak_pos_r >= filled_chars_r:
            bar_list_r = list(bar_r)
            bar_list_r[peak_pos_r] = "▌"
            bar_r = "".join(bar_list_r)
        
        # Color coding for left channel
        if self.current_level_db_l > -3:
            level_color_l = "\033[91m"  # Red
        elif self.current_level_db_l > -6:
            level_color_l = "\033[93m"  # Yellow
        elif self.current_level_db_l > -20:
            level_color_l = "\033[92m"  # Green
        else:
            level_color_l = "\033[90m"  # Gray
            
        # Color coding for right channel
        if self.current_level_db_r > -3:
            level_color_r = "\033[91m"  # Red
        elif self.current_level_db_r > -6:
            level_color_r = "\033[93m"  # Yellow
        elif self.current_level_db_r > -20:
            level_color_r = "\033[92m"  # Green
        else:
            level_color_r = "\033[90m"  # Gray
        
        level_text_l = f"{self.current_level_db_l:5.1f}dB"
        level_text_r = f"{self.current_level_db_r:5.1f}dB"
        clipping_text = " 🔴 CLIPPING!" if self.is_clipping else ""
        
        # Clear and print left channel line
        print(f"\033[K", end="")  # Clear line
        print(f"L: {level_color_l}[{bar_l}]{level_text_l}\033[0m")
        
        # Clear and print right channel line
        print(f"\033[K", end="")  # Clear line
        print(f"R: {level_color_r}[{bar_r}]{level_text_r}\033[0m{clipping_text}")
        
        # Add whiteline after level bars
        print(f"\033[K")  # Clear line (creates spacing)
        
        # Add audio interface information with channel details
        import sounddevice as sd
        try:
            device_info = sd.query_devices(self.device_index)
            device_name = device_info['name']
        except:
            device_name = f"Device {self.device_index}"
            
        # Build channel info string
        if self.is_asio and self.channel_selectors:
            # Convert 0-based to 1-based for display
            display_channels = [ch + 1 for ch in self.channel_selectors]
            if len(display_channels) == 2:
                channel_info = f" {display_channels[0]}/{display_channels[1]}"
            else:
                channel_info = f" {'/'.join(map(str, display_channels))}"
        elif self.channel_offset > 0:
            # Non-ASIO with offset
            start_ch = self.channel_offset + 1
            end_ch = start_ch + self.channels - 1
            if self.channels == 1:
                channel_info = f" {start_ch}"
            else:
                channel_info = f" {start_ch}/{end_ch}"
        else:
            # Standard stereo or mono
            if self.channels == 1:
                channel_info = " 1"
            elif self.channels == 2:
                channel_info = " 1/2"
            else:
                channel_info = f" 1-{self.channels}"
            
        print(f"\033[K", end="")  # Clear line
        print(f"Input: {device_name}{channel_info}")
        
        # Add empty line between bars and pitch
        print(f"\033[K")  # Clear line (creates spacing)
        
        # Clear and print pitch detection bar
        print(f"\033[K", end="")  # Clear line
        if self.current_note and self.current_frequency:
            # Create pitch deviation bar (-50 to +50 cents) - same width as signal bar
            cents_normalized = max(-1, min(1, self.current_cents / 50))  # Map -50 to +50 cents -> -1 to +1
            center_pos = bar_width // 2
            
            # Create the bar with center indicator
            pitch_bar = ['░'] * bar_width
            pitch_bar[center_pos] = '│'  # Center line
            
            # Add pitch indicator - show even small deviations
            if abs(cents_normalized) > 0.005:  # Show if deviation > 0.25 cent (was 1 cent)
                indicator_pos = int(center_pos + (cents_normalized * center_pos))
                indicator_pos = max(0, min(bar_width - 1, indicator_pos))
                
                if cents_normalized > 0:
                    pitch_bar[indicator_pos] = '▲'  # Sharp
                else:
                    pitch_bar[indicator_pos] = '▼'  # Flat
            else:
                pitch_bar[center_pos] = '●'  # In tune
            
            pitch_display = ''.join(pitch_bar)
            cents_text = f"{self.current_cents:+4.1f}¢" 
            freq_text = f"{self.current_frequency:6.1f}Hz"
            
            # Color coding for pitch accuracy
            if abs(self.current_cents) <= 5:
                pitch_color = "\033[92m"  # Green - in tune
            elif abs(self.current_cents) <= 15:
                pitch_color = "\033[93m"  # Yellow - slightly off
            else:
                pitch_color = "\033[91m"  # Red - out of tune
                
            print(f" Pitch: {pitch_color}[{pitch_display}]\033[0m {self.current_note:>3} {freq_text} {cents_text}")
        else:
            # Empty pitch bar when no signal - same width as signal bar
            empty_bar = '░' * 18 + '│' + '░' * 21
            print(f" Pitch: [\033[90m{empty_bar}\033[0m]  --    ---.- Hz   ---¢")
        
        # Add whiteline after pitch display for spacing
        print(f"\033[K")  # Clear line (creates final spacing)
        
        # Add extra whiteline after pitch display
        print(f"\033[K")  # Clear line (creates final spacing)
        
        # Flush output to ensure immediate display
        import sys
        sys.stdout.flush()
    
    def _update_display_simple(self):
        """Simple display update for terminals with limited cursor support."""
        # Just overwrite the current line using carriage return
        level_normalized = max(0, min(1, (self.current_level_db + 60) / 60))
        bar_width = 40
        filled_chars = int(level_normalized * bar_width)
        bar = "█" * filled_chars + "░" * (bar_width - filled_chars)
        
        # Peak indicator
        peak_normalized = max(0, min(1, (self.peak_hold_db + 60) / 60))
        peak_pos = int(peak_normalized * bar_width)
        if peak_pos < bar_width and peak_pos >= filled_chars:
            bar_list = list(bar)
            bar_list[peak_pos] = "▌"
            bar = "".join(bar_list)
        
        level_text = f"{self.current_level_db:5.1f}dB"
        clipping_text = " CLIP!" if self.is_clipping else "      "
        
        # Note info
        if self.current_note and self.current_frequency:
            cents_text = f"{self.current_cents:+3.0f}¢"
            note_text = f"Note:{self.current_note:>3} {cents_text}"
        else:
            note_text = "Note: --    0¢"
        
        # Single line display with carriage return
        display_line = f"\rSignal:[{bar}]{level_text} {clipping_text} {note_text}"
        print(display_line, end="", flush=True)
    
    def start_monitoring(self):
        """Start real-time audio monitoring."""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.stop_event.clear()
        
        try:
            # Configure device for monitoring - need to capture the right channels
            # For ASIO devices, we need to specify which channels to capture
            import sounddevice as sd
            
            if self.device_index is not None:
                device_info = sd.query_devices(self.device_index)
                host_apis = sd.query_hostapis()
                host_api_name = host_apis[device_info['hostapi']]['name']
                is_asio = 'ASIO' in host_api_name
                
                # Configure for ASIO multi-channel capture
                extra_settings = None
                actual_channels = self.channels
                
                if is_asio and device_info['max_input_channels'] > 2:
                    # For ASIO, calculate channel selectors based on channel_offset
                    # channel_offset is calculated from input_channels (e.g., "1-2" -> 0, "3-4" -> 2)
                    channel_selectors = [self.channel_offset, self.channel_offset + 1]
                    extra_settings = sd.AsioSettings(channel_selectors=channel_selectors)
                    actual_channels = 2
                    
                    # Store for display
                    self.channel_selectors = channel_selectors
                    self.is_asio = True
                    
                    # Display channels are 1-based
                    display_ch = [ch + 1 for ch in channel_selectors]
                    logging.info(f"ASIO monitoring: capturing channels {channel_selectors} ({display_ch[0]}-{display_ch[1]} in 1-based)")
                else:
                    logging.info(f"Standard monitoring: capturing {actual_channels} channels")
            else:
                extra_settings = None
                actual_channels = self.channels
            
            # Start audio stream
            self.stream = sd.InputStream(
                device=self.device_index,
                channels=actual_channels,
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                callback=self._audio_callback,
                dtype=np.float32,
                extra_settings=extra_settings
            )
            self.stream.start()
            
            # Start display thread
            self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
            self.display_thread.start()
            
            logging.info("Real-time audio monitoring started")
            
        except Exception as e:
            logging.error(f"Failed to start audio monitoring: {e}")
            self.is_monitoring = False
            raise
    
    def stop_monitoring(self):
        """Stop real-time audio monitoring."""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.stop_event.set()
        
        # Stop audio stream
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        # Wait for display thread
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=1.0)
        
        # Clear display
        print("\033[2J\033[H", end="")  # Clear screen and move to top
        
        logging.info("Real-time audio monitoring stopped")
    
    def get_current_status(self) -> dict:
        """Get current monitoring status as dictionary."""
        return {
            'level_db': self.current_level_db,
            'peak_db': self.peak_hold_db,
            'is_clipping': self.is_clipping,
            'frequency': self.current_frequency,
            'note': self.current_note,
            'cents': self.current_cents,
            'is_monitoring': self.is_monitoring
        }


def show_monitoring_interface(device_index: int, sample_rate: int = 44100,
                            channels: int = 1, channel_offset: int = 0,
                            duration: Optional[float] = None) -> dict:
    """
    Show real-time monitoring interface with user interaction.
    
    Args:
        device_index: Audio device index
        sample_rate: Sample rate in Hz
        channels: Number of channels
        channel_offset: Channel offset for multi-channel devices
        duration: Maximum duration in seconds (None = until user stops)
        
    Returns:
        Final monitoring status dictionary
    """
    monitor = RealtimeAudioMonitor(
        device_index=device_index,
        sample_rate=sample_rate,
        channels=channels,
        channel_offset=channel_offset
    )
    
    try:
        monitor.start_monitoring()
        
        # The display loop handles the header, just wait
        start_time = time.time()
        
        while monitor.is_monitoring:
            if duration and (time.time() - start_time) >= duration:
                break
                
            # Just sleep to let the display update
            time.sleep(0.1)
        
    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user")
    except Exception as e:
        logging.error(f"Monitoring error: {e}")
    finally:
        monitor.stop_monitoring()
    
    return monitor.get_current_status()


def show_pre_sampling_monitor(device_index: int, sample_rate: int = 44100,
                             channels: int = 1, channel_offset: int = 0,
                             title: str = "Audio Level Monitor") -> bool:
    """
    Show real-time monitoring before sampling with simple proceed/cancel.
    
    Args:
        device_index: Audio device index
        sample_rate: Sample rate in Hz  
        channels: Number of channels
        channel_offset: Channel offset for multi-channel devices
        title: Title for the monitoring display
        
    Returns:
        True to proceed, False to cancel
    """
    import sys
    import time
    
    monitor = RealtimeAudioMonitor(
        device_index=device_index,
        sample_rate=sample_rate,
        channels=channels,
        channel_offset=channel_offset
    )
    
    try:
        monitor.start_monitoring()
        
        # Print initial instructions - add whiteline before for clarity
        print()
        print("Press ENTER to continue or 'q' + ENTER to cancel...")
        print()
        
        # Platform-specific keyboard input handling
        if sys.platform == 'win32':
            import msvcrt
            input_buffer = ""
            
            while monitor.is_monitoring:
                # Check for keyboard input (non-blocking)
                if msvcrt.kbhit():
                    char = msvcrt.getch().decode('utf-8', errors='ignore')
                    
                    if char == '\r' or char == '\n':  # Enter key
                        user_input = input_buffer.strip().lower()
                        input_buffer = ""
                        
                        if user_input == 'q':
                            print("\nCancelling...")
                            return False
                        else:
                            print("\nProceeding...")
                            return True
                    elif char == '\x03':  # Ctrl+C
                        print("\nCancelled by user")
                        return False
                    elif char == '\b' or ord(char) == 8:  # Backspace
                        if input_buffer:
                            input_buffer = input_buffer[:-1]
                            print(f"\rInput: {input_buffer} ", end="", flush=True)
                    elif char.isprintable():
                        input_buffer += char
                        print(f"\rInput: {input_buffer}", end="", flush=True)
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.05)
        else:
            # Unix/Linux - use select for non-blocking input
            import select
            
            while monitor.is_monitoring:
                # Check for keyboard input (non-blocking)
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    try:
                        user_input = sys.stdin.readline().strip().lower()
                        if user_input == 'q':
                            print("Cancelling...")
                            return False
                        elif user_input == '':
                            print("Proceeding...")
                            return True
                        else:
                            print("Press ENTER to continue or 'q' + ENTER to cancel...")
                    except:
                        continue
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.05)
        
        return True
        
    except KeyboardInterrupt:
        print("\nCancelled by user")
        return False
    except Exception as e:
        logging.error(f"Monitoring error: {e}")
        print(f"\n[WARNING] Could not start audio monitoring: {e}")
        print("Continuing without real-time monitoring...")
        return True  # Don't block sampling if monitoring fails
    finally:
        monitor.stop_monitoring()


if __name__ == "__main__":
    # Test the monitoring system
    print("Testing real-time audio monitor...")
    
    try:
        final_status = show_pre_sampling_monitor(
            device_index=None,  # Use default device
            sample_rate=44100,
            channels=2,
            channel_offset=0,
            title="Audio Monitor Test"
        )
        
        print(f"\nMonitoring result: {'Proceed' if final_status else 'Cancel'}")
        
    except Exception as e:
        print(f"Error: {e}")