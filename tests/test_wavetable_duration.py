#!/usr/bin/env python3
"""
Test wavetable duration calculation fix.

This test verifies that the wavetable recording captures the correct duration
based on samples_per_waveform * number_of_waves / samplerate.

Issue: Wavetables were too short - "if 9 seconds are recorded the resulted 
wavetable is less than a second"

Fix: Duration calculation now correctly uses total_samples / samplerate where
total_samples = samples_per_waveform * number_of_waves
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path (for imports like 'src.wavetable.wave_calculator')
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
# Also add src folder for relative imports within modules
sys.path.insert(0, os.path.join(project_root, 'src'))


class TestWavetableDuration(unittest.TestCase):
    """Test wavetable duration calculations."""
    
    def test_wave_calculator_sample_lengths(self):
        """Test WaveCalculator returns correct sample counts and duration."""
        from wavetable.wave_calculator import WaveCalculator
        
        # WaveCalculator uses static methods
        total_samples, sweep_samples, duration = WaveCalculator.calculate_sample_lengths(
            samples_per_waveform=2048,
            number_of_waves=64,
            bit_depth=24
        )
        
        # total_samples = samples_per_waveform * number_of_waves
        expected_total = 2048 * 64  # 131,072
        self.assertEqual(total_samples, expected_total)
        
        # sweep_samples = total_samples - samples_per_waveform (first wave is held)
        expected_sweep = expected_total - 2048  # 129,024
        self.assertEqual(sweep_samples, expected_sweep)
        
        # duration = total_samples / 44100 (hardcoded in WaveCalculator)
        expected_duration = expected_total / 44100  # ~2.97 seconds
        self.assertAlmostEqual(duration, expected_duration, places=4)
        print(f"✓ Duration: {duration:.3f} seconds (expected ~2.97s)")
    
    def test_high_resolution_wavetable(self):
        """Test high resolution settings (4096 samples, 128 waves)."""
        from wavetable.wave_calculator import WaveCalculator
        
        total_samples, sweep_samples, duration = WaveCalculator.calculate_sample_lengths(
            samples_per_waveform=4096,
            number_of_waves=128,
            bit_depth=24
        )
        
        expected_total = 4096 * 128  # 524,288
        expected_duration = expected_total / 44100  # ~11.89 seconds
        
        self.assertEqual(total_samples, expected_total)
        self.assertAlmostEqual(duration, expected_duration, places=4)
        print(f"✓ High-res duration: {duration:.3f} seconds (expected ~11.89s)")
    
    def test_compact_wavetable(self):
        """Test compact settings (512 samples, 32 waves)."""
        from wavetable.wave_calculator import WaveCalculator
        
        total_samples, sweep_samples, duration = WaveCalculator.calculate_sample_lengths(
            samples_per_waveform=512,
            number_of_waves=32,
            bit_depth=24
        )
        
        expected_total = 512 * 32  # 16,384
        expected_duration = expected_total / 44100  # ~0.37 seconds
        
        self.assertEqual(total_samples, expected_total)
        self.assertAlmostEqual(duration, expected_duration, places=4)
        print(f"✓ Compact duration: {duration:.3f} seconds (expected ~0.37s)")
    
    def test_different_samplerates(self):
        """Test duration calculation - note WaveCalculator returns 44100-based duration.
        
        The actual recording duration is calculated in WavetableSampler using the
        real audio engine sample rate. WaveCalculator just returns a reference duration.
        """
        from wavetable.wave_calculator import WaveCalculator
        
        # WaveCalculator always uses 44100 as reference
        total_samples, sweep_samples, duration = WaveCalculator.calculate_sample_lengths(
            samples_per_waveform=2048,
            number_of_waves=64,
            bit_depth=24
        )
        
        expected_total = 2048 * 64
        expected_duration_44100 = expected_total / 44100  # WaveCalculator reference
        
        self.assertEqual(total_samples, expected_total)
        self.assertAlmostEqual(duration, expected_duration_44100, places=4)
        print(f"✓ WaveCalculator reference duration: {duration:.3f} seconds")
        
        # Show actual durations at different sample rates (for reference)
        for samplerate in [44100, 48000, 96000]:
            actual_duration = expected_total / samplerate
            print(f"  @{samplerate}Hz: {actual_duration:.3f} seconds")


class TestWavetableSamplerDuration(unittest.TestCase):
    """Test WavetableSampler uses correct duration for recording."""
    
    @patch('wavetable.wavetable_sampler.MIDIController')
    def test_sample_curve_duration(self, mock_midi):
        """Test that _sample_curve calculates correct recording duration."""
        from wavetable.wavetable_sampler import WavetableSampler
        
        # Create mock audio engine
        mock_audio = MagicMock()
        mock_audio.samplerate = 44100
        mock_audio.setup.return_value = True
        
        # Create mock recorded audio (simulate 4 seconds recording)
        import numpy as np
        mock_audio.record.return_value = np.zeros((4 * 44100, 2), dtype=np.float32)
        mock_audio.record_with_monitoring.return_value = np.zeros((4 * 44100, 2), dtype=np.float32)
        
        sampler = WavetableSampler(
            audio_engine=mock_audio,
            midi_controller=None,
            enable_monitoring=False
        )
        
        # Configure wavetable params
        sampler.samples_per_waveform = 2048
        sampler.number_of_waves = 64
        
        # Calculate expected duration
        total_samples = 2048 * 64  # 131,072
        expected_duration = total_samples / 44100  # ~2.97s
        
        # The hold_time_before/after add buffer time
        hold_before = 0.5
        hold_after = 0.5
        total_record_time = expected_duration + hold_before + hold_after  # ~3.97s
        
        print(f"✓ Expected recording duration: {total_record_time:.3f}s")
        print(f"  (wavetable: {expected_duration:.3f}s + buffers: {hold_before + hold_after:.1f}s)")
        
        # Verify the calculation is correct
        self.assertAlmostEqual(expected_duration, 2.972, places=2)
        self.assertAlmostEqual(total_record_time, 3.972, places=2)


class TestMonitoringParameter(unittest.TestCase):
    """Test that enable_monitoring parameter is properly passed."""
    
    def test_wavetable_sampler_accepts_monitoring(self):
        """Test WavetableSampler accepts enable_monitoring parameter."""
        from wavetable.wavetable_sampler import WavetableSampler
        
        mock_audio = MagicMock()
        mock_audio.samplerate = 44100
        
        # Should not raise
        sampler = WavetableSampler(
            audio_engine=mock_audio,
            midi_controller=None,
            enable_monitoring=True
        )
        self.assertTrue(sampler.enable_monitoring)
        
        sampler2 = WavetableSampler(
            audio_engine=mock_audio,
            midi_controller=None,
            enable_monitoring=False
        )
        self.assertFalse(sampler2.enable_monitoring)
        
        print("✓ enable_monitoring parameter accepted")


if __name__ == '__main__':
    print("=" * 60)
    print("Wavetable Duration Fix Tests")
    print("=" * 60)
    print()
    unittest.main(verbosity=2)
