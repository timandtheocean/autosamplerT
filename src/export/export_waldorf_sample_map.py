"""
Waldorf Sample Map (.map) Exporter for AutosamplerT

Exports SFZ multisamples to Waldorf Quantum/Iridium .map format.
This is a plain text file (no binary header like QPAT) that can be loaded
directly into Waldorf synthesizers.

Format: Tab-separated values with 16 columns per sample line
"""

import os
import logging
from typing import List, Dict, Tuple


class WaldorfSampleMapExporter:
    """Export to Waldorf .map format (text-only sample maps)."""
    
    def __init__(self, location: int = 2):
        """
        Initialize Waldorf sample map exporter.
        
        Args:
            location: Sample storage location
                2 = SD card (default)
                3 = Internal memory
                4 = USB storage
        """
        self.location = location
        
    def export(self, output_folder: str, map_name: str, 
               sfz_file: str, samples_folder: str) -> bool:
        """
        Export multisample to Waldorf .map format.
        
        Args:
            output_folder: Destination folder
            map_name: Name of the map file (without extension)
            sfz_file: Path to source SFZ file
            samples_folder: Path to sample files
            
        Returns:
            True if successful
        """
        try:
            logging.info(f"Exporting to Waldorf .map: {map_name}")
            
            # Parse SFZ to get regions
            regions = self._parse_sfz(sfz_file)
            
            if not regions:
                logging.error("No regions found in SFZ file")
                return False
            
            # Create output file
            map_file = os.path.join(output_folder, f'{map_name}.map')
            relative_sample_path = f'samples/{map_name}'
            
            # Write map file
            with open(map_file, 'w') as f:
                for region in regions:
                    line = self._create_map_line(region, relative_sample_path)
                    f.write(line + '\n')
            
            logging.info(f"Successfully exported {len(regions)} samples to {map_file}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to export Waldorf map: {e}")
            return False
    
    def _parse_sfz(self, sfz_file: str) -> List[Dict]:
        """
        Parse SFZ file to extract regions.
        
        Returns:
            List of region dictionaries
        """
        regions = []
        current_region = None
        
        with open(sfz_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('//'):
                    continue
                
                # Parse region header
                if line.startswith('<region>'):
                    # Save previous region
                    if current_region and 'sample' in current_region:
                        regions.append(current_region)
                    
                    current_region = {}
                    
                    # Parse inline parameters
                    params = line[8:].strip()  # Remove '<region>'
                    if params:
                        for param in params.split():
                            if '=' in param:
                                key, value = param.split('=', 1)
                                current_region[key] = value
                
                # Parse parameters on separate lines
                elif current_region is not None and '=' in line:
                    key, value = line.split('=', 1)
                    current_region[key.strip()] = value.strip()
        
        # Add last region
        if current_region and 'sample' in current_region:
            regions.append(current_region)
        
        return regions
    
    def _create_map_line(self, region: Dict, relative_sample_path: str) -> str:
        """
        Create a single map file line for a region.
        
        Format (16 tab-separated columns):
        1. Sample path (quoted, with location prefix)
        2. Root key (pitch_keycenter)
        3. Key low (lokey)
        4. Key high (hikey)
        5. Tune (cents)
        6. Velocity low (lovel)
        7. Velocity high (hivel)
        8. Volume (linear)
        9. Pan (-1.0 to 1.0)
        10. Sample start (0.0-1.0)
        11. Sample start random (0-1)
        12. Sample end (0.0-1.0)
        13. Loop start (0.0-1.0)
        14. Loop end random (0-1)
        15. Loop end (0.0-1.0)
        16. Loop mode (0=off, 1=forward, 2=ping-pong)
        
        Args:
            region: Region dictionary from SFZ
            relative_sample_path: Path prefix for samples
            
        Returns:
            Tab-separated line string
        """
        # Extract sample filename
        sample = region.get('sample', '')
        sample_name = os.path.basename(sample)
        
        # Build full path with location prefix
        sample_path = f'"{self.location}:{relative_sample_path}/{sample_name}"'
        
        # Extract key mapping (default to middle C if not specified)
        root_key = float(region.get('pitch_keycenter', 60))
        key_low = int(region.get('lokey', 0))
        key_high = int(region.get('hikey', 127))
        
        # Extract velocity mapping (default to full range)
        vel_low = int(region.get('lovel', 0))
        vel_high = int(region.get('hivel', 127))
        
        # Default values for other parameters
        tune = float(region.get('tune', 1.0))  # Cents tuning
        volume = float(region.get('volume', 0.5))  # Linear volume
        pan = float(region.get('pan', 0.0))  # Pan position
        sample_start = float(region.get('offset', 0.0))  # Sample start
        sample_start_random = 0  # No random start
        sample_end = float(region.get('end', 1.0))  # Sample end
        loop_start = float(region.get('loop_start', 0.0))  # Loop start
        loop_start_random = 0  # No random loop start
        loop_end = float(region.get('loop_end', 1.0))  # Loop end
        loop_mode = int(region.get('loop_mode', 1))  # 1=forward loop
        
        # Format line with tab separators
        line = '\t'.join([
            sample_path,
            f'{root_key:.8f}',
            str(key_low),
            str(key_high),
            f'{tune:.8f}',
            str(vel_low),
            str(vel_high),
            f'{volume:.8f}',
            f'{pan:.8f}',
            f'{sample_start:.8f}',
            str(sample_start_random),
            f'{sample_end:.8f}',
            f'{loop_start:.8f}',
            str(loop_start_random),
            f'{loop_end:.8f}',
            str(loop_mode)
        ])
        
        return line


def export_to_waldorf_map(output_folder: str, map_name: str,
                          sfz_file: str, samples_folder: str,
                          location: int = 2) -> bool:
    """
    Convenience function to export to Waldorf .map format.
    
    Args:
        output_folder: Destination folder for .map file
        map_name: Name of the map (used for filename)
        sfz_file: Path to source SFZ file to parse
        samples_folder: Path to folder containing sample WAV files
        location: Sample location (2=SD, 3=internal, 4=USB)
        
    Returns:
        True if export successful, False otherwise
    """
    exporter = WaldorfSampleMapExporter(location=location)
    return exporter.export(output_folder, map_name, sfz_file, samples_folder)
