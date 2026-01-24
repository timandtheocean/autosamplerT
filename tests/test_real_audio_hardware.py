#!/usr/bin/env python3
"""
Test silence threshold detection with REAL AUDIO HARDWARE.

This test disables test mode and attempts to use your actual audio interface
to record real silence and measure the actual noise floor.

WARNING: This requires:
1. Audio interface to be connected and working
2. Proper ASIO drivers installed (if using ASIO)
3. Correct device configuration in autosamplerT_config.yaml
"""

import os
import sys
import yaml
import logging
import numpy as np
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sampler import AutoSampler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def test_real_audio_interface():
    """Test silence threshold with real audio hardware."""
    
    print("="*70)
    print("REAL AUDIO HARDWARE TEST")
    print("="*70)
    print("WARNING: This will attempt to use your actual audio interface!")
    print("Make sure:")
    print("1. Audio interface is connected and powered on")
    print("2. ASIO drivers are installed (if using ASIO)")
    print("3. No audio playing (we want to measure true noise floor)")
    print("4. Synthesizer is connected but NOT playing anything")
    print()
    
    # Ask for confirmation unless in batch mode
    if '--yes' not in sys.argv:
        response = input("Continue with real hardware test? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("Test cancelled.")
            return False
    
    try:
        # Load configuration
        config_path = Path("conf/autosamplerT_config.yaml")
        if not config_path.exists():
            print(f"ERROR: Configuration file not found: {config_path}")
            return False
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Enable silence detection but DISABLE test mode for real hardware
        if 'postprocessing' not in config:
            config['postprocessing'] = {}
        config['postprocessing']['trim_silence'] = True
        config['postprocessing']['silence_detection'] = 'auto'
        
        if 'sampling' not in config:
            config['sampling'] = {}
        config['sampling']['test_mode'] = False  # REAL HARDWARE MODE
        
        print("1. Configuration:")
        print(f"   Audio Input Device: {config['audio_interface'].get('input_device_index', 'default')}")
        print(f"   Sample Rate: {config['audio_interface'].get('samplerate', 44100)} Hz")
        print(f"   Channels: {config['audio_interface'].get('mono_stereo', 'stereo')}")
        print(f"   Channel Offset: {config['audio_interface'].get('channel_offset', 0)}")
        print(f"   Test Mode: {config['sampling']['test_mode']} (REAL HARDWARE)")
        print()
        
        print("2. Initializing AutoSampler...")
        sampler = AutoSampler(config, batch_mode=True)
        
        print("3. Setting up audio engine...")
        if not sampler.audio_engine.setup():
            print("ERROR: Audio engine setup failed!")
            print("Check:")
            print("- Audio interface is connected and powered on")
            print("- Device indices in config are correct")
            print("- ASIO drivers are installed (if using ASIO)")
            return False
        
        print("4. Recording REAL SILENCE from your audio interface...")
        print("   Duration: 3 seconds")
        print("   Please ensure NO AUDIO is playing!")
        print("   Measuring noise floor of your signal chain...")
        print()
        
        # Record real noise floor
        threshold_db = sampler.sample_noise_floor(3.0)  # 3 seconds for accuracy
        
        print("5. RESULTS:")
        print(f"   Measured Noise Floor: {threshold_db - 6.0:.1f} dB")  # Remove the 6dB margin to show raw noise
        print(f"   Calculated Threshold: {threshold_db:.1f} dB (noise floor + 6dB margin)")
        print()
        
        # Analyze results
        raw_noise_floor = threshold_db - 6.0
        print("6. ANALYSIS:")
        if raw_noise_floor < -80:
            print("   EXCELLENT: Very quiet audio interface (professional grade)")
        elif raw_noise_floor < -70:
            print("   VERY GOOD: Clean audio interface")
        elif raw_noise_floor < -60:
            print("   GOOD: Acceptable noise floor for sampling")
        elif raw_noise_floor < -50:
            print("   FAIR: Higher noise floor, may affect quiet samples")
        else:
            print("   POOR: High noise floor - check connections and gain staging")
            
        print(f"   Recommended manual threshold: {raw_noise_floor + 10:.1f} dB")
        print()
        
        # Test a short recording to verify it works
        print("7. Testing short recording...")
        test_audio = sampler.audio_engine.record(0.5)
        if test_audio is not None:
            rms = np.sqrt(np.mean(test_audio ** 2))
            test_db = 20 * np.log10(rms + 1e-10)
            print(f"   Test recording RMS: {test_db:.1f} dB")
            print("   SUCCESS: Audio recording is working!")
        else:
            print("   ERROR: Test recording failed!")
            return False
        
        print("="*70)
        print("REAL HARDWARE TEST COMPLETED SUCCESSFULLY!")
        print("="*70)
        print(f"Your system's noise floor: {raw_noise_floor:.1f} dB")
        print(f"AutoSampler will use: {threshold_db:.1f} dB for silence trimming")
        print()
        
        return True
        
    except Exception as e:
        print(f"ERROR: Real hardware test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("This could be due to:")
        print("- Audio interface not connected or configured incorrectly")
        print("- Missing or incorrect ASIO drivers")
        print("- Device busy (close other audio applications)")
        print("- Incorrect device indices in configuration")
        return False

if __name__ == "__main__":
    success = test_real_audio_interface()
    if success:
        print("✅ REAL HARDWARE TEST PASSED")
        sys.exit(0) 
    else:
        print("❌ REAL HARDWARE TEST FAILED")
        sys.exit(1)