import mido
import yaml
import os
import sys

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../conf/autosamplerT_config.yaml')

def list_midi_devices():
    inputs = mido.get_input_names()
    outputs = mido.get_output_names()
    print("Available MIDI INPUT devices:")
    for idx, name in enumerate(inputs):
        print(f"  {idx}: {name}")
    print("\nAvailable MIDI OUTPUT devices:")
    for idx, name in enumerate(outputs):
        print(f"  {idx}: {name}")
    return inputs, outputs

def get_user_selection(devices, prompt):
    while True:
        try:
            idx = int(input(prompt))
            if 0 <= idx < len(devices):
                return devices[idx]
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")

def main():
    inputs, outputs = list_midi_devices()
    if not inputs:
        print("No MIDI input devices found. Please connect a MIDI device and restart the program.")
        sys.exit(1)
    if not outputs:
        print("No MIDI output devices found. Please connect a MIDI device and restart the program.")
        sys.exit(1)
    input_name = get_user_selection(inputs, "Select MIDI input device index: ")
    output_name = get_user_selection(outputs, "Select MIDI output device index: ")
    # Load existing config if present
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f) or {}
    if 'audio_interface' not in config:
        config['audio_interface'] = {'input_device_index': None, 'output_device_index': None, 'samplerate': None, 'bitdepth': None}
    config['midi_interface'] = {
        'midi_input_name': input_name,
        'midi_output_name': output_name
    }
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)
    print(f"MIDI configuration saved to {CONFIG_FILE}")

if __name__ == "__main__":
	main()

