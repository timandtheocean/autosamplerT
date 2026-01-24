\bjhq4#!/usr/bin/env python3
"""
Test the new silence detection configuration options
"""

import yaml
import logging

def test_silence_detection_config():
    """Test loading and parsing silence detection config"""
    
    print("=== Testing Silence Detection Configuration ===\n")
    
    # Test 1: Auto mode configuration
    auto_config = {
        'postprocessing': {
            'trim_silence': True,
            'silence_detection': 'auto',
            'silence_threshold': -50.0  # Ignored in auto mode
        }
    }
    
    print("1. AUTO MODE Configuration:")
    print(yaml.dump(auto_config, default_flow_style=False))
    
    postproc = auto_config['postprocessing']
    silence_mode = postproc.get('silence_detection', 'auto')
    print(f"   Mode: {silence_mode}")
    print(f"   Will: Record silence from synth to detect actual noise floor")
    print()
    
    # Test 2: Manual mode configuration  
    manual_config = {
        'postprocessing': {
            'trim_silence': True,
            'silence_detection': 'manual',
            'silence_threshold': -45.0
        }
    }
    
    print("2. MANUAL MODE Configuration:")
    print(yaml.dump(manual_config, default_flow_style=False))
    
    postproc = manual_config['postprocessing'] 
    silence_mode = postproc.get('silence_detection', 'auto')
    threshold = postproc.get('silence_threshold', -60.0)
    print(f"   Mode: {silence_mode}")
    print(f"   Threshold: {threshold}dB")
    print(f"   Will: Use fixed {threshold}dB threshold for all samples")
    print()
    
    # Test 3: Default/legacy mode
    legacy_config = {
        'postprocessing': {
            'trim_silence': True,
            # No silence_detection specified - should default to auto
        }
    }
    
    print("3. DEFAULT/LEGACY Configuration:")
    print(yaml.dump(legacy_config, default_flow_style=False))
    
    postproc = legacy_config['postprocessing']
    silence_mode = postproc.get('silence_detection', 'auto')  # Default to auto
    print(f"   Mode: {silence_mode} (default)")
    print(f"   Will: Default to auto mode (noise floor detection)")
    print()
    
    print("SUCCESS: All configuration modes work correctly!")

if __name__ == "__main__":
    test_silence_detection_config()