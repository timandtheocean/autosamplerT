"""
Ableton Live Sampler (ADV) Format Exporter
Exports multisamples to .adv format compatible with Ableton Live's Sampler instrument.

Format Specification:
- GZIP-compressed XML file with .adv extension
- Contains sample mappings with key/velocity zones
- Supports velocity crossfade between layers
- Supports round-robin via SelectorRange
- Loop points with crossfade

File Structure:
- Presets/Instruments/Sampler/<name>.adv  (GZIP XML)
- Samples/Imported/<name>/<samples>.wav

Key Features:
- Velocity layers with crossfade
- Key zones with crossfade
- Round-robin via SampleSelector
- Loop points (sustain and release)
- Amplitude/Pitch/Filter envelopes
"""

import os
import gzip
import struct
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# Local imports
from .waldorf_utils import read_wav_loop_points


class AbletonSamplerExporter:
    """Export multisamples to Ableton Live Sampler (ADV) format."""

    # Loop modes
    LOOP_OFF = 0
    LOOP_FORWARD = 1
    LOOP_ALTERNATING = 2  # Ping-pong

    def __init__(self, velocity_crossfade: int = 0, key_crossfade: int = 0):
        """
        Initialize Ableton exporter.

        Args:
            velocity_crossfade: Velocity crossfade amount (0-127, applied to layer boundaries)
            key_crossfade: Key/note crossfade amount (0-127, applied to zone boundaries)
        """
        self.velocity_crossfade = velocity_crossfade
        self.key_crossfade = key_crossfade

    def export(self, output_folder: str, multisample_name: str,
               sfz_file: str, samples_folder: str) -> bool:
        """
        Export multisample to Ableton ADV format.

        Args:
            output_folder: Base output folder (e.g., output/MySynth)
            multisample_name: Name of the multisample
            sfz_file: Path to source SFZ file
            samples_folder: Path to sample files

        Returns:
            True if successful
        """
        try:
            logging.info("Exporting to Ableton ADV: %s", multisample_name)

            # Parse SFZ to get groups and zones
            groups, metadata = self._parse_sfz(sfz_file)

            if not groups:
                logging.error("No groups found in SFZ file")
                return False

            # Create output structure following Ableton's folder convention
            # ADV file goes in same folder as samples for simplicity
            adv_file = os.path.join(output_folder, f'{multisample_name}.adv')

            # Generate XML content
            xml_content = self._create_xml(multisample_name, groups, samples_folder)

            # Write GZIP-compressed ADV file
            with gzip.open(adv_file, 'wb') as f:
                f.write(xml_content.encode('utf-8'))

            logging.info("[SUCCESS] Exported Ableton ADV: %s", adv_file)
            return True

        except Exception as e:
            logging.error("Failed to export Ableton ADV: %s", e)
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
        metadata = {'creator': 'AutosamplerT', 'description': ''}
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
                    if current_zone is not None and 'sample' in current_zone and current_group is not None:
                        current_group['zones'].append(current_zone)

                    if current_group is not None and current_group['zones']:
                        groups.append(current_group)

                    current_group = {'zones': [], 'settings': {}}
                    current_zone = None

                    # Parse inline group parameters
                    params = line[7:].strip()
                    if params:
                        for param in params.split():
                            if '=' in param:
                                key, value = param.split('=', 1)
                                current_group['settings'][key] = value

                # Parse region header
                elif line.startswith('<region>'):
                    if current_group is None:
                        current_group = {'zones': [], 'settings': {}}

                    if current_zone is not None and 'sample' in current_zone:
                        current_group['zones'].append(current_zone)

                    current_zone = {}

                    # Parse inline region parameters
                    params = line[8:].strip()
                    if params:
                        for param in params.split():
                            if '=' in param:
                                key, value = param.split('=', 1)
                                current_zone[key] = value

                # Parse parameters on separate lines
                elif '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

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

    def _create_xml(self, name: str, groups: List[Dict], samples_folder: str) -> str:
        """
        Create Ableton ADV XML content.

        Args:
            name: Preset name
            groups: List of sample groups
            samples_folder: Path to samples

        Returns:
            XML string
        """
        # Collect all zones to analyze for crossfade calculation
        all_zones = []
        for group in groups:
            for zone in group['zones']:
                zone_copy = dict(zone)
                zone_copy['_group_settings'] = group['settings']
                all_zones.append(zone_copy)
        
        # Calculate crossfade info based on zone distribution
        crossfade_info = self._calculate_zone_crossfades(all_zones)
        
        # Build MultiSamplePart entries
        sample_parts = []
        sample_id = 0

        for group in groups:
            for zone in group['zones']:
                # Find matching crossfade info for this zone
                zone_crossfade = self._get_zone_crossfade(zone, group['settings'], crossfade_info)
                part_xml = self._create_sample_part(zone, group['settings'], sample_id, 
                                                    name, samples_folder, zone_crossfade)
                sample_parts.append(part_xml)
                sample_id += 1

        # Create full XML using template
        xml = self._get_template()
        xml = xml.replace('%PRESET_NAME%', name.replace('.', '_'))
        xml = xml.replace('%FILE_NAME%', f'{name}.adv')
        xml = xml.replace('%MULTI_SAMPLE_PARTS%', '\n'.join(sample_parts))
        xml = xml.replace('%PITCHBEND_RANGE%', '2')

        # Default envelope values (can be customized later)
        xml = xml.replace('%AMP_EG_ATTACK_TIME%', '0')
        xml = xml.replace('%AMP_EG_DECAY_TIME%', '100')
        xml = xml.replace('%AMP_EG_RELEASE_TIME%', '500')
        xml = xml.replace('%AMP_EG_START_LEVEL%', '1')
        xml = xml.replace('%AMP_EG_HOLD_LEVEL%', '1')
        xml = xml.replace('%AMP_EG_SUSTAIN_LEVEL%', '1')
        xml = xml.replace('%AMP_EG_END_LEVEL%', '0')
        xml = xml.replace('%AMP_EG_ATTACK_SLOPE%', '0')
        xml = xml.replace('%AMP_EG_DECAY_SLOPE%', '0')
        xml = xml.replace('%AMP_EG_RELEASE_SLOPE%', '0')

        # Pitch envelope (disabled by default)
        xml = xml.replace('%PITCH_EG_ENABLED%', 'false')
        xml = xml.replace('%PITCH_EG_AMOUNT%', '0')
        xml = xml.replace('%PITCH_EG_ATTACK_TIME%', '0')
        xml = xml.replace('%PITCH_EG_DECAY_TIME%', '100')
        xml = xml.replace('%PITCH_EG_RELEASE_TIME%', '500')
        xml = xml.replace('%PITCH_EG_START_LEVEL%', '1')
        xml = xml.replace('%PITCH_EG_HOLD_LEVEL%', '1')
        xml = xml.replace('%PITCH_EG_SUSTAIN_LEVEL%', '1')
        xml = xml.replace('%PITCH_EG_END_LEVEL%', '0')
        xml = xml.replace('%PITCH_EG_ATTACK_SLOPE%', '0')
        xml = xml.replace('%PITCH_EG_DECAY_SLOPE%', '0')
        xml = xml.replace('%PITCH_EG_RELEASE_SLOPE%', '0')

        # Filter (disabled by default)
        xml = xml.replace('%FILTER_ENABLED%', 'false')
        xml = xml.replace('%FILTER_TYPE%', '0')
        xml = xml.replace('%FILTER_SLOPE%', 'false')
        xml = xml.replace('%FILTER_FREQ%', '18000')
        xml = xml.replace('%FILTER_RES%', '0.5')
        xml = xml.replace('%FILTER_EG_ENABLED%', 'false')
        xml = xml.replace('%FILTER_EG_AMOUNT%', '0')
        xml = xml.replace('%FILTER_EG_ATTACK_TIME%', '0')
        xml = xml.replace('%FILTER_EG_DECAY_TIME%', '100')
        xml = xml.replace('%FILTER_EG_RELEASE_TIME%', '500')
        xml = xml.replace('%FILTER_EG_START_LEVEL%', '1')
        xml = xml.replace('%FILTER_EG_HOLD_LEVEL%', '1')
        xml = xml.replace('%FILTER_EG_SUSTAIN_LEVEL%', '1')
        xml = xml.replace('%FILTER_EG_END_LEVEL%', '0')
        xml = xml.replace('%FILTER_EG_ATTACK_SLOPE%', '0')
        xml = xml.replace('%FILTER_EG_DECAY_SLOPE%', '0')
        xml = xml.replace('%FILTER_EG_RELEASE_SLOPE%', '0')
        xml = xml.replace('%FILTER_VELOCITY_MOD%', '0')
        xml = xml.replace('%VOLUME_VELOCITY_MOD%', '1')

        return xml

    def _calculate_zone_crossfades(self, zones: List[Dict]) -> Dict:
        """
        Calculate crossfade values for all zones based on their distribution.
        
        Analyzes key and velocity zones to determine appropriate crossfade amounts
        for smooth transitions between adjacent zones.
        
        Args:
            zones: List of all sample zones with their settings
            
        Returns:
            Dictionary with crossfade info per zone
        """
        if not zones:
            return {'key_crossfade': 0, 'vel_crossfade': 0, 'zones': {}}
        
        # Collect all unique key and velocity boundaries
        key_points = set()
        vel_points = set()
        
        for zone in zones:
            settings = zone.get('_group_settings', {})
            key_low = int(zone.get('lokey', settings.get('lokey', 0)))
            key_high = int(zone.get('hikey', settings.get('hikey', 127)))
            vel_low = int(zone.get('lovel', settings.get('lovel', 1)))
            vel_high = int(zone.get('hivel', settings.get('hivel', 127)))
            
            key_points.add(key_low)
            key_points.add(key_high)
            vel_points.add(vel_low)
            vel_points.add(vel_high)
        
        # Calculate key crossfade based on gaps between zones
        key_sorted = sorted(key_points)
        key_crossfade = 0
        if len(key_sorted) > 2:
            # Find typical gap between adjacent key zones
            gaps = [key_sorted[i+1] - key_sorted[i] for i in range(len(key_sorted)-1)]
            gaps = [g for g in gaps if g > 0]  # Only positive gaps
            if gaps:
                avg_gap = sum(gaps) / len(gaps)
                # Crossfade is typically half the gap, capped at 6 semitones
                key_crossfade = min(int(avg_gap / 2), 6)
        
        # Calculate velocity crossfade based on number of velocity layers
        vel_sorted = sorted(vel_points)
        vel_crossfade = 0
        if len(vel_sorted) > 2:
            # Count velocity layers
            vel_layers = len(vel_sorted) // 2
            if vel_layers > 1:
                # Default crossfade: ~10% of velocity range per layer
                vel_crossfade = min(15, 127 // (vel_layers * 2))
        
        logging.debug(f"Calculated crossfades: key={key_crossfade}, vel={vel_crossfade}")
        
        return {
            'key_crossfade': key_crossfade,
            'vel_crossfade': vel_crossfade,
            'zones': {}
        }
    
    def _get_zone_crossfade(self, zone: Dict, group_settings: Dict, 
                           crossfade_info: Dict) -> Dict:
        """
        Get crossfade values for a specific zone.
        
        Args:
            zone: Zone data
            group_settings: Group-level settings
            crossfade_info: Pre-calculated crossfade info
            
        Returns:
            Dictionary with key_low, key_high, vel_low, vel_high crossfade values
        """
        key_xf = crossfade_info.get('key_crossfade', 0)
        vel_xf = crossfade_info.get('vel_crossfade', 0)
        
        key_low = int(zone.get('lokey', group_settings.get('lokey', 0)))
        key_high = int(zone.get('hikey', group_settings.get('hikey', 127)))
        vel_low = int(zone.get('lovel', group_settings.get('lovel', 1)))
        vel_high = int(zone.get('hivel', group_settings.get('hivel', 127)))
        
        return {
            'key_crossfade_low': max(0, key_low - key_xf),
            'key_crossfade_high': min(127, key_high + key_xf),
            'vel_crossfade_low': max(1, vel_low - vel_xf),
            'vel_crossfade_high': min(127, vel_high + vel_xf),
        }

    def _create_sample_part(self, zone: Dict, group_settings: Dict, sample_id: int,
                           folder_name: str, samples_folder: str,
                           zone_crossfade: Optional[Dict] = None) -> str:
        """
        Create XML for a single MultiSamplePart.

        Args:
            zone: Zone data from SFZ
            group_settings: Group-level settings
            sample_id: Unique sample ID
            folder_name: Sample subfolder name
            samples_folder: Full path to samples
            zone_crossfade: Pre-calculated crossfade values for this zone

        Returns:
            XML string for MultiSamplePart
        """
        # Get sample file info
        sample_path = zone.get('sample', '')
        sample_name = os.path.basename(sample_path)
        full_sample_path = os.path.join(samples_folder, sample_name)

        # Get audio metadata
        sample_rate, num_samples, file_size = self._get_audio_info(full_sample_path)
        file_timestamp = int(os.path.getmtime(full_sample_path)) if os.path.exists(full_sample_path) else 0

        # Key range
        key_low = int(zone.get('lokey', group_settings.get('lokey', 0)))
        key_high = int(zone.get('hikey', group_settings.get('hikey', 127)))
        root_key = int(zone.get('pitch_keycenter', zone.get('key', (key_low + key_high) // 2)))

        # Velocity range
        vel_low = int(zone.get('lovel', group_settings.get('lovel', 1)))
        vel_high = int(zone.get('hivel', group_settings.get('hivel', 127)))

        # Selector range (for round-robin)
        # If seq_position is set, use it for selector range
        seq_position = int(zone.get('seq_position', group_settings.get('seq_position', 0)))
        seq_length = int(zone.get('seq_length', group_settings.get('seq_length', 1)))
        
        if seq_length > 1:
            # Map round-robin to selector range
            selector_step = 128 // seq_length
            selector_low = seq_position * selector_step
            selector_high = min(127, (seq_position + 1) * selector_step - 1)
        else:
            selector_low = 0
            selector_high = 127

        # Crossfade calculations - use pre-calculated values or fall back to instance defaults
        if zone_crossfade:
            key_crossfade_low = zone_crossfade['key_crossfade_low']
            key_crossfade_high = zone_crossfade['key_crossfade_high']
            vel_crossfade_low = zone_crossfade['vel_crossfade_low']
            vel_crossfade_high = zone_crossfade['vel_crossfade_high']
        else:
            key_crossfade_low = max(0, key_low - self.key_crossfade)
            key_crossfade_high = min(127, key_high + self.key_crossfade)
            vel_crossfade_low = max(1, vel_low - self.velocity_crossfade)
            vel_crossfade_high = min(127, vel_high + self.velocity_crossfade)

        # Tuning
        tune = float(zone.get('tune', 0))
        detune = int(tune * 100) % 100  # Cents

        # Volume and pan
        volume = float(zone.get('volume', 0))
        volume_linear = pow(2, volume / 6.0)  # dB to linear
        pan = float(zone.get('pan', 0)) / 100.0  # -100..100 to -1..1

        # Loop points from WAV file
        # read_wav_loop_points returns (loop_start_normalized, loop_end_normalized, has_loop)
        loop_start = 0
        loop_end = num_samples
        loop_mode = self.LOOP_OFF
        loop_crossfade = 0

        if os.path.exists(full_sample_path):
            loop_start_norm, loop_end_norm, has_loop = read_wav_loop_points(full_sample_path)
            if has_loop:
                # Convert normalized (0.0-1.0) to sample positions
                loop_start = int(loop_start_norm * num_samples)
                loop_end = int(loop_end_norm * num_samples)
                loop_mode = self.LOOP_FORWARD
                # Calculate crossfade in samples (default 10ms worth)
                loop_crossfade = int(sample_rate * 0.01)

        # Build XML
        template = self._get_sample_part_template()
        xml = template.replace('%SAMPLE_ID%', str(sample_id))
        xml = xml.replace('%SAMPLE_FOLDER%', folder_name)
        xml = xml.replace('%SAMPLE_FILE%', sample_name)
        xml = xml.replace('%SAMPLE_START%', '0')
        xml = xml.replace('%SAMPLE_END%', str(num_samples))
        xml = xml.replace('%SAMPLE_FILE_SIZE%', str(file_size))
        xml = xml.replace('%SAMPLE_FILE_TIMESTAMP%', str(file_timestamp))
        xml = xml.replace('%SAMPLE_RATE%', str(sample_rate))
        xml = xml.replace('%SAMPLE_DURATION%', str(num_samples))

        xml = xml.replace('%KEY_RANGE_LOW%', str(key_low))
        xml = xml.replace('%KEY_RANGE_HIGH%', str(key_high))
        xml = xml.replace('%KEY_RANGE_LOW_CROSSFADE%', str(key_crossfade_low))
        xml = xml.replace('%KEY_RANGE_HIGH_CROSSFADE%', str(key_crossfade_high))

        xml = xml.replace('%VEL_RANGE_LOW%', str(vel_low))
        xml = xml.replace('%VEL_RANGE_HIGH%', str(vel_high))
        xml = xml.replace('%VEL_RANGE_LOW_CROSSFADE%', str(vel_crossfade_low))
        xml = xml.replace('%VEL_RANGE_HIGH_CROSSFADE%', str(vel_crossfade_high))

        xml = xml.replace('%SELECTOR_LOW%', str(selector_low))
        xml = xml.replace('%SELECTOR_HIGH%', str(selector_high))

        xml = xml.replace('%ROOT_KEY%', str(root_key))
        xml = xml.replace('%DETUNE%', str(detune))
        xml = xml.replace('%TUNE_SCALE%', '100')  # Normal key tracking
        xml = xml.replace('%PANORAMA%', f'{pan:.8f}')
        xml = xml.replace('%VOLUME%', f'{volume_linear:.8f}')

        xml = xml.replace('%LOOP_MODE%', str(loop_mode))
        xml = xml.replace('%LOOP_START%', str(loop_start))
        xml = xml.replace('%LOOP_END%', str(loop_end))
        xml = xml.replace('%LOOP_CROSSFADE%', str(loop_crossfade))

        return xml

    def _get_audio_info(self, wav_path: str) -> Tuple[int, int, int]:
        """
        Get audio file information.

        Returns:
            (sample_rate, num_samples, file_size)
        """
        if not os.path.exists(wav_path):
            return 44100, 0, 0

        file_size = os.path.getsize(wav_path)
        sample_rate = 44100
        num_samples = 0

        try:
            with open(wav_path, 'rb') as f:
                # Read RIFF header
                riff = f.read(4)
                if riff != b'RIFF':
                    return sample_rate, num_samples, file_size

                f.read(4)  # File size
                wave = f.read(4)
                if wave != b'WAVE':
                    return sample_rate, num_samples, file_size

                # Find fmt chunk
                while True:
                    chunk_id = f.read(4)
                    if len(chunk_id) < 4:
                        break
                    chunk_size = struct.unpack('<I', f.read(4))[0]

                    if chunk_id == b'fmt ':
                        fmt_data = f.read(chunk_size)
                        audio_format = struct.unpack('<H', fmt_data[0:2])[0]
                        num_channels = struct.unpack('<H', fmt_data[2:4])[0]
                        sample_rate = struct.unpack('<I', fmt_data[4:8])[0]
                        bits_per_sample = struct.unpack('<H', fmt_data[14:16])[0]
                    elif chunk_id == b'data':
                        bytes_per_sample = bits_per_sample // 8 if bits_per_sample else 2
                        num_samples = chunk_size // (num_channels * bytes_per_sample)
                        break
                    else:
                        f.seek(chunk_size, 1)

        except Exception as e:
            logging.warning("Failed to read audio info from %s: %s", wav_path, e)

        return sample_rate, num_samples, file_size

    def _get_template(self) -> str:
        """Get the main ADV XML template."""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="5" MinorVersion="11.0_11300" SchemaChangeCount="3" Creator="AutosamplerT" Revision="">
	<MultiSampler>
		<LomId Value="0" />
		<LomIdView Value="0" />
		<IsExpanded Value="true" />
		<On>
			<LomId Value="0" />
			<Manual Value="true" />
			<AutomationTarget Id="0">
				<LockEnvelope Value="0" />
			</AutomationTarget>
			<MidiCCOnOffThresholds>
				<Min Value="64" />
				<Max Value="127" />
			</MidiCCOnOffThresholds>
		</On>
		<ModulationSourceCount Value="0" />
		<ParametersListWrapper LomId="0" />
		<Pointee Id="0" />
		<LastSelectedTimeableIndex Value="0" />
		<LastSelectedClipEnvelopeIndex Value="0" />
		<LastPresetRef>
			<Value>
				<FilePresetRef Id="0">
					<FileRef>
						<RelativePathType Value="6" />
						<RelativePath Value="Presets/Instruments/Sampler/%FILE_NAME%" />
						<Path Value="" />
						<Type Value="1" />
						<LivePackName Value="" />
						<LivePackId Value="" />
						<OriginalFileSize Value="0" />
						<OriginalCrc Value="0" />
					</FileRef>
				</FilePresetRef>
			</Value>
		</LastPresetRef>
		<LockedScripts />
		<IsFolded Value="false" />
		<ShouldShowPresetName Value="true" />
		<UserName Value="%PRESET_NAME%" />
		<Annotation Value="" />
		<SourceContext>
			<Value />
		</SourceContext>
		<OverwriteProtectionNumber Value="2820" />
		<Player>
			<MultiSampleMap>
				<SampleParts>
%MULTI_SAMPLE_PARTS%
				</SampleParts>
				<LoadInRam Value="false" />
				<LayerCrossfade Value="0" />
				<SourceContext />
			</MultiSampleMap>
			<LoopModulators>
				<IsModulated Value="false" />
				<SampleStart>
					<LomId Value="0" />
					<Manual Value="0" />
					<MidiControllerRange>
						<Min Value="0" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</SampleStart>
				<SampleLength>
					<LomId Value="0" />
					<Manual Value="1" />
					<MidiControllerRange>
						<Min Value="0" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</SampleLength>
				<LoopOn>
					<LomId Value="0" />
					<Manual Value="false" />
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<MidiCCOnOffThresholds>
						<Min Value="64" />
						<Max Value="127" />
					</MidiCCOnOffThresholds>
				</LoopOn>
				<LoopLength>
					<LomId Value="0" />
					<Manual Value="1" />
					<MidiControllerRange>
						<Min Value="0" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</LoopLength>
				<LoopFade>
					<LomId Value="0" />
					<Manual Value="0" />
					<MidiControllerRange>
						<Min Value="0" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</LoopFade>
			</LoopModulators>
			<Reverse>
				<LomId Value="0" />
				<Manual Value="false" />
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<MidiCCOnOffThresholds>
					<Min Value="64" />
					<Max Value="127" />
				</MidiCCOnOffThresholds>
			</Reverse>
			<Snap>
				<LomId Value="0" />
				<Manual Value="false" />
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<MidiCCOnOffThresholds>
					<Min Value="64" />
					<Max Value="127" />
				</MidiCCOnOffThresholds>
			</Snap>
			<SampleSelector>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="0" />
					<Max Value="127" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</SampleSelector>
			<SubOsc>
				<IsOn>
					<LomId Value="0" />
					<Manual Value="false" />
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<MidiCCOnOffThresholds>
						<Min Value="64" />
						<Max Value="127" />
					</MidiCCOnOffThresholds>
				</IsOn>
				<Slot>
					<Value />
				</Slot>
			</SubOsc>
			<InterpolationMode Value="1" />
			<UseConstPowCrossfade Value="true" />
		</Player>
		<Pitch>
			<TransposeKey>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="-48" />
					<Max Value="48" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</TransposeKey>
			<TransposeFine>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="-50" />
					<Max Value="50" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</TransposeFine>
			<PitchLfoAmount>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="0" />
					<Max Value="1" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</PitchLfoAmount>
			<Envelope>
				<IsOn>
					<LomId Value="0" />
					<Manual Value="%PITCH_EG_ENABLED%" />
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<MidiCCOnOffThresholds>
						<Min Value="64" />
						<Max Value="127" />
					</MidiCCOnOffThresholds>
				</IsOn>
				<Slot>
					<Value />
				</Slot>
			</Envelope>
			<ScrollPosition Value="-1073741824" />
		</Pitch>
		<Filter>
			<IsOn>
				<LomId Value="0" />
				<Manual Value="%FILTER_ENABLED%" />
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<MidiCCOnOffThresholds>
					<Min Value="64" />
					<Max Value="127" />
				</MidiCCOnOffThresholds>
			</IsOn>
			<Slot>
				<Value>
					<SimplerFilter Id="0">
						<LegacyType>
							<LomId Value="0" />
							<Manual Value="2" />
							<AutomationTarget Id="0">
								<LockEnvelope Value="0" />
							</AutomationTarget>
						</LegacyType>
						<Type>
							<LomId Value="0" />
							<Manual Value="%FILTER_TYPE%" />
							<AutomationTarget Id="0">
								<LockEnvelope Value="0" />
							</AutomationTarget>
						</Type>
						<CircuitLpHp>
							<LomId Value="0" />
							<Manual Value="2" />
							<AutomationTarget Id="0">
								<LockEnvelope Value="0" />
							</AutomationTarget>
						</CircuitLpHp>
						<CircuitBpNoMo>
							<LomId Value="0" />
							<Manual Value="0" />
							<AutomationTarget Id="0">
								<LockEnvelope Value="0" />
							</AutomationTarget>
						</CircuitBpNoMo>
						<Slope>
							<LomId Value="0" />
							<Manual Value="%FILTER_SLOPE%" />
							<AutomationTarget Id="0">
								<LockEnvelope Value="0" />
							</AutomationTarget>
							<MidiCCOnOffThresholds>
								<Min Value="64" />
								<Max Value="127" />
							</MidiCCOnOffThresholds>
						</Slope>
						<Freq>
							<LomId Value="0" />
							<Manual Value="%FILTER_FREQ%" />
							<MidiControllerRange>
								<Min Value="30" />
								<Max Value="22000" />
							</MidiControllerRange>
							<AutomationTarget Id="0">
								<LockEnvelope Value="0" />
							</AutomationTarget>
							<ModulationTarget Id="0">
								<LockEnvelope Value="0" />
							</ModulationTarget>
						</Freq>
						<Res>
							<LomId Value="0" />
							<Manual Value="%FILTER_RES%" />
							<MidiControllerRange>
								<Min Value="0" />
								<Max Value="1.25" />
							</MidiControllerRange>
							<AutomationTarget Id="0">
								<LockEnvelope Value="0" />
							</AutomationTarget>
							<ModulationTarget Id="0">
								<LockEnvelope Value="0" />
							</ModulationTarget>
						</Res>
					</SimplerFilter>
				</Value>
			</Slot>
			<Envelope>
				<IsOn>
					<LomId Value="0" />
					<Manual Value="%FILTER_EG_ENABLED%" />
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<MidiCCOnOffThresholds>
						<Min Value="64" />
						<Max Value="127" />
					</MidiCCOnOffThresholds>
				</IsOn>
				<Slot>
					<Value />
				</Slot>
			</Envelope>
			<ModByVelocity>
				<LomId Value="0" />
				<Manual Value="%FILTER_VELOCITY_MOD%" />
				<MidiControllerRange>
					<Min Value="-72" />
					<Max Value="72" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</ModByVelocity>
			<ModByPitch>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="-72" />
					<Max Value="72" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</ModByPitch>
			<ModByLfo>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="0" />
					<Max Value="1" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</ModByLfo>
			<ScrollPosition Value="-1073741824" />
		</Filter>
		<Shaper>
			<IsOn>
				<LomId Value="0" />
				<Manual Value="false" />
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<MidiCCOnOffThresholds>
					<Min Value="64" />
					<Max Value="127" />
				</MidiCCOnOffThresholds>
			</IsOn>
			<Slot>
				<Value />
			</Slot>
		</Shaper>
		<VolumeAndPan>
			<Volume>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="-36" />
					<Max Value="36" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</Volume>
			<VolumeVelScale>
				<LomId Value="0" />
				<Manual Value="%VOLUME_VELOCITY_MOD%" />
				<MidiControllerRange>
					<Min Value="0" />
					<Max Value="1" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</VolumeVelScale>
			<VolumeLfoAmount>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="0" />
					<Max Value="1" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</VolumeLfoAmount>
			<Panorama>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="-1" />
					<Max Value="1" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</Panorama>
			<PanoramaLfoAmount>
				<LomId Value="0" />
				<Manual Value="0" />
				<MidiControllerRange>
					<Min Value="0" />
					<Max Value="1" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</PanoramaLfoAmount>
			<Envelope>
				<AttackTime>
					<LomId Value="0" />
					<Manual Value="%AMP_EG_ATTACK_TIME%" />
					<MidiControllerRange>
						<Min Value="0" />
						<Max Value="100000" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</AttackTime>
				<DecayTime>
					<LomId Value="0" />
					<Manual Value="%AMP_EG_DECAY_TIME%" />
					<MidiControllerRange>
						<Min Value="1" />
						<Max Value="60000" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</DecayTime>
				<SustainLevel>
					<LomId Value="0" />
					<Manual Value="%AMP_EG_SUSTAIN_LEVEL%" />
					<MidiControllerRange>
						<Min Value="0" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</SustainLevel>
				<ReleaseTime>
					<LomId Value="0" />
					<Manual Value="%AMP_EG_RELEASE_TIME%" />
					<MidiControllerRange>
						<Min Value="1" />
						<Max Value="60000" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</ReleaseTime>
				<AttackSlope>
					<LomId Value="0" />
					<Manual Value="%AMP_EG_ATTACK_SLOPE%" />
					<MidiControllerRange>
						<Min Value="-1" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</AttackSlope>
				<DecaySlope>
					<LomId Value="0" />
					<Manual Value="%AMP_EG_DECAY_SLOPE%" />
					<MidiControllerRange>
						<Min Value="-1" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</DecaySlope>
				<ReleaseSlope>
					<LomId Value="0" />
					<Manual Value="%AMP_EG_RELEASE_SLOPE%" />
					<MidiControllerRange>
						<Min Value="-1" />
						<Max Value="1" />
					</MidiControllerRange>
					<AutomationTarget Id="0">
						<LockEnvelope Value="0" />
					</AutomationTarget>
					<ModulationTarget Id="0">
						<LockEnvelope Value="0" />
					</ModulationTarget>
				</ReleaseSlope>
			</Envelope>
			<OneShotEnvelope Value="false" />
			<ScrollPosition Value="-1073741824" />
		</VolumeAndPan>
		<AuxEnv>
			<IsOn>
				<LomId Value="0" />
				<Manual Value="false" />
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<MidiCCOnOffThresholds>
					<Min Value="64" />
					<Max Value="127" />
				</MidiCCOnOffThresholds>
			</IsOn>
			<Slot>
				<Value />
			</Slot>
			<ScrollPosition Value="-1073741824" />
		</AuxEnv>
		<Lfo>
			<IsOn>
				<LomId Value="0" />
				<Manual Value="false" />
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<MidiCCOnOffThresholds>
					<Min Value="64" />
					<Max Value="127" />
				</MidiCCOnOffThresholds>
			</IsOn>
			<Slot>
				<Value />
			</Slot>
			<ScrollPosition Value="-1073741824" />
		</Lfo>
		<Globals>
			<GlideTime>
				<LomId Value="0" />
				<Manual Value="100" />
				<MidiControllerRange>
					<Min Value="1" />
					<Max Value="10000" />
				</MidiControllerRange>
				<AutomationTarget Id="0">
					<LockEnvelope Value="0" />
				</AutomationTarget>
				<ModulationTarget Id="0">
					<LockEnvelope Value="0" />
				</ModulationTarget>
			</GlideTime>
			<GlideMode Value="0" />
			<PitchBendRange Value="%PITCHBEND_RANGE%" />
			<NumVoices Value="6" />
			<RetriggerMode Value="0" />
			<ModSources>
				<ModWheelOn Value="false" />
				<PressureOn Value="false" />
				<SlideOn Value="false" />
				<RandOn Value="false" />
				<AltOn Value="false" />
			</ModSources>
		</Globals>
		<ViewSettings>
			<SelectedPage Value="0" />
			<ZoneEditorVisible Value="true" />
		</ViewSettings>
	</MultiSampler>
</Ableton>'''

    def _get_sample_part_template(self) -> str:
        """Get the MultiSamplePart XML template."""
        return '''					<MultiSamplePart Id="%SAMPLE_ID%" HasImportedSlicePoints="true" NeedsAnalysisData="false">
						<LomId Value="0" />
						<Name Value="%SAMPLE_FILE%" />
						<Selection Value="true" />
						<IsActive Value="true" />
						<Solo Value="false" />
						<KeyRange>
							<Min Value="%KEY_RANGE_LOW%" />
							<Max Value="%KEY_RANGE_HIGH%" />
							<CrossfadeMin Value="%KEY_RANGE_LOW_CROSSFADE%" />
							<CrossfadeMax Value="%KEY_RANGE_HIGH_CROSSFADE%" />
						</KeyRange>
						<VelocityRange>
							<Min Value="%VEL_RANGE_LOW%" />
							<Max Value="%VEL_RANGE_HIGH%" />
							<CrossfadeMin Value="%VEL_RANGE_LOW_CROSSFADE%" />
							<CrossfadeMax Value="%VEL_RANGE_HIGH_CROSSFADE%" />
						</VelocityRange>
						<SelectorRange>
							<Min Value="%SELECTOR_LOW%" />
							<Max Value="%SELECTOR_HIGH%" />
							<CrossfadeMin Value="%SELECTOR_LOW%" />
							<CrossfadeMax Value="%SELECTOR_HIGH%" />
						</SelectorRange>
						<RootKey Value="%ROOT_KEY%" />
						<Detune Value="%DETUNE%" />
						<TuneScale Value="%TUNE_SCALE%" />
						<Panorama Value="%PANORAMA%" />
						<Volume Value="%VOLUME%" />
						<Link Value="false" />
						<SampleStart Value="%SAMPLE_START%" />
						<SampleEnd Value="%SAMPLE_END%" />
						<SustainLoop>
							<Start Value="%LOOP_START%" />
							<End Value="%LOOP_END%" />
							<Mode Value="%LOOP_MODE%" />
							<Crossfade Value="%LOOP_CROSSFADE%" />
							<Detune Value="0" />
						</SustainLoop>
						<ReleaseLoop>
							<Start Value="0" />
							<End Value="%SAMPLE_END%" />
							<Mode Value="3" />
							<Crossfade Value="0" />
							<Detune Value="0" />
						</ReleaseLoop>
						<SampleRef>
							<FileRef>
								<RelativePathType Value="5" />
								<RelativePath Value="samples/%SAMPLE_FILE%" />
								<Path Value="" />
								<Type Value="1" />
								<LivePackName Value="" />
								<LivePackId Value="" />
								<OriginalFileSize Value="%SAMPLE_FILE_SIZE%" />
							</FileRef>
							<LastModDate Value="%SAMPLE_FILE_TIMESTAMP%" />
							<SourceContext />
							<SampleUsageHint Value="0" />
							<DefaultDuration Value="%SAMPLE_DURATION%" />
							<DefaultSampleRate Value="%SAMPLE_RATE%" />
						</SampleRef>
						<SlicingThreshold Value="100" />
						<SlicingBeatGrid Value="4" />
						<SlicingRegions Value="8" />
						<SlicingStyle Value="0" />
						<SampleWarpProperties>
							<WarpMarkers />
							<WarpMode Value="0" />
							<GranularityTones Value="30" />
							<GranularityTexture Value="65" />
							<FluctuationTexture Value="25" />
							<ComplexProFormants Value="100" />
							<ComplexProEnvelope Value="128" />
							<TransientResolution Value="6" />
							<TransientLoopMode Value="2" />
							<TransientEnvelope Value="100" />
							<IsWarped Value="false" />
							<Onsets>
								<UserOnsets />
								<HasUserOnsets Value="false" />
							</Onsets>
							<TimeSignature>
								<TimeSignatures>
									<RemoteableTimeSignature Id="0">
										<Numerator Value="4" />
										<Denominator Value="4" />
										<Time Value="0" />
									</RemoteableTimeSignature>
								</TimeSignatures>
							</TimeSignature>
							<BeatGrid>
								<FixedNumerator Value="1" />
								<FixedDenominator Value="16" />
								<GridIntervalPixel Value="20" />
								<Ntoles Value="2" />
								<SnapToGrid Value="true" />
								<Fixed Value="false" />
							</BeatGrid>
						</SampleWarpProperties>
						<SlicePoints />
						<ManualSlicePoints />
						<BeatSlicePoints />
						<RegionSlicePoints />
						<UseDynamicBeatSlices Value="true" />
						<UseDynamicRegionSlices Value="true" />
					</MultiSamplePart>'''


def export_to_ableton(output_folder: str, multisample_name: str,
                      sfz_file: str, samples_folder: str,
                      velocity_crossfade: int = 0,
                      key_crossfade: int = 0) -> bool:
    """
    Export multisample to Ableton Live Sampler (ADV) format.

    Args:
        output_folder: Destination folder
        multisample_name: Name of the multisample
        sfz_file: Path to source SFZ file
        samples_folder: Path to sample files
        velocity_crossfade: Velocity crossfade amount (0-127)
        key_crossfade: Key crossfade amount (0-127)

    Returns:
        True if successful
    """
    exporter = AbletonSamplerExporter(velocity_crossfade, key_crossfade)
    return exporter.export(output_folder, multisample_name, sfz_file, samples_folder)
