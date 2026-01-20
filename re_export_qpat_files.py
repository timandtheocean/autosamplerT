#!/usr/bin/env python3
"""
Re-export all QPAT files with corrected sample paths.

This script finds all existing multisamples and regenerates their QPAT files
using the fixed export code to correct the double 'samples' directory issue.
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from export.export_qpat import WaldorfQpatExporter

def re_export_all_qpat_files():
    """Re-export all QPAT files in the output directory."""
    
    output_dir = Path("output")
    if not output_dir.exists():
        print("Output directory not found!")
        return
    
    print("="*70)
    print("RE-EXPORTING ALL QPAT FILES")
    print("="*70)
    print(f"Scanning: {output_dir.absolute()}")
    print()
    
    # Find all multisample folders (contain .sfz files)
    multisample_folders = []
    for folder in output_dir.iterdir():
        if folder.is_dir():
            # Look for SFZ files in this folder
            sfz_files = list(folder.glob("*.sfz"))
            if sfz_files:
                multisample_folders.append((folder, sfz_files[0]))  # Use first SFZ file
    
    if not multisample_folders:
        print("No multisample folders with SFZ files found!")
        return
    
    print(f"Found {len(multisample_folders)} multisample folders")
    print()
    
    # Re-export each multisample
    exporter = WaldorfQpatExporter(location=2, optimize_audio=True)
    success_count = 0
    
    for folder, sfz_file in multisample_folders:
        multisample_name = folder.name
        samples_folder = folder / "samples"
        
        print(f"Processing: {multisample_name}")
        
        # Check if samples folder exists
        if not samples_folder.exists():
            print(f"  ❌ No samples folder found")
            continue
        
        # Check if SFZ file exists
        if not sfz_file.exists():
            print(f"  ❌ SFZ file not found: {sfz_file}")
            continue
        
        try:
            # Re-export QPAT file
            success = exporter.export(
                output_folder=str(folder),
                multisample_name=multisample_name,
                sfz_file=str(sfz_file),
                samples_folder=str(samples_folder)
            )
            
            if success:
                print(f"  ✅ QPAT file re-exported successfully")
                success_count += 1
            else:
                print(f"  ❌ QPAT export failed")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print()
    print("="*70)
    print(f"SUMMARY: Successfully re-exported {success_count}/{len(multisample_folders)} QPAT files")
    print("="*70)
    
    if success_count > 0:
        print("✅ QPAT files now have corrected sample paths!")
        print("Fixed format: \"2:samples/Prophet_Program_XX/filename.wav\"")
        print("(Removed extra /samples/ directory)")
    else:
        print("❌ No QPAT files were re-exported successfully")

if __name__ == "__main__":
    re_export_all_qpat_files()