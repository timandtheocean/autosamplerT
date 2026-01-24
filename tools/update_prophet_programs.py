#!/usr/bin/env python3
"""
Update all prophet_program exports with corrected Column 5 mapping.

This script re-exports MAP and QPAT files for all prophet_program_* folders
using the fixed Waldorf column mapping where Column 5 is gain (not tune).
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.append('.')

from src.export.export_waldorf_sample_map import WaldorfSampleMapExporter
from src.export.export_qpat import WaldorfQpatExporter

def update_prophet_programs():
    """Update all prophet_program_* folders with corrected exports."""
    
    output_dir = Path('output')
    prophet_programs = sorted([d for d in output_dir.iterdir() 
                              if d.is_dir() and d.name.startswith('prophet_program_')])
    
    if not prophet_programs:
        print("No prophet_program_* folders found in output/")
        return
    
    print(f"Found {len(prophet_programs)} prophet program folders:")
    for prog in prophet_programs:
        print(f"  - {prog.name}")
    
    print(f"\nUpdating exports with corrected Column 5 mapping...")
    
    updated_count = 0
    skipped_count = 0
    
    for prog_folder in prophet_programs:
        prog_name = prog_folder.name
        sfz_file = prog_folder / f'{prog_name}.sfz'
        samples_folder = prog_folder / 'samples'
        
        print(f"\nProcessing {prog_name}...")
        
        if not sfz_file.exists():
            print(f"  ❌ SKIP: No SFZ file found")
            skipped_count += 1
            continue
            
        if not samples_folder.exists():
            print(f"  ❌ SKIP: No samples folder found") 
            skipped_count += 1
            continue
        
        try:
            # Update MAP file with corrected Column 5
            map_exporter = WaldorfSampleMapExporter(location=4)  # USB location
            map_success = map_exporter.export(
                str(prog_folder), prog_name, str(sfz_file), str(samples_folder)
            )
            
            # Update QPAT file with corrected Column 5  
            qpat_exporter = WaldorfQpatExporter(location=4)  # USB location
            qpat_success = qpat_exporter.export(
                str(prog_folder), prog_name, str(sfz_file), str(samples_folder)
            )
            
            print(f"  ✅ MAP: {'SUCCESS' if map_success else 'FAILED'}")
            print(f"  ✅ QPAT: {'SUCCESS' if qpat_success else 'FAILED'}")
            
            if map_success and qpat_success:
                updated_count += 1
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            skipped_count += 1
    
    print(f"\n" + "="*50)
    print(f"SUMMARY:")
    print(f"✅ Updated: {updated_count} prophet programs")
    print(f"❌ Skipped: {skipped_count} prophet programs")  
    print(f"📊 Total: {len(prophet_programs)} found")
    
    if updated_count > 0:
        print(f"\n🎉 SUCCESS: Prophet programs updated with corrected Column 5!")
        print(f"   - Column 5 now outputs GAIN (linear from dB)")
        print(f"   - Location set to 4: (USB) for easy import")
        print(f"   - Files ready for Waldorf Quantum/Iridium")

if __name__ == "__main__":
    update_prophet_programs()