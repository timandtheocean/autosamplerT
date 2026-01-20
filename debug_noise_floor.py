#!/usr/bin/env python3
"""
Detailed debug test for noise floor measurement and threshold calculation.
"""

import os
import sys
import yaml
import numpy as np
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sampler import AutoSampler

def debug_noise_threshold():
    """Debug the noise floor measurement and threshold calculation."""
    
    # Load configuration
    config_path = Path("conf/autosamplerT_config.yaml")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    config['postprocessing'] = {'trim_silence': True, 'silence_detection': 'auto'}
    config['sampling'] = {'test_mode': False}
    
    print("=== DETAILED NOISE FLOOR DEBUG ===")
    
    sampler = AutoSampler(config, batch_mode=True)
    sampler.audio_engine.setup()
    
    # Record multiple measurements
    print("Recording 5 measurements of 2 seconds each...")
    measurements = []
    
    for i in range(5):
        print(f"\nMeasurement {i+1}:")
        silence_audio = sampler.audio_engine.record(2.0)
        if silence_audio is not None:
            silence_rms = np.sqrt(np.mean(silence_audio ** 2))
            noise_floor_db = 20 * np.log10(silence_rms + 1e-10)
            measurements.append(noise_floor_db)
            
            # Show what threshold would be calculated (using the new logic)
            threshold = noise_floor_db + 0.1
                
            print(f"  Raw noise floor: {noise_floor_db:.1f} dB")
            print(f"  Threshold would be: {threshold:.1f} dB (raw + 0.1dB)")
    
    if measurements:
        avg_noise = sum(measurements) / len(measurements)
        print(f"\n=== SUMMARY ===")
        print(f"Average noise floor: {avg_noise:.1f} dB")
        print(f"Range: {min(measurements):.1f} to {max(measurements):.1f} dB")
        print(f"All measurements: {[f'{x:.1f}' for x in measurements]}")
        
        # Test the actual method
        print(f"\n=== TESTING sample_noise_floor() METHOD ===")
        calculated_threshold = sampler.sample_noise_floor(2.0)
        print(f"Method returned threshold: {calculated_threshold:.1f} dB")

if __name__ == "__main__":
    debug_noise_threshold()