"""
PROPOSED FIX: Waldorf Sample Map Column Corrections

Based on hardware testing and user observations, the current column mapping 
in export_waldorf_sample_map.py has several critical errors.

CURRENT PROBLEMS:
1. Column 5: We put 'tune' (cents) but hardware shows GAIN (dB)
2. Column 8: We put 'volume' but this might be wrong 
3. Column 13: Need to verify if values are normalized or raw sample counts

CORRECTED COLUMN MAPPING:
"""

# CORRECT Waldorf Map Format (16 columns, tab-separated):
# 1. Sample Location (quoted path with location prefix) - ✅ CORRECT
# 2. Pitch (root note + tuning) - ✅ CORRECT  
# 3. From Note (key range low) - ✅ CORRECT
# 4. To Note (key range high) - ✅ CORRECT
# 5. Sample Gain (linear multiplier from dB) - ❌ CURRENTLY WRONG (we put tune)
# 6. From Velo (velocity range low) - ✅ CORRECT
# 7. To Velo (velocity range high) - ✅ CORRECT
# 8. Unknown Field (pan? filter? stereo width?) - ❓ MYSTERY (we put volume)
# 9. Sample Start (normalized 0.0-1.0) - ✅ CORRECT
# 10. Sample End (normalized 0.0-1.0) - ✅ CORRECT
# 11. Loop Mode (0=off, 1=forward, 2=ping-pong) - ✅ CORRECT
# 12. Loop Start (normalized 0.0-1.0) - ✅ CORRECT
# 13. Loop End (normalized 0.0-1.0) - ❓ Need to verify if normalized vs raw
# 14. Direction (0=forward, 1=reverse) - ❓ Need verification
# 15. X-Fade (crossfade amount 0.0-1.0) - ❓ Need verification
# 16. Track Pitch (0=off, 1=on) - ✅ CORRECT

def corrected_create_map_line(region, relative_sample_path, samples_folder):
    """
    CORRECTED version of _create_map_line with proper column mapping.
    """
    import os
    import math
    from .waldorf_utils import read_wav_loop_points, format_double_value, calculate_crossfade_value
    
    # Extract sample filename
    sample = region.get('sample', '')
    sample_name = os.path.basename(sample)
    
    # Build full path with location prefix
    sample_path = f'"{self.location}:{relative_sample_path}/{sample_name}"'
    
    # Read loop points from WAV file SMPL chunk
    wav_path = os.path.join(samples_folder, sample_name)
    loop_start_norm, loop_end_norm, has_loop = read_wav_loop_points(wav_path)
    
    # Extract key mapping (default to middle C if not specified)
    root_key = float(region.get('pitch_keycenter', 60))
    key_low = int(region.get('lokey', 0))
    key_high = int(region.get('hikey', 127))
    
    # Extract velocity mapping (default to full range)
    vel_low = int(region.get('lovel', 1))
    vel_high = int(region.get('hivel', 127))
    
    # FIXED: Column 5 - Sample Gain (linear multiplier from dB)
    # Convert from SFZ volume (dB) to linear multiplier
    volume_db = float(region.get('volume', 0.0))  # SFZ volume in dB
    sample_gain = math.pow(10, volume_db / 20.0)  # Convert dB to linear
    
    # Column 8 - Unknown field (keep current behavior until verified)
    # TODO: Hardware testing needed to determine what this controls
    pan = float(region.get('pan', 0.5))  # Current: pan/volume (0.0-1.0)
    
    # Sample start/end (normalized 0.0-1.0)
    sample_start = 0.0
    sample_end = 1.0
    
    # Loop parameters
    loop_mode = self.loop_mode if has_loop else 0
    direction = 0  # 0=forward, 1=reverse
    crossfade = calculate_crossfade_value(self.crossfade_ms) if has_loop else 0.0
    track_pitch = 1  # Key tracking enabled by default
    
    # Format line with corrected column mapping
    line = '\t'.join([
        sample_path,                            # Column 1: File path ✅
        format_double_value(root_key),          # Column 2: Pitch/Root key ✅
        str(key_low),                           # Column 3: Key range low ✅
        str(key_high),                          # Column 4: Key range high ✅
        format_double_value(sample_gain),       # Column 5: GAIN (FIXED!) ✅
        str(vel_low),                           # Column 6: Velocity range low ✅
        str(vel_high),                          # Column 7: Velocity range high ✅
        format_double_value(pan),               # Column 8: Unknown field ❓
        format_double_value(sample_start),      # Column 9: Sample start ✅
        format_double_value(sample_end),        # Column 10: Sample end ✅
        str(loop_mode),                         # Column 11: Loop mode ✅
        format_double_value(loop_start_norm),   # Column 12: Loop start ✅
        format_double_value(loop_end_norm),     # Column 13: Loop end ❓
        str(direction),                         # Column 14: Direction ❓
        format_double_value(crossfade),         # Column 15: Crossfade ❓
        str(track_pitch)                        # Column 16: Track pitch ✅
    ])
    
    return line

# TESTING NEEDED:
# 1. Load verify_col05_gain_db.map - should show volume differences
# 2. Load verify_col08_mystery.map - document what changes
# 3. Test all other verification files
# 4. Update code with confirmed mappings