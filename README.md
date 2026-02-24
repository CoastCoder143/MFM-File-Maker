# MFM-File-Maker

A Python script to generate MIKE .mfm files from templates by automatically updating file paths in specific sections.

## Overview

This tool uses a template-based workflow to generate MIKE 21 FM .mfm files:
1. Template .mfm files are stored in the `input-mfm` folder with placeholder paths
2. The script copies templates to the `output` folder
3. The script updates paths in the copied files:
   - Updates the `file_name` in the `[DREDGER_1]` section with a matching .dfs0 file from an input folder
   - Updates the `file_name` in the first `[OUTPUT_1]` section after `[MORPHOLOGY]` → `[OUTPUTS]` with an output .dfsu path

## Folder Structure

```
MFM-File-Maker/
├── input-mfm/          # Template .mfm files (with placeholders)
├── output/             # Generated .mfm files (automatically created)
├── edit_mfm.py         # Main script
└── test_data/          # Test data for validation
    ├── input_dfs0/     # Sample .dfs0 files
    └── output_dfsu/    # Sample output folder
```

## Requirements

- Python 3.6 or higher
- No external dependencies required for basic operation
- Optional: `mikeio` for PFS format support (see [MIKEIO Integration](MIKEIO_INTEGRATION.md))

## Usage

Run the script and follow the prompts:

**On Unix/Linux/macOS:**
```bash
python3 edit_mfm.py
```

**On Windows:**
```bash
python edit_mfm.py
```

The script will prompt you for:
1. **Input .dfs0 folder**: Directory (folder) containing the .dfs0 file(s) to reference
   - ⚠️ **Important**: Provide the folder path, not the .dfs0 file path itself
   - Example (Windows): `C:\Projects\MyProject\Input` (not `C:\Projects\MyProject\Input\file.dfs0`)
   - Example (Unix/Linux): `/home/user/projects/input` (not `/home/user/projects/input/file.dfs0`)
   - 💡 **Tip**: You can use quotes around paths with spaces: `"C:\Path With Spaces\Input"`
2. **Output .dfsu folder**: Directory where the output .dfsu file(s) will be saved
3. **Template .mfm file name**: Name of the template file from the `input-mfm` folder
4. **Processing mode**: Choose between:
   - **Single file mode (S)**: Process one .dfs0 file (original behavior)
   - **Multiple file mode (M)**: Batch process multiple .dfs0 files with the same template

### Single File Mode Example

```
MIKE .mfm File Editor
==================================================
Enter input .dfs0 folder path: test_data/input_dfs0
Enter output .dfsu folder path: test_data/output_dfsu
Enter template .mfm file name (from input-mfm folder): template.mfm

==================================================
Process [M]ultiple .dfs0 files or [S]ingle file? (M/S): S

Processing: dredger_data.dfs0
✓ Created: output/template_dredger_data.mfm

Successfully processed 1 file
```

### Batch Processing Mode Example

Process all files or select specific ones:

```
MIKE .mfm File Editor
==================================================
Enter input .dfs0 folder path: test_data/multi_dfs0
Enter output .dfsu folder path: test_data/output_dfsu
Enter template .mfm file name (from input-mfm folder): template.mfm

==================================================
Process [M]ultiple .dfs0 files or [S]ingle file? (M/S): M

Found 6 .dfs0 files in 'test_data/multi_dfs0'

Process [A]ll files, [S]elect specific files, or [Q]uit? A
Selected all 6 files for processing

Processing 6 files...
============================================================

[1/6] Processing: file1.dfs0
    ✓ Created: template_file1.mfm

[2/6] Processing: file2.dfs0
    ✓ Created: template_file2.mfm

...

============================================================
Processing complete: 6 successful, 0 failed
```

**Selective file processing:**
```
Process [A]ll files, [S]elect specific files, or [Q]uit? S

All .dfs0 files in 'test_data/multi_dfs0':
  1. file1.dfs0
  2. file2.dfs0
  3. file3.dfs0
  4. file4.dfs0

Enter file numbers separated by commas (e.g., 1,3,5) or 'all': 1,3,4
Selected 3 file(s): file1.dfs0, file3.dfs0, file4.dfs0
```

## How It Works

### Template-Based Workflow

1. **Template Storage**: Store your template .mfm files in the `input-mfm` folder with placeholder paths (e.g., `"placeholder.dfs0|"`)
2. **Duplication**: The script copies the template to the `output` folder
3. **Path Updates**: The script performs section-order-aware edits on the copied file

### Batch Processing

The script supports two processing modes:

**Single File Mode:**
- Processes one .dfs0 file with the template
- Output filename: `template_basename.mfm`
- Exits with error if processing fails
- Backward compatible with original behavior

**Multiple File Mode:**
- Reuse the same template for multiple .dfs0 files
- Each .dfs0 file generates its own .mfm file
- Output filename: `template_basename_dfs0_basename.mfm`
- Options:
  - Process all .dfs0 files in the folder
  - Select specific files by number (e.g., `1,3,5`)
- **Robust error handling**: Continues processing remaining files even if individual files fail
- Progress tracking with success/failure counts
- Detailed error report at the end listing all failed files and their errors

**Use Cases for Batch Processing:**
- Generate multiple scenarios from the same template
- Process time-series data (e.g., `file_12am.dfs0`, `file_3am.dfs0`, `file_6am.dfs0`)
- Handle multiple locations with one template (e.g., `location1.dfs0`, `location2.dfs0`)

**Error Handling in Batch Mode:**
When processing multiple files, the script will:
1. Validate the template structure before processing any files
2. Continue processing remaining files even if one fails
3. Track which files succeeded and which failed
4. Display detailed error messages for each failure
5. Provide a summary at the end showing success/failure counts
6. List all failed files with their specific error messages

**Template Validation:**
Before processing any files, the script validates that the template has:
- `[DREDGER_1]` section with a `file_name` entry
- `[MORPHOLOGY]` section
- `[OUTPUTS]` section after `[MORPHOLOGY]`
- `[OUTPUT_1]` section after `[OUTPUTS]` with a `file_name` entry

If validation fails, the script stops immediately with a helpful error message explaining what's missing.

Example output with failures:
```
Processing complete: 43 successful, 3 failed

Failed files:
  - file1.dfs0: No file_name found in section [DREDGER_1]
  - file2.dfs0: Section [MORPHOLOGY] not found
  - file3.dfs0: No [OUTPUT_1] section found after [MORPHOLOGY] -> [OUTPUTS]
```

### Template Structure Requirements

Templates must follow this structure to work correctly:

```
[DREDGER_1]
file_name = "placeholder.dfs0|"    # Required: Will be updated with actual .dfs0 path
# ... other dredger settings ...

[MORPHOLOGY]
# ... morphology settings ...

[OUTPUTS]
number_of_outputs = 1

[OUTPUT_1]
file_name = "placeholder.dfsu"    # Required: Will be updated with output .dfsu path
# ... other output settings ...
```

**Key Requirements:**
- Must have `[DREDGER_1]` section with `file_name` entry
- Must have `[MORPHOLOGY]` section  
- Must have `[OUTPUTS]` section after `[MORPHOLOGY]`
- Must have `[OUTPUT_1]` section after `[OUTPUTS]` with `file_name` entry
- The `file_name` entries can contain placeholder values - they will be replaced during processing

The script validates these requirements before processing any files and will provide clear error messages if anything is missing.

### Section-Aware Parsing

The script parses the .mfm file into sections (e.g., `[DREDGER_1]`, `[MORPHOLOGY]`, etc.) and performs section-order-aware edits:

1. **DREDGER_1 Update**: 
   - Finds the `[DREDGER_1]` section
   - Locates .dfs0 file in the input folder (see "Smart File Matching" below)
   - Updates `file_name = "path"` with the full path to the .dfs0 file
   - Preserves the trailing pipe character: `file_name = "path/file.dfs0|"`

2. **OUTPUT_1 Update**:
   - Finds the `[MORPHOLOGY]` section
   - Locates the first `[OUTPUTS]` section that appears after `[MORPHOLOGY]`
   - Within that scope, finds the `[OUTPUT_1]` section
   - Updates `file_name = "path"` with the output .dfsu file path
   - In batch mode: Each output file gets a unique name (e.g., `template_file1.dfsu`, `template_file2.dfsu`)
   - Does NOT preserve the pipe character

### Smart File Matching

When there are multiple .dfs0 files in the input folder, the script uses intelligent matching:

1. **Auto-matching** (Single File Mode): Attempts to match the template filename to a .dfs0 file
   - Example: Template `MT2D_202602_SI-CB1_3am.mfm` → Auto-selects `40_SI-CB1_3am.dfs0`
   - Extracts meaningful parts from the template name (ignoring dates and common prefixes)
   - Searches for .dfs0 files containing matching patterns

2. **Interactive Selection**: If multiple matches are found or no match is found:
   - Lists all .dfs0 files in the folder with numbers
   - Prompts user to select the correct file
   - Example:
     ```
     All .dfs0 files in 'data/input':
       1. file1.dfs0
       2. file2.dfs0
       3. file3.dfs0
     
     Enter the number of the file to use (or 'q' to quit): 
     ```

3. **Single File**: If only one .dfs0 file exists, uses it automatically

### Error Handling

The script will abort with an error message if:
- The input .dfs0 folder doesn't exist or contains zero .dfs0 files
- The output .dfsu folder doesn't exist
- The template .mfm file doesn't exist in the `input-mfm` folder
- Required sections (`[DREDGER_1]`, `[MORPHOLOGY]`, `[OUTPUTS]`, `[OUTPUT_1]`) are missing
- Multiple instances of required sections exist (ambiguous)

## Testing

A test dataset is provided in the `test_data/` directory, and a sample template is in `input-mfm/`:

```bash
# Run the script with test data (use 'python' on Windows, 'python3' on Unix/Linux/macOS)
python3 edit_mfm.py
# Then enter:
# test_data/input_dfs0
# test_data/output_dfsu
# template.mfm
```

This will create a new file `output/template.mfm` with the correct paths.

## Creating Templates

To create a new template:
1. Create your .mfm file with placeholder paths
2. Save it in the `input-mfm` folder
3. Use placeholder values like:
   - `file_name = "placeholder.dfs0|"` for DREDGER_1
   - `file_name = "placeholder.dfsu"` for OUTPUT_1

The script will replace these placeholders with actual paths when generating output files.

## MIKEIO Integration

This tool uses a lightweight regex-based approach for editing .mfm files, which works well for the simplified format used in templates.

For users who need proper PFS format files or integration with MIKE tools:
- 📖 Read [MIKEIO Research](MIKEIO_RESEARCH.md) for detailed information about MIKEIO
- 🔄 Read [MIKEIO Integration Guide](MIKEIO_INTEGRATION.md) for migration instructions
- 🛠️ Use `convert_to_pfs.py` to convert templates to PFS format

```bash
# Optional: Install MIKEIO
pip install -r requirements.txt

# Convert template to PFS format
python convert_to_pfs.py input-mfm/template.mfm input-mfm/template_pfs.mfm
```

## License

MIT License
