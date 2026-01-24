"""
Normalization operations for postprocessing
"""

import numpy as np
import logging
from pathlib import Path
from typing import List


def normalize_sample(audio: np.ndarray, target_level: float = 0.95) -> np.ndarray:
    """
    Normalize single sample to target peak level.
    
    Args:
        audio: Audio data as numpy array
        target_level: Target peak amplitude (0.0-1.0)
        
    Returns:
        Normalized audio
    """
    peak = np.abs(audio).max()
    
    if peak > 0:
        scale_factor = target_level / peak
        normalized = audio * scale_factor
        logging.debug(f"Sample normalized: peak {peak:.3f} -> {target_level:.3f}")
        return normalized
    else:
        logging.warning("Audio is silent, cannot normalize")
        return audio


def normalize_patch(sample_paths: List[str], target_level: float = 0.95) -> None:
    """
    Normalize all samples in a patch to the same global peak level.
    Reads all files, finds global peak, then saves all files normalized.
    
    Args:
        sample_paths: List of WAV file paths
        target_level: Target peak amplitude (0.0-1.0)
    """
    import soundfile as sf
    
    if not sample_paths:
        logging.warning("No samples to normalize")
        return
    
    logging.info(f"Patch normalization: analyzing {len(sample_paths)} samples...")
    
    # Step 1: Find global peak across all samples
    global_peak = 0.0
    audio_data = []
    
    for path in sample_paths:
        try:
            audio, samplerate = sf.read(path, always_2d=True)
            audio_data.append((audio, samplerate, path))
            peak = np.abs(audio).max()
            global_peak = max(global_peak, peak)
        except Exception as e:
            logging.error(f"Failed to read {path}: {e}")
    
    if global_peak == 0:
        logging.warning("All samples are silent, cannot normalize")
        return
    
    # Step 2: Calculate scale factor
    scale_factor = target_level / global_peak
    logging.info(f"Global peak: {global_peak:.3f}, scale factor: {scale_factor:.3f}")
    
    # Step 3: Apply normalization and save
    for audio, samplerate, path in audio_data:
        try:
            normalized = audio * scale_factor
            sf.write(path, normalized, samplerate, subtype='PCM_24')
            logging.debug(f"Normalized: {Path(path).name}")
        except Exception as e:
            logging.error(f"Failed to save normalized {path}: {e}")
    
    logging.info(f"Patch normalization complete: {len(audio_data)} samples normalized")
