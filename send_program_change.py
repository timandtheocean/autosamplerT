#!/usr/bin/env python3
"""
Quick MIDI Program Change
========================
Send a single program change message
"""

import mido
import time

def send_program_change(program_number):
    """Send a single program change message"""
    
    print(f"🎛️  Sending Program Change: {program_number}")
    
    try:
        # List available MIDI outputs
        outputs = mido.get_output_names()
        prophet_port = None
        
        # Find Prophet 6 port
        for port_name in outputs:
            if "Prophet" in port_name or "prophet" in port_name.lower():
                prophet_port = port_name
                break
        
        if not prophet_port:
            print("❌ Could not find Prophet 6 MIDI port")
            print("Available MIDI outputs:")
            for port in outputs:
                print(f"  - {port}")
            return
        
        print(f"📡 Using MIDI port: {prophet_port}")
        
        # Open MIDI port and send program change
        with mido.open_output(prophet_port) as port:
            # Send program change (convert 1-based to 0-based)
            pc_msg = mido.Message('program_change', program=program_number - 1, channel=0)
            port.send(pc_msg)
            print(f"✅ Program Change {program_number} sent successfully!")
            
            # Small delay to ensure message is processed
            time.sleep(0.5)
        
    except Exception as e:
        print(f"❌ Error sending program change: {e}")

if __name__ == "__main__":
    send_program_change(1)  # This sends MIDI program 0, displays as "Program 1"