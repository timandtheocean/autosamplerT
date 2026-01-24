"""
DC offset removal for postprocessing
"""

import numpy as np
import logging


def remove_dc_offset(audio: np.ndarray) -> np.ndarray:
    """
    Remove DC offset from audio by subtracting mean.
    
    Args:
        audio: Audio data as numpy array
        
    Returns:
        Audio with DC offset removed
    """
    # Calculate mean per channel
    if audio.ndim == 2:
        # Stereo: remove DC offset per channel
        mean_per_channel = np.mean(audio, axis=0)
        corrected = audio - mean_per_channel
        
        if np.any(np.abs(mean_per_channel) > 0.001):
            logging.debug(f"DC offset removed: L={mean_per_channel[0]:.6f}, R={mean_per_channel[1]:.6f}")
    else:
        # Mono
        mean = np.mean(audio)
        corrected = audio - mean
        
        if abs(mean) > 0.001:
            logging.debug(f"DC offset removed: {mean:.6f}")
    
    return corrected
