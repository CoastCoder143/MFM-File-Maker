from pathlib import Path
import csv
import shutil
import re

# ------------------- CONFIG -------------------
TEMPLATE_FILE = Path(r"./model_template.mfm")   # your .mfm template file
RUNS_CSV      = Path(r"./runs.csv")             # list of runs
OUTPUT_DIR    = Path(r"./generated")            # where new copies go

DRY_RUN       = True                             # set False to actually write
# ------------------------------------------------

# Compile regex once
re_weights = re.compile(r"^(?P<indent>\s*)weights_fraction\s*=\s*(?P<rhs>.*)\s*$")
re_fname   = re.compile(r"^(?P<indent>\s*)file_name\s*=\s*(?P<rhs>.*)\s*$")

def normalize_weights(s: str) -> str:
    """
    Accepts:
      - "40.0, 40.0, 20.0, 0, 0, 0"
      - "40 40 20 0 0 0"
    Returns: "40.0, 40.0, 20.0, 0.0, 0.0, 0.0"
    """
    s = s.strip().strip('"').strip("'")
    parts = [p for p in re.split(r"[,\s]+", s) if p]
    floats = [float(p) for p in parts]
    return ", ".join(f"{x:.1f}" for x in floats)

def normalize_pipe_path(s: str) -> str:
    """Ensures the value is wrapped as |path| (your file format style)."""
    s = s.strip().strip('"').strip("'")
    if s.startswith("|") and s.endswith("|"):
        return s
    return f"|{s}|"

def safe_filename(name: str) -> str:
    keep = "._- "
    return "".join(c for c in name if c.isalnum() or c in keep).strip().replace(" ", "_")

def patch_key_within_section(text: str, section_name: str, key_regex: re.Pattern, new_value: str) -> tuple[str, int]:
    """
    Patch a single key (e.g. file_name) ONLY within:
      [SECTION] ... EndSect  // SECTION

    Returns: (patched_text, number_of_replacements_in_that_section)
    """
    lines = text.splitlines(True)  # keep line endings
    out = []
    in_section = False
    replaced = 0

    section_start = f"[{section_name}]"
    section_end   = f"EndSect  // {section_name}"

    for line in lines:
        if section_start in line:
            in_section = True
            out.append(line)
            continue

        if in_section and section_end in line:
            in_section = False
            out.append(line)
            continue

        if in_section:
            m = key_regex.match(line)
            if m:
                # Extract key name from the matched line (everything before the '=')
                key_name = line[:line.find('=')].strip()
                out.append(f"{m.group('indent')}{key_name} = {new_value}\n")
                replaced += 1
                continue

        out.append(line)

    return "".join(out), replaced

def patch_dredger_and_output(text: str, weights: str, dredger_file: str, output_file: str) -> tuple[str, dict]:
    """
    Patches:
      - DREDGER_1: weights_fraction, file_name
      - OUTPUT_1 : file_name
    Returns patched text and a dict of replacement counts.
    """
    counts = {}

    # DREDGER_1 weights_fraction
    text, c = patch_key_within_section(text, "DREDGER_1", re_weights, weights)
    counts["DREDGER_1.weights_fraction"] = c

    # DREDGER_1 file_name
    text, c = patch_key_within_section(text, "DREDGER_1", re_fname, dredger_file)
    counts["DREDGER_1.file_name"] = c

    # OUTPUT_1 file_name (this is the one you asked for)
    text, c = patch_key_within_section(text, "OUTPUT_1", re_fname, output_file)
    counts["OUTPUT_1.file_name"] = c

    return text, counts

def main():
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_FILE}")
    if not RUNS_CSV.exists():
        raise FileNotFoundError(f"CSV not found: {RUNS_CSV}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # .mfm is treated as a plain text file (same as editing in Notepad)
    template_text = TEMPLATE_FILE.read_text(encoding="utf-8")

    with RUNS_CSV.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required = {"run_name", "weights_fraction", "dredger_file_name", "output_file_name"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(f"CSV must have columns: {required}. Found: {reader.fieldnames}")

        count = 0
        for row in reader:
            run_name = safe_filename(row["run_name"])
            weights  = normalize_weights(row["weights_fraction"])
            dredger_file = normalize_pipe_path(row["dredger_file_name"])
            output_file  = normalize_pipe_path(row["output_file_name"])

            out_file = OUTPUT_DIR / f"{run_name}{TEMPLATE_FILE.suffix}"

            print(f"\n[{count+1}] Generate: {out_file}")
            print(f"    DREDGER_1.weights_fraction = {weights}")
            print(f"    DREDGER_1.file_name        = {dredger_file}")
            print(f"    OUTPUT_1.file_name         = {output_file}")

            if not DRY_RUN:
                # 1) duplicate template
                shutil.copy2(TEMPLATE_FILE, out_file)

                # 2) patch the copy
                text = out_file.read_text(encoding="utf-8")
                patched, counts = patch_dredger_and_output(text, weights, dredger_file, output_file)
                out_file.write_text(patched, encoding="utf-8")

                # Basic safety warnings if nothing got replaced (usually means section name differs)
                for k, v in counts.items():
                    if v == 0:
                        print(f"WARNING: did not replace {k} (check section name or key spelling).")

            count += 1

    print(f"\nDone. Prepared {count} file(s). (dry_run={DRY_RUN})")

if __name__ == "__main__":
    main()