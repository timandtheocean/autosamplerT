#!/usr/bin/env python3
"""
MIDI Input Debug Script

Tests MIDI input to see exactly what messages are received.
Shows raw messages, decoded control info, and tracks min/max values.
"""

import time
import mido
import sys
from typing import Dict, Optional

class MIDIInputTester:
    def __init__(self):
        self.nrpn_state = {}  # Per-channel NRPN state
        self.control_ranges = {}  # Track min/max for each control
        
    def analyze_message(self, msg: mido.Message) -> Optional[Dict]:
        """Analyze a MIDI message and return control info."""
        if msg.type == 'control_change':
            channel = msg.channel
            
            # NRPN sequence detection
            if msg.control == 99:  # NRPN MSB
                if channel not in self.nrpn_state:
                    self.nrpn_state[channel] = {}
                self.nrpn_state[channel]['nrpn_msb'] = msg.value
                return {
                    'type': 'nrpn_setup',
                    'channel': channel,
                    'controller': 'MSB',
                    'value': msg.value,
                    'name': f'NRPN MSB Ch{channel+1}'
                }
                
            elif msg.control == 98:  # NRPN LSB
                if channel not in self.nrpn_state:
                    self.nrpn_state[channel] = {}
                self.nrpn_state[channel]['nrpn_lsb'] = msg.value
                return {
                    'type': 'nrpn_setup',
                    'channel': channel,
                    'controller': 'LSB',
                    'value': msg.value,
                    'name': f'NRPN LSB Ch{channel+1}'
                }
                
            elif msg.control == 6:  # Data Entry MSB
                if (channel in self.nrpn_state and 
                    'nrpn_msb' in self.nrpn_state[channel] and 
                    'nrpn_lsb' in self.nrpn_state[channel]):
                    
                    # Complete NRPN message detected
                    nrpn_parameter = (self.nrpn_state[channel]['nrpn_msb'] << 7) + self.nrpn_state[channel]['nrpn_lsb']
                    return {
                        'type': 'nrpn',
                        'channel': channel,
                        'controller': nrpn_parameter,
                        'value': msg.value,
                        'name': f'NRPN{nrpn_parameter} Ch{channel+1}'
                    }
                else:
                    return {
                        'type': 'cc',
                        'channel': channel,
                        'controller': msg.control,
                        'value': msg.value,
                        'name': f'CC{msg.control} Ch{channel+1}'
                    }
                    
            elif msg.control == 38:  # Data Entry LSB
                return {
                    'type': 'data_lsb',
                    'channel': channel,
                    'controller': msg.control,
                    'value': msg.value,
                    'name': f'Data LSB Ch{channel+1}'
                }
                
            elif msg.control in [100, 101]:  # RPN controllers
                return {
                    'type': 'rpn',
                    'channel': channel,
                    'controller': msg.control,
                    'value': msg.value,
                    'name': f'RPN{msg.control} Ch{channel+1}'
                }
                
            # Standard CC message
            return {
                'type': 'cc',
                'channel': channel,
                'controller': msg.control,
                'value': msg.value,
                'name': f'CC{msg.control} Ch{channel+1}'
            }
            
        elif msg.type == 'pitchwheel':
            return {
                'type': 'pitchwheel',
                'channel': msg.channel,
                'controller': 'pitchwheel',
                'value': msg.pitch,
                'name': f'Pitchwheel Ch{msg.channel+1}'
            }
            
        return None
    
    def update_range(self, control_info: Dict):
        """Update min/max range for a control."""
        key = f"{control_info['type']}_{control_info['channel']}_{control_info['controller']}"
        value = control_info['value']
        
        if key not in self.control_ranges:
            self.control_ranges[key] = {
                'name': control_info['name'],
                'min': value,
                'max': value,
                'count': 1
            }
        else:
            self.control_ranges[key]['min'] = min(self.control_ranges[key]['min'], value)
            self.control_ranges[key]['max'] = max(self.control_ranges[key]['max'], value)
            self.control_ranges[key]['count'] += 1
    
    def print_ranges(self):
        """Print current min/max ranges for all detected controls."""
        print("\n=== Control Ranges ===")
        for key, data in self.control_ranges.items():
            print(f"{data['name']}: {data['min']}-{data['max']} ({data['count']} messages)")
        print("=" * 25)

def main():
    # List available MIDI inputs and outputs
    inputs = mido.get_input_names()
    outputs = mido.get_output_names()
    
    print("=== MIDI Device Check ===")
    print("Available MIDI inputs:")
    for i, name in enumerate(inputs):
        print(f"  {i}: {name}")
    
    print("\nAvailable MIDI outputs:")
    for i, name in enumerate(outputs):
        print(f"  {i}: {name}")
    
    if not inputs:
        print("ERROR: No MIDI input devices found!")
        return
    
    # Use first available input
    input_name = inputs[0]
    output_name = outputs[0] if outputs else None
    
    print(f"\nUsing MIDI input: {input_name}")
    if output_name:
        print(f"Using MIDI output: {output_name}")
        
        # Test MIDI output first
        print("\n=== Testing MIDI Output ===")
        try:
            with mido.open_output(output_name) as out_port:
                print("Sending test note C4 (60)...")
                out_port.send(mido.Message('note_on', note=60, velocity=64))
                time.sleep(0.1)
                out_port.send(mido.Message('note_off', note=60, velocity=64))
                print("Test note sent successfully!")
        except Exception as e:
            print(f"Output test failed: {e}")
    
    print(f"\n=== Testing MIDI Input ===")
    print("Try playing notes, moving controls, or sending NRPN messages...")
    print("Press Ctrl+C to stop and show results")
    print("-" * 60)
    
    tester = MIDIInputTester()
    message_count = 0
    
    try:
        with mido.open_input(input_name) as port:
            print(f"MIDI input port opened: {port}")
            start_time = time.time()
            last_status_time = start_time
            
            while True:
                for msg in port.iter_pending():
                    message_count += 1
                    print(f"[{message_count}] RAW: {msg}")
                    
                    # Analyze and show decoded info
                    control_info = tester.analyze_message(msg)
                    if control_info:
                        print(f"         -> {control_info['name']} = {control_info['value']}")
                        tester.update_range(control_info)
                    
                    sys.stdout.flush()
                
                # Show periodic status
                current_time = time.time()
                if current_time - last_status_time >= 10.0:
                    elapsed = int(current_time - start_time)
                    print(f"Status: {message_count} messages received in {elapsed}s")
                    if message_count == 0:
                        print("  -> No MIDI data detected. Check:")
                        print("     - MIDI cable connection")
                        print("     - Prophet 6 MIDI Out setting")
                        print("     - MIDI channel settings")
                    last_status_time = current_time
                    
                time.sleep(0.01)
                
    except KeyboardInterrupt:
        print(f"\n\nStopped by user - {message_count} total messages received")
        if message_count > 0:
            tester.print_ranges()
        else:
            print("No MIDI messages were received!")
            print("\nTroubleshooting:")
            print("1. Check MIDI cable is connected from Prophet 6 MIDI OUT to computer MIDI IN")
            print("2. Check Prophet 6 Global > MIDI > MIDI Out Channel setting")
            print("3. Try playing a note on the Prophet 6")
            print("4. Check if Prophet 6 is set to send MIDI data")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    main()