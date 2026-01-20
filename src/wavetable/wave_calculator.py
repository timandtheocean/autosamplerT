"""
Wave calculation utilities for wavetable creation.

Handles automatic note frequency calculation and sample length determination.
"""

import math
import logging
from typing import Tuple


class WaveCalculator:
    """Calculator for wavetable wave periods and optimal frequencies."""
    
    @staticmethod
    def calculate_optimal_note(sample_rate: int, samples_per_waveform: int) -> Tuple[float, int, str]:
        """
        Calculate the optimal note frequency for clean wave periods.
        
        Args:
            sample_rate: Audio sample rate in Hz
            samples_per_waveform: Target samples per wave period
            
        Returns:
            Tuple of (frequency_hz, midi_note_number, note_name)
        """
        # Calculate ideal frequency for exact period fit
        ideal_frequency = sample_rate / samples_per_waveform
        
        # Find closest MIDI note
        # MIDI note 69 (A4) = 440 Hz
        midi_note_float = 69 + 12 * math.log2(ideal_frequency / 440.0)
        midi_note = round(midi_note_float)
        
        # Calculate actual frequency for this MIDI note
        actual_frequency = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
        
        # Convert MIDI note to name
        note_name = WaveCalculator._midi_to_note_name(midi_note)
        
        logging.info(f"Optimal wavetable note: {note_name} (MIDI {midi_note}, {actual_frequency:.2f} Hz)")
        logging.info(f"Wave period: {sample_rate / actual_frequency:.2f} samples (target: {samples_per_waveform})")
        
        return actual_frequency, midi_note, note_name
    
    @staticmethod
    def calculate_sample_lengths(samples_per_waveform: int, number_of_waves: int, 
                                bit_depth: int, channels: int = 2) -> Tuple[int, int, float]:
        """
        Calculate total sample length and sweep length.
        
        Args:
            samples_per_waveform: Samples per wave period
            number_of_waves: Total number of waves in wavetable
            bit_depth: Audio bit depth (8, 16, 24)
            channels: Number of audio channels
            
        Returns:
            Tuple of (total_samples, sweep_samples, duration_seconds)
        """
        total_samples = samples_per_waveform * number_of_waves
        
        # Sweep is 1 wave period shorter than total length
        sweep_samples = total_samples - samples_per_waveform
        
        # Calculate duration assuming 44.1kHz (will be adjusted based on actual sample rate)
        duration_seconds = total_samples / 44100.0
        
        # Calculate file size for reference
        bytes_per_sample = bit_depth // 8
        total_bytes = total_samples * channels * bytes_per_sample
        
        logging.info(f"Wavetable length: {total_samples} samples ({number_of_waves} waves)")
        logging.info(f"Sweep length: {sweep_samples} samples ({number_of_waves - 1} waves)")
        logging.info(f"File size: {total_bytes / 1024:.1f} KB ({bit_depth}-bit, {channels} channels)")
        
        return total_samples, sweep_samples, duration_seconds
    
    @staticmethod
    def validate_wavetable_config(samples_per_waveform: int, number_of_waves: int) -> bool:
        """
        Validate wavetable configuration limits.
        
        Args:
            samples_per_waveform: Samples per wave period
            number_of_waves: Number of waves
            
        Returns:
            True if configuration is valid
        """
        # Check samples per waveform
        valid_samples = [128, 512, 1024, 2048, 4096]
        if samples_per_waveform not in valid_samples:
            logging.error(f"Invalid samples per waveform: {samples_per_waveform}. Must be one of: {valid_samples}")
            return False
        
        # Check number of waves limits
        if samples_per_waveform == 4096 and number_of_waves > 217:
            logging.error(f"Maximum 217 waves for 4096 samples per waveform (requested: {number_of_waves})")
            return False
        elif samples_per_waveform == 2048 and number_of_waves > 256:
            logging.error(f"Maximum 256 waves for 2048 samples per waveform (requested: {number_of_waves})")
            return False
        elif number_of_waves > 256:
            logging.error(f"Maximum 256 waves (requested: {number_of_waves})")
            return False
        
        if number_of_waves < 2:
            logging.error(f"Minimum 2 waves required (requested: {number_of_waves})")
            return False
            
        return True
    
    @staticmethod
    def calculate_wave_positions(total_samples: int, number_of_waves: int, samples_per_waveform: int) -> list:
        """
        Calculate sample positions for each wave in the wavetable.
        
        Args:
            total_samples: Total length of wavetable in samples
            number_of_waves: Number of waves
            samples_per_waveform: Samples per wave period
            
        Returns:
            List of (start_sample, end_sample) tuples for each wave
        """
        positions = []
        for wave_idx in range(number_of_waves):
            start_sample = wave_idx * samples_per_waveform
            end_sample = start_sample + samples_per_waveform
            positions.append((start_sample, min(end_sample, total_samples)))
            
        return positions
    
    @staticmethod
    def _midi_to_note_name(midi_note: int) -> str:
        """Convert MIDI note number to note name."""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note = notes[midi_note % 12]
        return f"{note}{octave}"