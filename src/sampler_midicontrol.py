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
        self.sysex_header_state = None  # Track last SysEx header for reuse across layers
    
    def send_midi_cc(self, cc_number: int, value: int, channel: int = 0) -> None:
        """
        Send a 7-bit MIDI Control Change message.
        
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
            logging.info(f"MIDI CC sent: cc={cc_number}, value={value}, channel={channel}")
        except Exception as e:
            logging.error(f"Failed to send MIDI CC: {e}")
    
    def send_midi_cc14(self, cc_number: int, value: int, channel: int = 0) -> None:
        """
        Send a 14-bit MIDI Control Change message.
        
        14-bit CC messages use two consecutive controllers:
        - MSB (Most Significant Byte): CC number (0-127)
        - LSB (Least Significant Byte): CC number + 32 (32-159, wraps for CC96+)
        
        Args:
            cc_number: CC number (0-127)
            value: CC value (0-16383, 14-bit)
            channel: MIDI channel (0-15)
        """
        if not self.midi_output_port or self.test_mode:
            logging.info(f"[TEST MODE] MIDI CC14: cc={cc_number}, value={value} (14-bit), channel={channel}")
            return
        
        try:
            # Split 14-bit value into MSB (bits 7-13) and LSB (bits 0-6)
            msb = (value >> 7) & 0x7F  # Upper 7 bits
            lsb = value & 0x7F          # Lower 7 bits
            
            # Send MSB first
            msb_msg = mido.Message('control_change', control=cc_number, value=msb, channel=channel)
            self.midi_output_port.send(msb_msg)
            
            # Send LSB second (CC number + 32)
            lsb_msg = mido.Message('control_change', control=cc_number + 32, value=lsb, channel=channel)
            self.midi_output_port.send(lsb_msg)
            
            logging.info(f"MIDI CC14 sent: cc={cc_number} (MSB={msb}, LSB={lsb}), value={value} (14-bit), channel={channel}")
        except Exception as e:
            logging.error(f"Failed to send 14-bit MIDI CC: {e}")
    
    def send_nrpn(self, parameter: int, value: int, channel: int = 0) -> None:
        """
        Send an NRPN (Non-Registered Parameter Number) message.
        
        NRPN messages use 4 CC messages in sequence:
        1. CC 99 (NRPN MSB) - Parameter number high byte
        2. CC 98 (NRPN LSB) - Parameter number low byte
        3. CC 6 (Data Entry MSB) - Value high byte
        4. CC 38 (Data Entry LSB) - Value low byte
        
        Args:
            parameter: NRPN parameter number (0-16383)
            value: NRPN value (0-16383)
            channel: MIDI channel (0-15)
        """
        if not self.midi_output_port or self.test_mode:
            logging.info(f"[TEST MODE] MIDI NRPN: param={parameter}, value={value}, channel={channel}")
            return
        
        try:
            # Split parameter into MSB/LSB
            param_msb = (parameter >> 7) & 0x7F  # Upper 7 bits
            param_lsb = parameter & 0x7F          # Lower 7 bits
            
            # Split value into MSB/LSB
            value_msb = (value >> 7) & 0x7F  # Upper 7 bits
            value_lsb = value & 0x7F          # Lower 7 bits
            
            # Send NRPN parameter selection (CC99 + CC98)
            nrpn_msb_msg = mido.Message('control_change', control=99, value=param_msb, channel=channel)
            self.midi_output_port.send(nrpn_msb_msg)
            
            nrpn_lsb_msg = mido.Message('control_change', control=98, value=param_lsb, channel=channel)
            self.midi_output_port.send(nrpn_lsb_msg)
            
            # Send data entry (CC6 + CC38)
            data_msb_msg = mido.Message('control_change', control=6, value=value_msb, channel=channel)
            self.midi_output_port.send(data_msb_msg)
            
            data_lsb_msg = mido.Message('control_change', control=38, value=value_lsb, channel=channel)
            self.midi_output_port.send(data_lsb_msg)
            
            logging.info(f"MIDI NRPN sent: param={parameter} (MSB={param_msb}, LSB={param_lsb}), "
                        f"value={value} (MSB={value_msb}, LSB={value_lsb}), channel={channel}")
        except Exception as e:
            logging.error(f"Failed to send NRPN: {e}")
    
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
        Send multiple 7-bit CC messages from a dictionary.
        
        Args:
            cc_dict: Dictionary of {cc_number: value} where values are 0-127
            channel: MIDI channel (0-15)
        """
        for cc_num, cc_val in cc_dict.items():
            self.send_midi_cc(int(cc_num), int(cc_val), channel)
            time.sleep(0.01)  # Small delay between messages
    
    def send_cc14_messages(self, cc14_dict: Dict[int, int], channel: int = 0) -> None:
        """
        Send multiple 14-bit CC messages from a dictionary.
        
        Args:
            cc14_dict: Dictionary of {cc_number: value} where values are 0-16383
            channel: MIDI channel (0-15)
        """
        for cc_num, cc_val in cc14_dict.items():
            self.send_midi_cc14(int(cc_num), int(cc_val), channel)
            time.sleep(0.02)  # Slightly longer delay for 14-bit (sends 2 messages)
    
    def send_nrpn_messages(self, nrpn_dict: Dict[int, int], channel: int = 0) -> None:
        """
        Send multiple NRPN messages from a dictionary.
        
        Args:
            nrpn_dict: Dictionary of {parameter: value} where both are 0-16383
            channel: MIDI channel (0-15)
        """
        for param, value in nrpn_dict.items():
            self.send_nrpn(int(param), int(value), channel)
            time.sleep(0.05)  # Longer delay for NRPN (sends 4 messages)
    
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
        Send initial MIDI setup messages (CC, 14-bit CC, NRPN, Program Change, SysEx).
        
        Args:
            config: Configuration dictionary with optional keys:
                   'cc_messages': Dict of 7-bit CC messages
                   'cc14_messages': Dict of 14-bit CC messages
                   'nrpn_messages': Dict of NRPN messages
                   'program_change': Program number
                   'sysex_messages': List of SysEx strings
            channel: MIDI channel (0-15)
        """
        # Send SysEx first (may configure synth parameters)
        sysex_messages = config.get('sysex_messages', [])
        if sysex_messages:
            self.send_sysex_messages(sysex_messages, channel)
        
        # Send 7-bit CC messages
        cc_messages = config.get('cc_messages', {})
        if cc_messages:
            self.send_cc_messages(cc_messages, channel)
        
        # Send 14-bit CC messages
        cc14_messages = config.get('cc14_messages', {})
        if cc14_messages:
            self.send_cc14_messages(cc14_messages, channel)
        
        # Send NRPN messages
        nrpn_messages = config.get('nrpn_messages', {})
        if nrpn_messages:
            self.send_nrpn_messages(nrpn_messages, channel)
        
        # Send Program Change
        program = config.get('program_change')
        if program is not None:
            self.send_program_change(program, channel)
            time.sleep(0.1)  # Allow program change to settle
    
    def apply_velocity_layer_midi(self, velocity_layer: int, velocity_midi_config: List[Dict], 
                                   default_channel: int = 0, message_delay: float = 0.0) -> None:
        """
        Apply MIDI settings for a specific velocity layer.
        
        Args:
            velocity_layer: Current velocity layer index (0, 1, 2, etc.)
            velocity_midi_config: List of velocity MIDI control configurations
            default_channel: Default MIDI channel if not specified
            message_delay: Delay in seconds after sending MIDI messages (before note-on)
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
            parsed_sysex, self.sysex_header_state = parse_sysex_messages(sysex_messages, self.sysex_header_state)
            self.send_sysex_messages(parsed_sysex, channel)
        
        # Send CC messages
        cc_messages = layer_config.get('cc_messages', {})
        if cc_messages:
            self.send_cc_messages(cc_messages, channel)
        
        # Send Program Change
        program = layer_config.get('program_change')
        if program is not None:
            self.send_program_change(program, channel)
            time.sleep(0.1)  # Allow program change to settle
        
        # Apply message delay if configured
        if message_delay > 0:
            logging.debug(f"Waiting {message_delay}s after velocity layer MIDI messages")
            time.sleep(message_delay)
    
    def apply_roundrobin_layer_midi(self, roundrobin_layer: int, roundrobin_midi_config: List[Dict],
                                     default_channel: int = 0, message_delay: float = 0.0) -> None:
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
            parsed_sysex, self.sysex_header_state = parse_sysex_messages(sysex_messages, self.sysex_header_state)
            self.send_sysex_messages(parsed_sysex, channel)
        
        # Send CC messages
        cc_messages = layer_config.get('cc_messages', {})
        if cc_messages:
            self.send_cc_messages(cc_messages, channel)
        
        # Send 14-bit CC messages
        cc14_messages = layer_config.get('cc14_messages', {})
        if cc14_messages:
            self.send_cc14_messages(cc14_messages, channel)
        
        # Send NRPN messages
        nrpn_messages = layer_config.get('nrpn_messages', {})
        if nrpn_messages:
            self.send_nrpn_messages(nrpn_messages, channel)
        
        # Send Program Change
        program = layer_config.get('program_change')
        if program is not None:
            self.send_program_change(program, channel)
            time.sleep(0.1)  # Allow program change to settle
        
        # Apply message delay if configured
        if message_delay > 0:
            logging.debug(f"Waiting {message_delay}s after round-robin layer MIDI messages")
            time.sleep(message_delay)
    
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
    Parse 7-bit CC messages from various input formats.
    
    Args:
        cc_input: Can be:
                 - Dict: {7: 127, 10: 64}
                 - String: "7,127;10,64" (controller,value pairs separated by semicolon)
                 - None or empty
    
    Returns:
        Dictionary of {cc_number: value} where values are 0-127
    """
    if not cc_input:
        return {}
    
    if isinstance(cc_input, dict):
        return {int(k): int(v) for k, v in cc_input.items()}
    
    if isinstance(cc_input, str):
        try:
            # Parse format: "7,127;10,64" -> {7: 127, 10: 64}
            result = {}
            pairs = cc_input.split(';')
            for pair in pairs:
                pair = pair.strip()
                if not pair:
                    continue
                parts = pair.split(',')
                if len(parts) != 2:
                    logging.error(f"Invalid CC message format: '{pair}' (expected 'controller,value')")
                    continue
                cc_num = int(parts[0].strip())
                cc_val = int(parts[1].strip())
                
                # Validate 7-bit ranges
                if not (0 <= cc_num <= 127):
                    logging.error(f"CC controller number {cc_num} out of range (0-127)")
                    continue
                if not (0 <= cc_val <= 127):
                    logging.error(f"CC value {cc_val} out of range (0-127)")
                    continue
                    
                result[cc_num] = cc_val
            return result
        except (ValueError, AttributeError) as e:
            logging.error(f"Failed to parse CC messages: {e}")
            return {}
    
    return {}


def parse_cc14_messages(cc14_input) -> Dict[int, int]:
    """
    Parse 14-bit CC messages from various input formats.
    
    Args:
        cc14_input: Can be:
                   - Dict: {1: 8192, 11: 16383}
                   - String: "1,8192;11,16383" (controller,value pairs separated by semicolon)
                   - None or empty
    
    Returns:
        Dictionary of {cc_number: value} where values are 0-16383 (14-bit)
        
    Note:
        14-bit CC uses two consecutive controllers:
        - MSB (Most Significant Byte): CC number (e.g., CC1)
        - LSB (Least Significant Byte): CC number + 32 (e.g., CC33)
        The function will automatically split the 14-bit value into MSB/LSB.
    """
    if not cc14_input:
        return {}
    
    if isinstance(cc14_input, dict):
        return {int(k): int(v) for k, v in cc14_input.items()}
    
    if isinstance(cc14_input, str):
        try:
            # Parse format: "1,8192;11,16383" -> {1: 8192, 11: 16383}
            result = {}
            pairs = cc14_input.split(';')
            for pair in pairs:
                pair = pair.strip()
                if not pair:
                    continue
                parts = pair.split(',')
                if len(parts) != 2:
                    logging.error(f"Invalid 14-bit CC message format: '{pair}' (expected 'controller,value')")
                    continue
                cc_num = int(parts[0].strip())
                cc_val = int(parts[1].strip())
                
                # Validate 14-bit ranges
                if not (0 <= cc_num <= 127):
                    logging.error(f"14-bit CC controller number {cc_num} out of range (0-127)")
                    continue
                if not (0 <= cc_val <= 16383):
                    logging.error(f"14-bit CC value {cc_val} out of range (0-16383)")
                    continue
                    
                result[cc_num] = cc_val
            return result
        except (ValueError, AttributeError) as e:
            logging.error(f"Failed to parse 14-bit CC messages: {e}")
            return {}
    
    return {}


def parse_sysex_messages(sysex_input, header_state: Optional[str] = None) -> tuple[List[str], Optional[str]]:
    """
    Parse SysEx messages from various input formats.
    
    Args:
        sysex_input: Can be:
                    - List of strings: ["F0 43 10 7F F7", "10 08 01 06 13 0A"]
                    - List of dicts: [{"header": "10 08 01 06", "controller": "13", "value": 10}, {"raw": "10 08 01 06 13 0A"}]
                    - Single string: "F0 43 10 7F F7"
                    - None or empty
        header_state: Previous SysEx header for reuse across layers
    
    Returns:
        Tuple of (List of SysEx hex strings, updated header state)
    """
    if not sysex_input:
        return [], header_state
    
    result = []
    last_header = header_state  # Start with provided header state
    
    # Handle list input
    if isinstance(sysex_input, list):
        for item in sysex_input:
            if not item:
                continue
            
            # String format (raw hex)
            if isinstance(item, str):
                msg = _ensure_sysex_wrapper(item)
                if msg:
                    result.append(msg)
            
            # Dict format (structured)
            elif isinstance(item, dict):
                # Raw format
                if 'raw' in item:
                    raw_data = str(item['raw']).strip()
                    msg = _ensure_sysex_wrapper(raw_data)
                    if msg:
                        result.append(msg)
                
                # Structured format
                elif 'controller' in item and 'value' in item:
                    # Get or reuse header
                    if 'header' in item:
                        last_header = str(item['header']).strip()
                    
                    if not last_header:
                        logging.error("SysEx structured format requires 'header' on first message or previous message")
                        continue
                    
                    # Parse controller and value
                    try:
                        controller = _parse_hex_value(item['controller'])
                        value = int(item['value'])
                        
                        # Validate ranges
                        if not (0 <= controller <= 127):
                            logging.error(f"SysEx controller {controller} out of range (0-127)")
                            continue
                        if not (0 <= value <= 127):
                            logging.error(f"SysEx value {value} out of range (0-127)")
                            continue
                        
                        # Build message: header + controller + value
                        msg_data = f"{last_header} {controller:02X} {value:02X}"
                        msg = _ensure_sysex_wrapper(msg_data)
                        if msg:
                            result.append(msg)
                    
                    except (ValueError, TypeError) as e:
                        logging.error(f"Failed to parse SysEx structured format: {e}")
                        continue
                else:
                    logging.error(f"Invalid SysEx dict format: {item}")
            else:
                logging.error(f"Invalid SysEx item type: {type(item)}")
    
    # Handle single string input
    elif isinstance(sysex_input, str):
        msg = _ensure_sysex_wrapper(sysex_input)
        if msg:
            result.append(msg)
    
    return result, last_header


def _parse_hex_value(value) -> int:
    """Parse hex value from string or int."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
        # Handle "0x13" or "13" format
        if value.startswith('0x') or value.startswith('0X'):
            return int(value, 16)
        else:
            return int(value, 16)
    raise ValueError(f"Cannot parse hex value: {value}")


def _ensure_sysex_wrapper(data: str) -> Optional[str]:
    """Ensure SysEx message has F0 and F7 wrapper."""
    data = data.strip()
    if not data:
        return None
    
    # Remove F0 and F7 if present
    parts = data.split()
    filtered = [p for p in parts if p.upper() not in ['F0', 'F7']]
    
    if not filtered:
        return None
    
    # Rebuild with F0 and F7
    return f"F0 {' '.join(filtered)} F7"
