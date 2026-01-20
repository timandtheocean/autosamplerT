"""
Patch Iterator for AutosamplerT.

Handles sampling multiple patches with program changes.
"""

import logging
import time
from typing import Dict, List, Callable
from pathlib import Path


class PatchIterator:
    """
    Manages multi-patch sampling with program changes.

    Iterates through MIDI programs, sending program changes
    and sampling each patch to separate folders.
    """

    def __init__(self, midi_controller, midi_message_delay: float = 0.1,
                 test_mode: bool = False):
        """
        Initialize patch iterator.

        Args:
            midi_controller: MIDIController instance for sending program changes
            midi_message_delay: Delay after MIDI messages
            test_mode: If True, skip user confirmation
        """
        self.midi_controller = midi_controller
        self.midi_message_delay = midi_message_delay
        self.test_mode = test_mode

    def run_patch_iteration(self, patch_config: Dict, sample_func: Callable,
                           generate_sfz_func: Callable, output_format: str,
                           base_output_folder: Path, original_name: str) -> bool:
        """
        Execute patch iteration sampling.

        Args:
            patch_config: Patch iteration configuration dict
            sample_func: Function to call for sampling (sample_range)
            generate_sfz_func: Function to generate SFZ file
            output_format: Output format ('sfz', etc.)
            base_output_folder: Base output folder path
            original_name: Original multisample name

        Returns:
            True if all patches successful, False otherwise
        """
        program_start = patch_config.get('program_start', 0)
        program_end = patch_config.get('program_end', 0)
        auto_naming = patch_config.get('auto_naming', True)
        base_name = patch_config.get('name_template', 'Patch')
        start_note = patch_config.get('start_note', 36)
        end_note = patch_config.get('end_note', 96)
        interval = patch_config.get('interval', 1)
        channel = patch_config.get('channel', 0)

        print("\n" + "="*70)
        print("PATCH ITERATION MODE")
        print("="*70)
        print(f"Sampling {program_end - program_start + 1} patches "
              f"(program {program_start}-{program_end})")
        print(f"Notes per patch: {start_note} to {end_note} (interval: {interval})")
        print(f"Auto-naming: {'Enabled' if auto_naming else 'Disabled'}")
        print("="*70)

        if not self.test_mode:
            response = input("\nContinue? [y/N]: ")
            if response.lower() != 'y':
                logging.info("Sampling cancelled by user")
                return False

        success_count = 0
        failed_patches = []

        for program in range(program_start, program_end + 1):
            print(f"\n{'='*70}")
            print(f"Sampling Program {program} "
                  f"({program - program_start + 1}/{program_end - program_start + 1})")
            print(f"{'='*70}")

            # Generate patch name
            if auto_naming:
                patch_name = f"{base_name}_{program:03d}"
            else:
                patch_name = f"{original_name}_{program:03d}"

            print(f"Patch name: {patch_name}")

            # Send program change
            if self.midi_controller:
                self.midi_controller.send_program_change(program, channel)
                time.sleep(self.midi_message_delay * 2)
                print(f"Program change sent: {program}")

            try:
                # Call the sampling function with updated name
                sample_list = sample_func(
                    start_note, end_note, interval, channel,
                    multisample_name=patch_name
                )

                logging.info(f"Program {program} complete: {len(sample_list)} samples")
                print(f"[SUCCESS] Program {program}: {len(sample_list)} samples")

                # Generate SFZ if requested
                if output_format == 'sfz':
                    generate_sfz_func(sample_list, patch_name=patch_name)

                success_count += 1

            except Exception as e:
                logging.error(f"Failed to sample program {program}: {e}", exc_info=True)
                print(f"[ERROR] Program {program} failed: {e}")
                failed_patches.append(program)

        # Summary
        print(f"\n{'='*70}")
        print("PATCH ITERATION COMPLETE")
        print(f"{'='*70}")
        print(f"Successful: {success_count}/{program_end - program_start + 1}")
        if failed_patches:
            print(f"Failed programs: {', '.join(map(str, failed_patches))}")
        print(f"{'='*70}")

        return len(failed_patches) == 0
