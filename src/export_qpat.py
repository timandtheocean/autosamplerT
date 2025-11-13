"""
Waldorf Quantum/Iridium QPAT Format Exporter
Exports multisamples to .qpat format compatible with Waldorf Quantum and Iridium synthesizers.

Format Specification:
- Binary header (512 bytes) with magic number, metadata, and resource headers
- Parameters section (synth engine settings)
- Sample maps (tab-separated text, up to 3 maps for velocity/round-robin layers)

Sample Map Format (16 columns, tab-separated):
"LOCATION:path/sample.wav" pitch fromNote toNote gain fromVelo toVelo pan start end loopMode loopStart loopEnd direction crossfade trackPitch

Location prefixes:
- 2: SD card
- 3: Internal memory  
- 4: USB drive (use this to trigger auto-import)

Constraints:
- Maximum 3 sample maps (velocity layers or round-robin groups)
- Maximum 128 samples per map
- ~360MB total RAM limit (32-bit float)
- Prefers 44.1kHz, 32-bit float audio
"""

import os
import struct
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging


class WaldorfQpatExporter:
    """Export multisamples to Waldorf Quantum/Iridium QPAT format."""
    
    # Constants
    MAGIC_NUMBER = 3402932
    PRESET_VERSION = 14
    MAX_STRING_LENGTH = 32
    MAX_GROUPS = 3
    MAX_SAMPLES_PER_MAP = 128
    HEADER_SIZE = 512
    
    def __init__(self, location: int = 4, optimize_audio: bool = True):
        """
        Initialize QPAT exporter.
        
        Args:
            location: Sample location (2=SD, 3=internal, 4=USB)
            optimize_audio: Convert samples to 44.1kHz 32-bit float
        """
        self.location = location
        self.optimize_audio = optimize_audio
        
    def export(self, output_folder: str, multisample_name: str, 
               sfz_file: str, samples_folder: str) -> bool:
        """
        Export multisample to QPAT format.
        
        Args:
            output_folder: Destination folder
            multisample_name: Name of the multisample
            sfz_file: Path to source SFZ file
            samples_folder: Path to sample files
            
        Returns:
            True if successful
        """
        try:
            logging.info(f"Exporting to QPAT: {multisample_name}")
            
            # Parse SFZ to get groups and zones
            groups, metadata = self._parse_sfz(sfz_file)
            
            if not groups:
                logging.error("No groups found in SFZ file")
                return False
            
            # Limit to 3 groups (Waldorf constraint)
            groups = self._reduce_groups(groups, self.MAX_GROUPS)
            
            # Create output structure
            qpat_file = os.path.join(output_folder, f'{multisample_name}.qpat')
            relative_sample_path = f'samples/{multisample_name}'
            
            # Generate sample maps
            sample_maps = self._create_sample_maps(groups, relative_sample_path)
            
            # Generate parameters
            parameters = self._create_parameters(groups, metadata)
            
            # Write QPAT file
            self._write_qpat(qpat_file, multisample_name, metadata, 
                            parameters, sample_maps)
            
            # Copy/convert samples
            sample_dest = os.path.join(output_folder, relative_sample_path)
            os.makedirs(sample_dest, exist_ok=True)
            self._copy_samples(groups, samples_folder, sample_dest)
            
            logging.info(f"[SUCCESS] Exported QPAT: {qpat_file}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to export QPAT: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _parse_sfz(self, sfz_file: str) -> Tuple[List[Dict], Dict]:
        """
        Parse SFZ file to extract groups and metadata.
        
        Returns:
            (groups, metadata)
        """
        groups = []
        metadata = {'creator': 'AutosamplerT', 'description': '', 
                   'category': '', 'keywords': []}
        current_group = None
        
        with open(sfz_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('//'):
                    continue
                
                # Parse headers
                if line.startswith('<group>'):
                    if current_group and current_group['zones']:
                        groups.append(current_group)
                    current_group = {'zones': [], 'settings': {}}
                    
                elif line.startswith('<region>'):
                    if not current_group:
                        current_group = {'zones': [], 'settings': {}}
                    current_zone = {}
                    
                    # Parse region parameters
                    params = line[8:].strip()  # Remove '<region>'
                    for param in params.split():
                        if '=' in param:
                            key, value = param.split('=', 1)
                            current_zone[key] = value
                    
                    if current_zone:
                        current_group['zones'].append(current_zone)
        
        # Add last group
        if current_group and current_group['zones']:
            groups.append(current_group)
        
        return groups, metadata
    
    def _reduce_groups(self, groups: List[Dict], max_groups: int) -> List[Dict]:
        """
        Reduce groups to maximum number by merging extras.
        
        Args:
            groups: List of groups
            max_groups: Maximum number of groups allowed
            
        Returns:
            Reduced groups list
        """
        if len(groups) <= max_groups:
            return groups
        
        logging.warning(f"Reducing {len(groups)} groups to {max_groups}")
        
        # Merge all groups beyond max into the last group
        reduced = groups[:max_groups]
        last_group = reduced[-1]
        
        for i in range(max_groups, len(groups)):
            last_group['zones'].extend(groups[i]['zones'])
        
        return reduced
    
    def _create_sample_maps(self, groups: List[Dict], 
                           relative_sample_path: str) -> List[str]:
        """
        Create tab-separated sample maps for each group.
        
        Args:
            groups: List of sample groups
            relative_sample_path: Path relative to QPAT file
            
        Returns:
            List of sample map strings (max 3)
        """
        sample_maps = []
        
        for group in groups[:self.MAX_GROUPS]:
            lines = []
            
            for zone in group['zones']:
                # Extract zone parameters
                sample_name = zone.get('sample', '').replace('\\', '/')
                sample_name = os.path.basename(sample_name)
                
                # Sample path with location prefix
                path = f'"{self.location}:{relative_sample_path}/{sample_name}"'
                
                # Pitch (root note - tune)
                pitch_key_center = int(zone.get('pitch_keycenter', 60))
                tune = float(zone.get('tune', 0)) / 100.0  # cents to semitones
                pitch = self._format_double(pitch_key_center - tune)
                
                # Key range
                from_note = int(zone.get('lokey', pitch_key_center))
                to_note = int(zone.get('hikey', pitch_key_center))
                
                # Gain (linear from dB)
                gain_db = float(zone.get('volume', 0))
                gain = self._format_double(10 ** (gain_db / 20))
                
                # Velocity range
                from_velo = int(zone.get('lovel', 0))
                to_velo = int(zone.get('hivel', 127))
                
                # Pan (0-1, center=0.5)
                pan_value = float(zone.get('pan', 0))  # -100 to +100
                pan = self._format_double((pan_value + 100) / 200.0)
                
                # Start/End (fraction of sample length)
                # SFZ uses sample offsets, we need fractions
                # For now, assume full sample
                start = self._format_double(0.0)
                end = self._format_double(1.0)
                
                # Loop mode and points
                loop_mode_str = zone.get('loop_mode', 'no_loop')
                if loop_mode_str == 'loop_continuous':
                    loop_mode = 1  # Forward
                elif loop_mode_str == 'loop_bidirectional':
                    loop_mode = 2  # Ping-pong
                else:
                    loop_mode = 0  # No loop
                
                loop_start = self._format_double(0.0)
                loop_end = self._format_double(1.0)
                
                # Direction (always forward for now)
                direction = 0
                
                # Crossfade
                crossfade = self._format_double(0.0)
                
                # Track pitch (key tracking)
                track_pitch = 1  # Always on
                
                # Build tab-separated line
                line = '\t'.join([
                    path, pitch, str(from_note), str(to_note), gain,
                    str(from_velo), str(to_velo), pan, start, end,
                    str(loop_mode), loop_start, loop_end,
                    str(direction), crossfade, str(track_pitch)
                ])
                
                lines.append(line)
            
            sample_maps.append('\n'.join(lines))
        
        return sample_maps
    
    def _create_parameters(self, groups: List[Dict], 
                          metadata: Dict) -> List[Dict]:
        """
        Create Waldorf synth parameters.
        
        Args:
            groups: Sample groups
            metadata: Multisample metadata
            
        Returns:
            List of parameter dictionaries
        """
        parameters = []
        
        for i, group in enumerate(groups[:self.MAX_GROUPS]):
            osc_num = i + 1
            
            # Oscillator type = Particle (sampler mode)
            parameters.append(self._create_param(
                f'Osc{osc_num}Type', 'Particle', 2.0))
            
            # Pitch settings
            parameters.append(self._create_param(
                f'Osc{osc_num}CoarsePitch', '+0 semi', 24.0))
            parameters.append(self._create_param(
                f'Osc{osc_num}FinePitch', '+0.0 cents', 0.5))
            
            # Pitch bend range (default ±2 semitones)
            parameters.append(self._create_param(
                f'Osc{osc_num}PitchBendRange', '+2', 26.0))
            
            # Volume
            parameters.append(self._create_param(
                f'Osc{osc_num}Vol', '+0.000 dB', 1.0))
            
            # Pan
            parameters.append(self._create_param(
                f'Osc{osc_num}Pan', 'Center', 0.5))
            
            # Only Osc1 gets filter and amp envelope
            if i == 0:
                # Filter bypass (no filtering)
                parameters.append(self._create_param(
                    'FilterState', 'Bypass', 1.0))
                
                # Amp envelope (basic ADSR)
                parameters.append(self._create_param(
                    'AmpEnvDelay', '0.00 secs', 0.0))
                parameters.append(self._create_param(
                    'AmpEnvAttack', '0.01 secs', 0.0))
                parameters.append(self._create_param(
                    'AmpEnvDecay', '0.10 secs', 0.1))
                parameters.append(self._create_param(
                    'AmpEnvSustain', '100.00 %', 1.0))
                parameters.append(self._create_param(
                    'AmpEnvRelease', '0.50 secs', 0.2))
        
        return parameters
    
    def _write_qpat(self, qpat_file: str, name: str, metadata: Dict,
                    parameters: List[Dict], sample_maps: List[str]) -> None:
        """
        Write QPAT binary file.
        
        Args:
            qpat_file: Output file path
            name: Patch name
            metadata: Metadata dictionary
            parameters: List of parameters
            sample_maps: List of sample map strings
        """
        with open(qpat_file, 'wb') as f:
            # Write header (512 bytes)
            self._write_header(f, name, metadata)
            
            # Write parameter count
            f.write(struct.pack('>H', len(parameters)))
            f.write(b'\x00\x00')  # Padding
            
            # Write resource headers (sample maps)
            for i, sample_map in enumerate(sample_maps):
                resource_type = i  # 0, 1, 2 for USER_SAMPLE_MAP1/2/3
                map_bytes = sample_map.encode('utf-8')
                self._write_resource_header(f, resource_type, len(map_bytes))
            
            # Pad remaining resource headers
            for _ in range(self.MAX_GROUPS - len(sample_maps)):
                self._write_resource_header(f, 0, 0)  # Empty
            
            # Write 2nd layer info (none)
            f.write(struct.pack('>H', 0))
            f.write(struct.pack('>H', 0))
            f.write(struct.pack('>I', 0))
            
            # Instrument type (0 = Quantum)
            f.write(b'\x00')
            
            # Pad header to 512 bytes
            current_pos = f.tell()
            padding = self.HEADER_SIZE - current_pos
            if padding > 0:
                f.write(b'\x00' * padding)
            
            # Write parameters
            for param in parameters:
                self._write_parameter(f, param)
            
            # Write sample maps
            for sample_map in sample_maps:
                f.write(sample_map.encode('utf-8'))
    
    def _write_header(self, f, name: str, metadata: Dict) -> None:
        """Write 512-byte header."""
        # Magic number
        f.write(struct.pack('>I', self.MAGIC_NUMBER))
        
        # Preset version
        f.write(struct.pack('>I', self.PRESET_VERSION))
        
        # Name
        self._write_ascii_padded(f, name, self.MAX_STRING_LENGTH)
        
        # Creator
        creator = metadata.get('creator', 'AutosamplerT')
        self._write_ascii_padded(f, creator, self.MAX_STRING_LENGTH)
        
        # Description
        desc = metadata.get('description', '')
        desc = desc.replace('\r', ' ').replace('\n', ' ')
        self._write_ascii_padded(f, desc, self.MAX_STRING_LENGTH)
        
        # Categories (4 × 32 bytes)
        categories = [metadata.get('category', '')]
        categories.extend(metadata.get('keywords', [])[:3])
        while len(categories) < 4:
            categories.append('')
        
        for cat in categories:
            self._write_ascii_padded(f, cat, self.MAX_STRING_LENGTH)
    
    def _write_resource_header(self, f, resource_type: int, length: int) -> None:
        """Write resource header (12 bytes)."""
        f.write(struct.pack('>I', resource_type))
        f.write(struct.pack('>I', length))
        f.write(struct.pack('>I', 0))  # Reserved
    
    def _write_parameter(self, f, param: Dict) -> None:
        """Write parameter (name + display + value)."""
        # Parameter name (32 bytes)
        self._write_ascii_padded(f, param['name'], self.MAX_STRING_LENGTH)
        
        # Display text (32 bytes)
        self._write_ascii_padded(f, param['display'], self.MAX_STRING_LENGTH)
        
        # Normalized value (4 bytes float, big-endian)
        f.write(struct.pack('>f', param['value']))
    
    def _write_ascii_padded(self, f, text: str, length: int) -> None:
        """Write ASCII string padded/truncated to exact length."""
        text_bytes = text[:length].encode('ascii', errors='replace')
        padded = text_bytes + b'\x00' * (length - len(text_bytes))
        f.write(padded)
    
    def _copy_samples(self, groups: List[Dict], source_folder: str,
                     dest_folder: str) -> None:
        """Copy sample files to destination."""
        for group in groups:
            for zone in group['zones']:
                sample_name = zone.get('sample', '')
                if not sample_name:
                    continue
                
                sample_name = os.path.basename(sample_name)
                source = os.path.join(source_folder, sample_name)
                dest = os.path.join(dest_folder, sample_name)
                
                if os.path.exists(source):
                    shutil.copy2(source, dest)
                    logging.debug(f"Copied: {sample_name}")
                else:
                    logging.warning(f"Sample not found: {source}")
    
    def _format_double(self, value: float) -> str:
        """Format float with 8 decimal places (Waldorf precision)."""
        return f"{value:.8f}"
    
    def _create_param(self, name: str, display: str, 
                     normalized_value: float) -> Dict:
        """Create parameter dictionary."""
        return {
            'name': name,
            'display': display,
            'value': float(normalized_value)
        }


def export_to_qpat(output_folder: str, multisample_name: str,
                   sfz_file: str, samples_folder: str,
                   location: int = 4, optimize_audio: bool = True) -> bool:
    """
    Export multisample to Waldorf QPAT format.
    
    Args:
        output_folder: Destination folder
        multisample_name: Name of the multisample  
        sfz_file: Path to source SFZ file
        samples_folder: Path to sample files
        location: Sample location (2=SD, 3=internal, 4=USB)
        optimize_audio: Convert to 44.1kHz 32-bit float
        
    Returns:
        True if successful
    """
    exporter = WaldorfQpatExporter(location, optimize_audio)
    return exporter.export(output_folder, multisample_name, 
                          sfz_file, samples_folder)
