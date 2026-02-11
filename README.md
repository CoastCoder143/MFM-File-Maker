# MFM-File-Maker

A Python script to edit MIKE .mfm files by automatically updating file paths in specific sections.

## Overview

This tool edits MIKE 21 FM .mfm files by:
1. Updating the `file_name` in the `[DREDGER_1]` section with a matching .dfs0 file from an input folder
2. Updating the `file_name` in the first `[OUTPUT_1]` section after `[MORPHOLOGY]` → `[OUTPUTS]` with an output .dfsu path

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Usage

Run the script and follow the prompts:

```bash
python3 edit_mfm.py
```

The script will prompt you for:
1. **Input .dfs0 folder**: Directory containing the .dfs0 file to reference
2. **Output .dfsu folder**: Directory where the output .dfsu file will be saved
3. **.mfm file path**: Path to the .mfm file to edit

### Example

```
MIKE .mfm File Editor
==================================================
Enter input .dfs0 folder path: /path/to/dfs0_files
Enter output .dfsu folder path: /path/to/dfsu_output
Enter .mfm file path: /path/to/project.mfm
```

## How It Works

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
   - Updates `file_name = "path"` with the output .dfsu file path constructed from the output folder and the .mfm file's base name (e.g., `output_folder/sample.dfsu` for `sample.mfm`)
   - Does NOT preserve the pipe character

### Error Handling

The script will abort with an error message if:
- The input .dfs0 folder doesn't exist or contains zero or multiple .dfs0 files (ambiguous)
- The output .dfsu folder doesn't exist
- The .mfm file doesn't exist
- Required sections (`[DREDGER_1]`, `[MORPHOLOGY]`, `[OUTPUTS]`, `[OUTPUT_1]`) are missing
- Multiple instances of required sections exist (ambiguous)

## Testing

A test dataset is provided in the `test_data/` directory:

```bash
# Run the script with test data
python3 edit_mfm.py
# Then enter:
# test_data/input_dfs0
# test_data/output_dfsu
# test_data/sample.mfm
```

This will update the sample .mfm file with the correct paths.

## License

MIT License
