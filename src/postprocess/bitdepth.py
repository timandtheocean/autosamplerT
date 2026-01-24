"""
Bitdepth conversion for postprocessing
"""

import numpy as np
import logging


def convert_bitdepth(audio: np.ndarray, target_bitdepth: int, dither: bool = False) -> np.ndarray:
    """
    Convert audio to different bit depth.
    
    Args:
        audio: Audio data as numpy array (float32, -1.0 to 1.0)
        target_bitdepth: Target bit depth (8, 16, 24, 32)
        dither: Apply dithering when reducing bit depth
        
    Returns:
        Audio converted to target bit depth (still as float32)
    """
    if target_bitdepth not in [8, 16, 24, 32]:
        logging.warning(f"Unsupported bit depth: {target_bitdepth}, skipping conversion")
        return audio
    
    # Placeholder - actual bitdepth conversion happens during file save
    # This is here for future implementation if needed
    logging.debug(f"Bitdepth conversion to {target_bitdepth}-bit (applied during save)")
    
    return audio
