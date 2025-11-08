"""
MIDI Control functions for AutosamplerT
Handles sending MIDI messages: CC, Program Change, SysEx, and per-layer MIDI control
"""

import mido
import logging
import time
from typing import Dict, List, Optional


class MIDIController:
    """Handles all MIDI control operations for sampling."""
    
    def __init__(self, midi_output_port: Optional[mido.ports.BaseOutput], test_mode: bool = False):
        """
        Initialize MIDI Controller.
        
        Args:
            midi_output_port: MIDI output port for sending messages
            test_mode: If True, only log messages without sending
        """
        self.midi_output_port = midi_output_port
        self.test_mode = test_mode
    
    def send_midi_cc(self, cc_number: int, value: int, channel: int = 0) -> None:
        """
        Send a MIDI Control Change message.
        
        Args:
            cc_number: CC number (0-127)
            value: CC value (0-127)
            channel: MIDI channel (0-15)
        """
        if not self.midi_output_port or self.test_mode:
            logging.info(f"[TEST MODE] MIDI CC: cc={cc_number}, value={value}, channel={channel}")
            return
        
        try:
            cc_msg = mido.Message('control_change', control=cc_number, value=value, channel=channel)
            self.midi_output_port.send(cc_msg)
            logging.debug(f"MIDI CC: cc={cc_number}, value={value}, channel={channel}")
        except Exception as e:
            logging.error(f"Failed to send MIDI CC: {e}")
    
    def send_program_change(self, program: int, channel: int = 0) -> None:
        """
        Send a MIDI Program Change message.
        
        Args:
            program: Program number (0-127)
            channel: MIDI channel (0-15)
        """
        if not self.midi_output_port or self.test_mode:
            logging.info(f"[TEST MODE] Program Change: program={program}, channel={channel}")
            return
        
        try:
            pc_msg = mido.Message('program_change', program=program, channel=channel)
            self.midi_output_port.send(pc_msg)
            logging.info(f"MIDI Program Change: program={program}, channel={channel}")
        except Exception as e:
            logging.error(f"Failed to send Program Change: {e}")
    
    def send_sysex(self, sysex_data: str, channel: int = 0) -> None:
        """
        Send a MIDI SysEx (System Exclusive) message.
        
        Args:
            sysex_data: SysEx message as hex string (e.g., "F0 43 10 7F 1C 00 00 00 01 F7")
            channel: MIDI channel (0-15) - note: most SysEx ignores channel
        """
        if not self.midi_output_port or self.test_mode:
            logging.info(f"[TEST MODE] SysEx: {sysex_data}, channel={channel}")
            return
        
        try:
            # Parse hex string to bytes
            sysex_bytes = bytes.fromhex(sysex_data.replace(" ", ""))
            
            # Validate SysEx format (must start with F0 and end with F7)
            if sysex_bytes[0] != 0xF0:
                logging.error(f"Invalid SysEx: must start with F0, got {hex(sysex_bytes[0])}")
                return
            if sysex_bytes[-1] != 0xF7:
                logging.error(f"Invalid SysEx: must end with F7, got {hex(sysex_bytes[-1])}")
                return
            
            # Extract data bytes (without F0 and F7)
            data_bytes = list(sysex_bytes[1:-1])
            
            # Create and send SysEx message
            sysex_msg = mido.Message('sysex', data=data_bytes)
            self.midi_output_port.send(sysex_msg)
            logging.info(f"MIDI SysEx sent: {sysex_data}")
        except ValueError as e:
            logging.error(f"Invalid SysEx hex string: {e}")
        except Exception as e:
            logging.error(f"Failed to send SysEx: {e}")
    
    def send_cc_messages(self, cc_dict: Dict[int, int], channel: int = 0) -> None:
        """
        Send multiple CC messages from a dictionary.
        
        Args:
            cc_dict: Dictionary of {cc_number: value}
            channel: MIDI channel (0-15)
        """
        for cc_num, cc_val in cc_dict.items():
            self.send_midi_cc(int(cc_num), int(cc_val), channel)
            time.sleep(0.01)  # Small delay between messages
    
    def send_sysex_messages(self, sysex_list: List[str], channel: int = 0) -> None:
        """
        Send multiple SysEx messages from a list.
        
        Args:
            sysex_list: List of SysEx hex strings
            channel: MIDI channel (0-15)
        """
        for sysex_data in sysex_list:
            if sysex_data.strip():  # Skip empty strings
                self.send_sysex(sysex_data, channel)
                time.sleep(0.05)  # Delay between SysEx messages (devices need time to process)
    
    def send_midi_setup(self, config: Dict, channel: int = 0) -> None:
        """
        Send initial MIDI setup messages (CC, Program Change, SysEx).
        
        Args:
            config: Configuration dictionary with optional keys:
                   'cc_messages': Dict of CC messages
                   'program_change': Program number
                   'sysex_messages': List of SysEx strings
            channel: MIDI channel (0-15)
        """
        # Send SysEx first (may configure synth parameters)
        sysex_messages = config.get('sysex_messages', [])
        if sysex_messages:
            self.send_sysex_messages(sysex_messages, channel)
        
        # Send CC messages
        cc_messages = config.get('cc_messages', {})
        if cc_messages:
            self.send_cc_messages(cc_messages, channel)
        
        # Send Program Change
        program = config.get('program_change')
        if program is not None:
            self.send_program_change(program, channel)
            time.sleep(0.1)  # Allow program change to settle
    
    def apply_velocity_layer_midi(self, velocity_layer: int, velocity_midi_config: List[Dict], 
                                   default_channel: int = 0) -> None:
        """
        Apply MIDI settings for a specific velocity layer.
        
        Args:
            velocity_layer: Current velocity layer index (0, 1, 2, etc.)
            velocity_midi_config: List of velocity MIDI control configurations
            default_channel: Default MIDI channel if not specified
        """
        if not velocity_midi_config:
            return
        
        # Find configuration for this velocity layer
        layer_config = None
        for config in velocity_midi_config:
            if config.get('velocity_layer') == velocity_layer:
                layer_config = config
                break
        
        if not layer_config:
            logging.debug(f"No MIDI config for velocity layer {velocity_layer}")
            return
        
        channel = layer_config.get('midi_channel', default_channel)
        
        logging.info(f"Applying MIDI settings for velocity layer {velocity_layer}")
        
        # Send SysEx
        sysex_messages = layer_config.get('sysex_messages', [])
        if sysex_messages:
            self.send_sysex_messages(sysex_messages, channel)
        
        # Send CC messages
        cc_messages = layer_config.get('cc_messages', {})
        if cc_messages:
            self.send_cc_messages(cc_messages, channel)
        
        # Send Program Change
        program = layer_config.get('program_change')
        if program is not None:
            self.send_program_change(program, channel)
            time.sleep(0.1)  # Allow program change to settle
    
    def apply_roundrobin_layer_midi(self, roundrobin_layer: int, roundrobin_midi_config: List[Dict],
                                     default_channel: int = 0) -> None:
        """
        Apply MIDI settings for a specific round-robin layer.
        
        Args:
            roundrobin_layer: Current round-robin layer index (0, 1, 2, etc.)
            roundrobin_midi_config: List of round-robin MIDI control configurations
            default_channel: Default MIDI channel if not specified
        """
        if not roundrobin_midi_config:
            return
        
        # Find configuration for this round-robin layer
        layer_config = None
        for config in roundrobin_midi_config:
            if config.get('roundrobin_layer') == roundrobin_layer:
                layer_config = config
                break
        
        if not layer_config:
            logging.debug(f"No MIDI config for round-robin layer {roundrobin_layer}")
            return
        
        channel = layer_config.get('midi_channel', default_channel)
        
        logging.info(f"Applying MIDI settings for round-robin layer {roundrobin_layer}")
        
        # Send SysEx
        sysex_messages = layer_config.get('sysex_messages', [])
        if sysex_messages:
            self.send_sysex_messages(sysex_messages, channel)
        
        # Send CC messages
        cc_messages = layer_config.get('cc_messages', {})
        if cc_messages:
            self.send_cc_messages(cc_messages, channel)
        
        # Send Program Change
        program = layer_config.get('program_change')
        if program is not None:
            self.send_program_change(program, channel)
            time.sleep(0.1)  # Allow program change to settle
    
    def get_layer_channel(self, velocity_layer: int, roundrobin_layer: int,
                          velocity_midi_config: List[Dict], roundrobin_midi_config: List[Dict],
                          default_channel: int = 0) -> int:
        """
        Get the MIDI channel for a specific velocity/round-robin layer combination.
        Priority: round-robin config > velocity config > default channel
        
        Args:
            velocity_layer: Current velocity layer index
            roundrobin_layer: Current round-robin layer index
            velocity_midi_config: List of velocity MIDI control configurations
            roundrobin_midi_config: List of round-robin MIDI control configurations
            default_channel: Default MIDI channel
        
        Returns:
            MIDI channel to use for this layer
        """
        # Check round-robin config first (higher priority)
        if roundrobin_midi_config:
            for config in roundrobin_midi_config:
                if config.get('roundrobin_layer') == roundrobin_layer:
                    return config.get('midi_channel', default_channel)
        
        # Check velocity config
        if velocity_midi_config:
            for config in velocity_midi_config:
                if config.get('velocity_layer') == velocity_layer:
                    return config.get('midi_channel', default_channel)
        
        return default_channel


def parse_cc_messages(cc_input) -> Dict[int, int]:
    """
    Parse CC messages from various input formats.
    
    Args:
        cc_input: Can be:
                 - Dict: {7: 127, 10: 64}
                 - JSON string: '{"7":127,"10":64}'
                 - None or empty
    
    Returns:
        Dictionary of {cc_number: value}
    """
    if not cc_input:
        return {}
    
    if isinstance(cc_input, dict):
        return {int(k): int(v) for k, v in cc_input.items()}
    
    if isinstance(cc_input, str):
        import json
        try:
            parsed = json.loads(cc_input)
            return {int(k): int(v) for k, v in parsed.items()}
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"Failed to parse CC messages: {e}")
            return {}
    
    return {}


def parse_sysex_messages(sysex_input) -> List[str]:
    """
    Parse SysEx messages from various input formats.
    
    Args:
        sysex_input: Can be:
                    - List: ["F0 43 10 7F F7", "F0 44 11 F7"]
                    - Single string: "F0 43 10 7F F7"
                    - None or empty
    
    Returns:
        List of SysEx hex strings
    """
    if not sysex_input:
        return []
    
    if isinstance(sysex_input, list):
        return [str(s) for s in sysex_input if s]
    
    if isinstance(sysex_input, str):
        return [sysex_input]
    
    return []
