#!/usr/bin/env python3
"""
Quick script to reprocess the problematic G#3 RR1 sample with fixed silence trimming
"""

import numpy as np
import soundfile as sf
import os
from src.postprocess import PostProcessor

def fix_sample():
    sample_path = 'output/Prophet_Program_0/samples/Prophet_Program_0_G#3_v127_rr1.wav'
    
    # Load the original sample
    print(f"Loading: {sample_path}")
    audio, sr = sf.read(sample_path)
    print(f"Original: {len(audio)} frames ({len(audio)/sr:.2f}s)")
    
    # Create PostProcessor
    pp = PostProcessor()
    
    # Process just this one sample using the file-based method
    operations = {
        'auto_loop': True,
        'loop_crossfade_percent': 10,
        'trim_silence': True
    }
    
    pp.process_samples([sample_path], operations)
    
    # Analyze the result
    fixed_audio, _ = sf.read(sample_path)
    print(f"Fixed: {len(fixed_audio)} frames ({len(fixed_audio)/sr:.2f}s)")
    
    peak = np.max(np.abs(fixed_audio))
    rms = np.sqrt(np.mean(fixed_audio ** 2))
    print(f"Fixed sample stats: Peak={peak:.6f} ({20*np.log10(peak):.1f}dB), RMS={rms:.6f} ({20*np.log10(rms):.1f}dB)")

if __name__ == "__main__":
    fix_sample()