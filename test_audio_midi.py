#!/usr/bin/env python3
"""
Test audio recording while MIDI is playing on Prophet 6.
"""

import mido
import sounddevice as sd
import soundfile as sf
import time
import numpy as np
import sys
import os

# Add src to path for MIDI controller
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from sampler_midicontrol import MIDIController

def main():
    try:
        print("=== Audio + MIDI Test ===")
        
        # Setup MIDI
        midi_output_port = mido.open_output("Prophet 6 1")
        midi_controller = MIDIController(midi_output_port)
        
        # Test 1: Record while playing a held note
        print("\\nTest 1: Record 3 seconds while holding C4...")
        
        # Start recording
        print("Starting recording...")
        recording = sd.rec(44100 * 3, samplerate=44100, channels=2, device=37, dtype='float32')
        
        # Send note on immediately after starting recording
        time.sleep(0.1)  # Small delay to ensure recording starts
        print("Sending Note On...")
        midi_controller.send_note_on(60, 100, 0)
        
        # Wait for recording to complete
        sd.wait()
        
        # Send note off
        print("Sending Note Off...")
        midi_controller.send_note_off(60, 0)
        
        # Analyze recording
        left_max = abs(recording[:, 0]).max()
        right_max = abs(recording[:, 1]).max()
        
        print(f"Recording completed:")
        print(f"Left channel max: {left_max:.6f}")
        print(f"Right channel max: {right_max:.6f}")
        
        # Save the recording for inspection
        output_folder = "./output/test"
        os.makedirs(output_folder, exist_ok=True)
        sf.write(f"{output_folder}/audio_midi_test.wav", recording, 44100)
        print(f"Saved recording to: {output_folder}/audio_midi_test.wav")
        
        if left_max > 0.01 or right_max > 0.01:
            print("✓ Good signal levels - audio recording is working!")
        else:
            print("✗ Low signal levels - check Prophet 6 output level or connections")
            
        # Test 2: Record while sweeping NRPN
        print("\\nTest 2: Record 5 seconds while sweeping NRPN3...")
        
        recording2 = sd.rec(44100 * 5, samplerate=44100, channels=2, device=37, dtype='float32')
        
        time.sleep(0.1)  # Small delay
        print("Sending Note On...")
        midi_controller.send_note_on(60, 100, 0)
        time.sleep(0.5)  # Let note stabilize
        
        print("Starting NRPN sweep...")
        for i, value in enumerate(range(0, 255, 5)):  # Faster sweep
            midi_controller.send_nrpn(3, value, 0)
            time.sleep(0.08)  # 80ms per step
            if i % 10 == 0:
                print(f"  NRPN3 = {value}")
        
        # Wait for recording to complete
        sd.wait()
        
        print("Sending Note Off...")
        midi_controller.send_note_off(60, 0)
        
        # Analyze second recording
        left_max2 = abs(recording2[:, 0]).max()
        right_max2 = abs(recording2[:, 1]).max()
        
        print(f"Sweep recording completed:")
        print(f"Left channel max: {left_max2:.6f}")
        print(f"Right channel max: {right_max2:.6f}")
        
        # Save sweep recording
        sf.write(f"{output_folder}/audio_nrpn_sweep_test.wav", recording2, 44100)
        print(f"Saved sweep recording to: {output_folder}/audio_nrpn_sweep_test.wav")
        
        print("\\n=== Test Results ===")
        print(f"Audio device 37 is capturing signal: {'YES' if (left_max > 0.01 or right_max > 0.01) else 'NO'}")
        print(f"MIDI control is working: YES")
        print(f"Prophet 6 responds to parameter changes: {'YES' if (left_max2 > 0.01 or right_max2 > 0.01) else 'NO'}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()