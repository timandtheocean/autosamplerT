#!/usr/bin/env python3
"""
Test ASIO recording levels with device 16 to see actual signal levels.
"""

import os
# Enable ASIO before importing sounddevice  
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_asio_recording():
    """Test recording with ASIO device 16."""
    
    device_16 = sd.query_devices(16)
    host_api = sd.query_hostapis(device_16['hostapi'])
    
    print("=== ASIO RECORDING TEST ===")
    print(f"Device: {device_16['name']}")
    print(f"Host API: {host_api['name']}")
    print(f"Max channels: {device_16['max_input_channels']} in, {device_16['max_output_channels']} out")
    print()
    
    # Test with AsioSettings for channels 2,3 (0-indexed)
    channel_selectors = [2, 3]  # Channels 3-4 in 1-indexed terms
    settings = sd.AsioSettings(channel_selectors=channel_selectors)
    
    print(f"Recording 3 seconds from ASIO channels {channel_selectors} (3-4 in 1-indexed)...")
    
    try:
        # Record using ASIO
        audio = sd.rec(
            frames=3 * 44100,  # 3 seconds at 44.1kHz
            samplerate=44100,
            channels=2,  # Stereo
            dtype='float32',
            device=16,  # ASIO device
            extra_settings=settings
        )
        
        # Wait for recording
        sd.wait()
        
        print("Recording completed!")
        
        # Analyze levels
        if audio is not None and len(audio) > 0:
            peak_l = np.abs(audio[:, 0]).max()
            peak_r = np.abs(audio[:, 1]).max() if audio.shape[1] > 1 else 0
            rms_l = np.sqrt(np.mean(audio[:, 0] ** 2))
            rms_r = np.sqrt(np.mean(audio[:, 1] ** 2)) if audio.shape[1] > 1 else 0
            
            peak_db_l = 20 * np.log10(peak_l) if peak_l > 0 else -200
            peak_db_r = 20 * np.log10(peak_r) if peak_r > 0 else -200  
            rms_db_l = 20 * np.log10(rms_l) if rms_l > 0 else -200
            rms_db_r = 20 * np.log10(rms_r) if rms_r > 0 else -200
            
            print(f"\nASIO RECORDING LEVELS:")
            print(f"Left  - Peak: {peak_l:.6f} ({peak_db_l:.1f} dB), RMS: {rms_l:.6f} ({rms_db_l:.1f} dB)")
            print(f"Right - Peak: {peak_r:.6f} ({peak_db_r:.1f} dB), RMS: {rms_r:.6f} ({rms_db_r:.1f} dB)")
            
            # Check bit depth utilization
            for bitdepth in [16, 24]:
                max_int = 32767 if bitdepth == 16 else 8388607
                peak_int = int(peak_l * max_int) if peak_l > 0 else 0
                usage_percent = peak_l * 100 if peak_l > 0 else 0
                print(f"{bitdepth}-bit utilization: {peak_int:,} (of {max_int:,}), {usage_percent:.3f}% of range")
                
            # Save test file
            import soundfile as sf
            sf.write("test_asio_recording.wav", audio, 44100, subtype='PCM_24')
            print(f"\nSaved to: test_asio_recording.wav")
            
            # Show what +10dB would do
            gain_10db = 10 ** (10 / 20.0)  # 3.16x
            would_clip = (peak_l * gain_10db) > 1.0
            new_peak = peak_l * gain_10db
            print(f"\nWith +10dB gain (3.16x):")
            print(f"New peak would be: {new_peak:.6f} {'[CLIPPED!]' if would_clip else '[OK]'}")
            
        else:
            print("Recording failed - no audio data returned")
            
    except Exception as e:
        print(f"ASIO recording failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_asio_recording()