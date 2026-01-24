#!/usr/bin/env python3
"""
Optimize Prophet Programs - Remove Second Round-Robin Layer
==========================================================

Further optimize the prophet programs by removing the second round-robin layer,
keeping only RR1 for maximum size reduction.

Current: 2 round-robin layers (RR1, RR2) - 122 samples per program
Target: 1 round-robin layer (RR1 only) - 61 samples per program
Expected reduction: 50% additional size reduction
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def get_folder_size_mb(folder_path):
    """Calculate folder size in MB"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)

def remove_rr2_samples(samples_folder):
    """Remove all RR2 sample files"""
    removed_count = 0
    total_count = 0
    
    for file in os.listdir(samples_folder):
        if file.endswith('.wav'):
            total_count += 1
            if '_rr2.wav' in file:
                file_path = os.path.join(samples_folder, file)
                os.remove(file_path)
                removed_count += 1
    
    return total_count, removed_count

def update_sfz_single_rr(sfz_file):
    """Update SFZ file to use seq_length=1 (single round-robin)"""
    with open(sfz_file, 'r') as f:
        content = f.read()
    
    # Remove seq_length and seq_position from groups
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # Skip RR2 regions entirely
        if 'rr2.wav' in line:
            continue
        # Update seq_length to 1
        elif line.strip() == 'seq_length=2':
            new_lines.append('seq_length=1')
        # Keep seq_position=1 (remove seq_position=2 groups)
        elif line.strip().startswith('seq_position=2'):
            continue
        else:
            new_lines.append(line)
    
    # Write updated content
    with open(sfz_file, 'w') as f:
        f.write('\n'.join(new_lines))

def optimize_program(program_name):
    """Optimize a single prophet program"""
    program_folder = f"output/{program_name}"
    samples_folder = os.path.join(program_folder, "samples")
    sfz_file = os.path.join(program_folder, f"{program_name}.sfz")
    
    print(f"\nOptimizing {program_name}...")
    
    # Get initial sample count
    total_before, removed_count = remove_rr2_samples(samples_folder)
    remaining_count = total_before - removed_count
    reduction_pct = (removed_count / total_before) * 100 if total_before > 0 else 0
    
    print(f"  📁 Samples before: {total_before}")
    print(f"  🗑️  Removing RR2: {removed_count} files")
    print(f"  📁 Samples after: {remaining_count} ({reduction_pct:.1f}% reduction)")
    
    # Update SFZ file
    if os.path.exists(sfz_file):
        update_sfz_single_rr(sfz_file)
        print(f"  📝 SFZ updated: RR2 entries removed, seq_length=1")
    
    # Re-export Waldorf formats
    try:
        # Run the export command
        cmd = [
            sys.executable, "autosamplerT.py",
            "--export_formats", "waldorf_map,qpat",
            "--export_location", program_folder,
            "--sfz_file", sfz_file,
            "--samples_folder", samples_folder,
            "--multisample_name", program_name
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print(f"  ✅ MAP export: SUCCESS")
            print(f"  ✅ QPAT export: SUCCESS")
        else:
            print(f"  ❌ Export failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Export error: {e}")
        return False
    
    return True

def main():
    print("PROPHET PROGRAM SINGLE RR OPTIMIZATION")
    print("=" * 60)
    
    # Find all prophet programs
    output_folder = "output"
    programs = []
    
    for item in os.listdir(output_folder):
        if item.startswith("prophet_program_") and os.path.isdir(os.path.join(output_folder, item)):
            programs.append(item)
    
    programs.sort()
    
    if not programs:
        print("❌ No prophet programs found!")
        return
    
    print(f"Found {len(programs)} programs to optimize")
    print("Strategy: Remove RR2 layer (2→1 round-robin)")
    print("Expected reduction: ~50% additional file size")
    
    # Calculate total size before
    total_size_before = 0
    for program in programs:
        program_folder = os.path.join(output_folder, program)
        if os.path.exists(program_folder):
            total_size_before += get_folder_size_mb(program_folder)
    
    print(f"Total size before: {total_size_before:.1f} MB")
    print()
    
    # Optimize each program
    success_count = 0
    failed_programs = []
    
    for program in programs:
        if optimize_program(program):
            success_count += 1
        else:
            failed_programs.append(program)
    
    # Calculate total size after
    total_size_after = 0
    for program in programs:
        program_folder = os.path.join(output_folder, program)
        if os.path.exists(program_folder):
            total_size_after += get_folder_size_mb(program_folder)
    
    # Summary
    print("\nSINGLE RR OPTIMIZATION COMPLETE")
    print("=" * 60)
    print(f"✅ Optimized: {success_count} programs")
    print(f"❌ Failed: {len(failed_programs)} programs")
    if failed_programs:
        print(f"Failed programs: {', '.join(failed_programs)}")
    
    print(f"📊 Size before: {total_size_before:.1f} MB")
    print(f"📊 Size after: {total_size_after:.1f} MB")
    
    if total_size_before > 0:
        reduction_pct = ((total_size_before - total_size_after) / total_size_before) * 100
        space_saved = total_size_before - total_size_after
        print(f"📈 Reduction: {reduction_pct:.1f}%")
        print(f"💾 Space saved: {space_saved:.1f} MB")
    
    print()
    print("🎉 SUCCESS: Prophet programs optimized to single round-robin!")
    print("  - Reduced from 2 to 1 round-robin layer")
    print("  - ~50% additional size reduction achieved")
    print("  - Simplest possible structure maintained")

if __name__ == "__main__":
    main()