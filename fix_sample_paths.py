#!/usr/bin/env python3
"""
Fix existing QPAT and MAP files to correct sample paths.

This script fixes the double "samples" directory issue in existing files:
From: "2:samples/Prophet_Program_XX/samples/file.wav"
To:   "2:samples/Prophet_Program_XX/file.wav"
"""

import os
import re
import glob
from pathlib import Path

def fix_sample_paths_in_file(file_path):
    """Fix sample paths in a single file."""
    
    print(f"Processing: {file_path}")
    
    # Read file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"  ERROR reading {file_path}: {e}")
        return False
    
    original_content = content
    
    # Pattern to match: "2:samples/FolderName/samples/filename.wav"
    # Replace with: "2:samples/FolderName/filename.wav"
    pattern = r'"([234]):samples/([^/]+)/samples/([^"]+\.wav)"'
    replacement = r'"\1:samples/\2/\3"'
    
    # Apply the fix
    content = re.sub(pattern, replacement, content)
    
    # Count changes
    changes = len(re.findall(pattern, original_content))
    
    if changes > 0:
        # Write back fixed content
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✅ Fixed {changes} sample paths")
            return True
        except Exception as e:
            print(f"  ERROR writing {file_path}: {e}")
            return False
    else:
        print(f"  No changes needed")
        return False

def fix_all_qpat_and_map_files():
    """Fix all QPAT and MAP files in the output directory."""
    
    output_dir = Path("output")
    if not output_dir.exists():
        print("Output directory not found!")
        return
    
    print("="*70)
    print("FIXING QPAT AND MAP FILE SAMPLE PATHS")
    print("="*70)
    print(f"Scanning: {output_dir.absolute()}")
    print()
    
    # Find all QPAT and MAP files
    qpat_files = list(output_dir.rglob("*.qpat"))
    map_files = list(output_dir.rglob("*.map"))
    
    all_files = qpat_files + map_files
    
    if not all_files:
        print("No QPAT or MAP files found!")
        return
    
    print(f"Found {len(qpat_files)} QPAT files and {len(map_files)} MAP files")
    print()
    
    # Process each file
    fixed_count = 0
    for file_path in sorted(all_files):
        if fix_sample_paths_in_file(file_path):
            fixed_count += 1
    
    print()
    print("="*70)
    print(f"SUMMARY: Fixed {fixed_count}/{len(all_files)} files")
    print("="*70)
    
    if fixed_count > 0:
        print("✅ Sample paths have been corrected!")
        print("New format: \"2:samples/Prophet_Program_XX/filename.wav\"")
        print("(Removed extra /samples/ directory)")
    else:
        print("ℹ️  All files were already correct")

if __name__ == "__main__":
    fix_all_qpat_and_map_files()