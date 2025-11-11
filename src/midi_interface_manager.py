import mido
import logging
import yaml
import os
from typing import Tuple, List, Optional

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../conf/autosamplerT_config.yaml')

class MidiInterfaceManager:
    def __init__(self) -> None:
        self.input_name: Optional[str] = None
        self.output_name: Optional[str] = None

    def list_midi_devices(self) -> Tuple[List[str], List[str]]:
        inputs = mido.get_input_names()
        outputs = mido.get_output_names()
        logging.debug(f"Available MIDI input devices: {inputs}")
        logging.debug(f"Available MIDI output devices: {outputs}")
        return inputs, outputs

    def set_midi_input(self, name: str) -> None:
        if name in mido.get_input_names():
            self.input_name = name
            logging.info(f"MIDI input set to: {name}")
        else:
            logging.error(f"MIDI input device not found: {name}")
            raise ValueError(f"MIDI input device not found: {name}")

    def set_midi_output(self, name: str) -> None:
        if name in mido.get_output_names():
            self.output_name = name
            logging.info(f"MIDI output set to: {name}")
        else:
            logging.error(f"MIDI output device not found: {name}")
            raise ValueError(f"MIDI output device not found: {name}")

    def verify_settings(self) -> None:
        logging.info(f"Current MIDI input: {self.input_name}")
        logging.info(f"Current MIDI output: {self.output_name}")


def main() -> None:
    """Main function to demonstrate MIDI interface manager."""
    manager = MidiInterfaceManager()
    
    try:
        # Load config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f)
            midi_conf = config.get('midi_interface', {})
            
            # List devices
            inputs, outputs = manager.list_midi_devices()
            
            # Set devices from config
            midi_input = midi_conf.get('midi_input_name')
            midi_output = midi_conf.get('midi_output_name')
            
            if midi_input:
                manager.set_midi_input(midi_input)
            if midi_output:
                manager.set_midi_output(midi_output)
            
            manager.verify_settings()
        else:
            logging.warning(f"Config file not found: {CONFIG_FILE}")
            manager.list_midi_devices()
    except Exception as e:
        logging.error(f"Error: {e}")


if __name__ == "__main__":
    main()
