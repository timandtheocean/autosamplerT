#!/usr/bin/env python3
"""
Quick audio analysis script to check peak levels and detect silence
"""
import sys
import numpy as np
import soundfile as sf
import os

def analyze_audio(wav_path):
    """Analyze audio file for peak levels and silence"""
    if not os.path.exists(wav_path):
        print(f"File not found: {wav_path}")
        return
    
    try:
        # Load audio data
        audio, samplerate = sf.read(wav_path, dtype='float32')
        
        # Calculate stats
        peak_level = np.max(np.abs(audio))
        rms_level = np.sqrt(np.mean(audio**2))
        duration = len(audio) / samplerate
        
        # Check for silence (very low levels)
        is_silence = peak_level < 0.001  # -60dB threshold
        
        print(f"=== {os.path.basename(wav_path)} ===")
        print(f"Duration: {duration:.2f}s")
        print(f"Peak Level: {peak_level:.6f} ({20*np.log10(peak_level):.1f} dB)" if peak_level > 0 else "Peak Level: -inf dB (silence)")
        print(f"RMS Level: {rms_level:.6f} ({20*np.log10(rms_level):.1f} dB)" if rms_level > 0 else "RMS Level: -inf dB (silence)")
        print(f"Silent: {'YES' if is_silence else 'NO'}")
        
        # Sample some values from different parts
        if len(audio) > 1000:
            start_sample = audio[1000]
            mid_sample = audio[len(audio)//2]
            end_sample = audio[-1000]
            print(f"Sample values: start={start_sample:.6f}, mid={mid_sample:.6f}, end={end_sample:.6f}")
        
        print()
        
    except Exception as e:
        print(f"Error analyzing {wav_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_audio.py <wav_file> [wav_file2] ...")
        sys.exit(1)
    
    for wav_file in sys.argv[1:]:
        analyze_audio(wav_file)