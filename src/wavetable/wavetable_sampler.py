"""
Wavetable sampling engine.

Uses the main sampler's audio and MIDI infrastructure - no code duplication.
Only implements wavetable-specific logic: MIDI sweep during recording, 
wavetable calculations, and level processing.
"""

import os
# Enable ASIO support in sounddevice (must be set before importing sounddevice)
os.environ["SD_ENABLE_ASIO"] = "1"

import time
import logging
import threading
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path

from .wave_calculator import WaveCalculator
from .sweep_curves import SweepCurves


class WavetableSampler:
    """
    Wavetable sampling engine using main sampler's infrastructure.
    
    This class orchestrates:
    - MIDI parameter sweeps during recording
    - Wavetable timing calculations
    - Audio level processing for wavetables
    - Wavetable file saving
    
    It does NOT handle:
    - Audio device setup (uses AudioEngine from main sampler)
    - MIDI port setup (uses MIDIController from main sampler)
    """
    
    def __init__(self, sampler):
        """
        Initialize wavetable sampler with main sampler instance.
        
        Args:
            sampler: AutoSampler instance (provides audio_engine, midi_controller, etc.)
        """
        self.sampler = sampler
        self.audio_engine = sampler.audio_engine
        self.midi_controller = sampler.midi_controller
        self.samplerate = self.audio_engine.samplerate
        
        # Track active note for cleanup
        self._active_note = None
        
        # Wavetable parameters (set by create_wavetables)
        self.samples_per_waveform = 2048
        self.number_of_waves = 64
        
        # Audio processing settings (configurable via wavetable_config.yaml)
        self.gain_boost_db = 0.0  # Default: no gain boost
        self.normalize = True
        self.normalize_target_db = -6.0
        
        # Monitoring setting (routes input to output during recording)
        self.enable_monitoring = False
        
        # Hold times before/after sweep
        self.hold_time_before = 0.5
        self.hold_time_after = 0.5
    
    def cleanup(self):
        """Clean up resources and ensure all notes are off."""
        try:
            if self.midi_controller and self._active_note is not None:
                self._send_note_off(self._active_note)
                self._active_note = None
                
                # Send All Notes Off (CC 123) as safety
                try:
                    self.midi_controller.send_midi_cc(123, 0, 0)
                    time.sleep(0.05)
                except Exception as e:
                    logging.warning(f"Failed to send All Notes Off: {e}")
            
            logging.debug("WavetableSampler cleanup completed")
            
        except Exception as e:
            logging.error(f"WavetableSampler cleanup failed: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()
    
    def create_wavetables(self, wavetable_config: Dict) -> bool:
        """
        Create wavetables with all curve types.
        
        Args:
            wavetable_config: Configuration dictionary with:
                - name: Wavetable name
                - samples_per_waveform: Samples per wave (128, 512, 1024, 2048, 4096)
                - number_of_waves: Number of waves (max 256, or 217 for 4096)
                - midi_note: MIDI note to play
                - control: Dict with type, controller, channel, min_value, max_value
                - output_folder: Output directory
                
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate configuration
            self.samples_per_waveform = wavetable_config['samples_per_waveform']
            self.number_of_waves = wavetable_config['number_of_waves']
            
            # Load audio processing settings from config
            self.gain_boost_db = wavetable_config.get('gain_boost_db', 0.0)
            self.normalize = wavetable_config.get('normalize', True)
            self.normalize_target_db = wavetable_config.get('normalize_target_db', -6.0)
            
            # Load monitoring setting
            self.enable_monitoring = wavetable_config.get('enable_monitoring', False)
            
            # Load hold time settings
            self.hold_time_before = wavetable_config.get('hold_time_before', 0.5)
            self.hold_time_after = wavetable_config.get('hold_time_after', 0.5)
            
            logging.info(f"Audio processing: gain={self.gain_boost_db}dB, normalize={self.normalize}, target={self.normalize_target_db}dB")
            logging.info(f"Hold times: before={self.hold_time_before}s, after={self.hold_time_after}s")
            if self.enable_monitoring:
                logging.info("Real-time monitoring enabled (input routed to output)")
            
            if not WaveCalculator.validate_wavetable_config(
                self.samples_per_waveform, self.number_of_waves):
                return False
            
            # Calculate sample lengths
            total_samples, sweep_samples, _ = WaveCalculator.calculate_sample_lengths(
                self.samples_per_waveform,
                self.number_of_waves,
                self.audio_engine.bitdepth
            )
            
            # Create output directory
            output_dir = Path(wavetable_config['output_folder'])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get curve types to generate
            curve_types = wavetable_config.get('curve_types', ['linear'])
            
            print(f"\nCreating wavetables: {wavetable_config['name']}")
            print(f"  Samples per wave: {self.samples_per_waveform}")
            print(f"  Number of waves: {self.number_of_waves}")
            print(f"  Total samples: {total_samples}")
            print(f"  Curves: {', '.join(curve_types)}")
            
            success_count = 0
            for curve_type in curve_types:
                print(f"\n--- Sampling curve: {curve_type} ---")
                if self._sample_curve(wavetable_config, curve_type, total_samples, sweep_samples):
                    success_count += 1
                else:
                    logging.error(f"Failed to sample curve: {curve_type}")
            
            print(f"\nCompleted: {success_count}/{len(curve_types)} curves")
            print(f"Output location: {output_dir.absolute()}")
            
            return success_count > 0
            
        except Exception as e:
            logging.error(f"Wavetable creation failed: {e}")
            return False
    
    def _sample_curve(self, config: Dict, curve_type: str, 
                     total_samples: int, sweep_samples: int) -> bool:
        """Sample a single curve type."""
        try:
            # Generate sweep curve values
            control_values = SweepCurves.generate_curve(
                curve_type,
                config['control']['min_value'],
                config['control']['max_value'],
                config['number_of_waves']
            )
            
            # Calculate timing based on required wavetable length
            # Add hold times: hold_before lets note stabilize, hold_after captures release/tail
            sweep_duration = sweep_samples / self.samplerate
            total_duration = (self.hold_time_before + sweep_duration + self.hold_time_after)
            step_duration = sweep_duration / len(control_values)
            
            print(f"Sampling {len(control_values)} steps over {sweep_duration:.2f} seconds")
            print(f"Hold times: {self.hold_time_before}s before, {self.hold_time_after}s after")
            print(f"Step duration: {step_duration:.3f} seconds") 
            print(f"Total recording duration: {total_duration:.2f} seconds")
            
            # Send initial MIDI note
            if self.midi_controller:
                self._send_note_on(config['midi_note'])
                time.sleep(0.1)  # Let note stabilize
            
            # Record with MIDI sweep
            print("Starting synchronized recording and MIDI sweep...")
            recorded_audio = self._record_with_midi_sweep(
                total_duration,
                control_values,
                step_duration,
                config['control']
            )
            
            if recorded_audio is None:
                logging.error("Audio recording with MIDI sweep failed")
                return False
            
            # Stop note
            if self.midi_controller:
                self._send_note_off(config['midi_note'])
                time.sleep(0.05)
            
            # Extract the sweep portion (skip hold_time_before, take sweep_samples)
            # The recording contains: [hold_before | sweep | hold_after]
            # We want just the sweep portion for the wavetable
            print(f"Recorded {len(recorded_audio)} samples")
            
            # Calculate the start offset (skip hold_time_before)
            start_offset = int(self.hold_time_before * self.samplerate)
            
            # Extract sweep portion
            if start_offset < len(recorded_audio):
                recorded_audio = recorded_audio[start_offset:]
                print(f"Skipped {start_offset} samples (hold_time_before)")
            
            # Trim or pad to exact wavetable length
            if len(recorded_audio) > total_samples:
                recorded_audio = recorded_audio[:total_samples]
                print(f"Trimmed to {total_samples} samples")
            elif len(recorded_audio) < total_samples:
                padding = np.zeros((total_samples - len(recorded_audio), recorded_audio.shape[1]), 
                                 dtype=recorded_audio.dtype)
                recorded_audio = np.vstack([recorded_audio, padding])
                print(f"Padded to {total_samples} samples")
            
            # Apply gain boost and normalization (wavetable-specific processing)
            recorded_audio = self._process_audio_levels(recorded_audio)
            
            # Save wavetable file
            control_name = config['control'].get('name', 'parameter').replace(' ', '_')
            filename = f"{config['name']}-{control_name}-{curve_type}-{config['samples_per_waveform']}.wav"
            filepath = Path(config['output_folder']) / filename
            
            success = self.audio_engine.save_audio(
                recorded_audio,
                str(filepath),
                metadata={
                    'name': config['name'],
                    'curve_type': curve_type,
                    'samples_per_waveform': config['samples_per_waveform'],
                    'number_of_waves': config['number_of_waves'],
                    'midi_note': config['midi_note']
                }
            )
            
            if success:
                print(f"Saved: {filename}")
                return True
            else:
                logging.error(f"Failed to save: {filename}")
                return False
                
        except Exception as e:
            logging.error(f"Curve sampling failed: {e}")
            return False
    
    def _record_with_midi_sweep(self, duration: float, control_values: List[int],
                               step_duration: float, control_info: Dict) -> Optional[np.ndarray]:
        """
        Record audio while performing synchronized MIDI parameter sweep.
        
        IMPORTANT: ASIO requires recording on the main thread.
        The MIDI sweep runs in a background thread, but recording happens on main thread.
        This is the same pattern used by the main sampler for ASIO compatibility.
        """
        try:
            # Check if we're using ASIO (recording must be on main thread for ASIO)
            is_asio = self._check_if_asio_device()
            
            if is_asio:
                logging.info("ASIO detected - recording on main thread, MIDI sweep on background thread")
                return self._record_with_midi_sweep_asio(duration, control_values, step_duration, control_info)
            else:
                logging.info("Non-ASIO device - using threaded recording")
                return self._record_with_midi_sweep_threaded(duration, control_values, step_duration, control_info)
                
        except Exception as e:
            logging.error(f"Record with MIDI sweep failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _check_if_asio_device(self) -> bool:
        """Check if the current audio device is ASIO."""
        try:
            import sounddevice as sd
            
            input_device = self.audio_engine.input_device
            if input_device is None:
                return False
                
            device_info = sd.query_devices(input_device)
            host_apis = sd.query_hostapis()
            host_api_name = host_apis[device_info['hostapi']]['name']
            
            return 'ASIO' in host_api_name
        except Exception as e:
            logging.warning(f"Could not detect ASIO: {e}")
            return False
    
    def _record_with_midi_sweep_asio(self, duration: float, control_values: List[int],
                                     step_duration: float, control_info: Dict) -> Optional[np.ndarray]:
        """
        ASIO-compatible recording: Record on main thread, MIDI sweep on background thread.
        
        This matches the pattern used by sample_processor.py for ASIO devices.
        """
        midi_sweep_error = [None]  # Use list to allow modification from thread
        hold_time = self.hold_time_before  # Capture for thread closure
        
        def midi_sweep_thread():
            """Background thread for MIDI parameter sweep."""
            try:
                # Wait for hold time before starting sweep
                time.sleep(hold_time)
                
                # Perform MIDI sweep with precise timing
                start_time = time.time()
                
                for i, value in enumerate(control_values):
                    target_time = start_time + (i * step_duration)
                    current_time = time.time()
                    
                    if current_time < target_time:
                        time.sleep(target_time - current_time)
                    
                    self._send_control_change(control_info, value)
                    time.sleep(0.001)  # Small delay for MIDI processing
                    
            except Exception as e:
                midi_sweep_error[0] = str(e)
                logging.error(f"MIDI sweep failed: {e}")
        
        # Start MIDI sweep thread
        midi_thread = threading.Thread(target=midi_sweep_thread, daemon=True)
        midi_thread.start()
        
        # Record on main thread (ASIO requirement)
        # Use monitoring if enabled (routes input to output for real-time listening)
        if self.enable_monitoring:
            logging.debug(f"Starting main-thread recording WITH MONITORING for {duration}s...")
            recorded_audio = self.audio_engine.record_with_monitoring(duration)
        else:
            logging.debug(f"Starting main-thread recording for {duration}s...")
            recorded_audio = self.audio_engine.record(duration)
        
        # Wait for MIDI thread to finish
        midi_thread.join(timeout=2.0)
        
        if midi_sweep_error[0]:
            logging.warning(f"MIDI sweep had error: {midi_sweep_error[0]} (recording may still be valid)")
        
        if recorded_audio is None:
            logging.error("ASIO recording returned None")
            return None
            
        logging.info(f"ASIO recording complete: {len(recorded_audio)} samples")
        return recorded_audio
    
    def _record_with_midi_sweep_threaded(self, duration: float, control_values: List[int],
                                         step_duration: float, control_info: Dict) -> Optional[np.ndarray]:
        """
        Non-ASIO recording: Both recording and MIDI sweep run in background threads.
        
        This is the original implementation for non-ASIO devices.
        """
        recorded_audio = None
        recording_error = None
        
        def record_audio_thread():
            """Background thread for audio recording."""
            nonlocal recorded_audio, recording_error
            try:
                recorded_audio = self.sampler.record_audio(duration)
                if recorded_audio is None:
                    recording_error = "Recording returned None"
            except Exception as e:
                recording_error = str(e)
                logging.error(f"Recording exception: {e}")
        
        def midi_sweep_thread():
            """Background thread for MIDI parameter sweep."""
            try:
                # Wait for hold time before starting sweep
                time.sleep(self.hold_time_before)
                
                # Perform MIDI sweep with precise timing
                start_time = time.time()
                
                for i, value in enumerate(control_values):
                    target_time = start_time + (i * step_duration)
                    current_time = time.time()
                    
                    if current_time < target_time:
                        time.sleep(target_time - current_time)
                    
                    self._send_control_change(control_info, value)
                    time.sleep(0.001)  # Small delay for MIDI processing
                    
            except Exception as e:
                logging.error(f"MIDI sweep failed: {e}")
        
        # Start both threads
        record_thread = threading.Thread(target=record_audio_thread, daemon=True)
        midi_thread = threading.Thread(target=midi_sweep_thread, daemon=True)
        
        record_thread.start()
        midi_thread.start()
        
        # Wait for completion
        record_thread.join(timeout=duration + 5.0)
        midi_thread.join(timeout=duration + 5.0)
        
        if recording_error:
            logging.error(f"Recording error: {recording_error}")
            return None
        
        return recorded_audio
    
    def _send_control_change(self, control_info: Dict, value: int) -> bool:
        """Send a MIDI control change message using main sampler's MIDI controller."""
        try:
            if not self.midi_controller:
                return True  # No MIDI = skip silently
                
            ctrl_type = control_info['type']
            channel = control_info.get('channel', 0)
            
            if ctrl_type == 'cc':
                self.midi_controller.send_midi_cc(
                    control_info['controller'], value, channel)
            elif ctrl_type == 'nrpn':
                self.midi_controller.send_nrpn(
                    control_info['controller'], value, channel)
            elif ctrl_type == 'cc14':
                self.midi_controller.send_midi_cc14(
                    control_info['controller'], value, channel)
            elif ctrl_type == 'pitchwheel':
                pitch_value = int((value / 127.0) * 16383) - 8192
                self.midi_controller.send_pitchwheel(pitch_value, channel)
            else:
                logging.warning(f"Unsupported control type: {ctrl_type}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to send control change: {e}")
            return False
    
    def _send_note_on(self, midi_note: int, velocity: int = 100, channel: int = 0) -> bool:
        """Send MIDI note on."""
        if self.midi_controller:
            try:
                self.midi_controller.send_note_on(midi_note, velocity, channel)
                self._active_note = midi_note
                return True
            except Exception as e:
                logging.error(f"Failed to send note on: {e}")
        return False
    
    def _send_note_off(self, midi_note: int, channel: int = 0) -> bool:
        """Send MIDI note off."""
        if self.midi_controller:
            try:
                self.midi_controller.send_note_off(midi_note, channel)
                self._active_note = None
                return True
            except Exception as e:
                logging.error(f"Failed to send note off: {e}")
        return False
    
    def _process_audio_levels(self, audio: np.ndarray) -> np.ndarray:
        """
        Process audio levels for wavetable output.
        
        Settings are configurable via wavetable_config.yaml:
        - gain_boost_db: Gain boost in dB (default 0, no boost)
        - normalize: Whether to normalize audio (default True)
        - normalize_target_db: Target peak level in dB (default -6)
        """
        try:
            # Apply gain boost if configured
            if self.gain_boost_db != 0.0:
                gain_linear = 10 ** (self.gain_boost_db / 20.0)
                audio = audio * gain_linear
                logging.debug(f"Applied gain boost: {self.gain_boost_db}dB ({gain_linear:.2f}x)")
            
            # Normalize to target peak level if enabled
            if self.normalize:
                peak = np.max(np.abs(audio))
                if peak > 0:
                    target_peak = 10 ** (self.normalize_target_db / 20.0)
                    audio = audio * (target_peak / peak)
                    logging.debug(f"Normalized to {self.normalize_target_db}dB peak")
            
            # Clip to valid range
            audio = np.clip(audio, -1.0, 1.0)
            
            return audio
            
        except Exception as e:
            logging.error(f"Audio level processing failed: {e}")
            return audio
