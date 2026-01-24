"""
Wavetable sampling engine.

Core sampling logic for wavetable creation using existing AutosamplerT infrastructure.
"""

import os
import time
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from src.sampler_midicontrol import MIDIController
from src.sampling.audio_engine import AudioEngine
from src.wavetable.wave_calculator import WaveCalculator
from src.wavetable.sweep_curves import SweepCurves


class WavetableSampler:
    """Core wavetable sampling engine using AutosamplerT infrastructure."""
    
    def __init__(self, audio_engine: 'AudioEngine',
                 midi_controller: Optional[MIDIController] = None,
                 enable_monitoring: bool = False):
        """
        Initialize wavetable sampler.
        
        Args:
            audio_engine: Pre-configured AudioEngine instance
            midi_controller: MIDI controller instance
            enable_monitoring: If True, use duplex monitoring during recording
        """
        self.audio_engine = audio_engine
        self.midi_controller = midi_controller
        self.enable_monitoring = enable_monitoring
        self._active_note = None  # Track active note for cleanup
    
    def cleanup(self):
        """Clean up resources and ensure all notes are off."""
        try:
            # Send all notes off and reset controller if MIDI is active
            if self.midi_controller and self._active_note is not None:
                self._send_note_off(self._active_note)
                self._active_note = None
                
                # Send CC 123 (All Notes Off) as additional safety
                try:
                    self.midi_controller.send_midi_cc(123, 0, 0)
                    time.sleep(0.05)
                except Exception as e:
                    logging.warning(f"Failed to send All Notes Off: {e}")
            
            # Stop any ongoing audio operations (same as main sampler)
            try:
                import sounddevice as sd
                sd.stop()
                logging.debug("Audio operations stopped")
            except Exception as e:
                logging.warning(f"Failed to stop audio operations: {e}")
            
            logging.info("WavetableSampler cleanup completed")
            
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
            wavetable_config: Wavetable configuration dictionary
            
        Returns:
            True if successful, False otherwise
            
        Config format:
            {
                'name': 'wavetable_name',
                'samples_per_waveform': 2048,
                'number_of_waves': 64,
                'note_frequency': 440.0,
                'midi_note': 69,
                'control': {
                    'type': 'cc',
                    'channel': 0,
                    'controller': 74,
                    'min_value': 0,
                    'max_value': 127
                },
                'output_folder': './output/wavetables'
            }
        """
        try:
            # Validate configuration
            if not self._validate_config(wavetable_config):
                return False
            
            # Calculate sample lengths
            total_samples, sweep_samples, duration = WaveCalculator.calculate_sample_lengths(
                wavetable_config['samples_per_waveform'],
                wavetable_config['number_of_waves'],
                self.audio_engine.bitdepth
            )
            
            # Create output directory
            output_dir = Path(wavetable_config['output_folder'])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Sample each curve type
            curve_types = SweepCurves.get_all_curves()
            success_count = 0
            
            for curve_type in curve_types:
                print(f"\\n=== Sampling {curve_type.upper()} curve ===")
                
                success = self._sample_curve(
                    wavetable_config,
                    curve_type,
                    total_samples,
                    sweep_samples
                )
                
                if success:
                    success_count += 1
                    print(f"✓ {curve_type.upper()} curve completed")
                else:
                    print(f"✗ {curve_type.upper()} curve failed")
            
            print(f"\\n=== Wavetable Creation Complete ===")
            print(f"Successfully created {success_count}/{len(curve_types)} wavetables")
            print(f"Output location: {output_dir.absolute()}")
            
            return success_count > 0
            
        except Exception as e:
            logging.error(f"Wavetable creation failed: {e}")
            return False
    
    def _sample_curve(self, config: Dict, curve_type: str, 
                     total_samples: int, sweep_samples: int) -> bool:
        """Sample a single curve type using main sampler's audio engine."""
        try:
            # Generate sweep curve values
            control_values = SweepCurves.generate_curve(
                curve_type,
                config['control']['min_value'],
                config['control']['max_value'],
                config['number_of_waves']
            )
            
            # Calculate timing based on required wavetable length
            # total_samples = samples_per_waveform * number_of_waves - this is the exact length needed
            # Recording duration must match this exactly so wave periods fit
            total_duration = total_samples / self.audio_engine.samplerate
            sweep_duration = sweep_samples / self.audio_engine.samplerate
            step_duration = sweep_duration / len(control_values)
            
            print(f"Sampling {len(control_values)} steps over {sweep_duration:.2f} seconds")
            print(f"Step duration: {step_duration:.3f} seconds") 
            print(f"Total recording duration: {total_duration:.2f} seconds")
            print(f"Required samples: {total_samples} (for {config['number_of_waves']} waves x {config['samples_per_waveform']} samples/wave)")
            
            # Send initial MIDI note
            if self.midi_controller:
                self._send_note_on(config['midi_note'])
                time.sleep(0.1)  # Let note stabilize
            
            # Record using the same method as main sampler
            print("Starting synchronized recording and MIDI sweep...")
            
            # Use a callback-based approach for precise MIDI timing during recording
            recorded_audio = self._record_with_midi_sweep(
                total_duration,
                control_values,
                step_duration,
                config['control']
            )
            
            if recorded_audio is None:
                logging.error("Audio recording with MIDI sweep failed")
                return False
            
            # Stop note - ensure it's always sent
            if self.midi_controller:
                self._send_note_off(config['midi_note'])
                time.sleep(0.05)  # Brief pause after note off
            
            # Trim or pad audio to exact wavetable length
            # This ensures wave periods fit exactly (total_samples = samples_per_waveform * number_of_waves)
            print(f"Recorded {len(recorded_audio)} samples ({len(recorded_audio) / self.audio_engine.samplerate:.2f}s)")
            if len(recorded_audio) > total_samples:
                recorded_audio = recorded_audio[:total_samples]
                print(f"Trimmed to {total_samples} samples ({total_samples / self.audio_engine.samplerate:.2f}s)")
            elif len(recorded_audio) < total_samples:
                # Pad with silence if recording was too short
                padding = np.zeros((total_samples - len(recorded_audio), recorded_audio.shape[1]), 
                                 dtype=recorded_audio.dtype)
                recorded_audio = np.vstack([recorded_audio, padding])
                print(f"Padded to {total_samples} samples ({total_samples / self.audio_engine.samplerate:.2f}s)")
            
            # Apply gain boost and normalization
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
                    'midi_note': config['midi_note'],
                    'control': config['control']
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
        Uses the same recording approach as main sampler to prevent driver locking.
        Supports real-time monitoring if enabled.
        """
        try:
            import threading
            import time
            
            # Use AudioEngine's record method directly (same as main sampler)
            recorded_audio = None
            recording_error = None
            midi_sweep_completed = threading.Event()
            
            def record_audio_thread():
                """Background thread for audio recording."""
                nonlocal recorded_audio, recording_error
                try:
                    # Use the same recording method as main sampler
                    # Support monitoring if enabled (like normal sampling)
                    logging.debug(f"Starting audio recording thread (monitoring={self.enable_monitoring})...")
                    if self.enable_monitoring:
                        recorded_audio = self.audio_engine.record_with_monitoring(duration)
                    else:
                        recorded_audio = self.audio_engine.record(duration)
                    if recorded_audio is None:
                        recording_error = "AudioEngine.record() returned None"
                    else:
                        logging.debug(f"Recording successful: {len(recorded_audio)} samples")
                except Exception as e:
                    recording_error = str(e)
                    import traceback
                    print("=== FULL TRACEBACK FOR AUDIO RECORDING ERROR ===")
                    traceback.print_exc()
                    print("=== END TRACEBACK ===")
                    logging.error(f"Recording exception: {traceback.format_exc()}")
            
            def midi_sweep_thread():
                """Background thread for MIDI parameter sweep."""
                nonlocal recording_error
                try:
                    # Wait for hold time before starting sweep (like main sampler)
                    hold_before_sweep = 1.0  # 1 second to let note stabilize
                    time.sleep(hold_before_sweep)
                    
                    # Perform MIDI sweep with precise timing
                    start_time = time.time()
                    
                    for i, value in enumerate(control_values):
                        # Calculate target time for this step
                        target_time = start_time + (i * step_duration)
                        current_time = time.time()
                        
                        # Wait if we're ahead of schedule
                        if current_time < target_time:
                            time.sleep(target_time - current_time)
                        
                        # Send MIDI control change
                        success = self._send_control_change(control_info, value)
                        if not success:
                            recording_error = f"MIDI control change failed at step {i}, value {value}"
                            break
                        
                        # Small delay for MIDI processing
                        time.sleep(0.001)
                    
                    midi_sweep_completed.set()
                    
                except Exception as e:
                    recording_error = f"MIDI sweep failed: {e}"
            
            # Start both threads
            record_thread = threading.Thread(target=record_audio_thread, daemon=True)
            midi_thread = threading.Thread(target=midi_sweep_thread, daemon=True)
            
            record_thread.start()
            midi_thread.start()
            
            # Wait for both to complete
            record_thread.join(timeout=duration + 5.0)  # Extra time for safety
            midi_thread.join(timeout=duration + 5.0)
            
            # Check for errors
            if recording_error:
                logging.error(f"Recording/MIDI error: {recording_error}")
                return None
                
            if recorded_audio is None:
                logging.error("No audio data received from recording")
                return None
            
            if not midi_sweep_completed.is_set():
                logging.warning("MIDI sweep may not have completed fully")
            
            logging.info(f"Successfully recorded {len(recorded_audio)} samples with MIDI sweep")
            return recorded_audio
            
        except Exception as e:
            logging.error(f"Record with MIDI sweep failed: {e}")
            return None
    
    def _perform_midi_sweep(self, control_values: List[int], 
                           step_duration: float, control_info: Dict) -> bool:
        """
        Legacy MIDI sweep method - replaced by _record_with_midi_sweep.
        Kept for backward compatibility but should not be used.
        """
        logging.warning("Using legacy _perform_midi_sweep - consider using _record_with_midi_sweep")
        return self._perform_midi_sweep_legacy(control_values, step_duration, control_info)
    
    def _perform_midi_sweep_legacy(self, control_values: List[int], 
                                  step_duration: float, control_info: Dict) -> bool:
        """Legacy MIDI parameter sweep method."""
        if not self.midi_controller:
            logging.warning("No MIDI controller - skipping sweep")
            return True
            
        try:
            start_time = time.time()
            
            for i, value in enumerate(control_values):
                # Calculate target time for this step
                target_time = start_time + (i * step_duration)
                current_time = time.time()
                
                # Wait if we're ahead of schedule
                if current_time < target_time:
                    time.sleep(target_time - current_time)
                
                # Send MIDI control change
                success = self._send_control_change(control_info, value)
                if not success:
                    logging.error(f"Failed to send control value {value} at step {i}")
                    return False
                
                # Small delay for MIDI processing
                time.sleep(0.001)
            
            return True
            
        except Exception as e:
            logging.error(f"MIDI sweep failed: {e}")
            return False
    
    def _send_control_change(self, control_info: Dict, value: int) -> bool:
        """Send a MIDI control change message."""
        try:
            if control_info['type'] == 'cc':
                self.midi_controller.send_midi_cc(
                    control_info['controller'],
                    value,
                    control_info['channel']
                )
            elif control_info['type'] == 'nrpn':
                self.midi_controller.send_nrpn(
                    control_info['controller'],
                    value,
                    control_info['channel']
                )
            elif control_info['type'] == 'pitchwheel':
                # Convert 7-bit value to 14-bit pitch wheel range
                pitch_value = int((value / 127.0) * 16383) - 8192
                self.midi_controller.send_pitchwheel(pitch_value, control_info['channel'])
            else:
                logging.error(f"Unsupported control type: {control_info['type']}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Failed to send control change: {e}")
            return False
    
    def _send_note_on(self, midi_note: int, velocity: int = 100, channel: int = 0) -> bool:
        """Send MIDI note on and track active note."""
        if self.midi_controller:
            try:
                self.midi_controller.send_note_on(midi_note, velocity, channel)
                self._active_note = midi_note
                logging.debug(f"Note ON: {midi_note} (vel={velocity}, ch={channel})")
                return True
            except Exception as e:
                logging.error(f"Failed to send note on: {e}")
        return False
    
    def _send_note_off(self, midi_note: int, channel: int = 0) -> bool:
        """Send MIDI note off and clear active note tracking."""
        if self.midi_controller:
            try:
                self.midi_controller.send_note_off(midi_note, channel)
                if self._active_note == midi_note:
                    self._active_note = None
                logging.debug(f"Note OFF: {midi_note} (ch={channel})")
                return True
            except Exception as e:
                logging.error(f"Failed to send note off: {e}")
        return False
    
    def _validate_config(self, config: Dict) -> bool:
        """Validate wavetable configuration."""
        required_fields = [
            'name', 'samples_per_waveform', 'number_of_waves',
            'note_frequency', 'midi_note', 'control', 'output_folder'
        ]
        
        for field in required_fields:
            if field not in config:
                logging.error(f"Missing required config field: {field}")
                return False
        
        # Validate wavetable parameters
        if not WaveCalculator.validate_wavetable_config(
            config['samples_per_waveform'],
            config['number_of_waves']
        ):
            return False
        
        # Validate control info
        control = config['control']
        if 'type' not in control or 'channel' not in control:
            logging.error("Invalid control configuration")
            return False
        
        return True
    
    def _process_audio_levels(self, audio: np.ndarray, target_db: float = -6.0, gain_boost_db: float = 12.0) -> np.ndarray:
        """
        Process audio levels with gain boost and normalization.
        
        Args:
            audio: Input audio array
            target_db: Target peak level in dB
            gain_boost_db: Initial gain boost in dB
            
        Returns:
            Processed audio array
        """
        try:
            if audio.size == 0:
                return audio
            
            # Apply initial gain boost
            gain_linear = 10.0 ** (gain_boost_db / 20.0)
            boosted_audio = audio * gain_linear
            
            # Find peak level
            peak_level = np.max(np.abs(boosted_audio))
            
            if peak_level > 0:
                # Calculate normalization factor to reach target dB
                target_linear = 10.0 ** (target_db / 20.0)
                norm_factor = target_linear / peak_level
                
                # Apply normalization
                normalized_audio = boosted_audio * norm_factor
                
                # Clip to prevent overflow
                normalized_audio = np.clip(normalized_audio, -1.0, 1.0)
                
                logging.info(f"Audio processed: boost={gain_boost_db}dB, peak={20*np.log10(peak_level):.1f}dB, target={target_db}dB")
                return normalized_audio
            else:
                logging.warning("No audio signal detected - returning original")
                return audio
                
        except Exception as e:
            logging.error(f"Audio processing failed: {e}")
            return audio