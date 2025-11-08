import sounddevice as sd
import logging
import yaml
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../conf/autosamplerT_config.yaml')

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    return {}

def list_devices():
    devices = sd.query_devices()
    input_devices = [(idx, dev['name']) for idx, dev in enumerate(devices) if dev['max_input_channels'] > 0]
    output_devices = [(idx, dev['name']) for idx, dev in enumerate(devices) if dev['max_output_channels'] > 0]
    print("Available INPUT devices:")
    for idx, name in input_devices:
        print(f"  {idx}: {name}")
    print("\nAvailable OUTPUT devices:")
    for idx, name in output_devices:
        print(f"  {idx}: {name}")
    return devices, input_devices, output_devices

def main():
    print("Listing audio devices...")
    try:
        config = load_config()
        audio_conf = config.get('audio_interface', {})
        devices, input_devices, output_devices = list_devices()

        # Use config or defaults
        input_device_index = audio_conf.get('input_device_index', input_devices[0][0] if input_devices else None)
        output_device_index = audio_conf.get('output_device_index', output_devices[0][0] if output_devices else None)
        samplerate = audio_conf.get('samplerate', 44100)
        bitdepth = audio_conf.get('bitdepth', 24)

        # Set devices
        input_info = None
        output_info = None
        if input_device_index is not None and output_device_index is not None:
            sd.default.device = (input_device_index, output_device_index)
            input_info = sd.query_devices(input_device_index)
            output_info = sd.query_devices(output_device_index)
            logging.info(f"Input device set to: {input_info['name']}")
            logging.info(f"Output device set to: {output_info['name']}")
        else:
            logging.warning("No valid audio devices configured.")

        # Set sample rate
        sd.default.samplerate = samplerate
        logging.info(f"Sample rate set to: {samplerate}")

        # Set bit depth (check only)
        supported_bitdepths = [16, 24, 32]
        if bitdepth in supported_bitdepths:
            logging.info(f"Bit depth set to: {bitdepth}")
        else:
            logging.error(f"Unsupported bit depth: {bitdepth}")
            raise ValueError(f"Unsupported bit depth: {bitdepth}")

        # Verify settings
        if input_device_index is not None and input_info:
            logging.debug(f"Input device info: {input_info}")
            if samplerate != input_info['default_samplerate']:
                logging.warning(f"Requested sample rate {samplerate} may not be the input device's default ({input_info['default_samplerate']}).")
        if output_device_index is not None and output_info:
            logging.debug(f"Output device info: {output_info}")
            if samplerate != output_info['default_samplerate']:
                logging.warning(f"Requested sample rate {samplerate} may not be the output device's default ({output_info['default_samplerate']}).")
        logging.debug(f"Bit depth set to: {bitdepth}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
	main()

