"""
Silence trimming operation for postprocessing
"""

import numpy as np
import logging


def trim_silence(audio: np.ndarray, samplerate: int, threshold_db: float = -60.0) -> np.ndarray:
    """
    Trim silence from beginning and end of audio.
    
    Args:
        audio: Audio data as numpy array
        samplerate: Sample rate in Hz
        threshold_db: Silence threshold in dB
        
    Returns:
        Trimmed audio
    """
    # Convert threshold from dB to linear
    threshold_linear = 10 ** (threshold_db / 20.0)
    
    # Calculate RMS in small windows
    window_size = int(samplerate * 0.01)  # 10ms windows
    
    if len(audio) < window_size:
        logging.warning("Audio too short to trim silence")
        return audio
    
    # Calculate envelope (max of all channels)
    if audio.ndim == 2:
        envelope = np.max(np.abs(audio), axis=1)
    else:
        envelope = np.abs(audio)
    
    # Find start (first sample above threshold)
    start_idx = 0
    for i in range(0, len(envelope) - window_size, window_size // 2):
        window = envelope[i:i + window_size]
        if np.max(window) > threshold_linear:
            start_idx = max(0, i - window_size)  # Include one window before
            break
    
    # Find end (last sample above threshold)
    end_idx = len(audio)
    for i in range(len(envelope) - window_size, 0, -window_size // 2):
        window = envelope[i:i + window_size]
        if np.max(window) > threshold_linear:
            end_idx = min(len(audio), i + window_size * 2)  # Include one window after
            break
    
    # Trim
    trimmed = audio[start_idx:end_idx]
    
    trimmed_samples = len(audio) - len(trimmed)
    trimmed_seconds = trimmed_samples / samplerate
    
    if trimmed_samples > 0:
        logging.debug(f"Trimmed {trimmed_seconds:.3f}s of silence (threshold: {threshold_db:.1f}dB)")
    
    return trimmed
