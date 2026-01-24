"""
Main postprocessing orchestrator
Runs after ALL sampling is complete for a patch
"""

import logging
import soundfile as sf
import numpy as np
from pathlib import Path
from typing import List, Dict

# Import old PostProcessor from renamed legacy module
try:
    from src.postprocess_legacy import PostProcessor as OldPostProcessor
except ImportError:
    OldPostProcessor = None
    logging.warning("Could not import old PostProcessor from postprocess_legacy")

from . import gain
from . import normalize
from . import trim_silence
from . import dc_offset
from . import bitdepth


class PostProcessor:
    """
    Orchestrates postprocessing operations on recorded samples.
    Runs AFTER sampling is complete, not during.
    """
    
    def __init__(self):
        """Initialize postprocessor."""
        pass
    
    def process_patch(self, sample_paths: List[str], operations: Dict) -> None:
        """
        Apply postprocessing operations to all samples in a patch.
        
        This runs AFTER all notes have been sampled.
        
        Args:
            sample_paths: List of WAV file paths to process
            operations: Dictionary of operations to apply:
                {
                    'gain_db': 10.0,              # Gain boost in dB
                    'patch_normalize': False,      # Normalize entire patch together
                    'sample_normalize': False,     # Normalize each sample individually
                    'trim_silence': True,          # Trim silence from samples
                    'silence_threshold': -60.0,    # Threshold in dB
                    'dc_offset_removal': True,     # Remove DC offset
                    'auto_loop': False,            # Find loop points (uses old implementation)
                    'convert_bitdepth': None,      # Target bitdepth
                    'dither': False                # Apply dithering
                }
        """
        if not sample_paths:
            logging.info("No samples to process")
            return
        
        logging.info(f"\n{'='*70}")
        logging.info("POST-PROCESSING (after sampling complete)")
        logging.info(f"{'='*70}")
        logging.info(f"Processing {len(sample_paths)} samples...")
        
        # If auto-loop is enabled, delegate entirely to old PostProcessor
        # (it handles all operations including loop detection)
        if operations.get('auto_loop'):
            if OldPostProcessor is None:
                logging.error("Auto-loop requested but old PostProcessor not available")
                return
            
            logging.info("\nUsing legacy PostProcessor for auto-loop...")
            old_processor = OldPostProcessor()
            old_processor.process_samples(sample_paths, operations)
            logging.info(f"\n{'='*70}")
            logging.info("POST-PROCESSING COMPLETE")
            logging.info(f"{'='*70}\n")
            return
        
        # Step 1: Patch normalization (if enabled, do this first before individual processing)
        if operations.get('patch_normalize'):
            logging.info("\nApplying patch normalization...")
            normalize.normalize_patch(sample_paths, target_level=0.95)
        
        # Step 2: Process each sample individually
        for idx, sample_path in enumerate(sample_paths, 1):
            filename = Path(sample_path).name
            logging.info(f"\n[{idx}/{len(sample_paths)}] Processing: {filename}")
            
            try:
                # Read WAV file
                audio, samplerate = sf.read(sample_path, always_2d=True)
                modified = False
                
                # DC offset removal
                if operations.get('dc_offset_removal'):
                    audio = dc_offset.remove_dc_offset(audio)
                    logging.info("  ✓ DC offset removed")
                    modified = True
                
                # Trim silence
                if operations.get('trim_silence'):
                    threshold_db = operations.get('silence_threshold', -60.0)
                    audio = trim_silence.trim_silence(audio, samplerate, threshold_db)
                    logging.info(f"  ✓ Silence trimmed (threshold: {threshold_db:.1f}dB)")
                    modified = True
                
                # Sample normalization (only if patch normalization wasn't done)
                if operations.get('sample_normalize') and not operations.get('patch_normalize'):
                    audio = normalize.normalize_sample(audio)
                    logging.info("  ✓ Sample normalized")
                    modified = True
                
                # Gain boost
                gain_db = operations.get('gain_db', 0.0)
                if gain_db != 0.0:
                    audio = gain.apply_gain(audio, gain_db)
                    logging.info(f"  ✓ Gain applied: {gain_db:+.1f}dB")
                    modified = True
                
                # Save modified audio
                if modified:
                    # Determine bitdepth
                    target_bitdepth = operations.get('convert_bitdepth', 24)
                    if target_bitdepth == 16:
                        subtype = 'PCM_16'
                    elif target_bitdepth == 24:
                        subtype = 'PCM_24'
                    elif target_bitdepth == 32:
                        subtype = 'PCM_32'
                    else:
                        subtype = 'PCM_24'
                    
                    sf.write(sample_path, audio, samplerate, subtype=subtype)
                    logging.info(f"  ✓ Saved modified audio")
                else:
                    logging.info("  - No modifications needed")
                    
            except Exception as e:
                logging.error(f"  ✗ Failed to process {filename}: {e}")
        
        logging.info(f"\n{'='*70}")
        logging.info("POST-PROCESSING COMPLETE")
        logging.info(f"{'='*70}\n")
