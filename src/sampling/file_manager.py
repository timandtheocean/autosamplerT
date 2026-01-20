"""
File I/O operations for WAV and SFZ files.

This module provides FileManager class that handles:
- WAV file saving with metadata
- RIFF chunk metadata writing
- SFZ file generation
- Sample file naming
- Output folder management
"""

import logging
import struct
import json
import wave
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np


class FileManager:
    """
    Handles all file I/O operations for sampling.

    Supports:
    - WAV file writing with custom bit depths (16/24/32)
    - RIFF metadata chunks for MIDI information
    - SFZ file generation with velocity layers and round-robin
    - Folder structure management
    """

    def __init__(self, sampling_config: Dict, audio_config: Dict, test_mode: bool = False):
        """
        Initialize the file manager.

        Args:
            sampling_config: Sampling configuration dictionary
            audio_config: Audio configuration dictionary (for WAV settings)
            test_mode: If True, skip certain I/O operations
        """
        self.sampling_config = sampling_config
        self.audio_config = audio_config
        self.test_mode = test_mode

        # Audio settings for WAV writing
        self.samplerate = audio_config.get('samplerate', 44100)
        self.bitdepth = audio_config.get('bitdepth', 24)
        self.channels = 2 if audio_config.get('mono_stereo', 'stereo') == 'stereo' else 1

        # Output settings
        self.base_output_folder = Path(sampling_config.get('output_folder', './output'))
        self.multisample_name = sampling_config.get('multisample_name', 'Multisample')

        # Create folder structure: output/multisample_name/samples/
        self.multisample_folder = self.base_output_folder / self.multisample_name
        self.output_folder = self.multisample_folder / 'samples'

        # SFZ key mapping range
        self.lowest_note = sampling_config.get('lowest_note', 0)
        self.highest_note = sampling_config.get('highest_note', 127)

        # Velocity settings for SFZ
        self.velocity_layers = sampling_config.get('velocity_layers', 1)
        self.velocity_layers_split = sampling_config.get('velocity_layers_split', None)
        self.velocity_minimum = sampling_config.get('velocity_minimum', 1)
        self.roundrobin_layers = sampling_config.get('roundrobin_layers', 1)

    def generate_sample_filename(self, note: int, velocity: int, rr_index: int = 0) -> str:
        """
        Generate standardized sample filename.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            rr_index: Round-robin index

        Returns:
            Filename string
        """
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note // 12) - 1
        note_name = note_names[note % 12]

        base_name = self.sampling_config.get('sample_name', self.multisample_name)

        if self.roundrobin_layers > 1:
            filename = f"{base_name}_{note_name}{octave}_v{velocity:03d}_rr{rr_index+1}.wav"
        else:
            filename = f"{base_name}_{note_name}{octave}_v{velocity:03d}.wav"

        return filename

    def save_wav(self, audio: np.ndarray, filepath: Path, metadata: Dict = None) -> bool:
        """
        Save audio to WAV file with optional metadata in RIFF chunks.

        Args:
            audio: Audio data as NumPy array
            filepath: Output file path
            metadata: Optional dictionary of metadata (note, velocity, etc.)

        Returns:
            True if save successful, False otherwise
        """
        try:
            logging.info(f"Saving WAV file: {filepath} ({len(audio)} frames)")

            # Convert float32 to appropriate bit depth
            if self.bitdepth == 16:
                audio_int = np.int16(audio * 32767)
                sampwidth = 2
            elif self.bitdepth == 24:
                audio_int = np.int32(audio * 8388607)
                sampwidth = 3
            elif self.bitdepth == 32:
                audio_int = np.int32(audio * 2147483647)
                sampwidth = 4
            else:
                audio_int = np.int16(audio * 32767)
                sampwidth = 2

            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Write WAV file using wave module for custom chunk support
            with wave.open(str(filepath), 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(sampwidth)
                wav_file.setframerate(self.samplerate)

                # Convert audio to bytes
                if self.bitdepth == 24:
                    # Special handling for 24-bit - efficient method
                    # Convert to bytes and extract 3 bytes per sample
                    audio_32bit = audio_int.tobytes()
                    audio_bytes = bytearray()
                    # Each 32-bit sample is 4 bytes, we want the lower 3 bytes
                    for i in range(0, len(audio_32bit), 4):
                        audio_bytes.extend(audio_32bit[i:i+3])
                    audio_bytes = bytes(audio_bytes)
                else:
                    audio_bytes = audio_int.tobytes()

                wav_file.writeframes(audio_bytes)

            # Now reopen the file and add custom RIFF chunks for metadata
            if metadata:
                self._add_riff_metadata(filepath, metadata)

            logging.info(f"Saved: {filepath}")
            return True
        except Exception as e:
            logging.error(f"Failed to save WAV file {filepath}: {e}")
            return False

    def _add_riff_metadata(self, filepath: Path, metadata: Dict) -> None:
        """
        Add custom RIFF chunks containing MIDI metadata to WAV file.

        Args:
            filepath: Path to WAV file
            metadata: Dictionary with note, velocity, etc.
        """
        try:
            # Read the entire file
            with open(filepath, 'rb', encoding=None) as f:
                data = bytearray(f.read())

            # Create custom 'note' chunk with MIDI data
            # Format: note (1 byte), velocity (1 byte), channel (1 byte)
            note_data = struct.pack('BBB',
                                   metadata.get('note', 0),
                                   metadata.get('velocity', 127),
                                   metadata.get('channel', 0))

            # RIFF chunk format: chunk_id (4 bytes), size (4 bytes), data
            chunk_id = b'note'
            chunk_size = struct.pack('<I', len(note_data))  # Little-endian 32-bit
            note_chunk = chunk_id + chunk_size + note_data

            # Pad to even length (RIFF requirement)
            if len(note_chunk) % 2:
                note_chunk += b'\x00'

            # Append chunk to file
            data.extend(note_chunk)

            # Update RIFF chunk size (at bytes 4-7)
            new_size = len(data) - 8
            data[4:8] = struct.pack('<I', new_size)

            # Write back to file
            with open(filepath, 'wb') as f:
                f.write(data)

            logging.debug(f"RIFF metadata added: note={metadata.get('note')}, "
                         f"vel={metadata.get('velocity')}")

            # Also write sidecar JSON only if debug mode is enabled
            if self.audio_config.get('debug', False):
                meta_path = filepath.with_suffix('.json')
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                logging.debug(f"Sidecar metadata written to {meta_path}")

        except Exception as e:
            logging.warning(f"Failed to add RIFF metadata: {e}")

    def generate_sfz(self, sample_list: List[Dict], output_path: Path = None) -> bool:
        """
        Generate SFZ mapping file for the sampled instrument.

        Args:
            sample_list: List of sample metadata dictionaries
            output_path: Output SFZ file path

        Returns:
            True if successful, False otherwise
        """
        if output_path is None:
            # SFZ file goes in the multisample folder
            output_path = self.multisample_folder / f"{self.multisample_name}.sfz"

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"// {self.multisample_name} - Generated by AutosamplerT\n")
                f.write(f"// Sample Rate: {self.samplerate} Hz\n")
                f.write(f"// Bit Depth: {self.bitdepth} bits\n\n")

                # Group samples by velocity layer and round-robin
                samples_by_vel_rr = {}
                for sample in sample_list:
                    vel_layer = sample.get('velocity_layer', 0)
                    rr_layer = sample.get('roundrobin_layer', 0)
                    key = (vel_layer, rr_layer)
                    if key not in samples_by_vel_rr:
                        samples_by_vel_rr[key] = []
                    samples_by_vel_rr[key].append(sample)

                # Also group by note for key mapping
                samples_by_note = {}
                for sample in sample_list:
                    note = sample['note']
                    if note not in samples_by_note:
                        samples_by_note[note] = []
                    samples_by_note[note].append(sample)

                # Get the note range for key mapping
                all_notes = sorted(samples_by_note.keys())
                if not all_notes:
                    logging.warning("No samples to write to SFZ")
                    return True

                # Write groups (for velocity layers and round-robin)
                # Sort groups by velocity layer, then round-robin
                sorted_groups = sorted(samples_by_vel_rr.keys())

                for group_key in sorted_groups:
                    vel_layer, rr_layer = group_key
                    group_samples = samples_by_vel_rr[group_key]

                    # Calculate velocity range for this group
                    lovel, hivel = self._calculate_velocity_range(vel_layer, group_samples)

                    # Write group header
                    f.write("<group>\n")
                    if self.velocity_layers > 1:
                        f.write(f"lovel={lovel}\n")
                        f.write(f"hivel={hivel}\n")

                    # Round-robin
                    if self.roundrobin_layers > 1:
                        f.write(f"seq_length={self.roundrobin_layers}\n")
                        f.write(f"seq_position={rr_layer + 1}\n")

                    f.write("\n")

                    # Write regions for this group
                    self._write_sfz_regions(f, group_samples, all_notes)

            logging.info(f"SFZ file generated: {output_path}")
            return True
        except Exception as e:
            logging.error(f"Failed to generate SFZ: {e}")
            return False

    def _calculate_velocity_range(self, vel_layer: int,
                                  group_samples: List[Dict]) -> tuple[int, int]:
        """Calculate lovel/hivel for a velocity layer."""
        if self.velocity_layers > 1:
            if self.velocity_layers_split is not None:
                # Use custom split points
                if vel_layer == 0:
                    lovel = self.velocity_minimum
                else:
                    lovel = self.velocity_layers_split[vel_layer - 1] + 1

                if vel_layer < len(self.velocity_layers_split):
                    hivel = self.velocity_layers_split[vel_layer]
                else:
                    hivel = 127
            else:
                # Calculate evenly-spaced velocity ranges for layers
                # This creates non-overlapping ranges regardless of sampled velocity
                range_size = 127 // self.velocity_layers
                
                lovel = vel_layer * range_size + 1
                if vel_layer == self.velocity_layers - 1:
                    # Last layer goes to 127
                    hivel = 127
                else:
                    hivel = (vel_layer + 1) * range_size
        else:
            lovel = 1
            hivel = 127

        return lovel, hivel

    def _write_sfz_regions(self, f, group_samples: List[Dict], all_notes: List[int]):
        """Write SFZ regions for a group."""
        # Group samples by note
        group_by_note = {}
        for sample in group_samples:
            note = sample['note']
            if note not in group_by_note:
                group_by_note[note] = []
            group_by_note[note].append(sample)

        for i, note in enumerate(all_notes):
            if note not in group_by_note:
                continue

            # Calculate key range for this sample
            note_lokey, note_hikey = self._calculate_key_range(i, note, all_notes)

            for sample in group_by_note[note]:
                f.write("<region>\n")
                # Reference sample with samples subfolder
                sample_name = Path(sample['file']).name
                f.write(f"sample=samples/{sample_name}\n")
                f.write(f"pitch_keycenter={note}\n")
                f.write(f"lokey={note_lokey}\n")
                f.write(f"hikey={note_hikey}\n")
                f.write("\n")

    def _calculate_key_range(self, index: int, note: int,
                            all_notes: List[int]) -> tuple[int, int]:
        """Calculate lokey/hikey for a note based on its position."""
        if len(all_notes) == 1:
            return self.lowest_note, self.highest_note

        # Lowest sample extends down to configured lowest_note
        if index == 0:
            note_lokey = self.lowest_note
            note_hikey = (note + all_notes[index + 1]) // 2
        # Highest sample extends up to configured highest_note
        elif index == len(all_notes) - 1:
            note_lokey = (all_notes[index - 1] + note) // 2 + 1
            note_hikey = self.highest_note
        # Middle samples split the range
        else:
            note_lokey = (all_notes[index - 1] + note) // 2 + 1
            note_hikey = (note + all_notes[index + 1]) // 2

        return note_lokey, note_hikey

    def check_output_folder(self) -> bool:
        """
        Check if output folder exists and prompt user for action.

        Returns:
            True to continue, False to abort
        """
        if self.multisample_folder.exists():
            # In test mode, just warn
            if self.test_mode:
                logging.warning(f"Multisample folder already exists: {self.multisample_folder}")
                logging.info("Test mode: Will overwrite existing files")
                return True

            print(f"\nWARNING: Multisample folder already exists: {self.multisample_folder}")
            print("This folder may contain samples from a previous session.")
            print("\nOptions:")
            print("  1) Delete folder and continue")
            print("  2) Use different name")
            print("  3) Cancel")

            while True:
                choice = input("\nSelect option (1-3): ").strip()

                if choice == '1':
                    # Delete folder
                    import shutil
                    try:
                        shutil.rmtree(self.multisample_folder)
                        logging.info(f"Deleted existing folder: {self.multisample_folder}")
                        return True
                    except Exception as e:
                        logging.error(f"Failed to delete folder: {e}")
                        print(f"Error deleting folder: {e}")
                        return False

                elif choice == '2':
                    # Ask for new name
                    new_name = input("Enter new multisample name: ").strip()
                    if new_name:
                        self.multisample_name = new_name
                        self.multisample_folder = self.base_output_folder / self.multisample_name
                        self.output_folder = self.multisample_folder / 'samples'
                        logging.info(f"Changed multisample name to: {self.multisample_name}")
                        # Check again recursively
                        return self.check_output_folder()

                    print("Invalid name. Please try again.")

                elif choice == '3':
                    print("Cancelled by user")
                    return False

                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")

        return True
