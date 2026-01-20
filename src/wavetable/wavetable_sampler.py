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

from ..sampler_midicontrol import MIDIController
from ..sampling.audio_engine import AudioEngine
from .wave_calculator import WaveCalculator
from .sweep_curves import SweepCurves


class WavetableSampler:
    """Core wavetable sampling engine using AutosamplerT infrastructure."""
    
    def __init__(self, audio_device_index: int, sample_rate: int, bit_depth: int,
                 midi_controller: Optional[MIDIController] = None):
        """
        Initialize wavetable sampler.
        
        Args:
            audio_device_index: Audio input device index
            sample_rate: Audio sample rate
            bit_depth: Audio bit depth (8, 16, 24)
            midi_controller: MIDI controller instance
        """
        self.audio_device_index = audio_device_index
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth
        self.midi_controller = midi_controller
        
        # Initialize audio engine
        self.audio_engine = AudioEngine(
            device_index=audio_device_index,
            sample_rate=sample_rate,
            bit_depth=bit_depth,
            channels=2,  # Stereo
            channel_offset=0
        )
        
        logging.info(f"Wavetable sampler initialized: {sample_rate}Hz, {bit_depth}-bit")
    
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
                self.bit_depth
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
        """Sample a single curve type."""
        try:
            # Generate sweep curve values
            control_values = SweepCurves.generate_curve(
                curve_type,
                config['control']['min_value'],
                config['control']['max_value'],
                config['number_of_waves']
            )
            
            # Calculate timing
            sweep_duration = sweep_samples / self.sample_rate
            step_duration = sweep_duration / len(control_values)
            
            print(f"Sampling {len(control_values)} steps over {sweep_duration:.2f} seconds")
            print(f"Step duration: {step_duration:.3f} seconds")
            
            # Send initial MIDI note
            if self.midi_controller:
                self._send_note_on(config['midi_note'])
                time.sleep(0.1)  # Let note stabilize
            
            # Start audio recording
            print("Starting recording...")
            recorded_audio = self.audio_engine.record_samples(
                duration=total_samples / self.sample_rate,
                apply_postprocessing=False
            )
            
            if recorded_audio is None:
                logging.error("Audio recording failed")
                return False
            
            # Simultaneously perform MIDI sweep
            print("Starting MIDI sweep...")
            sweep_success = self._perform_midi_sweep(
                control_values,
                step_duration,
                config['control']
            )
            
            if not sweep_success:
                logging.error("MIDI sweep failed")
                return False
            
            # Stop note
            if self.midi_controller:
                self._send_note_off(config['midi_note'])
            
            # Trim audio to exact length
            if len(recorded_audio) > total_samples:
                recorded_audio = recorded_audio[:total_samples]
            elif len(recorded_audio) < total_samples:
                # Pad with silence if needed
                padding = np.zeros((total_samples - len(recorded_audio), recorded_audio.shape[1]), 
                                 dtype=recorded_audio.dtype)
                recorded_audio = np.vstack([recorded_audio, padding])
            
            # Save wavetable file
            filename = f"{config['name']}-wavetable-{curve_type}-{config['samples_per_waveform']}.wav"
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
    
    def _perform_midi_sweep(self, control_values: List[int], 
                           step_duration: float, control_info: Dict) -> bool:
        """Perform the MIDI parameter sweep."""
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
                self.midi_controller.send_cc(
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
        """Send MIDI note on."""
        if self.midi_controller:
            try:
                self.midi_controller.send_note_on(midi_note, velocity, channel)
                return True
            except Exception as e:
                logging.error(f"Failed to send note on: {e}")
        return False
    
    def _send_note_off(self, midi_note: int, channel: int = 0) -> bool:
        """Send MIDI note off."""
        if self.midi_controller:
            try:
                self.midi_controller.send_note_off(midi_note, channel)
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