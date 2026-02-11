#!/usr/bin/env python3
"""
MIKE .mfm File Editor

This script edits MIKE .mfm files by updating file paths in specific sections:
1. [DREDGER_1] section: Updates file_name with matching .dfs0 file
2. [MORPHOLOGY] -> [OUTPUTS] -> [OUTPUT_1]: Updates file_name with output .dfsu path

Usage:
    python edit_mfm.py
"""

import os
import sys
import re
from pathlib import Path


def prompt_user():
    """Prompt user for required inputs."""
    print("MIKE .mfm File Editor")
    print("=" * 50)
    
    # Prompt for input .dfs0 folder
    dfs0_folder = input("Enter input .dfs0 folder path: ").strip()
    if not os.path.isdir(dfs0_folder):
        print(f"Error: '{dfs0_folder}' is not a valid directory")
        sys.exit(1)
    
    # Prompt for output .dfsu folder
    dfsu_folder = input("Enter output .dfsu folder path: ").strip()
    if not os.path.isdir(dfsu_folder):
        print(f"Error: '{dfsu_folder}' is not a valid directory")
        sys.exit(1)
    
    # Prompt for .mfm file
    mfm_file = input("Enter .mfm file path: ").strip()
    if not os.path.isfile(mfm_file):
        print(f"Error: '{mfm_file}' is not a valid file")
        sys.exit(1)
    
    return dfs0_folder, dfsu_folder, mfm_file


def find_dfs0_file(folder):
    """Find .dfs0 file in the specified folder."""
    dfs0_files = [f for f in os.listdir(folder) if f.endswith('.dfs0')]
    
    if len(dfs0_files) == 0:
        print(f"Error: No .dfs0 files found in '{folder}'")
        sys.exit(1)
    elif len(dfs0_files) > 1:
        print(f"Error: Multiple .dfs0 files found in '{folder}': {dfs0_files}")
        print("Ambiguous - cannot determine which file to use")
        sys.exit(1)
    
    return dfs0_files[0]


def parse_mfm_sections(lines):
    """Parse .mfm file into sections."""
    sections = []
    current_section = None
    section_start = -1
    
    for i, line in enumerate(lines):
        # Check if line is a section header (e.g., [SECTION_NAME])
        if line.strip().startswith('[') and line.strip().endswith(']'):
            if current_section is not None:
                sections.append({
                    'name': current_section,
                    'start': section_start,
                    'end': i - 1
                })
            current_section = line.strip()
            section_start = i
    
    # Add the last section
    if current_section is not None:
        sections.append({
            'name': current_section,
            'start': section_start,
            'end': len(lines) - 1
        })
    
    return sections


def find_section_by_name(sections, name):
    """Find section by name."""
    matches = [s for s in sections if s['name'] == name]
    if len(matches) == 0:
        return None
    elif len(matches) > 1:
        print(f"Error: Multiple '{name}' sections found - ambiguous")
        sys.exit(1)
    return matches[0]


def find_first_section_after(sections, after_name, target_name):
    """Find the first occurrence of target_name section after after_name section."""
    after_section = find_section_by_name(sections, after_name)
    if after_section is None:
        print(f"Error: Section '{after_name}' not found")
        sys.exit(1)
    
    # Find all target sections that start after the after_section
    matching = [s for s in sections 
                if s['name'] == target_name and s['start'] > after_section['end']]
    
    if len(matching) == 0:
        print(f"Error: No '{target_name}' section found after '{after_name}'")
        sys.exit(1)
    
    # Return the first one (earliest start position)
    return min(matching, key=lambda s: s['start'])


def update_file_name_in_section(lines, section, new_value, preserve_pipe=False):
    """Update file_name in the specified section."""
    # Pattern captures: (indent)(spacing_before_eq)(spacing_after_eq)(value_without_pipe)(rest_after_closing_quote)
    file_name_pattern = re.compile(r'^(\s*)file_name(\s*)=(\s*)"([^"|]*)\|?"(.*)$')
    
    updated = False
    for i in range(section['start'], section['end'] + 1):
        match = file_name_pattern.match(lines[i])
        if match:
            indent = match.group(1)
            space_before_eq = match.group(2)
            space_after_eq = match.group(3)
            rest = match.group(5)
            pipe = '|' if preserve_pipe else ''
            lines[i] = f'{indent}file_name{space_before_eq}={space_after_eq}"{new_value}{pipe}"{rest}\n'
            updated = True
            break
    
    if not updated:
        print(f"Error: No file_name found in section {section['name']}")
        sys.exit(1)


def edit_mfm_file(dfs0_folder, dfsu_folder, mfm_file):
    """Edit the .mfm file with the specified changes."""
    # Find the .dfs0 file
    dfs0_file = find_dfs0_file(dfs0_folder)
    print(f"Found .dfs0 file: {dfs0_file}")
    
    # Read the .mfm file
    with open(mfm_file, 'r') as f:
        lines = f.readlines()
    
    # Parse sections
    sections = parse_mfm_sections(lines)
    
    # A) Update [DREDGER_1] section
    dredger_section = find_section_by_name(sections, '[DREDGER_1]')
    if dredger_section is None:
        print("Error: [DREDGER_1] section not found")
        sys.exit(1)
    
    dfs0_path = os.path.join(dfs0_folder, dfs0_file)
    update_file_name_in_section(lines, dredger_section, dfs0_path, preserve_pipe=True)
    print(f"Updated [DREDGER_1] file_name to: {dfs0_path}|")
    
    # B) Update [MORPHOLOGY] -> [OUTPUTS] -> [OUTPUT_1]
    # First find [OUTPUTS] after [MORPHOLOGY]
    outputs_section = find_first_section_after(sections, '[MORPHOLOGY]', '[OUTPUTS]')
    
    # Re-parse sections within the OUTPUTS section to find [OUTPUT_1]
    # We need to look for sections starting after outputs_section.start
    output1_sections = [s for s in sections 
                        if s['name'] == '[OUTPUT_1]' and s['start'] > outputs_section['start']]
    
    if len(output1_sections) == 0:
        print("Error: No [OUTPUT_1] section found after [MORPHOLOGY] -> [OUTPUTS]")
        sys.exit(1)
    
    # Find the first OUTPUT_1 that is within or right after the OUTPUTS section
    # This is the one that belongs to MORPHOLOGY
    output1_section = min(output1_sections, key=lambda s: s['start'])
    
    # Generate output file name: <output_folder>\<mfm_basename>.dfsu
    mfm_basename = os.path.splitext(os.path.basename(mfm_file))[0]
    dfsu_filename = f"{mfm_basename}.dfsu"
    dfsu_path = os.path.join(dfsu_folder, dfsu_filename)
    
    update_file_name_in_section(lines, output1_section, dfsu_path, preserve_pipe=False)
    print(f"Updated [OUTPUT_1] file_name to: {dfsu_path}")
    
    # Write back to file
    with open(mfm_file, 'w') as f:
        f.writelines(lines)
    
    print(f"\nSuccessfully updated {mfm_file}")


def main():
    """Main entry point."""
    try:
        dfs0_folder, dfsu_folder, mfm_file = prompt_user()
        edit_mfm_file(dfs0_folder, dfsu_folder, mfm_file)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
