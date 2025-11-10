import argparse
import sys
import os
import yaml
import re

def note_name_to_midi(note_str):
    """
    Convert note name to MIDI number.
    Accepts: C-1 to G9, with optional # or b for sharps/flats.
    Examples: C4 = 60, A4 = 69, C#4 = 61, Db4 = 61
    
    Args:
        note_str: Note name (e.g., 'C4', 'A#3', 'Bb2') or MIDI number as string
        
    Returns:
        MIDI note number (0-127) or None if invalid
    """
    # If it's already a number, return it
    try:
        midi_num = int(note_str)
        if 0 <= midi_num <= 127:
            return midi_num
        return None
    except ValueError:
        pass
    
    # Parse note name
    note_str = note_str.strip().upper()
    match = re.match(r'^([A-G])([#B]?)(-?[0-9])$', note_str)
    if not match:
        return None
    
    note_name, accidental, octave = match.groups()
    octave = int(octave)
    
    # Note to semitone mapping (C=0, D=2, E=4, F=5, G=7, A=9, B=11)
    note_values = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    semitone = note_values[note_name]
    
    # Apply accidental
    if accidental == '#':
        semitone += 1
    elif accidental == 'B':  # Flat
        semitone -= 1
    
    # Calculate MIDI number (C-1 = 0, C0 = 12, C4 = 60)
    midi_num = (octave + 1) * 12 + semitone
    
    if 0 <= midi_num <= 127:
        return midi_num
    return None

def get_arg_parser():
    parser = argparse.ArgumentParser(
        description="AutosamplerT - Crossplatform hardware synth autosampler",
        add_help=False
    )
    
    # Main options
    main_group = parser.add_argument_group('main', 'Main options')
    main_group.add_argument('--config', type=str, default='conf/autosamplerT_config.yaml', 
                           help='Path to config YAML')
    main_group.add_argument('--script', type=str, 
                           help='Path to script YAML for batch sampling')
    main_group.add_argument('--setup', action='store_true', 
                           help='Run setup for audio and MIDI interfaces')
    main_group.add_argument('--help', nargs='?', const='main', default=None, 
                           choices=['main', 'audio', 'midi', 'sampling', 'postprocessing'], 
                           help='Show help for main, audio, midi, sampling, or postprocessing options')

    # Audio options
    audio = parser.add_argument_group('audio', 'Audio interface options')
    audio.add_argument('--input_device_index', type=int, metavar='N',
                      help='Audio input device index')
    audio.add_argument('--output_device_index', type=int, metavar='N',
                      help='Audio output device index')
    audio.add_argument('--samplerate', type=int, metavar='RATE',
                      help='Sample rate (e.g., 44100, 48000, 96000)')
    audio.add_argument('--bitdepth', type=int, metavar='BITS',
                      choices=[16, 24, 32], help='Bit depth (16, 24, or 32)')
    audio.add_argument('--mono_stereo', choices=['mono', 'stereo'],
                      help='Mono or stereo recording')
    audio.add_argument('--mono_channel', type=int, metavar='CH',
                      choices=[0, 1], help='Channel to use for mono recording (0=left, 1=right)')
    audio.add_argument('--gain', type=float, metavar='GAIN',
                      help='Input gain (0.0 to 2.0)')
    audio.add_argument('--latency_compensation', type=float, metavar='MS',
                      help='Latency compensation in milliseconds')
    audio.add_argument('--audio_inputs', type=int, metavar='N',
                      choices=[1, 2, 4, 8], help='Number of audio input channels')
    audio.add_argument('--debug', action='store_true',
                      help='Enable debug mode for audio')

    # MIDI options
    midi = parser.add_argument_group('midi', 'MIDI interface options')
    midi.add_argument('--midi_input_name', type=str, metavar='NAME',
                     help='MIDI input device name')
    midi.add_argument('--midi_output_name', type=str, metavar='NAME',
                     help='MIDI output device name')
    midi.add_argument('--midi_channels', type=int, nargs='+', metavar='CH',
                     help='MIDI channels (space-separated list)')
    midi.add_argument('--sysex_messages', type=str, nargs='+', metavar='MSG',
                     help='SysEx messages (space-separated hex strings)')
    midi.add_argument('--program_change', type=int, metavar='PC',
                     help='Program change number (0-127)')
    midi.add_argument('--cc_messages', type=str, metavar='CC_LIST',
                     help='7-bit CC messages (e.g., "7,127;10,64" for CC7=127, CC10=64)')
    midi.add_argument('--cc14_messages', type=str, metavar='CC14_LIST',
                     help='14-bit CC messages (e.g., "1,8192;11,16383" for CC1=8192, CC11=16383)')
    midi.add_argument('--note_range_start', type=str, metavar='NOTE',
                     help='Starting note (MIDI number 0-127 or note name like C2, A#4)')
    midi.add_argument('--note_range_end', type=str, metavar='NOTE',
                     help='Ending note (MIDI number 0-127 or note name like C7, G#6)')
    midi.add_argument('--note_range_interval', type=int, metavar='N',
                     help='Interval between notes (1=chromatic, 12=octaves)')
    midi.add_argument('--velocity_layers', type=int, metavar='N',
                     help='Number of velocity layers')
    midi.add_argument('--velocity_minimum', type=int, metavar='N',
                     help='Minimum velocity value (default: 1, range: 1-127)')
    midi.add_argument('--velocity_layers_split', type=str, metavar='SPLITS',
                     help='Comma-separated velocity split points (e.g., "40,100,120,127" for 4 layers)')
    midi.add_argument('--roundrobin_layers', type=int, metavar='N',
                     help='Number of round-robin layers')
    midi.add_argument('--midi_latency_adjust', type=float, metavar='MS',
                     help='MIDI latency adjustment in milliseconds')

    # Sampling options
    sampling = parser.add_argument_group('sampling', 'Sampling options')
    sampling.add_argument('--hold_time', type=float, metavar='SEC',
                         help='Note hold time in seconds')
    sampling.add_argument('--release_time', type=float, metavar='SEC',
                         help='Release time in seconds')
    sampling.add_argument('--pause_time', type=float, metavar='SEC',
                         help='Pause between samples in seconds')
    sampling.add_argument('--sample_name', type=str, metavar='NAME',
                         help='Sample name template')
    sampling.add_argument('--multisample_name', type=str, metavar='NAME',
                         help='Multisample name')
    sampling.add_argument('--test_mode', action='store_true',
                         help='Run in test mode (no recording)')
    sampling.add_argument('--script_mode', action='store_true',
                         help='Run in script/batch mode')
    sampling.add_argument('--output_format', type=str, metavar='FMT',
                         choices=['wav', 'sfz'], help='Output format (wav, sfz)')
    sampling.add_argument('--output_folder', type=str, metavar='PATH',
                         help='Output folder path')
    sampling.add_argument('--lowest_note', type=int, metavar='NOTE',
                         help='Lowest MIDI note for SFZ key mapping (0-127, default: 0)')
    sampling.add_argument('--highest_note', type=int, metavar='NOTE',
                         help='Highest MIDI note for SFZ key mapping (0-127, default: 127)')

    # Post-processing options
    postprocessing = parser.add_argument_group('postprocessing', 'Post-processing options (process existing samples)')
    postprocessing.add_argument('--process', type=str, metavar='NAME',
                               help='Process existing multisample by name (looks in output folder)')
    postprocessing.add_argument('--process_folder', type=str, metavar='PATH',
                               help='Process samples in specified folder path')
    postprocessing.add_argument('--patch_normalize', action='store_true',
                               help='Normalize entire patch: all samples gain same amount to consistent peak level (maintains relative dynamics)')
    postprocessing.add_argument('--sample_normalize', action='store_true',
                               help='Normalize individual samples: each sample maximized independently (destroys relative dynamics, good for drums)')
    postprocessing.add_argument('--trim_silence', action='store_true',
                               help='Trim silence from start/end of samples')
    postprocessing.add_argument('--auto_loop', action='store_true',
                               help='Find and set loop points using autocorrelation with zero-crossing detection')
    postprocessing.add_argument('--loop_min_duration', type=str, metavar='DURATION',
                               help='Minimum loop duration: percentage (e.g., "55%%") or seconds (e.g., "8.25"). Default: 0.1')
    postprocessing.add_argument('--loop_start_time', type=float, metavar='SECONDS',
                               help='Fixed loop start time in seconds (optional)')
    postprocessing.add_argument('--loop_end_time', type=float, metavar='SECONDS',
                               help='Fixed loop end time in seconds (optional)')
    postprocessing.add_argument('--dc_offset_removal', action='store_true',
                               help='Remove DC offset from samples')
    postprocessing.add_argument('--crossfade_loop', type=float, metavar='MS',
                               help='Crossfade loop points with equal-power curve (milliseconds, requires --auto_loop)')
    postprocessing.add_argument('--convert_bitdepth', type=int, metavar='BITS',
                               choices=[16, 24, 32], help='Convert to different bit depth')
    postprocessing.add_argument('--dither', action='store_true',
                               help='Apply dithering when converting bit depth')
    postprocessing.add_argument('--backup', action='store_true',
                               help='Create backup before processing')

    return parser

def show_help(parser, section):
    """Show help for specific section or main help."""
    if section == 'main':
        # Show all help
        parser.print_help()
    else:
        # Find the specific group
        for group in parser._action_groups:
            if group.title == section:
                print(f"\n{group.title.upper()} OPTIONS:")
                print(f"{group.description}\n" if group.description else "")
                for action in group._group_actions:
                    opts = ', '.join(action.option_strings)
                    help_text = action.help or ''
                    if action.metavar:
                        opts += f' {action.metavar}'
                    print(f"  {opts:30} {help_text}")
                return
        print(f"Unknown help section: {section}")
        print("Available sections: main, audio, midi, sampling")

def main():
    parser = get_arg_parser()
    args, unknown = parser.parse_known_args()

    if args.help is not None:
        show_help(parser, args.help)
        sys.exit(0)

    # Load config
    config_path = args.config
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        sys.exit(1)
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Optionally load and merge script YAML
    if args.script:
        if not os.path.exists(args.script):
            print(f"Script file not found: {args.script}")
            sys.exit(1)
        with open(args.script, 'r') as f:
            script_config = yaml.safe_load(f)
        
        # Merge script config into main config (script overrides config file)
        if script_config:
            for section in ['audio_interface', 'midi_interface', 'sampling']:
                if section in script_config:
                    if section not in config:
                        config[section] = {}
                    config[section].update(script_config[section])
            
            # Special handling for note_range in midi_interface - convert note names to MIDI numbers
            if 'midi_interface' in script_config and 'note_range' in script_config['midi_interface']:
                note_range = script_config['midi_interface']['note_range']
                if isinstance(note_range, dict):
                    if 'start' in note_range:
                        start_midi = note_name_to_midi(str(note_range['start']))
                        if start_midi is not None:
                            config['midi_interface']['note_range']['start'] = start_midi
                        else:
                            print(f"Warning: Invalid start note '{note_range['start']}' in script")
                    if 'end' in note_range:
                        end_midi = note_name_to_midi(str(note_range['end']))
                        if end_midi is not None:
                            config['midi_interface']['note_range']['end'] = end_midi
                        else:
                            print(f"Warning: Invalid end note '{note_range['end']}' in script")

    # Merge CLI args into config (CLI args override everything)
    def update_config_from_args(cfg, args_dict, section):
        for k, v in args_dict.items():
            if v is not None:
                if section not in cfg:
                    cfg[section] = {}
                cfg[section][k] = v

    # Handle boolean arguments that might be None (not set)
    def get_arg_if_set(args, name):
        val = getattr(args, name, None)
        return val if val is not None else None

    update_config_from_args(config, {
        'input_device_index': args.input_device_index,
        'output_device_index': args.output_device_index,
        'samplerate': args.samplerate,
        'bitdepth': args.bitdepth,
        'mono_stereo': args.mono_stereo,
        'mono_channel': args.mono_channel,
        'gain': args.gain,
        'latency_compensation': args.latency_compensation,
        'patch_normalize': get_arg_if_set(args, 'patch_normalize'),
        'sample_normalize': get_arg_if_set(args, 'sample_normalize'),
        'silence_detection': get_arg_if_set(args, 'silence_detection'),
        'audio_inputs': args.audio_inputs,
        'debug': args.debug if args.debug else None
    }, 'audio_interface')
    
    # Build note_range dict from individual arguments
    note_range_dict = None
    if args.note_range_start is not None or args.note_range_end is not None or args.note_range_interval is not None:
        note_range_dict = {}
        if args.note_range_start is not None:
            start_midi = note_name_to_midi(args.note_range_start)
            if start_midi is None:
                print(f"Error: Invalid start note '{args.note_range_start}'")
                sys.exit(1)
            note_range_dict['start'] = start_midi
        if args.note_range_end is not None:
            end_midi = note_name_to_midi(args.note_range_end)
            if end_midi is None:
                print(f"Error: Invalid end note '{args.note_range_end}'")
                sys.exit(1)
            note_range_dict['end'] = end_midi
        if args.note_range_interval is not None:
            note_range_dict['interval'] = args.note_range_interval
    
    # Parse and validate velocity_layers_split if provided
    velocity_splits = None
    if args.velocity_layers_split is not None:
        try:
            velocity_splits = [int(v.strip()) for v in args.velocity_layers_split.split(',')]
            
            # Validate: must match velocity_layers - 1 (splits are boundaries between layers)
            expected_splits = args.velocity_layers - 1 if args.velocity_layers is not None else len(velocity_splits) + 1
            if args.velocity_layers is not None and len(velocity_splits) != expected_splits:
                print(f"Error: velocity_layers_split count ({len(velocity_splits)}) must be velocity_layers - 1")
                print(f"  For {args.velocity_layers} layers, you need {expected_splits} split points")
                print(f"  Split points provided: {velocity_splits}")
                sys.exit(1)
            
            # Validate: must be ascending
            if velocity_splits != sorted(velocity_splits):
                print(f"Error: velocity_layers_split values must be in ascending order")
                print(f"  Provided: {velocity_splits}")
                print(f"  Expected: {sorted(velocity_splits)}")
                sys.exit(1)
            
            # Validate: must be in valid range
            velocity_min = args.velocity_minimum if args.velocity_minimum is not None else 1
            for v in velocity_splits:
                if v < velocity_min or v > 127:
                    print(f"Error: velocity_layers_split values must be between {velocity_min} and 127")
                    print(f"  Invalid value: {v}")
                    sys.exit(1)
                    
        except ValueError as e:
            print(f"Error: Invalid velocity_layers_split format: '{args.velocity_layers_split}'")
            print(f"  Expected comma-separated integers, e.g., '40,100,120,127'")
            sys.exit(1)
    
    update_config_from_args(config, {
        'midi_input_name': args.midi_input_name,
        'midi_output_name': args.midi_output_name,
        'midi_channels': args.midi_channels,
        'sysex_messages': args.sysex_messages,
        'program_change': args.program_change,
        'cc_messages': args.cc_messages,
        'cc14_messages': args.cc14_messages,
        'note_range': note_range_dict,
        'velocity_minimum': args.velocity_minimum,
        'velocity_layers_split': velocity_splits,
        'midi_latency_adjust': args.midi_latency_adjust
    }, 'midi_interface')
    
    update_config_from_args(config, {
        'hold_time': args.hold_time,
        'release_time': args.release_time,
        'pause_time': args.pause_time,
        'sample_name': args.sample_name,
        'multisample_name': args.multisample_name,
        'velocity_layers': args.velocity_layers,
        'roundrobin_layers': args.roundrobin_layers,
        'auto_looping': get_arg_if_set(args, 'auto_looping'),
        'wav_meta': get_arg_if_set(args, 'wav_meta'),
        'test_mode': args.test_mode if args.test_mode else None,
        'script_mode': args.script_mode if args.script_mode else None,
        'output_format': args.output_format,
        'output_folder': args.output_folder,
        'lowest_note': args.lowest_note,
        'highest_note': args.highest_note
    }, 'sampling')

    # Setup mode
    if args.setup:
        print("Launching audio and MIDI setup...")
        os.system(f"{sys.executable} src/set_audio_config.py")
        os.system(f"{sys.executable} src/set_midi_config.py")
        print("Setup complete.")
        sys.exit(0)

    # Postprocessing mode
    if args.process or args.process_folder:
        print("=== AutosamplerT - Postprocessing ===")
        
        try:
            from src.postprocess import PostProcessor
            from pathlib import Path
            
            # Create postprocessor
            processor = PostProcessor(backup=args.backup)
            
            # Get sample paths
            sample_paths = []
            
            if args.process_folder:
                # Process specific folder
                folder = Path(args.process_folder)
                if not folder.exists():
                    print(f"Error: Folder not found: {folder}")
                    sys.exit(1)
                sample_paths = list(folder.glob("*.wav"))
                print(f"Processing folder: {folder}")
            elif args.process:
                # Process multisample by name
                multisample_folder = Path(config.get('sampling', {}).get('output_folder', './output')) / args.process
                samples_folder = multisample_folder / 'samples'
                
                if not samples_folder.exists():
                    print(f"Error: Multisample not found: {args.process}")
                    print(f"Expected folder: {samples_folder}")
                    sys.exit(1)
                
                sample_paths = list(samples_folder.glob("*.wav"))
                print(f"Processing multisample: {args.process}")
            
            if not sample_paths:
                print("Error: No WAV files found to process")
                sys.exit(1)
            
            print(f"Found {len(sample_paths)} samples")
            
            # Build operations dictionary from arguments
            operations = {
                'patch_normalize': args.patch_normalize,
                'sample_normalize': args.sample_normalize,
                'trim_silence': args.trim_silence,
                'auto_loop': args.auto_loop,
                'loop_min_duration': args.loop_min_duration if args.loop_min_duration else "0.1",
                'loop_start_time': args.loop_start_time,
                'loop_end_time': args.loop_end_time,
                'crossfade_loop': args.crossfade_loop,
                'dc_offset_removal': args.dc_offset_removal,
                'convert_bitdepth': args.convert_bitdepth,
                'dither': args.dither,
                'update_note_metadata': True  # Always update metadata from filename
            }
            
            # Process samples
            processor.process_samples([str(p) for p in sample_paths], operations)
            
            print("\nPostprocessing completed successfully!")
            sys.exit(0)
            
        except ImportError as e:
            print(f"Error: Missing dependencies - {e}")
            print("Please install required packages: numpy, scipy")
            sys.exit(1)
        except Exception as e:
            print(f"Error during postprocessing: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    # Run sampling
    print("=== AutosamplerT ===")
    print(f"Config: {config_path}")
    if args.script:
        print(f"Script: {args.script}")
    
    # Import and run sampler
    try:
        from src.sampler import AutoSampler
        
        # Create sampler instance
        sampler = AutoSampler(config)
        
        # Run sampling workflow
        success = sampler.run()
        
        if success:
            print("\nSampling completed successfully!")
            print(f"Output folder: {sampler.output_folder}")
        else:
            print("\nSampling failed - check logs for details")
            sys.exit(1)
    except ImportError as e:
        print(f"Error: Missing dependencies - {e}")
        print("Please install required packages: numpy, scipy")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
