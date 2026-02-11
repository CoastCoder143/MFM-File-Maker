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
- No external dependencies (uses only standard library)

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
1. **Input .dfs0 folder**: Directory (folder) containing the .dfs0 file to reference
   - ⚠️ **Important**: Provide the folder path, not the .dfs0 file path itself
   - Example (Windows): `C:\Projects\MyProject\Input` (not `C:\Projects\MyProject\Input\file.dfs0`)
   - Example (Unix/Linux): `/home/user/projects/input` (not `/home/user/projects/input/file.dfs0`)
2. **Output .dfsu folder**: Directory where the output .dfsu file will be saved
3. **Template .mfm file name**: Name of the template file from the `input-mfm` folder

### Example

```
MIKE .mfm File Editor
==================================================
Enter input .dfs0 folder path: test_data/input_dfs0
Enter output .dfsu folder path: test_data/output_dfsu
Enter template .mfm file name (from input-mfm folder): template.mfm

Found .dfs0 file: dredger_data.dfs0
Copied template to: output/template.mfm
Updated [DREDGER_1] file_name to: test_data/input_dfs0/dredger_data.dfs0|
Updated [OUTPUT_1] file_name to: test_data/output_dfsu/template.dfsu

Successfully created and updated output/template.mfm
```

## How It Works

### Template-Based Workflow

1. **Template Storage**: Store your template .mfm files in the `input-mfm` folder with placeholder paths (e.g., `"placeholder.dfs0|"`)
2. **Duplication**: The script copies the template to the `output` folder
3. **Path Updates**: The script performs section-order-aware edits on the copied file

### Section-Aware Parsing

The script parses the .mfm file into sections (e.g., `[DREDGER_1]`, `[MORPHOLOGY]`, etc.) and performs section-order-aware edits:

1. **DREDGER_1 Update**: 
   - Finds the `[DREDGER_1]` section
   - Locates exactly one .dfs0 file in the input folder
   - Updates `file_name = "path"` with the full path to the .dfs0 file
   - Preserves the trailing pipe character: `file_name = "path/file.dfs0|"`

2. **OUTPUT_1 Update**:
   - Finds the `[MORPHOLOGY]` section
   - Locates the first `[OUTPUTS]` section that appears after `[MORPHOLOGY]`
   - Within that scope, finds the `[OUTPUT_1]` section
   - Updates `file_name = "path"` with the output .dfsu file path constructed from the output folder and the .mfm file's base name (e.g., `output_folder/template.dfsu` for `template.mfm`)
   - Does NOT preserve the pipe character

### Error Handling

The script will abort with an error message if:
- The input .dfs0 folder doesn't exist or contains zero or multiple .dfs0 files (ambiguous)
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

## License

MIT License
