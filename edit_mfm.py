#!/usr/bin/env python3
"""
MIKE .mfm File Editor

This script edits MIKE .mfm files by updating file paths in specific sections:
1. [DREDGER_1] section: Updates file_name with matching .dfs0 file
2. [MORPHOLOGY] -> [OUTPUTS] -> [OUTPUT_1]: Updates file_name with output .dfsu path

The script uses a template-based workflow:
- Template .mfm files are stored in the 'input-mfm' folder
- Generated .mfm files are saved to the 'output' folder
- The script duplicates templates and processes them

Usage:
    python edit_mfm.py
"""

import os
import sys
import re
import shutil
from pathlib import Path


def prompt_user():
    """Prompt user for required inputs."""
    print("MIKE .mfm File Editor")
    print("=" * 50)
    
    # Prompt for input .dfs0 folder
    dfs0_folder = input("Enter input .dfs0 folder path: ").strip()
    
    # Check if user provided a .dfs0 file path (even if it doesn't exist)
    if dfs0_folder.lower().endswith('.dfs0'):
        print(f"Error: You provided a .dfs0 file path, but a folder path is required.")
        print(f"Please provide the folder containing the .dfs0 file.")
        print(f"Example: Instead of '{dfs0_folder}'")
        print(f"         Use: '{os.path.dirname(dfs0_folder) if os.path.dirname(dfs0_folder) else '.'}'")
        sys.exit(1)
    
    # Check if user provided a file instead of a folder
    if os.path.isfile(dfs0_folder):
        parent_dir = os.path.dirname(dfs0_folder)
        example_dir = parent_dir if parent_dir else '.'
        print(f"Error: You provided a file path, but a folder path is required.")
        print(f"Please provide the folder path instead.")
        print(f"Example: Instead of '{dfs0_folder}'")
        print(f"         Use: '{example_dir}'")
        sys.exit(1)
    
    if not os.path.isdir(dfs0_folder):
        print(f"Error: '{dfs0_folder}' is not a valid directory")
        print(f"Please provide a valid folder path containing .dfs0 files.")
        sys.exit(1)
    
    # Prompt for output .dfsu folder
    dfsu_folder = input("Enter output .dfsu folder path: ").strip()
    
    # Check if user provided a file instead of a folder
    if os.path.isfile(dfsu_folder):
        parent_dir = os.path.dirname(dfsu_folder)
        example_dir = parent_dir if parent_dir else '.' 
        print(f"Error: You provided a file path, but a folder path is required.")
        print(f"Please provide the folder path where .dfsu files will be saved.")
        print(f"Example: Instead of '{dfsu_folder}'")
        print(f"         Use: '{example_dir}'")
        sys.exit(1)
    
    if not os.path.isdir(dfsu_folder):
        print(f"Error: '{dfsu_folder}' is not a valid directory")
        print(f"Please provide a valid folder path for output .dfsu files.")
        sys.exit(1)
    
    # Prompt for template .mfm file from input-mfm folder
    mfm_file = input("Enter template .mfm file name (from input-mfm folder): ").strip()
    
    # Construct full path to template
    template_path = os.path.join('input-mfm', mfm_file)
    if not os.path.isfile(template_path):
        print(f"Error: '{template_path}' is not a valid file")
        sys.exit(1)
    
    return dfs0_folder, dfsu_folder, template_path


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


def edit_mfm_file(dfs0_folder, dfsu_folder, template_path):
    """Edit the .mfm file with the specified changes."""
    # Find the .dfs0 file
    dfs0_file = find_dfs0_file(dfs0_folder)
    print(f"Found .dfs0 file: {dfs0_file}")
    
    # Create output folder if it doesn't exist
    os.makedirs('output', exist_ok=True)
    
    # Copy template to output folder
    template_basename = os.path.basename(template_path)
    output_path = os.path.join('output', template_basename)
    shutil.copy2(template_path, output_path)
    print(f"Copied template to: {output_path}")
    
    # Read the .mfm file from output folder
    with open(output_path, 'r') as f:
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
    
    # Generate output file name: <output_folder>/<mfm_basename>.dfsu
    mfm_basename = os.path.splitext(os.path.basename(output_path))[0]
    dfsu_filename = f"{mfm_basename}.dfsu"
    dfsu_path = os.path.join(dfsu_folder, dfsu_filename)
    
    update_file_name_in_section(lines, output1_section, dfsu_path, preserve_pipe=False)
    print(f"Updated [OUTPUT_1] file_name to: {dfsu_path}")
    
    # Write back to file in output folder
    with open(output_path, 'w') as f:
        f.writelines(lines)
    
    print(f"\nSuccessfully created and updated {output_path}")


def main():
    """Main entry point."""
    try:
        dfs0_folder, dfsu_folder, template_path = prompt_user()
        edit_mfm_file(dfs0_folder, dfsu_folder, template_path)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
