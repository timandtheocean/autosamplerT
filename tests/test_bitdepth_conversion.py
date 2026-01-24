#!/usr/bin/env python3
"""
Test script to verify bit depth conversion and recording levels.
This will help diagnose if WDM is recording at very low levels.
"""

import os
import sys
import logging
import numpy as np
import soundfile as sf
import sounddevice as sd
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sampling.audio_engine import AudioEngine

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_float_to_bitdepth_conversion():
    """Test how different float32 levels convert to different bit depths."""
    print("=== FLOAT32 TO BIT DEPTH CONVERSION TEST ===")
    
    # Test different signal levels
    test_levels = [1.0, 0.5, 0.1, 0.01, 0.001]  # Full scale to very quiet
    
    for level in test_levels:
        # Create test signal at this level
        samplerate = 44100
        duration = 0.1  # 100ms
        samples = int(duration * samplerate)
        
        # Generate sine wave at this amplitude
        t = np.linspace(0, duration, samples)
        freq = 440  # A4
        signal = level * np.sin(2 * np.pi * freq * t)
        
        # Make stereo
        signal_stereo = np.column_stack([signal, signal])
        
        # Test each bit depth
        for bitdepth in [16, 24, 32]:
            subtype = f'PCM_{bitdepth}'
            filename = f"test_level_{level:.3f}_bit{bitdepth}.wav"
            
            # Write and read back
            sf.write(filename, signal_stereo, samplerate, subtype=subtype)
            read_signal, _ = sf.read(filename)
            
            # Calculate actual levels
            peak_written = np.abs(signal_stereo).max()
            peak_read = np.abs(read_signal).max()
            
            # Calculate theoretical max for this bit depth
            if bitdepth == 16:
                max_int = 32767
            elif bitdepth == 24:
                max_int = 8388607  # 2^23 - 1
            elif bitdepth == 32:
                max_int = 2147483647  # 2^31 - 1
                
            # How much of bit depth range are we using?
            usage_percent = (peak_written * max_int / max_int) * 100
            
            print(f"  Level {level:.3f} -> {bitdepth}-bit: "
                  f"Peak written: {peak_written:.6f}, Peak read: {peak_read:.6f}, "
                  f"Bit depth usage: {usage_percent:.1f}%")
            
            # Clean up
            os.remove(filename)
    
    print()

def test_actual_recording_levels():
    """Test actual recording levels from the configured device."""
    print("=== ACTUAL RECORDING LEVELS TEST ===")
    
    try:
        # Load audio config
        import yaml
        with open('conf/autosamplerT_config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize audio engine
        audio_config = config['audio_interface']
        engine = AudioEngine(audio_config, test_mode=False)
        
        print(f"Recording from device {engine.input_device} for 2 seconds...")
        
        # Record 2 seconds
        audio = engine.record(2.0)
        
        if audio is not None:
            # Analyze levels
            peak_l = np.abs(audio[:, 0]).max() if audio.shape[1] > 0 else 0
            peak_r = np.abs(audio[:, 1]).max() if audio.shape[1] > 1 else 0
            rms_l = np.sqrt(np.mean(audio[:, 0] ** 2)) if audio.shape[1] > 0 else 0
            rms_r = np.sqrt(np.mean(audio[:, 1] ** 2)) if audio.shape[1] > 1 else 0
            
            peak_db_l = 20 * np.log10(peak_l) if peak_l > 0 else -200
            peak_db_r = 20 * np.log10(peak_r) if peak_r > 0 else -200
            rms_db_l = 20 * np.log10(rms_l) if rms_l > 0 else -200
            rms_db_r = 20 * np.log10(rms_r) if rms_r > 0 else -200
            
            print(f"RECORDED LEVELS (float32):")
            print(f"  Left  - Peak: {peak_l:.6f} ({peak_db_l:.1f} dB), RMS: {rms_l:.6f} ({rms_db_l:.1f} dB)")
            print(f"  Right - Peak: {peak_r:.6f} ({peak_db_r:.1f} dB), RMS: {rms_r:.6f} ({rms_db_r:.1f} dB)")
            
            # Show what this means for different bit depths
            print(f"\nBIT DEPTH UTILIZATION:")
            for bitdepth in [16, 24]:
                if bitdepth == 16:
                    max_int = 32767
                elif bitdepth == 24:
                    max_int = 8388607
                
                peak_int = int(peak_l * max_int) if peak_l > 0 else 0
                usage_percent = (peak_l * 100) if peak_l > 0 else 0
                
                print(f"  {bitdepth}-bit: Peak = {peak_int:,} (of {max_int:,} max), "
                      f"Using {usage_percent:.2f}% of range")
            
            # Save test file for comparison
            test_file = "test_recorded_levels.wav"
            success = engine.save_audio(test_file, audio)
            if success:
                print(f"\nSaved recording to: {test_file}")
                
                # Read it back and compare
                read_audio, _ = sf.read(test_file)
                read_peak = np.abs(read_audio).max()
                print(f"Read back peak: {read_peak:.6f}")
        else:
            print("Recording failed!")
            
    except Exception as e:
        print(f"Recording test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_float_to_bitdepth_conversion()
    test_actual_recording_levels()