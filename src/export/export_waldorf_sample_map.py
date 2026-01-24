"""
Waldorf Sample Map (.map) Exporter for AutosamplerT

Exports SFZ multisamples to Waldorf Quantum/Iridium .map format.
This is a plain text file (no binary header like QPAT) that can be loaded
directly into Waldorf synthesizers.

Format: Tab-separated values with 16 columns per sample line
"""

# Standard library imports
import os
import struct
import logging
import math
from typing import List, Dict, Tuple

# Local imports
from .waldorf_utils import read_wav_loop_points, format_double_value, calculate_crossfade_value

# Local imports
from .waldorf_utils import read_wav_loop_points, format_double_value, calculate_crossfade_value


class WaldorfSampleMapExporter:
    """Export to Waldorf .map format (text-only sample maps)."""

    def __init__(self, location: int = 2, loop_mode: int = 1, crossfade_ms: float = 10.0):
        """
        Initialize Waldorf sample map exporter.

        Args:
            location: Sample storage location
                2 = SD card (default)
                3 = Internal memory
                4 = USB storage
            loop_mode: Loop mode
                0 = Loop off
                1 = Forward loop (default)
                2 = Ping-pong loop
            crossfade_ms: Loop crossfade time in milliseconds (default 10ms)
        """
        self.location = location
        self.loop_mode = loop_mode
        self.crossfade_ms = crossfade_ms

    def export(self, output_folder: str, map_name: str,
               sfz_file: str, samples_folder: str) -> bool:
        """
        Export multisample to Waldorf .map format.

        Args:
            output_folder: Destination folder (e.g., output/prophet6-test1-basic)
            map_name: Name of the map file (without extension)
            sfz_file: Path to source SFZ file
            samples_folder: Path to sample files (e.g., output/prophet6-test1-basic/samples)

        Returns:
            True if successful
        """
        try:
            logging.info("Exporting to Waldorf .map: %s", map_name)

            # Parse SFZ to get regions
            regions = self._parse_sfz(sfz_file)

            if not regions:
                logging.error("No regions found in SFZ file")
                return False

            # Create output file
            map_file = os.path.join(output_folder, f'{map_name}.map')
            
            # Build relative sample path: multisample_name/samples
            # Format: "4:Prophet_Program/samples/filename.wav" (no 'samples/' prefix)
            multisample_folder_name = os.path.basename(output_folder)
            relative_sample_path = f'{multisample_folder_name}/samples'

            # Write map file
            with open(map_file, 'w', encoding='utf-8') as f:
                for region in regions:
                    line = self._create_map_line(region, relative_sample_path, samples_folder)
                    f.write(line + '\n')

            logging.info("Successfully exported %s samples to %s", len(regions), map_file)
            return True

        except Exception as e:
            logging.error("Failed to export Waldorf map: %s", e)
            import traceback
            traceback.print_exc()
            return False

    def _parse_sfz(self, sfz_file: str) -> List[Dict]:
        """
        Parse SFZ file to extract groups and regions with proper group inheritance.
        Groups define velocity layers, regions define individual samples.

        Returns:
            List of region dictionaries with group settings inherited
        """
        regions = []
        groups = []
        metadata = {'creator': 'AutosamplerT'}
        current_group = None
        current_region = None

        with open(sfz_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('//'):
                    continue

                # Parse group header
                if line.startswith('<group>'):
                    # Save previous region to previous group (if exists)
                    if current_region is not None and 'sample' in current_region and current_group is not None:
                        current_group['zones'].append(current_region)
                    
                    # Save previous group
                    if current_group is not None and current_group['zones']:
                        groups.append(current_group)

                    current_group = {'zones': [], 'settings': {}}
                    current_region = None

                    # Parse inline group parameters
                    params = line[7:].strip()  # Remove '<group>'
                    if params:
                        for param in params.split():
                            if '=' in param:
                                key, value = param.split('=', 1)
                                current_group['settings'][key] = value

                # Parse region header
                elif line.startswith('<region>'):
                    # Create group if none exists (for groupless SFZ files)
                    if current_group is None:
                        current_group = {'zones': [], 'settings': {}}

                    # Save previous region
                    if current_region is not None and 'sample' in current_region:
                        current_group['zones'].append(current_region)

                    current_region = {}

                    # Parse inline region parameters
                    params = line[8:].strip()  # Remove '<region>'
                    if params:
                        for param in params.split():
                            if '=' in param:
                                key, value = param.split('=', 1)
                                current_region[key] = value

                # Parse parameters on separate lines (multi-line format)
                elif '=' in line:
                    # Handle multiple parameters on one line (e.g., "lovel=1 hivel=127")
                    # First try to split by spaces to find multiple key=value pairs
                    potential_params = line.split()
                    parsed_any = False
                    
                    for potential_param in potential_params:
                        if '=' in potential_param:
                            parts = potential_param.split('=', 1)
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip()
                                
                                # Group settings or region parameters
                                if current_region is not None:
                                    current_region[key] = value
                                elif current_group is not None:
                                    current_group['settings'][key] = value
                                parsed_any = True
                    
                    # If no parameters were parsed via space-splitting, fall back to old method
                    if not parsed_any:
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()

                            # Group settings or region parameters
                            if current_region is not None:
                                current_region[key] = value
                            elif current_group is not None:
                                current_group['settings'][key] = value

        # Save last region and group
        if current_region and 'sample' in current_region:
            current_group['zones'].append(current_region)
        if current_group and current_group['zones']:
            groups.append(current_group)

        # Flatten groups into regions with inherited group settings
        for group in groups:
            group_settings = group['settings']
            for zone in group['zones']:
                # Create a copy of the zone with group settings inherited as defaults
                region = zone.copy()
                
                # Inherit group settings if not overridden in zone
                for key, value in group_settings.items():
                    if key not in region:
                        region[key] = value
                        
                regions.append(region)

        return regions

    def _create_map_line(self, region: Dict, relative_sample_path: str, samples_folder: str) -> str:
        """
        Create a single map file line for a region.

        Waldorf .map format (16 tab-separated columns):
        1. Sample Location (quoted path with location prefix)
        2. Pitch (root note + tuning)
        3. From Note (key range low)
        4. To Note (key range high)  
        5. Sample Gain (volume/gain multiplier)
        6. From Velo (velocity range low)
        7. To Velo (velocity range high)
        8. ??? (Unknown field - purpose undocumented)
        9. Sample Start (normalized 0.0-1.0)
        10. Sample End (normalized 0.0-1.0)
        11. Loop Mode (0=off, 1=forward, 2=ping-pong)
        12. Loop Start (normalized 0.0-1.0, from WAV SMPL chunk)
        13. Loop End (normalized 0.0-1.0, from WAV SMPL chunk)
        14. Direction (0=forward, 1=reverse)
        15. X-Fade (crossfade amount 0.0-1.0)
        16. Track Pitch (0=off, 1=on)

        IMPLEMENTATION NOTE: Current mapping has some issues:
        - Column 8 purpose unknown, currently outputs pan but may be incorrect
        - Column 14 should be Direction but currently outputs loop_end_random=0
        - Column 15 should be X-Fade but currently outputs loop_start again

        Args:
            region: Region dictionary from SFZ
            relative_sample_path: Path prefix for samples (e.g., "samples/prophet6-test1-basic/samples")
            samples_folder: Full path to samples folder for reading WAV metadata

        Returns:
            Tab-separated line string
        """
        # Extract sample filename
        sample = region.get('sample', '')
        sample_name = os.path.basename(sample)

        # Build full path with location prefix
        # Format: "2:samples/multisample_name/samples/filename.wav"
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

        # FIXED: Column 5 - Convert SFZ volume (dB) to linear gain
        volume_db = float(region.get('volume', 0.0))  # SFZ volume in dB
        sample_gain = math.pow(10, volume_db / 20.0)  # Convert dB to linear gain
        
        # Column 8 - Unknown field (keep current pan behavior until verified)
        pan = float(region.get('pan', 0.5))  # Pan/unknown field (0.0-1.0)
        
        # Sample start/end (normalized 0.0-1.0)
        sample_end = 1.0  # Full sample by default
        sample_start = 0.0  # Start at beginning
        
        # Loop parameters
        loop_end_random = 0  # No random loop end
        
        # Use configured loop mode only if WAV has loop points (from auto-looping)
        loop_mode = self.loop_mode if has_loop else 0  # 0=off, 1=forward, 2=ping-pong
        
        # Calculate crossfade value
        crossfade = calculate_crossfade_value(self.crossfade_ms) if has_loop else 0.0
        
        # Track pitch (key tracking) - always enabled
        track_pitch = 1

        # Format line with tab separators (16 columns)
        # Based on Waldorf Quantum/Iridium MAP format specification
        line = '\t'.join([
            sample_path,                            # Column 1: File path ✅
            format_double_value(root_key),          # Column 2: Pitch/Root key ✅
            str(key_low),                           # Column 3: Key range low ✅
            str(key_high),                          # Column 4: Key range high ✅
            format_double_value(sample_gain),       # Column 5: GAIN (FIXED!) ✅
            str(vel_low),                           # Column 6: Velocity range low ✅
            str(vel_high),                          # Column 7: Velocity range high ✅
            format_double_value(pan),               # Column 8: Unknown field ❓
            format_double_value(sample_start),      # Column 9: Sample start position
            format_double_value(sample_end),        # Column 10: Sample end position
            str(loop_mode),                         # Column 11: Loop mode (0/1/2)
            format_double_value(loop_start_norm),   # Column 12: Loop START
            format_double_value(loop_end_norm),     # Column 13: Loop END  
            str(loop_end_random),                   # Column 14: Loop end random/direction
            format_double_value(crossfade),         # Column 15: Crossfade
            str(track_pitch)                        # Column 16: Track pitch
        ])

        return line

    def _read_wav_loop_points(self, wav_path: str) -> Tuple[float, float, bool]:
        """
        DEPRECATED: Use shared waldorf_utils.read_wav_loop_points instead.
        Kept for backward compatibility.
        """
        return read_wav_loop_points(wav_path)


def export_to_waldorf_map(output_folder: str, map_name: str,
                          sfz_file: str, samples_folder: str,
                          location: int = 2, loop_mode: int = 1, crossfade_ms: float = 10.0) -> bool:
    """
    Convenience function to export to Waldorf .map format.

    Args:
        output_folder: Destination folder for .map file
        map_name: Name of the map (used for filename)
        sfz_file: Path to source SFZ file to parse
        samples_folder: Path to folder containing sample WAV files
        location: Sample location (2=SD, 3=internal, 4=USB)
        loop_mode: Loop mode (0=off, 1=forward, 2=ping-pong)
        crossfade_ms: Loop crossfade time in milliseconds

    Returns:
        True if export successful, False otherwise
    """
    exporter = WaldorfSampleMapExporter(location=location, loop_mode=loop_mode, crossfade_ms=crossfade_ms)
    return exporter.export(output_folder, map_name, sfz_file, samples_folder)
