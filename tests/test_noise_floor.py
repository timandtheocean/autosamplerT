#!/usr/bin/env python3
"""
Test the new noise floor detection system
"""

import numpy as np
from src.sampler import AutoSampler
import logging

def test_noise_floor_detection():
    """Test noise floor detection functionality"""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    print("=== Testing Noise Floor Detection ===")
    
    # Create a minimal config
    test_config = {
        'audio': {
            'samplerate': 44100,
            'bitdepth': 24,
            'mono_stereo': 'mono',
            'input_device': None,  # Use default
            'output_device': None
        },
        'midi_interface': {
            'output_port_name': None
        },
        'sampling': {
            'hold_time': 1.0,
            'release_time': 0.5
        },
        'postprocessing': {
            'trim_silence': True
        }
    }
    
    try:
        # Create sampler instance
        sampler = AutoSampler(test_config)
        
        # Test noise floor detection
        threshold = sampler.sample_noise_floor(1.0)  # 1 second test
        
        print(f"Test result: Detected threshold = {threshold:.1f}dB")
        print("SUCCESS: Noise floor detection method is working!")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    test_noise_floor_detection()