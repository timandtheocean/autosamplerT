"""
Gain boost operation for postprocessing
Applies simple dB gain to audio samples
"""

import numpy as np
import logging


def apply_gain(audio: np.ndarray, gain_db: float = 0.0) -> np.ndarray:
    """
    Apply gain boost to audio.
    
    Args:
        audio: Audio data as numpy array (float32, range -1.0 to 1.0)
        gain_db: Gain in decibels (e.g., +10.0 for +10dB boost)
        
    Returns:
        Audio with gain applied
    """
    if gain_db == 0.0:
        return audio
    
    # Convert dB to linear multiplier
    # Formula: linear = 10^(dB/20)
    gain_linear = 10 ** (gain_db / 20.0)
    
    # Apply gain
    gained_audio = audio * gain_linear
    
    logging.debug(f"Applied gain: {gain_db:+.1f}dB (linear multiplier: {gain_linear:.3f}x)")
    
    return gained_audio
