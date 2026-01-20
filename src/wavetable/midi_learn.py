"""
MIDI Learn functionality for wavetable creation.

Handles learning MIDI controls (CC, NRPN, CC14) and their min/max ranges.
"""

import logging
import time
from typing import Dict, Optional, Tuple, Union
import mido


class MIDILearn:
    """MIDI learn system for wavetable control parameter detection."""
    
    def __init__(self, midi_input_port: Optional[mido.ports.BaseInput] = None):
        """
        Initialize MIDI learn system.
        
        Args:
            midi_input_port: MIDI input port for learning
        """
        self.midi_input_port = midi_input_port
        self.learned_control: Optional[Dict] = None
        
    def learn_control(self, timeout: float = 30.0) -> Optional[Dict]:
        """
        Learn a MIDI control by detecting incoming messages.
        
        Args:
            timeout: Timeout in seconds for learning
            
        Returns:
            Dict with control info or None if learning failed
            
        Format:
            {
                'type': 'cc'|'cc14'|'nrpn',
                'channel': 0-15,
                'controller': int (CC number, NRPN parameter, CC14 controller),
                'name': str
            }
        """
        if not self.midi_input_port:
            logging.error("No MIDI input port available for learning")
            return None
            
        print("MIDI Learn: Move the control you want to learn...")
        print(f"Timeout: {timeout} seconds")
        
        start_time = time.time()
        detected_messages = {}
        
        try:
            while (time.time() - start_time) < timeout:
                for msg in self.midi_input_port.iter_pending():
                    control_info = self._analyze_message(msg)
                    if control_info:
                        key = f"{control_info['type']}_{control_info['channel']}_{control_info['controller']}"
                        if key not in detected_messages:
                            detected_messages[key] = {
                                'info': control_info,
                                'count': 1,
                                'last_value': control_info.get('value', 0)
                            }
                        else:
                            detected_messages[key]['count'] += 1
                            detected_messages[key]['last_value'] = control_info.get('value', 0)
                
                # If we have consistent messages, use the most frequent one
                if detected_messages:
                    best_match = max(detected_messages.values(), key=lambda x: x['count'])
                    if best_match['count'] >= 3:  # At least 3 messages for confidence
                        self.learned_control = best_match['info']
                        print(f"✓ Learned: {self._format_control_name(self.learned_control)}")
                        return self.learned_control
                
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage
                
        except KeyboardInterrupt:
            print("\\nMIDI learn cancelled by user")
            return None
            
        print("✗ MIDI learn timeout - no control detected")
        return None
    
    def learn_range(self, control_info: Dict, timeout: float = 60.0) -> Optional[Tuple[int, int]]:
        """
        Learn the min/max range of a MIDI control.
        
        Args:
            control_info: Control information from learn_control()
            timeout: Total timeout for range learning
            
        Returns:
            Tuple of (min_value, max_value) or None if failed
        """
        if not self.midi_input_port:
            logging.error("No MIDI input port available for range learning")
            return None
            
        print(f"\\nRange Learning for: {self._format_control_name(control_info)}")
        print("Step 1: Move control to MINIMUM position and hold...")
        
        min_value = self._learn_position("MINIMUM", control_info, timeout / 2)
        if min_value is None:
            return None
            
        print(f"Step 2: Move control to MAXIMUM position and hold...")
        
        max_value = self._learn_position("MAXIMUM", control_info, timeout / 2)
        if max_value is None:
            return None
            
        # Ensure min < max
        if min_value > max_value:
            min_value, max_value = max_value, min_value
            
        print(f"✓ Range learned: {min_value} to {max_value}")
        return (min_value, max_value)
    
    def _learn_position(self, position_name: str, control_info: Dict, timeout: float) -> Optional[int]:
        """Learn a specific position (min or max) of the control."""
        start_time = time.time()
        stable_value = None
        stable_count = 0
        last_values = []
        
        try:
            while (time.time() - start_time) < timeout:
                for msg in self.midi_input_port.iter_pending():
                    if self._message_matches_control(msg, control_info):
                        value = self._extract_value_from_message(msg, control_info)
                        if value is not None:
                            last_values.append(value)
                            if len(last_values) > 10:
                                last_values.pop(0)
                            
                            # Check for stability (same value for multiple readings)
                            if len(last_values) >= 5:
                                recent_values = last_values[-5:]
                                if all(v == recent_values[0] for v in recent_values):
                                    if stable_value != recent_values[0]:
                                        stable_value = recent_values[0]
                                        stable_count = 1
                                    else:
                                        stable_count += 1
                                    
                                    # If stable for enough readings, we have our position
                                    if stable_count >= 10:
                                        print(f"✓ {position_name} position: {stable_value}")
                                        return stable_value
                
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print(f"\\n{position_name} position learning cancelled")
            return None
            
        print(f"✗ {position_name} position learning timeout")
        return None
    
    def _analyze_message(self, msg: mido.Message) -> Optional[Dict]:
        """Analyze a MIDI message to extract control information."""
        if msg.type == 'control_change':
            # Standard CC or part of CC14/NRPN
            if msg.control in [6, 38, 98, 99, 100, 101]:
                # These are CC14/NRPN data/parameter controllers - ignore for direct learning
                return None
            return {
                'type': 'cc',
                'channel': msg.channel,
                'controller': msg.control,
                'value': msg.value,
                'name': f"CC{msg.control}"
            }
        elif msg.type == 'pitchwheel':
            return {
                'type': 'pitchwheel',
                'channel': msg.channel,
                'controller': 'pitchwheel',
                'value': msg.pitch,
                'name': 'Pitch Wheel'
            }
            
        return None
    
    def _message_matches_control(self, msg: mido.Message, control_info: Dict) -> bool:
        """Check if a MIDI message matches the learned control."""
        if msg.channel != control_info['channel']:
            return False
            
        if control_info['type'] == 'cc':
            return (msg.type == 'control_change' and 
                   msg.control == control_info['controller'])
        elif control_info['type'] == 'pitchwheel':
            return msg.type == 'pitchwheel'
            
        return False
    
    def _extract_value_from_message(self, msg: mido.Message, control_info: Dict) -> Optional[int]:
        """Extract the control value from a MIDI message."""
        if control_info['type'] == 'cc':
            return msg.value if msg.type == 'control_change' else None
        elif control_info['type'] == 'pitchwheel':
            return msg.pitch if msg.type == 'pitchwheel' else None
            
        return None
    
    def _format_control_name(self, control_info: Dict) -> str:
        """Format control information for display."""
        channel_display = control_info['channel'] + 1  # 1-based for display
        return f"{control_info['name']} (Channel {channel_display})"