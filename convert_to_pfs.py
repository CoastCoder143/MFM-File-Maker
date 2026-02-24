#!/usr/bin/env python3
"""
Convert simple INI-style .mfm files to proper PFS format.

This tool converts .mfm files from the simple format (using [SECTION]) 
to the proper PFS format (using [SECTION] ... EndSect) that mikeio can read.
"""

import re
import sys
from pathlib import Path


def convert_ini_to_pfs(input_content):
    """
    Convert INI-style .mfm content to PFS format.
    
    Args:
        input_content: String containing the INI-style content
        
    Returns:
        String containing the PFS format content
    """
    lines = input_content.split('\n')
    output_lines = []
    current_section = None
    section_content = []
    
    for line in lines:
        # Check if it's a section header
        section_match = re.match(r'^\[([^\]]+)\]', line)
        
        if section_match:
            # Close previous section if exists
            if current_section:
                output_lines.append(f"[{current_section}]")
                for content_line in section_content:
                    output_lines.append(f"   {content_line}")
                output_lines.append(f"EndSect  // {current_section}")
                output_lines.append("")
            
            # Start new section
            current_section = section_match.group(1)
            section_content = []
        elif current_section and line.strip() and not line.strip().startswith('//'):
            # Add content to current section (skip comments and empty lines)
            section_content.append(line.strip())
        elif not current_section:
            # Keep header comments
            output_lines.append(line)
    
    # Close final section
    if current_section:
        output_lines.append(f"[{current_section}]")
        for content_line in section_content:
            output_lines.append(f"   {content_line}")
        output_lines.append(f"EndSect  // {current_section}")
    
    return '\n'.join(output_lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_to_pfs.py <input_file> [output_file]")
        print("If output_file is not specified, will create .pfs version of input")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    if not input_file.exists():
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)
    
    # Determine output file
    if len(sys.argv) >= 3:
        output_file = Path(sys.argv[2])
    else:
        output_file = input_file.with_suffix('.pfs')
    
    # Read input
    with open(input_file, 'r') as f:
        content = f.read()
    
    # Convert
    pfs_content = convert_ini_to_pfs(content)
    
    # Write output
    with open(output_file, 'w') as f:
        f.write(pfs_content)
    
    print(f"Converted '{input_file}' to '{output_file}'")
    print(f"The new file is in proper PFS format compatible with mikeio")


if __name__ == '__main__':
    main()
