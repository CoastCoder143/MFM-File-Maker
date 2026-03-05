# MFM-File-Maker

A professional tool for generating run-specific MIKE FM model files (`.mfm`) from templates and CSV parameters. Automates batch creation of model configurations for parameter studies and sensitivity analysis.

## Quick Navigation

| Section | Description |
|---------|-------------|
| **[Installation](#1-install-uv-first-time-only)** | Get uv up and running |
| **[Getting Started](#2-clone-and-enter-the-project)** | Clone and sync the project |
| **[Usage](#4-run-the-tool)** | Create template-based model runs |
| **[CSV Format](#csv-format)** | Input file structure |
| **[Contributing](CONTRIBUTING.md)** | Report issues, request features, submit PRs |
| **[License](#license)** | MIT License |

## What It Does

- ✅ Copies a template `.mfm` file for each CSV row
- ✅ Patches values inside specified sections (`[DREDGER_1]`, `[OUTPUT_1]`)
- ✅ Normalizes weights and file paths automatically
- ✅ Generates sanitized filenames
- ✅ Supports dry-run mode for validation

## 1) Install uv (first-time only)

### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### macOS / Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Confirm installation:
```bash
uv --version
```

## 2) Clone and enter the project

```bash
git clone <your-repo-url>
cd MFM-File-Maker
```

## 3) Create and sync the virtual environment

From the project root, run:
```bash
uv sync
```

What this does:
- Creates `.venv/` automatically (if missing)
- Installs dependencies from `pyproject.toml`
- Uses `uv.lock` for reproducible versions

## 4) Run the tool

Use `uv run` so you do not need to manually activate `.venv`.

### Quick Start

1. **Place your template file** in the project root (or update `TEMPLATE_FILE` path in `src/make_runs.py`)
2. **Create a `runs.csv`** in the project root with your run parameters
3. **Run the script**:

```bash
uv run python make_runs.py
```

**Important:** By default, the script runs in **dry-run mode** (no files written). To actually generate files, edit `src/make_runs.py` and set:
```python
DRY_RUN = False
```

Output files are written to `generated/`.

## CSV Format

Required columns (header row must include all):

| Column | Description | Example |
|--------|-------------|---------|
| `run_name` | Name for this run (becomes filename) | `Run_01` |
| `weights_fraction` | Comma or space-separated weights | `40 40 20 0 0 0` or `40.0,40.0,20.0,0,0,0` |
| `dredger_file_name` | Path to dredger file | `dredger_a.dfsu` |
| `output_file_name` | Path to output file | `output_a.dfsu` |

### Example CSV

```csv
run_name,weights_fraction,dredger_file_name,output_file_name
Run 01,"40 40 20 0 0 0",dredger_a.dfsu,output_a.dfsu
Run 02,"40.0,40.0,20.0,0,0,0",|dredger_b.dfsu|,|output_b.dfsu|
Run 03,"30 30 30 10 0 0",dredger_c.dfsu,output_c.dfsu
```

**Notes:**
- `weights_fraction` can be space- or comma-separated; normalized to one decimal place
- `dredger_file_name` and `output_file_name` are automatically wrapped as `|path|` if not already
- `run_name` is sanitized into safe filename (spaces become `_`)

## Template Expectations

Your template `.mfm` file must contain these sections and keys:

```
[DREDGER_1]
    weights_fraction = ...
    file_name = ...
EndSect  // DREDGER_1

[OUTPUT_1]
    file_name = ...
EndSect  // OUTPUT_1
```

The script will find and replace values within these sections only.

## Configuration

Edit the top of `src/make_runs.py` to customize paths:

```python
TEMPLATE_FILE = Path(r"./model_template.mfm")   # Your template file
RUNS_CSV      = Path(r"./runs.csv")             # Your run parameters
OUTPUT_DIR    = Path(r"./generated")            # Output folder
DRY_RUN       = True                             # Set False to write files
```

## Dry Run vs Write Mode

- **`DRY_RUN = True`** (default): Prints what would be generated, no files written
- **`DRY_RUN = False`**: Writes files to `generated/` folder

Use dry-run mode first to validate your CSV and template setup!

## Repository Structure

```
MFM-File-Maker/
├── src/
│   ├── __init__.py
│   └── make_runs.py           # Main generator module
├── tests/
│   ├── runs.csv               # Sample CSV input
│   └── MT2D_202603_SI-CB4_12pm.mfm  # Sample template
├── docs/                       # Documentation (future)
├── generated/                  # Generated .mfm files (output)
├── make_runs.py                # Entry point wrapper
├── pyproject.toml              # Project metadata & dependencies
├── uv.lock                     # Locked dependency versions
├── LICENSE                     # MIT License
├── CONTRIBUTING.md             # Contribution guidelines
└── README.md                   # This file
```

## Troubleshooting

### `uv` not found
Reopen terminal after installation, then run `uv --version`.

### Permission error activating `.venv` on Windows
Use `uv run ...` instead of activation, or allow local scripts:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### "Template not found"
Ensure your template `.mfm` file exists at the path specified in `TEMPLATE_FILE` (default: `./model_template.mfm`).

### "CSV not found"
Ensure `runs.csv` exists at the path specified in `RUNS_CSV` (default: `./runs.csv`).

### Warnings about replacements
Section or key names in your template differ from expected format. Check:
- Section names: `[DREDGER_1]`, `[OUTPUT_1]`
- Key names: `weights_fraction`, `file_name`
- Proper `EndSect  // SECTION_NAME` closures

## Getting Help

- 🐛 **Found a bug?** — Open an [issue on GitHub](https://github.com/CoastCoder143/Code-Work/issues)
- 💡 **Have a feature request?** — Discuss it in [GitHub Discussions](https://github.com/CoastCoder143/Code-Work/discussions) or open an issue
- 🤝 **Want to contribute?** — See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

**Author:** CHWY
