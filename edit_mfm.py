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


def remove_quotes(s):
    """
    Remove matching outer quotes from a string.
    
    This function strips whitespace first, then removes only matching outer quotes
    (both single or both double). Non-matching quotes are preserved.
    
    Args:
        s: Input string that may have quotes
        
    Returns:
        String with matching outer quotes removed
        
    Examples:
        >>> remove_quotes('"path"')
        'path'
        >>> remove_quotes("'path'")
        'path'
        >>> remove_quotes("path")
        'path'
        >>> remove_quotes('"\'path\'"')
        "'path'"
        >>> remove_quotes('"path\'')
        '"path\''
    """
    s = s.strip()
    if len(s) >= 2:
        if (s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'"):
            return s[1:-1]
    return s


def list_available_templates():
    """
    List available .mfm template files in the input-mfm folder.
    
    Prints the list of templates to stdout. If the directory cannot be accessed
    (OSError or FileNotFoundError), prints an error message instead.
    
    Returns:
        None
    """
    try:
        templates = [f for f in os.listdir('input-mfm') if f.endswith('.mfm')]
        if templates:
            for template in sorted(templates):
                print(f"  - {template}")
        else:
            print("  (no .mfm templates found)")
    except (OSError, FileNotFoundError):
        print("  (unable to list templates)")


def prompt_user():
    """Prompt user for required inputs."""
    print("MIKE .mfm File Editor")
    print("=" * 50)
    
    # Prompt for input .dfs0 folder
    dfs0_folder = remove_quotes(input("Enter input .dfs0 folder path: "))
    
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
    dfsu_folder = remove_quotes(input("Enter output .dfsu folder path: "))
    
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
    mfm_file = remove_quotes(input("Enter template .mfm file name (from input-mfm folder): "))
    
    # Check if user provided a folder path instead of a filename
    if os.path.isdir(mfm_file):
        print(f"Error: You provided a folder path, but a template filename is required.")
        print(f"Please provide just the template filename, not the full path.")
        print(f"\nAvailable templates in 'input-mfm' folder:")
        list_available_templates()
        print(f"\nExample: Instead of '{mfm_file}'")
        print(f"         Use: 'template.mfm'")
        sys.exit(1)
    
    # Check if user provided a full path to a file (contains path separators)
    # Check for both forward slash and backslash to handle Windows paths
    if '/' in mfm_file or '\\' in mfm_file:
        # Extract just the filename
        # On Unix, os.path.basename doesn't treat backslash as path separator,
        # so we normalize to forward slashes first to handle Windows paths correctly
        basename = os.path.basename(mfm_file.replace('\\', '/'))
        print(f"Error: You provided a full path, but only the filename is needed.")
        print(f"Please provide just the template filename from the 'input-mfm' folder.")
        print(f"\nAvailable templates in 'input-mfm' folder:")
        list_available_templates()
        if basename and basename.endswith('.mfm'):
            print(f"\nExample: Instead of '{mfm_file}'")
            print(f"         Use: '{basename}'")
        else:
            print(f"\nExample: Use 'template.mfm'")
        sys.exit(1)
    
    # Construct full path to template
    template_path = os.path.join('input-mfm', mfm_file)
    if not os.path.isfile(template_path):
        print(f"Error: Template file '{mfm_file}' not found in 'input-mfm' folder.")
        print(f"\nAvailable templates:")
        list_available_templates()
        sys.exit(1)
    
    # Validate template structure before processing
    try:
        validate_template(template_path)
    except ValueError as e:
        print(f"Error: Invalid template file.")
        print(str(e))
        sys.exit(1)
    except IOError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Ask if user wants batch mode
    print("\n" + "=" * 50)
    batch_mode = False
    while True:
        choice = input("Process [M]ultiple .dfs0 files or [S]ingle file? (M/S): ").strip().upper()
        if choice == 'M':
            batch_mode = True
            break
        elif choice == 'S':
            batch_mode = False
            break
        else:
            print("Please enter 'M' for multiple or 'S' for single")
    
    return dfs0_folder, dfsu_folder, template_path, batch_mode



def find_dfs0_files(folder, template_basename=None, batch_mode=False):
    """
    Find .dfs0 file(s) in the specified folder.
    
    If batch_mode is True, returns all .dfs0 files or lets user select multiple.
    If batch_mode is False, returns a single file (original behavior).
    
    Args:
        folder: Path to folder containing .dfs0 files
        template_basename: Optional basename of template (without extension) to help match
        batch_mode: If True, allow selecting/returning multiple files
        
    Returns:
        List of filenames of selected .dfs0 files (not full paths)
    """
    # Sort once at the beginning for consistent ordering
    dfs0_files = sorted([f for f in os.listdir(folder) if f.endswith('.dfs0')])
    
    if len(dfs0_files) == 0:
        print(f"Error: No .dfs0 files found in '{folder}'")
        sys.exit(1)
    elif len(dfs0_files) == 1:
        return [dfs0_files[0]]
    
    # Multiple files found
    if batch_mode:
        # In batch mode, ask user if they want all files or specific files
        print(f"\nFound {len(dfs0_files)} .dfs0 files in '{folder}'")
        
        while True:
            choice = input("\nProcess [A]ll files, [S]elect specific files, or [Q]uit? ").strip().upper()
            if choice == 'Q':
                print("Operation cancelled by user")
                sys.exit(0)
            elif choice == 'A':
                print(f"Selected all {len(dfs0_files)} files for processing")
                return dfs0_files
            elif choice == 'S':
                break
            else:
                print("Please enter 'A' for all, 'S' for select, or 'Q' to quit")
        
        # Show all files for selection
        print(f"\nAll .dfs0 files in '{folder}':")
        for i, f in enumerate(dfs0_files, 1):
            print(f"  {i}. {f}")
        
        # Get user selection
        while True:
            try:
                selection = input("\nEnter file numbers separated by commas (e.g., 1,3,5) or 'all': ").strip()
                if selection.lower() == 'all':
                    return dfs0_files
                
                # Parse comma-separated numbers
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                
                # Validate indices
                invalid = [i for i in indices if i < 0 or i >= len(dfs0_files)]
                if invalid:
                    print(f"Invalid file number(s). Please enter numbers between 1 and {len(dfs0_files)}")
                    continue
                
                selected_files = [dfs0_files[i] for i in indices]
                print(f"Selected {len(selected_files)} file(s): {', '.join(selected_files)}")
                return selected_files
                
            except ValueError:
                print("Please enter valid numbers separated by commas")
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                sys.exit(0)
    else:
        # Original single-file behavior with smart matching
        if template_basename:
            # Normalize template name for matching (replace delimiters with underscore)
            normalized_template = template_basename.replace('-', '_').replace(' ', '_')
            
            # Extract potential matching parts from template name
            # E.g., "MT2D_202602_SI_CB1_3am" -> look for "SI_CB1_3am" or "CB1_3am"
            template_parts = normalized_template.split('_')
            
            # Filter out common generic parts (pure numbers and 6-digit dates like 202602)
            meaningful_parts = [p for p in template_parts 
                              if len(p) > 1 and not p.isdigit()]
            
            # Try exact matches first - look for files containing the last N parts of template
            candidates = []
            
            # Strategy 1: Look for files containing the last 2 meaningful parts
            if len(meaningful_parts) >= 2:
                search_pattern = '_'.join(meaningful_parts[-2:])
                # Normalize filenames for comparison
                candidates = [f for f in dfs0_files 
                             if search_pattern.lower() in f.replace('-', '_').lower()]
            
            # Strategy 2: If no match, try last meaningful part
            if not candidates and meaningful_parts:
                search_pattern = meaningful_parts[-1]
                candidates = [f for f in dfs0_files 
                             if search_pattern.lower() in f.replace('-', '_').lower()]
            
            # Strategy 3: Look for files containing any of the last few meaningful parts
            if not candidates and len(meaningful_parts) >= 2:
                for part in meaningful_parts[-3:]:  # Check last 3 parts
                    if len(part) >= 3:  # Only meaningful parts with 3+ chars
                        matching = [f for f in dfs0_files 
                                  if part.lower() in f.replace('-', '_').lower()]
                        if len(matching) == 1:
                            candidates = matching
                            break
            
            if len(candidates) == 1:
                print(f"Auto-selected .dfs0 file based on template name: {candidates[0]}")
                return [candidates[0]]
            elif len(candidates) > 1:
                print(f"\nFound {len(candidates)} .dfs0 files matching template pattern:")
                for i, f in enumerate(candidates, 1):
                    print(f"  {i}. {f}")
                print(f"\nNote: All {len(dfs0_files)} files in folder are shown below for reference.")
            else:
                # No matches found based on template
                print(f"\nCould not auto-match template to .dfs0 file.")
                print(f"Template: {template_basename}")
        
        # Show all files for selection
        print(f"\nAll .dfs0 files in '{folder}':")
        for i, f in enumerate(dfs0_files, 1):
            print(f"  {i}. {f}")
        
        # Interactive selection for single file
        while True:
            try:
                choice = input("\nEnter the number of the file to use (or 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    print("Operation cancelled by user")
                    sys.exit(0)
                
                idx = int(choice) - 1
                if 0 <= idx < len(dfs0_files):
                    selected_file = dfs0_files[idx]
                    print(f"Selected: {selected_file}")
                    return [selected_file]
                else:
                    print(f"Please enter a number between 1 and {len(dfs0_files)}")
            except ValueError:
                print("Please enter a valid number or 'q' to quit")
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                sys.exit(0)


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
    """
    Find section by name.
    
    Returns:
        Section dict if found and unique, None if not found
        
    Raises:
        ValueError: If multiple sections with the same name are found (ambiguous)
    """
    matches = [s for s in sections if s['name'] == name]
    if len(matches) == 0:
        return None
    elif len(matches) > 1:
        raise ValueError(f"Multiple '{name}' sections found - ambiguous")
    return matches[0]


def find_first_section_after(sections, after_name, target_name):
    """
    Find the first occurrence of target_name section after after_name section.
    
    Raises:
        ValueError: If after_name section is not found or no target_name section exists after it
    """
    after_section = find_section_by_name(sections, after_name)
    if after_section is None:
        raise ValueError(f"Section '{after_name}' not found")
    
    # Find all target sections that start after the after_section
    matching = [s for s in sections 
                if s['name'] == target_name and s['start'] > after_section['end']]
    
    if len(matching) == 0:
        raise ValueError(f"No '{target_name}' section found after '{after_name}'")
    
    # Return the first one (earliest start position)
    return min(matching, key=lambda s: s['start'])


def update_file_name_in_section(lines, section, new_value, preserve_pipe=False):
    """
    Update file_name in the specified section.
    
    Raises:
        ValueError: If no file_name entry is found in the section
    """
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
        raise ValueError(f"No file_name found in section {section['name']}")


def validate_template(template_path):
    """
    Validate that the template file has required sections and file_name entries.
    
    Args:
        template_path: Path to the template .mfm file
        
    Raises:
        ValueError: If template is missing required sections or file_name entries
        IOError: If template file cannot be read
    """
    try:
        with open(template_path, 'r') as f:
            lines = f.readlines()
    except (IOError, OSError) as e:
        raise IOError(f"Cannot read template file '{template_path}': {e}")
    
    # Parse sections
    sections = parse_mfm_sections(lines)
    
    # Check for required [DREDGER_1] section
    dredger_section = find_section_by_name(sections, '[DREDGER_1]')
    if dredger_section is None:
        raise ValueError(
            f"Template '{template_path}' is missing required [DREDGER_1] section.\n"
            "Please ensure your template has a [DREDGER_1] section with a file_name entry."
        )
    
    # Check for file_name in [DREDGER_1]
    file_name_pattern = re.compile(r'^\s*file_name\s*=\s*"[^"]*"')
    has_file_name = False
    for i in range(dredger_section['start'], dredger_section['end'] + 1):
        if file_name_pattern.match(lines[i]):
            has_file_name = True
            break
    
    if not has_file_name:
        raise ValueError(
            f"Template '{template_path}' is missing file_name in [DREDGER_1] section.\n"
            "Please add a line like: file_name = \"placeholder.dfs0|\" in the [DREDGER_1] section."
        )
    
    # Check for [MORPHOLOGY] section
    morphology_section = find_section_by_name(sections, '[MORPHOLOGY]')
    if morphology_section is None:
        raise ValueError(
            f"Template '{template_path}' is missing required [MORPHOLOGY] section.\n"
            "Please ensure your template has a [MORPHOLOGY] section."
        )
    
    # Check for [OUTPUTS] after [MORPHOLOGY]
    try:
        outputs_section = find_first_section_after(sections, '[MORPHOLOGY]', '[OUTPUTS]')
    except ValueError:
        raise ValueError(
            f"Template '{template_path}' is missing [OUTPUTS] section after [MORPHOLOGY].\n"
            "Please ensure your template has an [OUTPUTS] section after the [MORPHOLOGY] section."
        )
    
    # Check for [OUTPUT_1] after [OUTPUTS]
    output1_sections = [s for s in sections 
                        if s['name'] == '[OUTPUT_1]' and s['start'] > outputs_section['start']]
    
    if len(output1_sections) == 0:
        raise ValueError(
            f"Template '{template_path}' is missing [OUTPUT_1] section after [MORPHOLOGY] -> [OUTPUTS].\n"
            "Please ensure your template has an [OUTPUT_1] section after the [OUTPUTS] section."
        )
    
    # Check for file_name in [OUTPUT_1]
    output1_section = min(output1_sections, key=lambda s: s['start'])
    has_file_name = False
    for i in range(output1_section['start'], output1_section['end'] + 1):
        if file_name_pattern.match(lines[i]):
            has_file_name = True
            break
    
    if not has_file_name:
        raise ValueError(
            f"Template '{template_path}' is missing file_name in [OUTPUT_1] section.\n"
            "Please add a line like: file_name = \"placeholder.dfsu\" in the [OUTPUT_1] section."
        )


def process_single_dfs0(dfs0_file, dfs0_folder, dfsu_folder, template_path):
    """
    Process a single .dfs0 file with the template.
    
    Args:
        dfs0_file: Filename of the .dfs0 file (not full path)
        dfs0_folder: Folder containing the .dfs0 file
        dfsu_folder: Folder for output .dfsu files
        template_path: Path to the template .mfm file
        
    Returns:
        tuple: (success: bool, output_path: str or None, error_msg: str or None)
    """
    try:
        # Create output folder if it doesn't exist
        os.makedirs('output', exist_ok=True)
        
        # Generate output filename: include dfs0 basename for uniqueness
        template_basename = os.path.splitext(os.path.basename(template_path))[0]
        dfs0_basename = os.path.splitext(dfs0_file)[0]
        
        # Output filename: template_basename_dfs0_basename.mfm
        output_filename = f"{template_basename}_{dfs0_basename}.mfm"
        output_path = os.path.join('output', output_filename)
        
        # Copy template to output folder with new name
        shutil.copy2(template_path, output_path)
        
        # Read the .mfm file from output folder
        with open(output_path, 'r') as f:
            lines = f.readlines()
        
        # Parse sections
        sections = parse_mfm_sections(lines)
        
        # A) Update [DREDGER_1] section
        dredger_section = find_section_by_name(sections, '[DREDGER_1]')
        if dredger_section is None:
            return (False, None, "[DREDGER_1] section not found in template")
        else:
            dfs0_path = os.path.join(dfs0_folder, dfs0_file)
            try:
                update_file_name_in_section(lines, dredger_section, dfs0_path, preserve_pipe=True)
            except ValueError as e:
                return (False, None, str(e))
        
        # B) Update [MORPHOLOGY] -> [OUTPUTS] -> [OUTPUT_1]
        try:
            # First find [OUTPUTS] after [MORPHOLOGY]
            outputs_section = find_first_section_after(sections, '[MORPHOLOGY]', '[OUTPUTS]')
            
            # Re-parse sections within the OUTPUTS section to find [OUTPUT_1]
            output1_sections = [s for s in sections 
                                if s['name'] == '[OUTPUT_1]' and s['start'] > outputs_section['start']]
            
            if len(output1_sections) == 0:
                return (False, None, "No [OUTPUT_1] section found after [MORPHOLOGY] -> [OUTPUTS]")
            else:
                # Find the first OUTPUT_1 that is within or right after the OUTPUTS section
                output1_section = min(output1_sections, key=lambda s: s['start'])
                
                # Generate output dfsu file name: based on output mfm filename
                mfm_basename = os.path.splitext(output_filename)[0]
                dfsu_filename = f"{mfm_basename}.dfsu"
                dfsu_path = os.path.join(dfsu_folder, dfsu_filename)
                
                try:
                    update_file_name_in_section(lines, output1_section, dfsu_path, preserve_pipe=False)
                except ValueError as e:
                    return (False, None, str(e))
        except ValueError as e:
            return (False, None, f"Could not update [OUTPUT_1]: {str(e)}")
        
        # Write back to file in output folder
        with open(output_path, 'w') as f:
            f.writelines(lines)
        
        return (True, output_path, None)
    
    except (IOError, OSError) as e:
        # File I/O errors
        return (False, None, f"File error: {str(e)}")
    except ValueError as e:
        # Section/parsing errors from our functions
        return (False, None, str(e))


def edit_mfm_file(dfs0_folder, dfsu_folder, template_path, batch_mode=False):
    """
    Edit the .mfm file with the specified changes.
    
    Args:
        dfs0_folder: Folder containing .dfs0 files
        dfsu_folder: Folder for output .dfsu files
        template_path: Path to template .mfm file
        batch_mode: If True, process multiple files
    """
    # Extract template basename for matching
    template_basename = os.path.splitext(os.path.basename(template_path))[0]
    
    # Find the .dfs0 file(s)
    dfs0_files = find_dfs0_files(dfs0_folder, template_basename, batch_mode=batch_mode)
    
    if len(dfs0_files) == 1:
        # Single file processing
        dfs0_file = dfs0_files[0]
        print(f"\nProcessing: {dfs0_file}")
        success, output_path, error_msg = process_single_dfs0(dfs0_file, dfs0_folder, dfsu_folder, template_path)
        
        if success:
            print(f"✓ Created: {output_path}")
            print(f"\nSuccessfully processed 1 file")
        else:
            print(f"✗ Failed: {error_msg}")
            sys.exit(1)
    else:
        # Batch processing multiple files
        print(f"\nProcessing {len(dfs0_files)} files...")
        print("=" * 60)
        
        successful = 0
        failed = 0
        failed_files = []
        
        for i, dfs0_file in enumerate(dfs0_files, 1):
            print(f"\n[{i}/{len(dfs0_files)}] Processing: {dfs0_file}")
            success, output_path, error_msg = process_single_dfs0(dfs0_file, dfs0_folder, dfsu_folder, template_path)
            
            if success:
                print(f"    ✓ Created: {os.path.basename(output_path)}")
                successful += 1
            else:
                print(f"    ✗ Failed: {error_msg}")
                failed += 1
                failed_files.append((dfs0_file, error_msg))
        
        print("\n" + "=" * 60)
        print(f"Processing complete: {successful} successful, {failed} failed")
        
        if failed > 0:
            print(f"\nFailed files:")
            for filename, error in failed_files:
                print(f"  - {filename}: {error}")


def main():
    """Main entry point."""
    try:
        dfs0_folder, dfsu_folder, template_path, batch_mode = prompt_user()
        edit_mfm_file(dfs0_folder, dfsu_folder, template_path, batch_mode)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
