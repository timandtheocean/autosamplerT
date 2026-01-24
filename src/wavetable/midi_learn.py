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
        
        # NRPN sequence tracking
        self.nrpn_state = {}  # Per-channel NRPN state
        self.nrpn_data_lsb = {}  # Track Data Entry LSB for 14-bit values
        
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
        import sys
        sys.stdout.flush()
        
        start_time = time.time()
        detected_messages = {}
        last_progress_time = start_time
        message_count = 0
        
        try:
            while (time.time() - start_time) < timeout:
                for msg in self.midi_input_port.iter_pending():
                    message_count += 1
                    # Debug: show all incoming messages
                    print(f"Raw MIDI: {msg}")
                    sys.stdout.flush()
                    
                    control_info = self._analyze_message(msg)
                    if control_info:
                        key = f"{control_info['type']}_{control_info['channel']}_{control_info['controller']}"
                        if key not in detected_messages:
                            detected_messages[key] = {
                                'info': control_info,
                                'count': 1,
                                'last_value': control_info.get('value', 0)
                            }
                            print(f"Detected: {self._format_control_name(control_info)} = {control_info.get('value', 0)}")
                            sys.stdout.flush()
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
                
                # Show progress every 5 seconds
                current_time = time.time()
                if current_time - last_progress_time >= 5.0:
                    remaining = int(timeout - (current_time - start_time))
                    if message_count > 0:
                        print(f"Messages received: {message_count}, Time remaining: {remaining}s")
                    else:
                        print(f"Listening... Time remaining: {remaining}s")
                    sys.stdout.flush()
                    last_progress_time = current_time
                
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage
                
        except KeyboardInterrupt:
            print("\nMIDI learn cancelled by user")
            return None
            
        print("MIDI learn timeout - no control detected")
        return None
    
    def learn_range(self, control_info: Dict, timeout: float = 60.0) -> Optional[Tuple[int, int]]:
        """
        Learn the min/max range of a MIDI control using step-by-step position detection.
        
        Args:
            control_info: Control information from learn_control()
            timeout: Total timeout for range learning (not used, each step has 20s timeout)
            
        Returns:
            Tuple of (min_value, max_value) or None if failed
        """
        if not self.midi_input_port:
            logging.error("No MIDI input port available for range learning")
            return None
            
        print(f"\nRange Learning for: {self._format_control_name(control_info)}")
        print("This uses a step-by-step approach for maximum reliability...")
        import sys
        sys.stdout.flush()
        
        return self._learn_range_by_sweep(control_info, timeout)
    
    def _learn_range_by_sweep(self, control_info: Dict, timeout: float) -> Optional[Tuple[int, int]]:
        """Learn parameter range by step-by-step position detection."""
        print(f"\n=== Learning Range Step-by-Step ===")
        print("This will learn the range in 3 steps:")
        print("1. Dial to MINIMUM position")
        print("2. Dial to MAXIMUM position") 
        print("3. Dial back to MINIMUM position (verification)")
        print()
        
        try:
            # Step 1: Learn minimum position
            print("STEP 1: Please dial the control to its MINIMUM position")
            print("Hold it steady once you reach the minimum...")
            min_value_1 = self._detect_stable_position("minimum", control_info, 20.0)
            if min_value_1 is None:
                print("Failed to detect minimum position")
                return None
            print(f"Minimum position: {min_value_1}")
            
            # Step 2: Learn maximum position  
            print(f"\nSTEP 2: Please dial the control to its MAXIMUM position")
            print("Hold it steady once you reach the maximum...")
            max_value = self._detect_stable_position("maximum", control_info, 20.0)
            if max_value is None:
                print("Failed to detect maximum position")
                return None
            print(f"Maximum position: {max_value}")
            
            # Step 3: Verify minimum position
            print(f"\nSTEP 3: Please dial the control back to its MINIMUM position")
            print("Hold it steady to verify the minimum...")
            min_value_2 = self._detect_stable_position("minimum (verification)", control_info, 20.0)
            if min_value_2 is None:
                print("Failed to verify minimum - using first minimum value")
                min_value_final = min_value_1
            else:
                print(f"Minimum verified: {min_value_2}")
                
                # Use the most restrictive minimum (smallest value)
                min_value_final = min(min_value_1, min_value_2)
                if min_value_1 != min_value_2:
                    print(f"Min values differ: {min_value_1} vs {min_value_2}, using {min_value_final}")
            
            # Final range check
            if min_value_final >= max_value:
                print(f"Invalid range: min({min_value_final}) >= max({max_value})")
                return None
                
            range_size = max_value - min_value_final + 1
            print(f"\nRANGE LEARNED: Min={min_value_final}, Max={max_value} (size: {range_size})")
            return (min_value_final, max_value)
            
        except KeyboardInterrupt:
            print("\nRange learning cancelled by user")
            return None

    def _detect_stable_position(self, position_name: str, control_info: Dict, timeout: float) -> Optional[int]:
        """Detect a stable position by looking at the final few messages."""
        start_time = time.time()
        recent_values = []
        last_value_time = start_time
        
        print(f"Detecting {position_name} position... (timeout: {int(timeout)}s)")
        print("Press ENTER when ready, or wait 3 seconds after stopping movement")
        import sys
        sys.stdout.flush()
        
        # Set up non-blocking keyboard input for Windows
        if sys.platform == "win32":
            import msvcrt
        
        try:
            while (time.time() - start_time) < timeout:
                current_time = time.time()
                
                # Process MIDI messages
                for msg in self.midi_input_port.iter_pending():
                    # First, analyze the message to update NRPN state
                    analyzed = self._analyze_message(msg)
                    
                    # If this message matches our control, extract the value
                    if self._message_matches_control(msg, control_info):
                        value = self._extract_value_from_message(msg, control_info)
                        if value is not None:
                            recent_values.append(value)
                            last_value_time = current_time
                            
                            # Keep only the last 10 values
                            if len(recent_values) > 10:
                                recent_values.pop(0)
                            
                            # Show current value
                            if len(recent_values) >= 3:
                                last_3 = recent_values[-3:]
                                if all(v == last_3[0] for v in last_3):
                                    print(f"Stable at {last_3[0]} (hold to confirm)", end='\r')
                                else:
                                    print(f"Current: {value} (moving)", end='\r')
                            else:
                                print(f"Current: {value}", end='\r')
                            sys.stdout.flush()
                
                # Check for Enter key press (Windows)
                if sys.platform == "win32" and msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key in [b'\r', b'\n']:  # Enter key
                        if recent_values:
                            stable_value = recent_values[-1]
                            print(f"\n{position_name} confirmed: {stable_value}")
                            sys.stdout.flush()
                            return stable_value
                        else:
                            print(f"\nNo values received yet, please move the control first")
                
                # Check for stable value (no new messages for 3 seconds OR stable pattern)
                if recent_values:
                    # Method 1: No new values for 3 seconds (auto-detection)
                    if (current_time - last_value_time) >= 3.0:
                        # Look at the final few values for stability
                        if len(recent_values) >= 2:
                            stable_value = recent_values[-1]
                            print(f"\n{position_name} detected: {stable_value}")
                            sys.stdout.flush()
                            return stable_value
                    
                    # Method 2: Same value for the last 5 readings (immediate detection)
                    if len(recent_values) >= 5:
                        final_values = recent_values[-5:]
                        if all(v == final_values[0] for v in final_values):
                            stable_value = final_values[0]
                            print(f"\n{position_name} detected: {stable_value}")
                            sys.stdout.flush()
                            return stable_value
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print(f"\n{position_name} detection cancelled")
            return None
            
        print(f"\n{position_name} detection timeout")
        return None

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
            print(f"\n{position_name} position learning cancelled")
            return None
            
        print(f"✗ {position_name} position learning timeout")
        return None
    
    def _analyze_message(self, msg: mido.Message) -> Optional[Dict]:
        """Analyze a MIDI message to extract control information."""
        if msg.type == 'control_change':
            channel = msg.channel
            
            # NRPN sequence detection
            if msg.control == 99:  # NRPN MSB
                if channel not in self.nrpn_state:
                    self.nrpn_state[channel] = {}
                self.nrpn_state[channel]['nrpn_msb'] = msg.value
                return None
                
            elif msg.control == 98:  # NRPN LSB
                if channel not in self.nrpn_state:
                    self.nrpn_state[channel] = {}
                self.nrpn_state[channel]['nrpn_lsb'] = msg.value
                return None
                
            elif msg.control == 6:  # Data Entry MSB
                if (channel in self.nrpn_state and 
                    'nrpn_msb' in self.nrpn_state[channel] and 
                    'nrpn_lsb' in self.nrpn_state[channel]):
                    
                    # Store MSB for later combination with LSB
                    nrpn_parameter = (self.nrpn_state[channel]['nrpn_msb'] << 7) + self.nrpn_state[channel]['nrpn_lsb']
                    self.nrpn_state[channel]['data_msb'] = msg.value
                    
                    # Debug: show what we're storing
                    print(f"Storing Data MSB: {msg.value} for NRPN{nrpn_parameter}")
                    
                    # Don't return anything yet - wait for LSB
                return None
                
            elif msg.control == 38:  # Data Entry LSB (for 14-bit NRPN)
                if (channel in self.nrpn_state and 
                    'nrpn_msb' in self.nrpn_state[channel] and 
                    'nrpn_lsb' in self.nrpn_state[channel] and
                    'data_msb' in self.nrpn_state[channel]):
                    
                    # Now we have both MSB and LSB - return complete 14-bit NRPN value
                    nrpn_parameter = (self.nrpn_state[channel]['nrpn_msb'] << 7) + self.nrpn_state[channel]['nrpn_lsb']
                    data_msb = self.nrpn_state[channel]['data_msb']
                    data_lsb = msg.value
                    full_14bit_value = (data_msb << 7) + data_lsb
                    
                    # Debug: print the calculation
                    print(f"NRPN{nrpn_parameter}: MSB={data_msb}, LSB={data_lsb} → {full_14bit_value}")
                    
                    return {
                        'type': 'nrpn',
                        'channel': channel,
                        'controller': nrpn_parameter,
                        'value': full_14bit_value,  # Complete 14-bit value (0-16383)
                        'name': f"NRPN{nrpn_parameter}"
                    }
                else:
                    print(f"LSB received but missing state - channel: {channel}, state: {self.nrpn_state.get(channel, {})}")
                return None
                
            elif msg.control in [100, 101]:  # RPN controllers - ignore
                return None
                
            # Standard CC message
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
        elif control_info['type'] == 'nrpn':
            # For NRPN, we want to trigger on Data Entry LSB (CC38) messages
            # since that's when we have the complete 14-bit value
            if msg.type == 'control_change' and msg.control == 38:
                channel = msg.channel
                if (channel in self.nrpn_state and 
                    'nrpn_msb' in self.nrpn_state[channel] and 
                    'nrpn_lsb' in self.nrpn_state[channel]):
                    
                    current_nrpn = (self.nrpn_state[channel]['nrpn_msb'] << 7) + self.nrpn_state[channel]['nrpn_lsb']
                    return current_nrpn == control_info['controller']
            return False
        elif control_info['type'] == 'pitchwheel':
            return msg.type == 'pitchwheel'
            
        return False
    
    def _extract_value_from_message(self, msg: mido.Message, control_info: Dict) -> Optional[int]:
        """Extract the control value from a MIDI message."""
        if control_info['type'] == 'cc':
            return msg.value if msg.type == 'control_change' else None
        elif control_info['type'] == 'nrpn':
            # For NRPN, the value is already calculated in _analyze_message
            # We only get here when the message matches our learned control
            if msg.type == 'control_change' and msg.control == 38:
                # This is the LSB message that triggers the complete 14-bit value
                channel = msg.channel
                if (channel in self.nrpn_state and 
                    'data_msb' in self.nrpn_state[channel]):
                    data_msb = self.nrpn_state[channel]['data_msb']
                    data_lsb = msg.value
                    return (data_msb << 7) + data_lsb
            return None
        elif control_info['type'] == 'pitchwheel':
            return msg.pitch if msg.type == 'pitchwheel' else None
            
        return None
    
    def _format_control_name(self, control_info: Dict) -> str:
        """Format control information for display."""
        channel_display = control_info['channel'] + 1  # 1-based for display
        return f"{control_info['name']} (Channel {channel_display})"