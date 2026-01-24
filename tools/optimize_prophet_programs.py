#!/usr/bin/env python3
"""
Optimize Prophet Programs - Reduce size by 30%

This script removes the 3rd round-robin layer (RR3) from all prophet programs,
reducing their size by approximately 33% while maintaining musical quality.

Strategy:
- Keep RR1 and RR2 (2 round-robin layers)  
- Remove all RR3 samples and SFZ entries
- Update MAP/QPAT exports with optimized structure
"""

import sys
import os
import shutil
from pathlib import Path

# Add src to path for imports
sys.path.append('.')

from src.export.export_waldorf_sample_map import WaldorfSampleMapExporter
from src.export.export_qpat import WaldorfQpatExporter

def optimize_prophet_program(program_folder: Path):
    """Optimize a single prophet program by removing RR3 layer."""
    
    program_name = program_folder.name
    samples_folder = program_folder / 'samples'
    sfz_file = program_folder / f'{program_name}.sfz'
    
    print(f"Optimizing {program_name}...")
    
    if not samples_folder.exists() or not sfz_file.exists():
        print(f"  ❌ SKIP: Missing samples folder or SFZ file")
        return False
    
    # Step 1: Remove RR3 sample files
    rr3_samples = list(samples_folder.glob('*_rr3.wav'))
    total_before = len(list(samples_folder.glob('*.wav')))
    
    print(f"  📁 Samples before: {total_before}")
    print(f"  🗑️  Removing RR3: {len(rr3_samples)} files")
    
    for sample in rr3_samples:
        try:
            sample.unlink()  # Delete the file
        except Exception as e:
            print(f"    ❌ Failed to delete {sample.name}: {e}")
    
    total_after = len(list(samples_folder.glob('*.wav')))
    reduction = ((total_before - total_after) / total_before) * 100
    print(f"  📁 Samples after: {total_after} ({reduction:.1f}% reduction)")
    
    # Step 2: Update SFZ file - remove RR3 entries
    try:
        with open(sfz_file, 'r', encoding='utf-8') as f:
            sfz_content = f.read()
        
        # Remove RR3 entries and update seq_length
        lines = sfz_content.split('\\n')
        new_lines = []
        skip_region = False
        
        for line in lines:
            # Update seq_length from 3 to 2
            if 'seq_length=3' in line:
                line = line.replace('seq_length=3', 'seq_length=2')
            
            # Skip RR3 regions
            if '<region>' in line:
                skip_region = False
            elif 'sample=' in line and '_rr3.wav' in line:
                skip_region = True
                continue
            
            if not skip_region:
                new_lines.append(line)
        
        # Write optimized SFZ
        with open(sfz_file, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(new_lines))
        
        print(f"  📝 SFZ updated: RR3 entries removed")
        
    except Exception as e:
        print(f"  ❌ SFZ update failed: {e}")
        return False
    
    # Step 3: Re-export MAP and QPAT with optimized structure
    try:
        # Update MAP file
        map_exporter = WaldorfSampleMapExporter(location=4)
        map_success = map_exporter.export(
            str(program_folder), program_name, str(sfz_file), str(samples_folder)
        )
        
        # Update QPAT file  
        qpat_exporter = WaldorfQpatExporter(location=4)
        qpat_success = qpat_exporter.export(
            str(program_folder), program_name, str(sfz_file), str(samples_folder)
        )
        
        print(f"  ✅ MAP export: {'SUCCESS' if map_success else 'FAILED'}")
        print(f"  ✅ QPAT export: {'SUCCESS' if qpat_success else 'FAILED'}")
        
        return map_success and qpat_success
        
    except Exception as e:
        print(f"  ❌ Export failed: {e}")
        return False

def optimize_all_prophet_programs():
    """Optimize all prophet_program_* folders."""
    
    output_dir = Path('output')
    prophet_programs = sorted([d for d in output_dir.iterdir() 
                              if d.is_dir() and d.name.startswith('prophet_program_')])
    
    if not prophet_programs:
        print("❌ No prophet_program_* folders found in output/")
        return
    
    print(f"PROPHET PROGRAM SIZE OPTIMIZATION")
    print(f"=" * 40)
    print(f"Found {len(prophet_programs)} programs to optimize")
    print(f"Strategy: Remove RR3 layer (3→2 round-robin)")
    print(f"Expected reduction: ~33% file size")
    print()
    
    # Show size before
    total_size_before = 0
    for prog in prophet_programs:
        samples_folder = prog / 'samples'
        if samples_folder.exists():
            folder_size = sum(f.stat().st_size for f in samples_folder.glob('*.wav'))
            total_size_before += folder_size
    
    print(f"Total size before: {total_size_before / (1024**2):.1f} MB")
    print()
    
    optimized_count = 0
    failed_count = 0
    
    for program_folder in prophet_programs:
        try:
            success = optimize_prophet_program(program_folder)
            if success:
                optimized_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed_count += 1
        print()
    
    # Show size after
    total_size_after = 0
    for prog in prophet_programs:
        samples_folder = prog / 'samples'
        if samples_folder.exists():
            folder_size = sum(f.stat().st_size for f in samples_folder.glob('*.wav'))
            total_size_after += folder_size
    
    actual_reduction = ((total_size_before - total_size_after) / total_size_before) * 100
    
    print(f"OPTIMIZATION COMPLETE")
    print(f"=" * 40)
    print(f"✅ Optimized: {optimized_count} programs")
    print(f"❌ Failed: {failed_count} programs")
    print(f"📊 Size before: {total_size_before / (1024**2):.1f} MB")
    print(f"📊 Size after: {total_size_after / (1024**2):.1f} MB")
    print(f"📈 Reduction: {actual_reduction:.1f}%")
    print(f"💾 Space saved: {(total_size_before - total_size_after) / (1024**2):.1f} MB")
    
    if optimized_count > 0:
        print(f"\\n🎉 SUCCESS: Prophet programs optimized!")
        print(f"   - Reduced from 3 to 2 round-robin layers")
        print(f"   - {actual_reduction:.1f}% size reduction achieved")  
        print(f"   - Musical quality preserved with 2 RR layers")

if __name__ == "__main__":
    optimize_all_prophet_programs()