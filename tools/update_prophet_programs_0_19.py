#!/usr/bin/env python3
"""
Update existing Prophet Programs 0-19 to include the new silence detection configuration
"""

import os
import re
from pathlib import Path

def update_existing_prophet_programs():
    """Update Prophet Programs 0-19 with new silence detection config"""
    
    config_dir = Path("conf/prophet_programs")
    updated_count = 0
    
    # Update programs 0-19 (add silence detection config)
    for program_num in range(0, 20):
        config_file = config_dir / f"prophet_program_{program_num}.yaml"
        
        if config_file.exists():
            # Read current content
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if already has silence_detection config
            if 'silence_detection:' in content:
                print(f"Already updated: {config_file}")
                continue
            
            # Add silence detection config after trim_silence: true
            old_pattern = r'  trim_silence: true'
            new_text = '''  trim_silence: true
  silence_detection: auto     # "auto" (detect noise floor) or "manual" (use threshold)
  silence_threshold: -60.0    # Manual threshold in dB (used when silence_detection: manual)'''
            
            updated_content = re.sub(old_pattern, new_text, content)
            
            # Write updated content
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print(f"Updated: {config_file}")
            updated_count += 1
        else:
            print(f"Not found: {config_file}")
    
    print(f"\nSUCCESS: Updated {updated_count} existing Prophet Program configurations")
    print(f"All Prophet Programs 0-99 now have consistent silence detection configuration")

if __name__ == "__main__":
    update_existing_prophet_programs()