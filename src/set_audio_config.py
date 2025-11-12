import os
# Enable ASIO support in sounddevice (must be set before importing sounddevice)
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd
import yaml
import platform

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../conf/autosamplerT_config.yaml')

def clear_screen():
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')

def list_output_devices():
    devices = sd.query_devices()
    host_apis = sd.query_hostapis()
    output_devices = [(idx, dev['name']) for idx, dev in enumerate(devices) if dev['max_output_channels'] > 0]
    print("Available OUTPUT devices:")
    for idx, name in output_devices:
        dev = devices[idx]
        host_api_name = host_apis[dev['hostapi']]['name']
        print(f"  {idx}: {name} [{host_api_name}]")
    return devices, output_devices

def list_input_devices(devices):
    host_apis = sd.query_hostapis()
    input_devices = [(idx, dev['name']) for idx, dev in enumerate(devices) if dev['max_input_channels'] > 0]
    print("Available INPUT devices:")
    for idx, name in input_devices:
        dev = devices[idx]
        host_api_name = host_apis[dev['hostapi']]['name']
        print(f"  {idx}: {name} [{host_api_name}]")
    return input_devices

def get_user_selection(devices, prompt):
    while True:
        try:
            idx = int(input(prompt))
            if any(d[0] == idx for d in devices):
                return idx
            else:
                print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")

def main():
    devices, output_devices = list_output_devices()
    if output_devices:
        output_idx = get_user_selection(output_devices, "Select output device index: ")
    else:
        output_idx = None
    clear_screen()
    input_devices = list_input_devices(devices)
    if input_devices:
        input_idx = get_user_selection(input_devices, "Select input device index: ")
    else:
        input_idx = None

    # Get supported sample rates from input/output device info
    if input_idx is not None:
        input_info = sd.query_devices(input_idx)
        default_samplerate = int(input_info.get('default_samplerate', 44100))
    else:
        default_samplerate = 44100
    supported_samplerates = [44100, 48000, 88200, 96000, 192000]  # Common rates
    print(f"\nSupported sample rates: {supported_samplerates}")
    print(f"Current (default) sample rate: {default_samplerate}")
    samplerate_in = input(f"Enter sample rate [{default_samplerate}]: ")
    samplerate = int(samplerate_in) if samplerate_in.strip() else default_samplerate

    # Bit depth
    supported_bitdepths = [16, 24, 32]
    default_bitdepth = 24
    print(f"\nSupported bit depths: {supported_bitdepths}")
    print(f"Current (default) bit depth: {default_bitdepth}")
    bitdepth_in = input(f"Enter bit depth [{default_bitdepth}]: ")
    bitdepth = int(bitdepth_in) if bitdepth_in.strip() else default_bitdepth

    # Load existing config if present
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f) or {}
    config['audio_interface'] = {
        'input_device_index': input_idx,
        'output_device_index': output_idx,
        'samplerate': samplerate,
        'bitdepth': bitdepth
    }
    if 'midi_interface' not in config:
        config['midi_interface'] = {'midi_input_name': None, 'midi_output_name': None}
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)
    print(f"Configuration saved to {CONFIG_FILE}")

if __name__ == "__main__":
	main()
