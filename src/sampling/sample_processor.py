"""
Sample Processor for AutosamplerT.

Handles core sampling logic including note recording and velocity calculations.
"""

import logging
import time
import threading
from typing import Optional

import numpy as np

try:
    import sounddevice as sd
    import mido
except ImportError:
    sd = None
    mido = None


class SampleProcessor:
    """
    Processes individual sample recordings with MIDI and audio coordination.

    Handles the complete sampling workflow for a single note:
    - MIDI note on/off timing
    - Audio recording coordination
    - ASIO vs non-ASIO device handling
    - Velocity layer calculations
    """

    def __init__(self, midi_note_engine, audio_engine, hold_time: float,
                 release_time: float, pause_time: float, input_device=None,
                 test_mode: bool = False, velocity_minimum: int = 1,
                 velocity_layers_split=None):
        """
        Initialize sample processor.

        Args:
            midi_note_engine: MIDINoteEngine instance for MIDI operations
            audio_engine: AudioEngine instance for audio recording
            hold_time: Duration to hold MIDI note (seconds)
            release_time: Duration to record after note off (seconds)
            pause_time: Pause between samples (seconds)
            input_device: Audio input device index
            test_mode: If True, skip actual recording
            velocity_minimum: Minimum velocity value for layer 0
            velocity_layers_split: Custom velocity split points or None
        """
        self.midi_note_engine = midi_note_engine
        self.audio_engine = audio_engine
        self.hold_time = hold_time
        self.release_time = release_time
        self.pause_time = pause_time
        self.input_device = input_device
        self.test_mode = test_mode
        self.velocity_minimum = velocity_minimum
        self.velocity_layers_split = velocity_layers_split

    def calculate_velocity_value(self, layer: int, total_layers: int) -> int:
        """
        Calculate MIDI velocity for a given velocity layer.

        Args:
            layer: Current layer index (0-based)
            total_layers: Total number of velocity layers

        Returns:
            MIDI velocity value (1-127)
        """
        # Use custom split points if provided
        if self.velocity_layers_split is not None:
            # Sample at the split point value
            # Layer 0 -> first split, Layer 1 -> second split, etc.
            # Last layer -> 127
            if layer < len(self.velocity_layers_split):
                return self.velocity_layers_split[layer]
            else:
                return 127

        # Default behavior: logarithmic distribution (more density at higher velocities)
        if total_layers == 1:
            return 127  # Full velocity for single layer

        min_vel = self.velocity_minimum
        max_vel = 127

        # Logarithmic curve: velocity feels more "musical"
        # Uses exponential mapping: velocity grows faster toward the end
        import math

        # Normalize layer position (0.0 to 1.0)
        position = layer / (total_layers - 1)

        # Apply exponential curve (base 2 works well for velocity)
        # This gives more samples at higher velocities
        curve_factor = 2.0
        curved_position = (math.pow(curve_factor, position) - 1) / (curve_factor - 1)

        # Map to velocity range
        velocity = int(min_vel + (max_vel - min_vel) * curved_position)
        return max(1, min(127, velocity))

    def sample_note(self, note: int, velocity: int, channel: int = 0,
                    rr_index: int = 0, midi_note: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Sample a single note: send MIDI, record audio, process.

        Args:
            note: SFZ note number (used for filenames, metadata, and SFZ mapping)
            velocity: MIDI velocity
            channel: MIDI channel
            rr_index: Round-robin layer index
            midi_note: MIDI note to send (if different from note due to MIDI range mapping)

        Returns:
            Processed audio array or None
        """
        # Use midi_note if provided, otherwise use note (1:1 mapping)
        if midi_note is None:
            midi_note = note

        # Log with simplified format as requested
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

        # Calculate note info for display
        sfz_octave = (note // 12) - 1
        sfz_note_name = note_names[note % 12]
        midi_octave = (midi_note // 12) - 1
        midi_note_name = note_names[midi_note % 12]

        # Log with MIDI mapping info if different
        if midi_note != note:
            logging.info(f"Sampling: MIDI={midi_note_name}{midi_octave} ({midi_note}) "
                        f"-> SFZ={sfz_note_name}{sfz_octave} ({note}), "
                        f"Vel={velocity}, RR={rr_index}, "
                        f"Hold={self.hold_time}s, Release={self.release_time}s, "
                        f"Pause={self.pause_time}s")
        else:
            logging.info(f"Sampling: Note={sfz_note_name}{sfz_octave} ({note}), "
                        f"Vel={velocity}, RR={rr_index}, "
                        f"Hold={self.hold_time}s, Release={self.release_time}s, "
                        f"Pause={self.pause_time}s")

        # Calculate total recording duration
        total_duration = self.hold_time + self.release_time

        # Send MIDI note on (using mapped MIDI note)
        self.midi_note_engine.send_midi_note(midi_note, velocity, channel)

        # Check if we're using ASIO (ASIO doesn't work from threads)
        device_info = sd.query_devices(self.input_device) if self.input_device is not None else None
        is_asio = False
        if device_info:
            host_apis = sd.query_hostapis()
            host_api_name = host_apis[device_info['hostapi']]['name']
            is_asio = 'ASIO' in host_api_name

        # Start recording
        recording_complete = threading.Event()
        audio_result = [None]

        def record_thread() -> None:
            audio_result[0] = self.audio_engine.record(total_duration)
            recording_complete.set()

        if not self.test_mode:
            if is_asio:
                # ASIO must run in main thread - record directly without threading
                logging.debug("ASIO detected - recording in main thread")

                # Record the full duration in main thread (ASIO requirement)
                audio = self.audio_engine.record(total_duration)

                # Send note-off after recording completes (note was already released)
                # This is OK because we record the full duration anyway
                note_off = mido.Message('note_off', note=midi_note, velocity=0, channel=channel)
                if self.midi_note_engine.midi_output_port:
                    self.midi_note_engine.midi_output_port.send(note_off)
            else:
                # Non-ASIO: use threading as before
                # Start recording thread
                record_thread_obj = threading.Thread(target=record_thread)
                record_thread_obj.start()

                # Wait for hold time, then send note off
                time.sleep(self.hold_time)
                note_off = mido.Message('note_off', note=midi_note, velocity=0, channel=channel)
                if self.midi_note_engine.midi_output_port:
                    self.midi_note_engine.midi_output_port.send(note_off)

                # Wait for recording to complete
                recording_complete.wait()
                audio = audio_result[0]
        else:
            # Test mode: just record without MIDI timing
            audio = self.audio_engine.record(total_duration)

        if audio is None:
            logging.error("Audio recording returned None")
            return None

        # Note: Silence trimming removed from recording - now only in postprocessing
        # This ensures we capture the full recording duration and any clicks at the end
        # are visible for debugging

        # Normalize individual sample (optional)
        audio_processed = self.audio_engine.normalize(audio)

        return audio_processed
