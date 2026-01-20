#!/usr/bin/env python3
"""
Generate extended Prophet programs with 6 round-robin layers and 7 second sampling.
"""

import os
import yaml
from pathlib import Path

def create_extended_prophet_programs():
    """Create extended Prophet program configurations."""
    
    source_dir = Path("conf/prophet_programs")
    target_dir = Path("conf/prophet_programs_extended")
    
    # Template for extended configuration
    template = {
        "name": "",
        "description": "",
        "output": {
            "multisample_name": ""
        },
        "audio": {
            "samplerate": 44100,
            "bitdepth": 24,
            "mono_stereo": "mono"
        },
        "midi_interface": {
            "output_port_name": "Prophet 6",
            "program_change": 0
        },
        "sampling": {
            "note_range_start": 36,
            "note_range_end": 96, 
            "note_range_interval": 5,
            "velocity_layers": 1,
            "roundrobin_layers": 6,  # EXTENDED: 6 RR layers
            "hold_time": 7.0,        # EXTENDED: 7 seconds sampling
            "release_time": 2.0,
            "pause_time": 2.0
        },
        "postprocessing": {
            "auto_loop": True,
            "loop_crossfade_percent": 10,
            "trim_silence": True,
            "silence_detection": "auto",
            "silence_threshold": -60.0
        },
        "export": {
            "formats": ["qpat", "waldorf_map"],
            "qpat": {
                "location": 2,
                "optimize_audio": True
            },
            "waldorf_map": {
                "location": 2
            }
        }
    }
    
    print(f"Creating extended Prophet programs (6 RR layers, 7s sampling)...")
    
    # Generate all 100 programs
    for program_num in range(100):
        # Update template for this program
        config = template.copy()
        config["name"] = f"Prophet Program {program_num} Extended"
        config["description"] = f"Prophet 6 Program {program_num} - Every 5 semitones, 6 RR layers, 7s sampling"
        config["output"]["multisample_name"] = f"Prophet_Program_{program_num}_Extended"
        config["midi_interface"]["program_change"] = program_num
        
        # Write to file
        filename = f"prophet_program_{program_num}_extended.yaml"
        filepath = target_dir / filename
        
        with open(filepath, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)
        
        if program_num % 10 == 0:
            print(f"  Created programs 0-{program_num}")
    
    print(f"✅ Created 100 extended Prophet programs in {target_dir}")
    print("Key changes:")
    print("  - Round-robin layers: 3 → 6")
    print("  - Hold time: 4.0s → 7.0s") 
    print("  - Total samples per program: 39 → 78 (13 notes × 6 RR)")
    print("  - Estimated time per program: ~12 minutes")

if __name__ == "__main__":
    create_extended_prophet_programs()