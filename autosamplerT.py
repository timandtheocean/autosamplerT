import os
# Enable ASIO support in sounddevice (must be set before importing sounddevice)
os.environ["SD_ENABLE_ASIO"] = "1"

import argparse
import sys
import yaml
import re
from typing import Optional

def note_name_to_midi(note_str: str) -> Optional[int]:
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

def get_arg_parser() -> argparse.ArgumentParser:
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
    main_group.add_argument('--script-folder', type=str, 
                           help='Path to folder containing multiple YAML scripts to process sequentially')
    # Setup can target specific subsystems: --setup audio | midi | all (default: all if no value provided)
    main_group.add_argument('--setup', nargs='?', const='all', choices=['audio','midi','all'],
                           help='Run setup for interfaces: audio, midi, or all (default: all)')
    main_group.add_argument('--export_only', action='store_true',
                           help='Export existing SFZ to other formats without sampling (requires --multisample_name or --script)')
    main_group.add_argument('--help', nargs='?', const='main', default=None, 
                           choices=['main', 'audio', 'midi', 'sampling', 'postprocessing', 'examples'], 
                           help='Show help for main, audio, midi, sampling, postprocessing, or examples')
    main_group.add_argument('--batch', action='store_true',
                           help=argparse.SUPPRESS)  # Hidden flag for internal batch processing
    main_group.add_argument('--wavetable', action='store_true',
                           help='Create wavetables by sampling parameter sweeps')

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
    # Note: --channel_offset is set via --setup audio, not as CLI argument
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
    midi.add_argument('--sysex_messages', type=str, metavar='MSG',
                     help='SysEx messages (semicolon-separated, without F0/F7). Example: "43 10 7F 1C 00;41 10 00 20 12"')
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
    sampling.add_argument('--output_format', type=str, metavar='FMT',
                         choices=['wav', 'sfz'], help='Output format (wav, sfz)')
    sampling.add_argument('--output_folder', type=str, metavar='PATH',
                         help='Output folder path')
    sampling.add_argument('--lowest_note', type=int, metavar='NOTE',
                         help='Lowest MIDI note for SFZ key mapping (0-127, default: 0)')
    sampling.add_argument('--highest_note', type=int, metavar='NOTE',
                         help='Highest MIDI note for SFZ key mapping (0-127, default: 127)')

    # Interactive sampling options
    interactive = parser.add_argument_group('interactive', 'Interactive sampling options')
    interactive.add_argument('--interactive_every', type=int, metavar='N',
                            help='Pause every N notes for user intervention (e.g., loading samples into hardware sampler)')
    interactive.add_argument('--interactive_continue', type=float, metavar='SEC',
                            help='Auto-resume after N seconds (0=wait for keypress, default: 0)')
    interactive.add_argument('--interactive_prompt', type=str, metavar='MSG',
                            help='Custom message to display during pause')

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
                               help='Trim silence from start/end of samples (postprocessing only - not applied during recording)')
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
    postprocessing.add_argument('--convert_bitdepth', type=int, metavar='BITS',
                               choices=[16, 24, 32], help='Convert to different bit depth')
    postprocessing.add_argument('--dither', action='store_true',
                               help='Apply dithering when converting bit depth')
    postprocessing.add_argument('--backup', action='store_true',
                               help='Create backup before processing')
    
    # Export format options
    postprocessing.add_argument('--export_formats', type=str, metavar='FORMATS',
                               help='Export to additional sampler formats: qpat,waldorf_map,ableton,exs,sxt (comma-separated)')
    postprocessing.add_argument('--export_location', type=int, metavar='LOC',
                               choices=[2, 3, 4], default=2,
                               help='Waldorf sample location: 2=SD card (default), 3=internal, 4=USB')
    postprocessing.add_argument('--export_loop_mode', type=int, metavar='MODE',
                               choices=[0, 1, 2], default=1,
                               help='Loop mode: 0=off, 1=forward (default), 2=ping-pong')
    postprocessing.add_argument('--export_loop_crossfade', type=float, metavar='MS',
                               default=10.0,
                               help='Loop crossfade time in milliseconds (default: 10.0ms)')
    postprocessing.add_argument('--export_optimize_audio', action='store_true',
                               help='Convert samples to 44.1kHz 32-bit float for Waldorf QPAT')

    return parser

def show_help(parser: argparse.ArgumentParser, section: str) -> None:
    """Show help for specific section or main help."""
    if section == 'main':
        # Show custom main help with usage examples
        print("\nAutosamplerT - Crossplatform hardware synth autosampler\n")
        print("USAGE:")
        print("  python autosamplerT.py [OPTIONS]\n")
        print("COMMON WORKFLOWS:\n")
        print("  First-time setup:")
        print("    python autosamplerT.py --setup all\n")
        print("  Quick sampling:")
        print("    python autosamplerT.py --note_range_start C3 --note_range_end C5\n")
        print("  Script-based sampling:")
        print("    python autosamplerT.py --script conf/my_script.yaml\n")
        print("  Test without recording:")
        print("    python autosamplerT.py --test_mode --note_range_start C4 --note_range_end E4\n")
        print("  Post-process samples:")
        print("    python autosamplerT.py --process MySynth --patch_normalize --trim_silence\n")
        print("HELP TOPICS:")
        print("  python autosamplerT.py --help examples       Show practical sampling examples")
        print("  python autosamplerT.py --help audio          Show audio interface options")
        print("  python autosamplerT.py --help midi           Show MIDI interface and control options")
        print("  python autosamplerT.py --help sampling       Show sampling configuration options")
        print("  python autosamplerT.py --help postprocessing Show post-processing options\n")
        print("MAIN OPTIONS:")
        for group in parser._action_groups:
            if group.title == 'main':
                for action in group._group_actions:
                    if action.dest == 'help':
                        continue  # Skip --help itself since we're showing custom help
                    opts = ', '.join(action.option_strings)
                    help_text = action.help or ''
                    if action.metavar:
                        opts += f' {action.metavar}'
                    print(f"  {opts:30} {help_text}")
        print("\nFor complete documentation, see: doc/DOCUMENTATION.md")
        print("For quick start guide, see: doc/QUICKSTART.md\n")
    elif section == 'examples':
        # Show practical examples
        print("\nAutosamplerT - Practical Examples\n")
        
        print("1. SAMPLE 2 NOTES PER OCTAVE (whole keyboard)")
        print("   Sample every major 6th interval (9 semitones):")
        print("   python autosamplerT.py --note_range_start C2 --note_range_end C7 --note_range_interval 9\n")
        
        print("2. SAMPLE 1 NOTE FOR WHOLE KEYBOARD")
        print("   Single sample, no pitch mapping (good for drones/pads):")
        print("   python autosamplerT.py --note_range_start C4 --note_range_end C4 --note_range_interval 1\n")
        
        print("3. EVERY 5TH (perfect 4th intervals)")
        print("   Sample every 5 semitones across the keyboard:")
        print("   python autosamplerT.py --note_range_start C2 --note_range_end C7 --note_range_interval 5\n")
        
        print("4. ROUND-ROBIN LAYERS")
        print("   3 round-robin variations for more realistic playback:")
        print("   python autosamplerT.py --note_range_start C3 --note_range_end C5 --roundrobin_layers 3\n")
        
        print("5. VELOCITY LAYERS")
        print("   4 velocity layers with automatic logarithmic distribution:")
        print("   python autosamplerT.py --note_range_start C3 --note_range_end C5 --velocity_layers 4\n")
        
        print("6. VELOCITY + ROUND-ROBIN COMBINED")
        print("   3 velocity layers × 2 round-robin = realistic and expressive:")
        print("   python autosamplerT.py --note_range_start C3 --note_range_end C5 \\")
        print("     --velocity_layers 3 --roundrobin_layers 2\n")
        
        print("7. RUN A SCRIPT")
        print("   Use YAML script for complex configurations:")
        print("   python autosamplerT.py --script conf/my_synth.yaml\n")
        
        print("8. CUSTOM VELOCITY SPLITS")
        print("   Precise control over velocity breakpoints:")
        print("   python autosamplerT.py --note_range_start C3 --note_range_end C5 \\")
        print("     --velocity_layers 3 --velocity_layers_split 40,80\n")
        
        print("9. SKIP SOFT SAMPLES")
        print("   Start from higher velocity (skip noisy soft samples):")
        print("   python autosamplerT.py --note_range_start C3 --note_range_end C5 \\")
        print("     --velocity_layers 3 --velocity_minimum 50\n")
        
        print("10. WITH MIDI CONTROL")
        print("    Send CC and program change before sampling:")
        print("    python autosamplerT.py --note_range_start C3 --note_range_end C5 \\")
        print("      --program_change 10 --cc_messages \"7,127;74,64\"\n")
        
        print("11. AUTO-LOOPING (Post-Processing)")
        print("    Find loop points in existing samples:")
        print("    python autosamplerT.py --process MySynth --auto_loop\n")
        
        print("TIP: Add --test_mode to any example to verify without recording")
        print("     Example: python autosamplerT.py --test_mode --note_range_start C3 --note_range_end C5\n")
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
                print()  # Add blank line at end
                return
        print(f"Unknown help section: {section}")
        print("Available sections: main, audio, midi, sampling, postprocessing, examples")

def main() -> None:
    parser = get_arg_parser()
    args, unknown = parser.parse_known_args()

    if args.help is not None:
        show_help(parser, args.help)
        sys.exit(0)

    # Handle wavetable mode
    if args.wavetable:
        from src.wavetable_mode import run_wavetable_mode
        success = run_wavetable_mode(args)
        sys.exit(0 if success else 1)

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
            for section in ['audio_interface', 'midi_interface', 'sampling', 'sampling_midi', 'interactive_sampling', 'output', 'audio', 'postprocessing', 'export']:
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
        # channel_offset is set via --setup audio, not from CLI args
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
    
    # Parse sysex_messages - split by semicolon to support multiple messages
    sysex_list = None
    if args.sysex_messages is not None:
        # Split by semicolon: "msg1;msg2;msg3" -> ["msg1", "msg2", "msg3"]
        sysex_list = [msg.strip() for msg in args.sysex_messages.split(';') if msg.strip()]
    
    # Parse cc14_messages - convert from string to dict format
    cc14_dict = None
    if args.cc14_messages is not None:
        from src.sampler_midicontrol import parse_cc14_messages
        cc14_dict = parse_cc14_messages(args.cc14_messages)
    
    update_config_from_args(config, {
        'midi_input_name': args.midi_input_name,
        'midi_output_name': args.midi_output_name,
        'midi_channels': args.midi_channels,
        'sysex_messages': sysex_list,
        'program_change': args.program_change,
        'cc_messages': args.cc_messages,
        'cc14_messages': cc14_dict,
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
        'output_format': args.output_format,
        'output_folder': args.output_folder,
        'lowest_note': args.lowest_note,
        'highest_note': args.highest_note
    }, 'sampling')
    
    # Interactive sampling arguments
    if args.interactive_every is not None or args.interactive_continue is not None or args.interactive_prompt is not None:
        update_config_from_args(config, {
            'every': args.interactive_every,
            'continue': args.interactive_continue,
            'prompt': args.interactive_prompt
        }, 'interactive_sampling')
    
    # Merge export formats from config if not specified in CLI
    if not args.export_formats and 'export' in config and 'formats' in config['export']:
        formats_list = config['export']['formats']
        if isinstance(formats_list, list):
            args.export_formats = ','.join(formats_list)
    
    # Merge export location from config if not specified in CLI
    if 'export' in config:
        if 'qpat' in config['export'] and 'location' in config['export']['qpat']:
            if args.export_location == 2:  # Only override if it's the default
                args.export_location = config['export']['qpat']['location']
        
        # Load crossfade setting from config
        if 'loop_crossfade_ms' in config['export']:
            if not hasattr(args, 'export_loop_crossfade') or args.export_loop_crossfade == 10.0:  # Default value
                args.export_loop_crossfade = config['export']['loop_crossfade_ms']

    # Setup mode
    if args.setup:
        target = args.setup  # 'audio', 'midi', or 'all'
        if target == 'all':
            print("Launching AUDIO + MIDI setup...")
            os.system(f"{sys.executable} src/set_audio_config.py")
            os.system(f"{sys.executable} src/set_midi_config.py")
        elif target == 'audio':
            print("Launching AUDIO setup...")
            os.system(f"{sys.executable} src/set_audio_config.py")
        elif target == 'midi':
            print("Launching MIDI setup...")
            os.system(f"{sys.executable} src/set_midi_config.py")
        print("Setup complete.")
        sys.exit(0)

    # Script folder mode - process all YAML files in folder
    if args.script_folder:
        from pathlib import Path
        import glob
        
        script_folder = Path(args.script_folder)
        if not script_folder.exists():
            print(f"[ERROR] Script folder not found: {script_folder}")
            sys.exit(1)
        
        if not script_folder.is_dir():
            print(f"[ERROR] Path is not a directory: {script_folder}")
            sys.exit(1)
        
        # Find all YAML files
        yaml_files = sorted(script_folder.glob('*.yaml')) + sorted(script_folder.glob('*.yml'))
        
        if not yaml_files:
            print(f"[ERROR] No YAML files found in: {script_folder}")
            sys.exit(1)
        
        print(f"=== AutosamplerT - Batch Processing ===")
        print(f"Found {len(yaml_files)} YAML file(s) in: {script_folder}\n")
                # Show pre-batch monitoring if not in batch mode
        if not args.batch:
            print("=" * 70)
            print("PRE-BATCH AUDIO MONITORING")
            print("=" * 70)
            print("Before starting batch processing, verify your audio setup.")
            print("This will be used for all scripts in the folder.\n")
            
            try:
                from src.realtime_monitor import show_pre_sampling_monitor
                
                # Use basic audio settings for monitoring
                proceed = show_pre_sampling_monitor(
                    device_index=None,  # Use default or from config
                    sample_rate=44100,
                    channels=2,
                    channel_offset=0,
                    title="Pre-Batch Audio Monitor"
                )
                
                if not proceed:
                    print("Batch processing cancelled by user")
                    sys.exit(0)
                    
                print("\nProceeding with batch processing...\n")
                
            except ImportError:
                print("[WARNING] Audio monitoring not available")
            except Exception as e:
                print(f"[WARNING] Could not start audio monitoring: {e}")
                print("Continuing with batch processing...\n")
        
        for i, yaml_file in enumerate(yaml_files, 1):
            print(f"\n{'='*80}")
            print(f"Processing {i}/{len(yaml_files)}: {yaml_file.name}")
            print(f"{'='*80}\n")
            
            # Build command: python autosamplerT.py --script <yaml_file> --batch
            # Preserve key arguments from current invocation
            cmd = [sys.executable, __file__, '--script', str(yaml_file), '--batch']
            
            # Add output folder if specified
            if args.output_folder:
                cmd.extend(['--output_folder', args.output_folder])
            
            # Add export formats if specified
            if args.export_formats:
                cmd.extend(['--export_formats', args.export_formats])
            
            # Add export location if specified and not default
            if args.export_location != 2:
                cmd.extend(['--export_location', str(args.export_location)])
            
            # Run the script
            import subprocess
            result = subprocess.run(cmd)
            
            if result.returncode != 0:
                print(f"\n[WARNING] Script {yaml_file.name} failed with return code {result.returncode}")
                response = input("Continue with remaining scripts? (y/n): ")
                if response.lower() != 'y':
                    print("Batch processing cancelled.")
                    sys.exit(1)
            else:
                print(f"\n[SUCCESS] Script {yaml_file.name} completed successfully")
        
        print(f"\n{'='*80}")
        print(f"Batch processing complete: {len(yaml_files)} file(s) processed")
        print(f"{'='*80}\n")
        sys.exit(0)

    # Export-only mode (convert existing SFZ to other formats)
    if args.export_only:
        print("=== AutosamplerT - Export Only Mode ===\n")
        
        if not args.export_formats:
            print("[ERROR] --export_formats is required for export-only mode")
            print("Example: --export_only --export_formats qpat,waldorf_map --multisample_name MySynth")
            sys.exit(1)
        
        # Determine multisample name and output folder
        multisample_name = args.multisample_name
        output_folder = args.output_folder or config.get('sampling', {}).get('output_folder', './output')
        
        # If using script mode, get name from script config
        if args.script and not multisample_name:
            multisample_name = config.get('sampling', {}).get('multisample_name')
        
        if not multisample_name:
            print("[ERROR] --multisample_name is required for export-only mode")
            print("Or use --script with a script file that specifies multisample_name")
            sys.exit(1)
        
        print(f"Multisample: {multisample_name}")
        print(f"Output folder: {output_folder}")
        print(f"Export formats: {args.export_formats}\n")
        
        _export_multisample_formats(args, config, multisample_name, output_folder)
        
        print("\n=== Export Complete ===")
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
                'dc_offset_removal': args.dc_offset_removal,
                'convert_bitdepth': args.convert_bitdepth,
                'dither': args.dither,
                'update_note_metadata': True  # Always update metadata from filename
            }
            
            # Process samples
            processor.process_samples([str(p) for p in sample_paths], operations)
            
            # Export to additional formats if requested
            if args.export_formats and args.process:
                _export_multisample_formats(args, config, args.process, 
                                           config.get('sampling', {}).get('output_folder', './output'))
            
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
        sampler = AutoSampler(config, batch_mode=args.batch)
        
        # Run sampling workflow
        success = sampler.run()
        
        if success:
            print("\nSampling completed successfully!")
            print(f"Output folder: {sampler.output_folder}")
            
            # Copy script file to multisample folder if script was used
            if args.script:
                import shutil
                multisample_folder = str(sampler.multisample_folder)
                script_dest = os.path.join(multisample_folder, os.path.basename(args.script))
                try:
                    shutil.copy2(args.script, script_dest)
                    print(f"Script copied to: {script_dest}")
                except Exception as e:
                    print(f"Warning: Could not copy script file: {e}")
            
            # Export to additional formats if requested
            if args.export_formats:
                multisample_name = sampler.multisample_name
                output_folder = sampler.base_output_folder
                _export_multisample_formats(args, config, multisample_name, output_folder)
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


def _export_multisample_formats(args, config, multisample_name, output_folder):
    """Export multisample to additional formats."""
    export_formats = [f.strip().lower() for f in args.export_formats.split(',')]
    
    # Find SFZ file
    multisample_folder = os.path.join(output_folder, multisample_name)
    sfz_file = os.path.join(multisample_folder, f'{multisample_name}.sfz')
    samples_folder = os.path.join(multisample_folder, 'samples')
    
    if not os.path.exists(sfz_file):
        print(f"[ERROR] SFZ file not found: {sfz_file}")
        return
    
    for fmt in export_formats:
        if fmt == 'qpat':
            print(f"\n[EXPORT] Converting to Waldorf QPAT format...")
            from src.export.export_qpat import export_to_qpat
            success = export_to_qpat(
                output_folder=multisample_folder,
                multisample_name=multisample_name,
                sfz_file=sfz_file,
                samples_folder=samples_folder,
                location=args.export_location,
                loop_mode=getattr(args, 'export_loop_mode', 1),
                optimize_audio=args.export_optimize_audio,
                crossfade_ms=getattr(args, 'export_loop_crossfade', 10.0)
            )
            if success:
                print(f"[SUCCESS] Exported to QPAT: {multisample_folder}/{multisample_name}.qpat")
            else:
                print(f"[ERROR] Failed to export QPAT")
        
        elif fmt == 'waldorf_map':
            print(f"\n[EXPORT] Converting to Waldorf Sample Map format...")
            from src.export.export_waldorf_sample_map import export_to_waldorf_map
            success = export_to_waldorf_map(
                output_folder=multisample_folder,
                map_name=multisample_name,
                sfz_file=sfz_file,
                samples_folder=samples_folder,
                location=args.export_location,
                loop_mode=getattr(args, 'export_loop_mode', 1),
                crossfade_ms=getattr(args, 'export_loop_crossfade', 10.0)
            )
            if success:
                print(f"[SUCCESS] Exported to Waldorf Map: {multisample_folder}/{multisample_name}.map")
            else:
                print(f"[ERROR] Failed to export Waldorf Map")
        
        elif fmt == 'ableton':
            print(f"\n[EXPORT] Converting to Ableton Live Sampler format...")
            from src.export.export_ableton import export_to_ableton
            success = export_to_ableton(
                output_folder=multisample_folder,
                multisample_name=multisample_name,
                sfz_file=sfz_file,
                samples_folder=samples_folder,
                velocity_crossfade=getattr(args, 'ableton_velocity_crossfade', 0),
                key_crossfade=getattr(args, 'ableton_key_crossfade', 0)
            )
            if success:
                print(f"[SUCCESS] Exported to Ableton ADV: {multisample_folder}/{multisample_name}.adv")
            else:
                print(f"[ERROR] Failed to export Ableton ADV")
        
        elif fmt in ['exs', 'sxt']:
            print(f"[TODO] {fmt.upper()} export not yet implemented")
        else:
            print(f"[ERROR] Unknown export format: {fmt}")


if __name__ == "__main__":
    main()
