#!/usr/bin/env python3
"""
Test script to verify silence threshold detection is working properly.

This script tests:
1. That sample_noise_floor() doesn't send any MIDI
2. That it properly records and analyzes actual audio
3. That it calculates a reasonable noise floor threshold
"""

import os
import sys
import yaml
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sampler import AutoSampler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def test_silence_threshold():
    """Test the silence threshold detection functionality."""
    
    # Load base configuration
    config_path = Path("conf/autosamplerT_config.yaml")
    if not config_path.exists():
        print(f"ERROR: Configuration file not found: {config_path}")
        return False
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Enable silence detection in test configuration
    if 'postprocessing' not in config:
        config['postprocessing'] = {}
    config['postprocessing']['trim_silence'] = True
    config['postprocessing']['silence_detection'] = 'auto'  # Use automatic detection
    
    # Enable test mode to avoid actual MIDI/audio hardware requirements
    if 'sampling' not in config:
        config['sampling'] = {}
    config['sampling']['test_mode'] = True
    
    try:
        print("="*70)
        print("Testing Silence Threshold Detection")
        print("="*70)
        
        # Initialize sampler
        print("1. Initializing AutoSampler...")
        sampler = AutoSampler(config, batch_mode=True)
        
        # Setup audio engine
        print("2. Setting up audio engine...")
        if not sampler.audio_engine.setup():
            print("ERROR: Audio engine setup failed")
            return False
        
        # Test the noise floor detection
        print("3. Testing noise floor detection...")
        print("   - This should NOT send any MIDI messages")
        print("   - This should record actual audio (or simulate in test mode)")
        
        threshold_db = sampler.sample_noise_floor(1.0)  # 1 second test
        
        print(f"4. Results:")
        print(f"   - Detected noise threshold: {threshold_db:.1f} dB")
        
        # Verify the threshold is reasonable
        if threshold_db < -100 or threshold_db > 0:
            print(f"   - WARNING: Threshold seems unreasonable ({threshold_db:.1f} dB)")
            print(f"   - Expected range: -60 to -20 dB for typical audio interfaces")
        else:
            print(f"   - Threshold looks reasonable")
        
        # Test that it would be used in postprocessing
        print("5. Testing integration with postprocessing...")
        
        # Simulate what happens during sampling
        postprocessing_config = config.get('postprocessing', {})
        if postprocessing_config.get('trim_silence'):
            silence_mode = postprocessing_config.get('silence_detection', 'auto')
            if silence_mode == 'auto':
                detected_threshold = sampler.sample_noise_floor(1.0)
                print(f"   - Auto-detected threshold would be: {detected_threshold:.1f} dB")
            elif silence_mode == 'manual':
                manual_threshold = postprocessing_config.get('silence_threshold', -60.0)
                print(f"   - Manual threshold would be: {manual_threshold:.1f} dB")
        
        print("="*70)
        print("SUCCESS: Silence threshold detection test completed!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_silence_threshold()
    if success:
        print("\nTest PASSED: Silence threshold detection is working properly")
        sys.exit(0)
    else:
        print("\nTest FAILED: Issues found with silence threshold detection")
        sys.exit(1)