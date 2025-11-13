"""
Quick test script to send MIDI Program Change message
"""

import mido
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# List available MIDI output ports
print("Available MIDI output ports:")
output_ports = mido.get_output_names()
for i, port_name in enumerate(output_ports):
    print(f"  {i}: {port_name}")

if not output_ports:
    print("No MIDI output ports found!")
    exit(1)

# Ask user which port to use
port_index = 0
if len(output_ports) > 1:
    port_index = int(input(f"\nSelect MIDI output port (0-{len(output_ports)-1}): "))

selected_port = output_ports[port_index]
print(f"\nUsing MIDI output port: {selected_port}")

# Open MIDI output port
try:
    midi_out = mido.open_output(selected_port)
    print("MIDI port opened successfully")
except Exception as e:
    print(f"Failed to open MIDI port: {e}")
    exit(1)

# Send Program Change for patch 6
# Note: MIDI Program Change values are 0-127
# Patch 6 = Program number 5 (0-indexed) or 6 (1-indexed, user-facing)
# Let's send both interpretations so user can verify which their synth uses

channel = 0  # MIDI channel 1 (0-indexed)

print("\n--- Testing Program Change ---")
print("Sending Program Change 5 (patch 6 if 0-indexed)")
pc_msg = mido.Message('program_change', program=5, channel=channel)
midi_out.send(pc_msg)
print(f"Sent: {pc_msg}")
time.sleep(2)

print("\nSending Program Change 6 (patch 6 if 1-indexed, or patch 7 if 0-indexed)")
pc_msg = mido.Message('program_change', program=6, channel=channel)
midi_out.send(pc_msg)
print(f"Sent: {pc_msg}")

print("\n--- Test Complete ---")
print("Check your synth to see which program changed to patch 6")
print("Note: Different synths may interpret program numbers differently:")
print("  - Program 5 = Patch 6 (if synth uses 0-indexed)")
print("  - Program 6 = Patch 6 (if synth uses 1-indexed, which is less common)")

# Close MIDI port
midi_out.close()
print("\nMIDI port closed")
