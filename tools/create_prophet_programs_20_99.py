#!/usr/bin/env python3
"""
Generate Prophet Program configurations for programs 20-99 in conf/prophet_programs/
Based on the existing Prophet Program 0 template
"""

import os
from pathlib import Path

def create_prophet_program_configs():
    """Create Prophet Program configs for programs 20-99 in conf/prophet_programs/"""
    
    # Template based on Prophet Program 0 from conf/prophet_programs/
    template = '''name: "Prophet Program {program_num}"
description: "Prophet 6 Program {program_num} - Every 5 semitones, 2 RR layers"

# Output settings
output:
  multisample_name: "Prophet_Program_{program_num}"

# Audio settings
audio:
  samplerate: 44100
  bitdepth: 24
  mono_stereo: mono

# MIDI interface
midi_interface:
  output_port_name: "Prophet 6"
  program_change: {program_num}

# Sampling configuration  
sampling:
  note_range_start: 36    # C2
  note_range_end: 96      # C7
  note_range_interval: 5  # Every 5 semitones
  velocity_layers: 1      # Single velocity
  roundrobin_layers: 2    # 2 round-robin layers
  hold_time: 4.0          # 4 seconds sampling
  release_time: 2.0       # 2 seconds release/pause
  pause_time: 2.0         # 2 seconds pause between samples

# Post-processing
postprocessing:
  auto_loop: true
  loop_crossfade_percent: 10  # 10% crossfade
  trim_silence: true
  silence_detection: auto     # "auto" (detect noise floor) or "manual" (use threshold)
  silence_threshold: -60.0    # Manual threshold in dB (used when silence_detection: manual)

# Export formats
export:
  formats:
    - qpat
    - waldorf_map  # Creates .map file for Waldorf
  qpat:
    location: 2  # SD card
    optimize_audio: true
  waldorf_map:
    location: 2  # SD card
'''

    config_dir = Path("conf/prophet_programs")
    created_count = 0
    
    # Create programs 20-99 (programs 0-19 already exist)
    for program_num in range(20, 100):
        config_file = config_dir / f"prophet_program_{program_num}.yaml"
        
        # Generate config content
        config_content = template.format(program_num=program_num)
        
        # Write config file
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print(f"Created: {config_file}")
        created_count += 1
    
    print(f"\nSUCCESS: Created {created_count} Prophet Program configurations")
    print(f"Programs 20-99 are now available in conf/prophet_programs/")
    print(f"Total Prophet Programs: 0-99 (100 programs)")

if __name__ == "__main__":
    create_prophet_program_configs()