#!/usr/bin/env python3
"""
Quick MIDI test to verify Prophet 6 note triggering and NRPN control.
"""

import mido
import time
import sys
import os

# Add src to path for MIDI controller
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from sampler_midicontrol import MIDIController

def main():
    try:
        print("=== Prophet 6 MIDI Test ===")
        
        # Open MIDI output
        midi_output_port = mido.open_output("Prophet 6 1")
        midi_controller = MIDIController(midi_output_port)
        
        # Test note triggering
        print("Testing note triggering...")
        print("Sending Note On C4 (60) with velocity 100")
        midi_controller.send_note_on(60, 100, 0)
        
        print("Holding note for 2 seconds...")
        time.sleep(2)
        
        print("Sending Note Off C4 (60)")
        midi_controller.send_note_off(60, 0)
        
        print()
        print("Testing NRPN parameter sweep while note is held...")
        
        # Send note on again
        print("Sending Note On C4 (60)")
        midi_controller.send_note_on(60, 100, 0)
        time.sleep(0.5)  # Let note stabilize
        
        # Sweep NRPN3 (Osc1 Shape) from 0 to 254
        print("Sweeping NRPN3 from 0 to 254...")
        for value in range(0, 255, 10):  # Step by 10 for speed
            print(f"NRPN3 = {value}")
            midi_controller.send_nrpn(3, value, 0)
            time.sleep(0.2)
        
        # Send note off
        print("Sending Note Off C4 (60)")
        midi_controller.send_note_off(60, 0)
        
        print("MIDI test completed!")
        print("Did you hear the Prophet 6 playing and the waveshape changing?")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()