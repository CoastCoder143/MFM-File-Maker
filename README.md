# MFM-File-Maker

Generate run-specific model files from a template and a CSV of run parameters.

## What it does
- Copies a template file for each CSV row
- Patches values inside two sections:
  - `[DREDGER_1]` -> `weights_fraction`, `file_name`
  - `[OUTPUT_1]` -> `file_name`

## Requirements
- Python 3.8+ (uses `pathlib`, `csv`, `re`, `shutil`)

## Files
- `make_runs.py` (script)
- `model_template.mfm` (template file; you provide this)
- `runs.csv` (input rows; you provide this)
- `generated/` (output folder; created automatically)

## Quick start
1) Put your template file at `model_template.mfm` in this folder.
2) Create a `runs.csv` in this folder using the format below.
3) Open `make_runs.py` and set `DRY_RUN = False` when ready.
4) Run:

```bash
python make_runs.py
```

## CSV format
Required columns (header row must include all):

- `run_name`
- `weights_fraction`
- `dredger_file_name`
- `output_file_name`

Example:

```csv
run_name,weights_fraction,dredger_file_name,output_file_name
Run 01,"40 40 20 0 0 0",dredger_a.dfsu,output_a.dfsu
Run 02,"40.0,40.0,20.0,0,0,0",|dredger_b.dfsu|,|output_b.dfsu|
```

Notes:
- `weights_fraction` can be space- or comma-separated; it is normalized to one decimal place.
- `dredger_file_name` and `output_file_name` are wrapped as `|path|` if not already.
- `run_name` is sanitized into a safe filename (spaces become `_`).

## Template expectations
The template must contain these sections and keys:

```
[DREDGER_1]
    weights_fraction = ...
    file_name = ...
EndSect  // DREDGER_1

[OUTPUT_1]
    file_name = ...
EndSect  // OUTPUT_1
```

If a key is not found within the section, a warning is printed.

## Configuration
Edit the top of `make_runs.py` if you want different paths:

- `TEMPLATE_FILE` (default: `./model_template.mfm`)
- `RUNS_CSV` (default: `./runs.csv`)
- `OUTPUT_DIR` (default: `./generated`)
- `DRY_RUN` (default: `True`)

## Dry run vs write
- `DRY_RUN = True`: prints what would be generated, no files written.
- `DRY_RUN = False`: writes files to `generated/`.

## .mfm handling
The script treats `.mfm` as plain text (same as opening and editing in Notepad) and writes a new `.mfm` per run.

## Troubleshooting
- "Template not found" -> ensure `model_template.mfm` exists in this folder.
- "CSV not found" -> ensure `runs.csv` exists in this folder.
- Warnings about replacements -> section or key names differ from the template.
