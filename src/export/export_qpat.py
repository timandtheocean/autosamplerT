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

# Standard library imports
import os
import struct
import shutil
import logging
from typing import List, Dict, Tuple

# Local imports
from .export_waldorf_sample_map import WaldorfSampleMapExporter
from .waldorf_utils import read_wav_loop_points, format_double_value



class WaldorfQpatExporter:
    """Export multisamples to Waldorf Quantum/Iridium QPAT format."""

    # Constants
    MAGIC_NUMBER = 3402932
    PRESET_VERSION = 14
    MAX_STRING_LENGTH = 32
    MAX_GROUPS = 3
    MAX_SAMPLES_PER_MAP = 128
    HEADER_SIZE = 512

    def __init__(self, location: int = 4, loop_mode: int = 1, optimize_audio: bool = True, crossfade_ms: float = 10.0):
        """
        Initialize QPAT exporter.

        Args:
            location: Sample location (2=SD, 3=internal, 4=USB)
            loop_mode: Loop mode (0=off, 1=forward, 2=ping-pong)
            optimize_audio: Convert samples to 44.1kHz 32-bit float
            crossfade_ms: Loop crossfade time in milliseconds (default 10ms)
        """
        self.location = location
        self.loop_mode = loop_mode
        self.optimize_audio = optimize_audio
        self.crossfade_ms = crossfade_ms

    def export(self, output_folder: str, multisample_name: str,
               sfz_file: str, samples_folder: str) -> bool:
        """
        Export multisample to QPAT format.

        Args:
            output_folder: Destination folder (e.g., output/prophet6-test1-basic)
            multisample_name: Name of the multisample
            sfz_file: Path to source SFZ file
            samples_folder: Path to sample files (e.g., output/prophet6-test1-basic/samples)

        Returns:
            True if successful
        """
        try:
            logging.info("Exporting to QPAT: %s", multisample_name)

            # Parse SFZ to get groups and zones
            groups, metadata = self._parse_sfz(sfz_file)
            
            if not groups:
                logging.error("No groups found in SFZ file")
                return False

            # Limit to 3 groups (Waldorf constraint)
            groups = self._reduce_groups(groups, self.MAX_GROUPS)

            # Create output structure
            qpat_file = os.path.join(output_folder, f'{multisample_name}.qpat')
            
            # Build relative sample path: samples/multisample_name
            multisample_folder_name = os.path.basename(output_folder)
            relative_sample_path = f'samples/{multisample_folder_name}'

            # Generate sample maps using shared MAP export logic
            sample_maps = self._create_sample_maps_from_map_exporter(groups, relative_sample_path, samples_folder)

            # Generate parameters
            parameters = self._create_parameters(groups, metadata)

            # Write QPAT file
            self._write_qpat(qpat_file, multisample_name, metadata,
                            parameters, sample_maps)

            # Copy/convert samples if needed
            # Note: Samples are already in samples_folder (output_folder/samples)
            # Only copy/convert if optimize_audio is enabled AND we implement conversion
            # For now, skip copying to avoid "same file" error
            if self.optimize_audio:
                logging.warning("Audio optimization not yet implemented - using samples as-is")
                # TODO: Implement audio conversion to 44.1kHz 32-bit float
                # sample_dest = os.path.join(output_folder, 'samples')
                # os.makedirs(sample_dest, exist_ok=True)
                # self._copy_samples(groups, samples_folder, sample_dest)

            logging.info("[SUCCESS] Exported QPAT: %s", qpat_file)
            return True

        except Exception as e:
            logging.error("Failed to export QPAT: %s", e)
            import traceback
            traceback.print_exc()
            return False

    def _parse_sfz(self, sfz_file: str) -> Tuple[List[Dict], Dict]:
        """
        Parse SFZ file to extract groups and metadata.
        Supports both inline and multi-line SFZ formats.

        Returns:
            (groups, metadata)
        """
        groups = []
        metadata = {'creator': 'AutosamplerT', 'description': '',
                   'category': '', 'keywords': []}
        current_group = None
        current_zone = None

        with open(sfz_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('//'):
                    continue

                # Parse group header
                if line.startswith('<group>'):
                    # Save previous region to previous group (if exists)
                    if current_zone is not None and 'sample' in current_zone and current_group is not None:
                        current_group['zones'].append(current_zone)
                    
                    # Save previous group
                    if current_group is not None and current_group['zones']:
                        groups.append(current_group)

                    current_group = {'zones': [], 'settings': {}}
                    current_zone = None

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
                    if current_zone is not None and 'sample' in current_zone:
                        current_group['zones'].append(current_zone)

                    current_zone = {}

                    # Parse inline region parameters
                    params = line[8:].strip()  # Remove '<region>'
                    if params:
                        for param in params.split():
                            if '=' in param:
                                key, value = param.split('=', 1)
                                current_zone[key] = value

                # Parse parameters on separate lines (multi-line format)
                elif '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    # Group settings or region parameters
                    if current_zone is not None:
                        current_zone[key] = value
                    elif current_group is not None:
                        current_group['settings'][key] = value

        # Save last region and group
        if current_zone and 'sample' in current_zone:
            current_group['zones'].append(current_zone)
        if current_group and current_group['zones']:
            groups.append(current_group)

        return groups, metadata

    def _reduce_groups(self, groups: List[Dict], max_groups: int) -> List[Dict]:
        """
        Reduce groups to maximum number by merging round-robin and velocity layers.
        
        In Waldorf QPAT format:
        - Round-robin samples for the same note go in the SAME map (consecutive lines)
        - Different velocity layers go in DIFFERENT maps (max 3 maps)
        
        This function:
        1. Merges groups with same velocity but different seq_position (round-robin)
        2. Limits to max_groups velocity layers

        Args:
            groups: List of groups from SFZ
            max_groups: Maximum number of maps (velocity layers)

        Returns:
            Merged groups list (one group per velocity layer)
        """
        # Group by velocity layer (merge round-robin groups)
        velocity_groups = {}
        
        for group in groups:
            settings = group['settings']
            
            # Extract velocity range (use as key)
            lovel = settings.get('lovel', '0')
            hivel = settings.get('hivel', '127')
            vel_key = (lovel, hivel)
            
            if vel_key not in velocity_groups:
                velocity_groups[vel_key] = {
                    'zones': [],
                    'settings': {k: v for k, v in settings.items() 
                               if k not in ['seq_length', 'seq_position']}
                }
                # Keep velocity settings
                if 'lovel' in settings:
                    velocity_groups[vel_key]['settings']['lovel'] = lovel
                if 'hivel' in settings:
                    velocity_groups[vel_key]['settings']['hivel'] = hivel
            
            # Merge zones from this group (round-robin samples)
            velocity_groups[vel_key]['zones'].extend(group['zones'])
        
        # Convert back to list and sort by velocity
        merged_groups = []
        for vel_key in sorted(velocity_groups.keys(), key=lambda x: int(x[0])):
            merged_groups.append(velocity_groups[vel_key])
        
        # Limit to max_groups
        if len(merged_groups) > max_groups:
            logging.warning("Reducing %s velocity layers to %s (Waldorf limit)", 
                          len(merged_groups), max_groups)
            # Merge remaining into last group
            for i in range(max_groups, len(merged_groups)):
                merged_groups[max_groups - 1]['zones'].extend(merged_groups[i]['zones'])
            merged_groups = merged_groups[:max_groups]
        
        return merged_groups

    def _create_sample_maps_from_map_exporter(self, groups: List[Dict],
                                            relative_sample_path: str,
                                            samples_folder: str) -> List[str]:
        """
        Create sample maps using the shared MAP export logic to avoid code duplication.
        
        Args:
            groups: List of sample groups (one per velocity layer)
            relative_sample_path: Path relative to QPAT file 
            samples_folder: Full path to samples folder
            
        Returns:
            List of sample map strings (max 3)
        """
        sample_maps = []
        
        # Create a MAP exporter with our settings
        map_exporter = WaldorfSampleMapExporter(
            location=self.location,
            loop_mode=self.loop_mode,
            crossfade_ms=self.crossfade_ms
        )
        
        for group in groups[:self.MAX_GROUPS]:
            lines = []
            
            for zone in group['zones']:
                # Create a sample line using the MAP exporter logic
                line = map_exporter._create_map_line(zone, relative_sample_path, samples_folder)
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

        for i in range(min(len(groups), self.MAX_GROUPS)):
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
                    logging.debug("Copied: %s", sample_name)
                else:
                    logging.warning("Sample not found: %s", source)

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
                   location: int = 4, loop_mode: int = 1, optimize_audio: bool = True,
                   crossfade_ms: float = 10.0) -> bool:
    """
    Export multisample to Waldorf QPAT format.

    Args:
        output_folder: Destination folder
        multisample_name: Name of the multisample
        sfz_file: Path to source SFZ file
        samples_folder: Path to sample files
        location: Sample location (2=SD, 3=internal, 4=USB)
        loop_mode: Loop mode (0=off, 1=forward, 2=ping-pong)
        optimize_audio: Convert to 44.1kHz 32-bit float
        crossfade_ms: Loop crossfade time in milliseconds

    Returns:
        True if successful
    """
    exporter = WaldorfQpatExporter(location, loop_mode, optimize_audio, crossfade_ms)
    return exporter.export(output_folder, multisample_name,
                          sfz_file, samples_folder)
