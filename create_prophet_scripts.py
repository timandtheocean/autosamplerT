#!/usr/bin/env python3
"""
Generate Prophet Program Scripts
===============================

Create 19 YAML scripts for Prophet 6 programs with optimized settings:
- Every 5 semitones (C2 to C7)  
- 2 round-robin layers
- Auto loop with 10% crossfade
- 4 second hold, 2 second release
- Program change 1-19
"""

import os
from pathlib import Path

def create_prophet_script(program_number):
    """Create a single prophet program script"""
    
    script_content = f'''name: "Prophet Program {program_number}"
description: "Prophet 6 Program {program_number} - Every 5 semitones, 2 RR layers"

# Output settings
output:
  multisample_name: "Prophet_Program_{program_number}"

# Audio settings
audio:
  samplerate: 44100
  bitdepth: 24
  mono_stereo: mono

# MIDI interface
midi_interface:
  output_port_name: "Prophet 6"
  program_change: {program_number}

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

# Export formats
export:
  formats:
    - qpat
    - waldorf_map  # Creates .map file for Waldorf
  qpat:
    location: 2  # SD card
    optimize_audio: true
  waldorf_map:
    location: 2  # SD card'''
    
    return script_content

def main():
    """Generate all 19 prophet program scripts"""
    
    # Create output directory
    output_dir = Path("conf/prophet_programs")
    output_dir.mkdir(exist_ok=True)
    
    print("CREATING PROPHET PROGRAM SCRIPTS")
    print("=" * 50)
    print("Settings:")
    print("  📝 Programs: 1-19")
    print("  🎹 Range: C2 to C7 (every 5 semitones)")
    print("  🔄 Round-robin: 2 layers")
    print("  ⏱️  Timing: 4s hold + 2s release")
    print("  🔁 Auto-loop: ON (10% crossfade)")
    print("  💾 Export: QPAT + Waldorf MAP")
    print()
    
    # Calculate sample count
    note_range = range(36, 97, 5)  # C2 to C7, every 5 semitones
    notes_per_program = len(list(note_range))
    samples_per_program = notes_per_program * 2  # 2 RR layers
    
    print(f"📊 Efficiency:")
    print(f"  🎵 Notes per program: {notes_per_program}")
    print(f"  📁 Samples per program: {samples_per_program}")
    print(f"  📈 Total samples (19 programs): {samples_per_program * 19}")
    print()
    
    # Generate scripts
    for program_num in range(1, 20):
        script_path = output_dir / f"prophet_program_{program_num}.yaml"
        script_content = create_prophet_script(program_num)
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        print(f"✅ Created: prophet_program_{program_num}.yaml")
    
    print()
    print("🎉 SUCCESS: All 19 prophet program scripts created!")
    print()
    print("📝 Usage:")
    print("  # Sample all programs (auto-accept):")
    print("  python autosamplerT.py --script-folder conf/prophet_programs --batch")
    print()
    print("  # Sample single program (auto-accept):")
    print("  python autosamplerT.py --script conf/prophet_programs/prophet_program_1.yaml --batch")
    print()
    print("🎹 Note mapping (every 5 semitones):")
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    for note_midi in range(36, 97, 5):
        octave = (note_midi // 12) - 1
        note_name = note_names[note_midi % 12]
        print(f"  📍 {note_name}{octave} (MIDI {note_midi})")

if __name__ == "__main__":
    main()