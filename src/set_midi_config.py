import mido
import yaml
import os
import sys
from typing import List, Optional

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../conf/autosamplerT_config.yaml')

def list_midi_devices() -> (List[str], List[str]):
    """Retrieve and display MIDI input/output devices with indices."""
    inputs = mido.get_input_names() or []
    outputs = mido.get_output_names() or []
    print("\n=== MIDI DEVICE LIST ===")
    print("INPUTS:")
    if inputs:
        for idx, name in enumerate(inputs):
            print(f"  [{idx}] {name}")
    else:
        print("  (none detected)")
    print("OUTPUTS:")
    if outputs:
        for idx, name in enumerate(outputs):
            print(f"  [{idx}] {name}")
    else:
        print("  (none detected)")
    print("========================\n")
    return inputs, outputs

def get_user_selection(devices: List[str], device_type: str, allow_skip: bool = True) -> Optional[str]:
    """
    Interactive selection supporting:
      - numeric index
      - empty entry to skip (if allow_skip)
    Returns selected device name or None if skipped.
    """
    if not devices:
        return None
    
    # Show available devices for this type
    print(f"\nAvailable {device_type} devices:")
    for idx, name in enumerate(devices):
        print(f"  [{idx}] {name}")
    
    while True:
        prompt = f"Select {device_type} (enter index"
        if allow_skip:
            prompt += ", or press Enter to skip"
        prompt += "): "
        
        raw = input(prompt).strip()
        
        if allow_skip and raw == "":
            print(f"({device_type} skipped)")
            return None
        
        # Try numeric index
        if raw.isdigit():
            idx = int(raw)
            if 0 <= idx < len(devices):
                selected = devices[idx]
                print(f"Selected: [{idx}] {selected}")
                return selected
            print(f"Invalid index {idx}. Valid range: 0-{len(devices)-1}")
            continue
        else:
            print(f"Please enter a number (0-{len(devices)-1})")

def main():
    inputs, outputs = list_midi_devices()
    if not inputs and not outputs:
        print("No MIDI devices detected. Connect devices and re-run.")
        sys.exit(1)
    if not inputs:
        print("Warning: No MIDI INPUT devices detected. Input will be left unset.")
    if not outputs:
        print("Warning: No MIDI OUTPUT devices detected. Output will be left unset.")

    input_name = get_user_selection(inputs, "MIDI INPUT")
    output_name = get_user_selection(outputs, "MIDI OUTPUT")

    # Load existing config if present
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f) or {}
    if 'audio_interface' not in config:
        config['audio_interface'] = {'input_device_index': None, 'output_device_index': None, 'samplerate': None, 'bitdepth': None}
    # Validate selections explicitly
    valid_input = input_name in inputs if input_name else True
    valid_output = output_name in outputs if output_name else True

    config['midi_interface'] = {
        'midi_input_name': input_name,
        'midi_output_name': output_name,
        'midi_input_valid': valid_input,
        'midi_output_valid': valid_output
    }
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)
    print(f"MIDI configuration saved to {os.path.abspath(CONFIG_FILE)}")
    print("Summary:")
    status_in = "OK" if valid_input and input_name else ("SKIPPED" if not input_name else "NOT FOUND")
    status_out = "OK" if valid_output and output_name else ("SKIPPED" if not output_name else "NOT FOUND")
    print(f"  Input : {input_name if input_name else '(none)'}  [{status_in}]")
    print(f"  Output: {output_name if output_name else '(none)'}  [{status_out}]")
    if status_in == "NOT FOUND" or status_out == "NOT FOUND":
        print("Warning: One or more selected MIDI devices were not found in enumeration.")

if __name__ == "__main__":
	main()

