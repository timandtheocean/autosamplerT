"""
MIDI Note Engine for AutosamplerT.

Handles MIDI note on/off operations during sampling.
"""

import logging
import time
from typing import Optional

try:
    import mido
except ImportError:
    mido = None


class MIDINoteEngine:
    """
    Handles MIDI note on/off sequences for sampling.

    Works in conjunction with MIDIController from sampler_midicontrol.py
    for sending note messages.
    """

    def __init__(self, midi_output_port=None, test_mode: bool = False):
        """
        Initialize MIDI note engine.

        Args:
            midi_output_port: MIDI output port from mido
            test_mode: If True, log actions without sending MIDI
        """
        self.midi_output_port = midi_output_port
        self.test_mode = test_mode

    def send_midi_note(self, note: int, velocity: int, channel: int = 0,
                       duration: float = None) -> None:
        """
        Send a MIDI note on/off sequence.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            channel: MIDI channel (0-15)
            duration: Note duration in seconds (if None, only sends note_on)
        """
        if not self.midi_output_port:
            logging.warning("No MIDI output port - skipping MIDI note")
            return

        if self.test_mode:
            logging.info(f"[TEST MODE] Would send: Note={note}, Vel={velocity}, Ch={channel}")
            return

        try:
            # Send note on
            note_on = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
            self.midi_output_port.send(note_on)
            logging.debug(f"MIDI Note ON: note={note}, velocity={velocity}, channel={channel}")

            # If duration specified, wait and send note off
            if duration is not None:
                time.sleep(duration)
                note_off = mido.Message('note_off', note=note, velocity=0, channel=channel)
                self.midi_output_port.send(note_off)
                logging.debug(f"MIDI Note OFF: note={note}")

        except Exception as e:
            logging.error(f"Failed to send MIDI note: {e}")
