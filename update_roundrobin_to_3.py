#!/usr/bin/env python3
"""
Update all Prophet Programs 0-99 to increase roundrobin layers from 2 to 3
"""

import os
import re
from pathlib import Path

def update_roundrobin_layers():
    """Update all Prophet Programs to use 3 round-robin layers instead of 2"""
    
    config_dir = Path("conf/prophet_programs")
    updated_count = 0
    
    # Update all programs 0-99
    for program_num in range(0, 100):
        config_file = config_dir / f"prophet_program_{program_num}.yaml"
        
        if config_file.exists():
            # Read current content
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update roundrobin_layers from 2 to 3
            old_pattern = r'  roundrobin_layers: 2    # 2 round-robin layers'
            new_text = '  roundrobin_layers: 3    # 3 round-robin layers'
            
            if old_pattern in content:
                updated_content = content.replace(old_pattern, new_text)
                
                # Also update description
                desc_pattern = r'description: "Prophet 6 Program \d+ - Every 5 semitones, 2 RR layers"'
                desc_replacement = lambda m: m.group(0).replace('2 RR layers', '3 RR layers')
                updated_content = re.sub(desc_pattern, desc_replacement, updated_content)
                
                # Write updated content
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                print(f"Updated: {config_file}")
                updated_count += 1
            else:
                print(f"Pattern not found in: {config_file}")
        else:
            print(f"Not found: {config_file}")
    
    print(f"\nSUCCESS: Updated {updated_count} Prophet Program configurations")
    print(f"All Prophet Programs now use 3 round-robin layers instead of 2")

if __name__ == "__main__":
    update_roundrobin_layers()