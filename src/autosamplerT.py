import argparse
import sys
import os
import yaml

# Paths
SRC_DIR = os.path.dirname(__file__)
CONF_DIR = os.path.join(SRC_DIR, '../conf')
AUDIO_CONFIG = os.path.join(SRC_DIR, 'set_audio_config.py')
MIDI_CONFIG = os.path.join(SRC_DIR, 'set_midi_config.py')
CONFIG_FILE = os.path.join(CONF_DIR, 'autosamplerT_config.yaml')


def run_config_script(script_path):
    os.system(f'{sys.executable} {script_path}')


def read_yaml_script(script_path):
    with open(script_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='autosamplerT main program')
    parser.add_argument('--setup', choices=['audio', 'midi'], help='Run audio or midi setup')
    parser.add_argument('--script', type=str, help='Path to sampling script YAML')
    parser.add_argument('--input_device_index', type=int, help='Set audio input device index')
    parser.add_argument('--output_device_index', type=int, help='Set audio output device index')
    parser.add_argument('--samplerate', type=int, help='Set audio sample rate')
    parser.add_argument('--bitdepth', type=int, help='Set audio bit depth')
    parser.add_argument('--midi_input_name', type=str, help='Set MIDI input device name')
    parser.add_argument('--midi_output_name', type=str, help='Set MIDI output device name')
    parser.add_argument('--dummy', action='store_true', help='Dummy argument for sampling and other features')
    args = parser.parse_args()

    # Setup mode
    if args.setup == 'audio':
        run_config_script(AUDIO_CONFIG)
        return
    elif args.setup == 'midi':
        run_config_script(MIDI_CONFIG)
        return

    # Script mode
    if args.script:
        print(f'Reading sampling script: {args.script}')
        script_data = read_yaml_script(args.script)
        print('Script contents:', script_data)
        # Dummy: actual sampling logic to be implemented later
        print('Sampling logic not yet implemented.')
        return

    # Direct config via arguments
    if any([args.input_device_index, args.output_device_index, args.samplerate, args.bitdepth, args.midi_input_name, args.midi_output_name]):
        # Load config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        # Update audio config
        if 'audio_interface' not in config:
            config['audio_interface'] = {}
        if args.input_device_index is not None:
            config['audio_interface']['input_device_index'] = args.input_device_index
        if args.output_device_index is not None:
            config['audio_interface']['output_device_index'] = args.output_device_index
        if args.samplerate is not None:
            config['audio_interface']['samplerate'] = args.samplerate
        if args.bitdepth is not None:
            config['audio_interface']['bitdepth'] = args.bitdepth
        # Update midi config
        if 'midi_interface' not in config:
            config['midi_interface'] = {}
        if args.midi_input_name is not None:
            config['midi_interface']['midi_input_name'] = args.midi_input_name
        if args.midi_output_name is not None:
            config['midi_interface']['midi_output_name'] = args.midi_output_name
        # Save config
        with open(CONFIG_FILE, 'w') as f:
            yaml.dump(config, f)
        print('Configuration updated via arguments.')
        return

    # Dummy for sampling and other features
    if args.dummy:
        print('Dummy: Sampling and other features will be implemented later.')
        return

    parser.print_help()

if __name__ == '__main__':
    main()
