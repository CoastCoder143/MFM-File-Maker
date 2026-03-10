# MFM-File-Maker

Generate run-specific model files from a template and a CSV of run parameters.

## What it does
- Copies a template file for each CSV row
- Patches values inside dredger and output sections:
  - `[DREDGER_1]` → `weights_fraction`, `file_name`
  - `[DREDGER_2]`, `[DREDGER_3]`, … (generated dynamically; template unchanged)
  - `[OUTPUT_1]` → `file_name`
- Supports a **dynamic number of dredgers** per run, driven entirely by the CSV.

## Requirements
- Python 3.10+ (uses `pathlib`, `csv`, `re`, `shutil`)

## Files
- `make_runs.py` (script)
- `model_template.mfm` (template file; you provide this)
- `runs.csv` (input rows; you provide this)
- `runs_template_multidredger.csv` (example CSV with multiple dredgers)
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

### Single dredger (legacy / default)

Required columns:

| Column | Description |
|---|---|
| `run_name` | Identifier used as the output filename |
| `weights_fraction` | Sediment fraction weights (space- or comma-separated) |
| `dredger_file_name` | Path to the dredger `.dfs0` source file |
| `output_file_name` | Path for the output `.dfsu` result file |

Example:

```csv
run_name,weights_fraction,dredger_file_name,output_file_name
Run 01,"40 40 20 0 0 0",dredger_a.dfs0,output_a.dfsu
Run 02,"40.0,40.0,20.0,0,0,0",|dredger_b.dfs0|,|output_b.dfsu|
```

### Multiple dredgers (dynamic)

Replace `dredger_file_name` with numbered columns:
`dredger_1_file_name`, `dredger_2_file_name`, … (add as many as needed).

You may also add per-dredger weight overrides with matching
`dredger_1_weights`, `dredger_2_weights`, … columns.
If a `dredger_N_weights` value is blank or the column is omitted,
`weights_fraction` is used for that dredger.

| Column | Description |
|---|---|
| `run_name` | Identifier used as the output filename |
| `weights_fraction` | Default weights applied to any dredger with no explicit weights |
| `dredger_1_file_name` | Path for the first dredger's `.dfs0` file |
| `dredger_1_weights` *(optional)* | Per-dredger weight override for dredger 1 |
| `dredger_2_file_name` | Path for the second dredger's `.dfs0` file |
| `dredger_2_weights` *(optional)* | Per-dredger weight override for dredger 2 |
| … | Add more numbered columns as needed |
| `output_file_name` | Path for the output `.dfsu` result file |

Example:

```csv
run_name,weights_fraction,dredger_1_file_name,dredger_1_weights,dredger_2_file_name,dredger_2_weights,output_file_name
Run_multi_01,"49 43 8 0 0 0",dredger_a.dfs0,"40 40 20 0 0 0",dredger_b.dfs0,"0 0 0 49 43 8",output_01.dfsu
Run_multi_02,"40 40 20 0 0 0",dredger_c.dfs0,,dredger_d.dfs0,,output_02.dfsu
```

Notes:
- `weights_fraction` (and per-dredger overrides) can be space- or comma-separated; values are normalized to one decimal place.
- `dredger_*_file_name` and `output_file_name` are wrapped as `|path|` if not already.
- `run_name` is sanitized into a safe filename (spaces become `_`).
- See `runs_template_multidredger.csv` for a complete example with 1-5 dredgers.

## Template expectations
The template must contain a `[DREDGER_1]` section with `weights_fraction` and
`file_name` keys, and an `[OUTPUT_1]` section with a `file_name` key:

```
[DREDGING]
   number_of_dredgers = 1
   MzSEPfsListItemCount = 1
   [DREDGER_1]
       weights_fraction = ...
       file_name = ...
   EndSect  // DREDGER_1
EndSect  // DREDGING

[OUTPUT_1]
    file_name = ...
EndSect  // OUTPUT_1
```

When the CSV specifies more than one dredger, the script clones the
`[DREDGER_1]` block to create `[DREDGER_2]`, `[DREDGER_3]`, … sections and
updates `number_of_dredgers` / `MzSEPfsListItemCount` automatically.
**The original template file is never modified.**

**Important:** If your template already contains multiple `[DREDGER_N]` sections (N ≥ 2),
the script will remove them and regenerate clean sections based on your CSV.
Each cloned dredger will have its `name` field updated appropriately
(e.g., 'Dredger 2', 'Dredger 3').

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
- "Template not found" → ensure `model_template.mfm` exists in this folder.
- "CSV not found" → ensure `runs.csv` exists in this folder.
- Warnings about replacements → section or key names differ from the template.
