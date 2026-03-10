from pathlib import Path
import csv
import shutil
import re

# ------------------- CONFIG -------------------
TEMPLATE_FILE = Path(r"./model_template.mfm")   # your .mfm template file
RUNS_CSV      = Path(r"./runs_template_multidredger.csv")             # list of runs
OUTPUT_DIR    = Path(r"./generated")            # where new copies go

DRY_RUN       = False                             # set False to actually write
# ------------------------------------------------

# Compile regex once
re_weights = re.compile(r"^(?P<indent>\s*)weights_fraction\s*=\s*(?P<rhs>.*)\s*$")
re_fname   = re.compile(r"^(?P<indent>\s*)file_name\s*=\s*(?P<rhs>.*)\s*$")
re_dredge_count = re.compile(
    r"^(?P<indent>\s*)(?P<key>number_of_dredgers|MzSEPfsListItemCount)\s*=\s*(?P<rhs>.*)\s*$"
)

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

def extract_section_block(text: str, section_name: str) -> str:
    """
    Extracts the full text block of a section (including start/end markers):
      [SECTION_NAME]
      ...
      EndSect  // SECTION_NAME

    Returns the block as a string, or an empty string if not found.
    """
    section_start = f"[{section_name}]"
    section_end   = f"EndSect  // {section_name}"
    lines = text.splitlines(True)
    block: list[str] = []
    in_section = False
    for line in lines:
        if not in_section and section_start in line:
            in_section = True
        if in_section:
            block.append(line)
        if in_section and section_end in line:
            break
    return "".join(block)

def patch_dredger_block(block: str, dredger_num: int, file_name: str, weights: str) -> str:
    """
    Given a DREDGER_1 text block, rename it to DREDGER_N and patch
    weights_fraction, file_name, and name with the supplied values.
    """
    new_n = str(dredger_num)
    block = block.replace("[DREDGER_1]", f"[DREDGER_{new_n}]")
    block = block.replace("EndSect  // DREDGER_1", f"EndSect  // DREDGER_{new_n}")
    
    # Update the 'name' field to reflect the dredger number
    block = re.sub(
        r"(\s*)name\s*=\s*'Dredger\s+\d+'",
        f"\\1name = 'Dredger {new_n}'",
        block
    )
    
    block, _ = patch_key_within_section(block, f"DREDGER_{new_n}", re_weights, weights)
    block, _ = patch_key_within_section(block, f"DREDGER_{new_n}", re_fname, file_name)
    return block

def remove_existing_dredgers_except_1(text: str) -> str:
    """
    Removes all [DREDGER_N] sections (N >= 2) from the template text,
    leaving only [DREDGER_1] intact. This prevents duplication when
    the template already has multiple dredger sections.
    """
    lines = text.splitlines(True)
    out = []
    skip = False
    dredger_pattern = re.compile(r"\[DREDGER_(\d+)\]")
    
    for line in lines:
        # Check if this is the start of a DREDGER_N section where N > 1
        m = dredger_pattern.search(line)
        if m:
            n = int(m.group(1))
            if n > 1:
                skip = True
                continue
        
        # Check if we're at the end of a DREDGER_N section where N > 1
        if skip:
            if "EndSect  // DREDGER_" in line:
                skip = False
            continue
        
        out.append(line)
    
    return "".join(out)

def insert_extra_dredgers(text: str, extra_entries: list[tuple[str, str]]) -> str:
    """
    Inserts DREDGER_2, DREDGER_3, … blocks immediately after
    'EndSect  // DREDGER_1' in *text*.

    extra_entries: list of (file_name, weights) tuples for dredgers 2, 3, …
    """
    if not extra_entries:
        return text

    dredger_1_block = extract_section_block(text, "DREDGER_1")
    if not dredger_1_block:
        raise ValueError("Could not find [DREDGER_1] section in template.")

    extra_blocks = []
    for i, (fname, weights) in enumerate(extra_entries, start=2):
        extra_blocks.append(patch_dredger_block(dredger_1_block, i, fname, weights))

    insertion = "\n" + "".join(extra_blocks)
    end_marker = "EndSect  // DREDGER_1"
    idx = text.find(end_marker)
    if idx == -1:
        raise ValueError("Could not find 'EndSect  // DREDGER_1' in template.")
    after_marker = idx + len(end_marker)
    newline_idx = text.find("\n", after_marker)
    if newline_idx == -1:
        newline_idx = len(text)
    return text[: newline_idx + 1] + insertion + text[newline_idx + 1 :]

def patch_dredging_counts(text: str, num_dredgers: int) -> str:
    """
    Updates number_of_dredgers and MzSEPfsListItemCount inside [DREDGING].
    """
    lines = text.splitlines(True)
    out = []
    in_dredging = False
    for line in lines:
        if "[DREDGING]" in line and not in_dredging:
            in_dredging = True
            out.append(line)
            continue
        if in_dredging:
            if "EndSect  // DREDGING" in line:
                in_dredging = False
                out.append(line)
                continue
            m = re_dredge_count.match(line)
            if m:
                out.append(f"{m.group('indent')}{m.group('key')} = {num_dredgers}\n")
                continue
        out.append(line)
    return "".join(out)

def patch_dredger_and_output(
    text: str,
    dredger_entries: list[tuple[str, str]],
    output_file: str,
) -> tuple[str, dict]:
    """
    Patches all dredger sections and the OUTPUT_1 file_name.

    dredger_entries: list of (file_name, weights) tuples, one per dredger.
      - The first entry patches the existing DREDGER_1 section.
      - Additional entries are inserted as DREDGER_2, DREDGER_3, … by cloning
        the DREDGER_1 block from the template; the template itself is never
        modified.
    Returns: (patched_text, counts_dict)
    """
    counts: dict[str, int] = {}
    num_dredgers = len(dredger_entries)

    # Remove any existing DREDGER_2+ sections from the template to prevent duplication
    text = remove_existing_dredgers_except_1(text)

    # Patch DREDGER_1 with the first entry
    fname_1, weights_1 = dredger_entries[0]
    text, c = patch_key_within_section(text, "DREDGER_1", re_weights, weights_1)
    counts["DREDGER_1.weights_fraction"] = c
    text, c = patch_key_within_section(text, "DREDGER_1", re_fname, fname_1)
    counts["DREDGER_1.file_name"] = c

    # Insert DREDGER_2 … DREDGER_N (cloned from DREDGER_1; template unchanged)
    if num_dredgers > 1:
        text = insert_extra_dredgers(text, dredger_entries[1:])
        for i in range(2, num_dredgers + 1):
            counts[f"DREDGER_{i}.file_name"] = 1

    # Keep DREDGING header counts in sync
    text = patch_dredging_counts(text, num_dredgers)
    counts["DREDGING.number_of_dredgers"] = num_dredgers

    # OUTPUT_1 file_name
    text, c = patch_key_within_section(text, "OUTPUT_1", re_fname, output_file)
    counts["OUTPUT_1.file_name"] = c

    return text, counts

def get_dredger_columns(fieldnames: list[str]) -> list[tuple[str, str | None]]:
    """
    Detects dredger columns from the CSV header and returns an ordered list of
    (file_col, weights_col_or_None) tuples.

    Supported formats:
      Legacy (single dredger):
        dredger_file_name                          → 1 dredger, global weights_fraction
      Numbered (dynamic):
        dredger_1_file_name [, dredger_1_weights]
        dredger_2_file_name [, dredger_2_weights]
        …                                          → N dredgers; per-dredger weights
                                                     optional (falls back to weights_fraction)
    """
    has_numbered = any(re.match(r"dredger_\d+_file_name", f) for f in fieldnames)

    if not has_numbered:
        if "dredger_file_name" not in fieldnames:
            raise ValueError(
                "CSV must have either 'dredger_file_name' or numbered columns "
                "'dredger_1_file_name' [, 'dredger_2_file_name', …]."
            )
        return [("dredger_file_name", None)]

    numbered: list[tuple[int, str, str | None]] = []
    for f in fieldnames:
        m = re.match(r"dredger_(\d+)_file_name", f)
        if m:
            n = int(m.group(1))
            wt_col = f"dredger_{n}_weights"
            numbered.append((n, f, wt_col if wt_col in fieldnames else None))

    numbered.sort(key=lambda x: x[0])
    return [(col, wt_col) for _, col, wt_col in numbered]

def main():
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_FILE}")
    if not RUNS_CSV.exists():
        raise FileNotFoundError(f"CSV not found: {RUNS_CSV}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # .mfm is treated as a plain text file (same as editing in Notepad)

    with RUNS_CSV.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required = {"run_name", "weights_fraction", "output_file_name"}
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(f"CSV must have columns: {required}. Found: {reader.fieldnames}")

        dredger_cols = get_dredger_columns(reader.fieldnames or [])

        count = 0
        for row in reader:
            run_name    = safe_filename(row["run_name"])
            global_weights = normalize_weights(row["weights_fraction"])
            output_file = normalize_pipe_path(row["output_file_name"])

            # Build per-dredger (file_name, weights) list
            dredger_entries: list[tuple[str, str]] = []
            for file_col, wt_col in dredger_cols:
                fname   = normalize_pipe_path(row[file_col])
                raw_wt  = row[wt_col].strip() if wt_col else ""
                weights = normalize_weights(raw_wt) if raw_wt else global_weights
                dredger_entries.append((fname, weights))

            out_file = OUTPUT_DIR / f"{run_name}{TEMPLATE_FILE.suffix}"

            print(f"\n[{count+1}] Generate: {out_file}")
            for i, (fn, w) in enumerate(dredger_entries, start=1):
                print(f"    DREDGER_{i}.weights_fraction = {w}")
                print(f"    DREDGER_{i}.file_name        = {fn}")
            print(f"    OUTPUT_1.file_name         = {output_file}")

            if not DRY_RUN:
                # 1) duplicate template
                shutil.copy2(TEMPLATE_FILE, out_file)

                # 2) patch the copy
                text = out_file.read_text(encoding="utf-8")
                patched, counts = patch_dredger_and_output(text, dredger_entries, output_file)
                out_file.write_text(patched, encoding="utf-8")

                # Basic safety warnings if nothing got replaced (usually means section name differs)
                for k, v in counts.items():
                    if v == 0:
                        print(f"WARNING: did not replace {k} (check section name or key spelling).")

            count += 1

    print(f"\nDone. Prepared {count} file(s). (dry_run={DRY_RUN})")

if __name__ == "__main__":
    main()