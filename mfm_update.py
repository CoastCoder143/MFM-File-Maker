#!/usr/bin/env python3
"""
CLI tool to batch-edit MIKE FM .mfm files from a CSV mapping file.

Each row in the CSV produces one output .mfm file where the dredger path,
weights_fraction, and output dfsu path are updated inside their respective
sections without touching anything else in the file.

Usage:
    python mfm_update.py --template path/to/template.mfm \\
                         --csv path/to/list.csv \\
                         --outdir path/to/out

Optional flags:
    --dry-run     Print what would change without writing files.
    --in-place    Edit the template file directly (ignores --outdir).
    --suffix      Append to scenario name in output filename.
    --encoding    File encoding (default: utf-8).
    --backup      Write a .bak backup before overwriting an existing file.
"""

import argparse
import csv
import os
import shutil
import sys

from mfm_editor import (
    find_block,
    get_key_value_in_block,
    update_mfm_content,
    validate_weights_fraction,
)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            'Batch-edit MIKE FM .mfm files by updating specific keys '
            'inside specific sections using a CSV mapping file.'
        )
    )
    parser.add_argument(
        '--template', required=True,
        help='Path to the template .mfm file.'
    )
    parser.add_argument(
        '--csv', required=True, dest='csv_file',
        help='Path to the CSV mapping file.'
    )
    parser.add_argument(
        '--outdir', required=True,
        help='Output directory for generated .mfm files.'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Print changes without writing any files.'
    )
    parser.add_argument(
        '--in-place', action='store_true', dest='in_place',
        help='Edit the template file directly (default: write new files).'
    )
    parser.add_argument(
        '--suffix', default='',
        help='Suffix appended to the scenario name in the output filename.'
    )
    parser.add_argument(
        '--encoding', default='utf-8',
        help='File encoding used for reading and writing (default: utf-8).'
    )
    parser.add_argument(
        '--backup', action='store_true',
        help='Write a .bak backup before overwriting an existing file.'
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# CSV reading
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {'scenario', 'dredger_dfs0', 'weights_fraction', 'output_dfsu'}


def read_csv(csv_path, encoding='utf-8'):
    """
    Read the CSV mapping file and return a list of row dicts.

    Args:
        csv_path: Path to the CSV file.
        encoding: File encoding.

    Returns:
        List of dicts, one per data row.

    Raises:
        ValueError: If required columns are missing.
        IOError:    If the file cannot be opened.
    """
    try:
        with open(csv_path, 'r', encoding=encoding, errors='replace',
                  newline='') as fh:
            reader = csv.DictReader(fh)
            fieldnames = reader.fieldnames or []
            missing = REQUIRED_COLUMNS - set(fieldnames)
            if missing:
                raise ValueError(
                    f"CSV '{csv_path}' is missing required columns: "
                    f"{sorted(missing)}"
                )
            return list(reader)
    except (IOError, OSError) as exc:
        raise IOError(f"Cannot read CSV file '{csv_path}': {exc}") from exc


# ---------------------------------------------------------------------------
# Row validation
# ---------------------------------------------------------------------------

def validate_row(row):
    """
    Validate a single CSV row.

    Raises ValueError if weights_fraction is invalid.  Returns a list of
    warning strings for extension mismatches (non-fatal).

    Args:
        row: Dict with keys scenario, dredger_dfs0, weights_fraction,
             output_dfsu.

    Returns:
        List of warning strings (may be empty).

    Raises:
        ValueError: If weights_fraction is not comma-separated numbers.
    """
    validate_weights_fraction(row['weights_fraction'])

    warnings = []
    if not row['dredger_dfs0'].lower().endswith('.dfs0'):
        warnings.append(
            f"dredger_dfs0 '{row['dredger_dfs0']}' does not end with .dfs0"
        )
    if not row['output_dfsu'].lower().endswith('.dfsu'):
        warnings.append(
            f"output_dfsu '{row['output_dfsu']}' does not end with .dfsu"
        )
    return warnings


# ---------------------------------------------------------------------------
# Single-scenario processing
# ---------------------------------------------------------------------------

def _extract_old_values(lines):
    """
    Extract the current file_name / weights_fraction values from *lines*
    for logging purposes.  Returns a dict with keys:
      old_dredger, old_weights, old_output.
    Any value that cannot be found is represented as '<not found>'.
    """
    def _safe(lines, section, *path_sections):
        try:
            start, end = find_block(lines, section)
            for sub in path_sections:
                start, end = find_block(lines, sub, start, end)
            val = get_key_value_in_block(lines, start, end, 'file_name')
            return val if val is not None else '<not found>'
        except ValueError:
            return '<not found>'

    def _safe_weights(lines):
        try:
            ds, de = find_block(lines, 'DREDGING')
            d1s, d1e = find_block(lines, 'DREDGER_1', ds, de)
            val = get_key_value_in_block(lines, d1s, d1e, 'weights_fraction')
            return val if val is not None else '<not found>'
        except ValueError:
            return '<not found>'

    return {
        'old_dredger': _safe(lines, 'DREDGING', 'DREDGER_1'),
        'old_weights': _safe_weights(lines),
        'old_output': _safe(lines, 'OUTPUTS', 'OUTPUT_1'),
    }


def process_scenario(row, template_path, outdir,
                     dry_run=False, in_place=False,
                     suffix='', encoding='utf-8', backup=False):
    """
    Process one scenario row.

    Args:
        row:           Dict with CSV columns.
        template_path: Path to the template .mfm file.
        outdir:        Output directory (used unless *in_place* is True).
        dry_run:       If True, print changes without writing.
        in_place:      If True, overwrite the template file.
        suffix:        Appended to scenario name in output filename.
        encoding:      File encoding.
        backup:        Write a .bak backup if the output file already exists.

    Returns:
        Output path string (or the template path when *in_place* is True).
        Returns None when *dry_run* is True.

    Raises:
        ValueError: On any structural or validation error.
        IOError:    On file read/write error.
    """
    scenario = row['scenario']
    dredger_dfs0 = row['dredger_dfs0']
    weights_fraction = row['weights_fraction']
    output_dfsu = row['output_dfsu']

    # Warn about non-fatal issues
    warnings = validate_row(row)
    for w in warnings:
        print(f"  WARNING: {w}", file=sys.stderr)

    # Read template
    with open(template_path, 'r', encoding=encoding, errors='replace') as fh:
        lines = fh.readlines()

    # Capture old values for logging
    old = _extract_old_values(lines)

    # Apply section-aware edits
    new_lines = update_mfm_content(lines, dredger_dfs0, weights_fraction,
                                   output_dfsu)

    # Determine output path
    if in_place:
        out_path = template_path
    else:
        filename = f"{scenario}{suffix}.mfm"
        out_path = os.path.join(outdir, filename)

    # Log one concise line
    print(
        f"scenario={scenario}  "
        f"dredger: {old['old_dredger']} -> {dredger_dfs0}  "
        f"weights: {old['old_weights']} -> {weights_fraction}  "
        f"output: {old['old_output']} -> {output_dfsu}"
    )

    if dry_run:
        changed = [
            (i + 1, lines[i].rstrip(), new_lines[i].rstrip())
            for i in range(len(lines))
            if lines[i] != new_lines[i]
        ]
        for lineno, old_line, new_line in changed:
            print(f"  [DRY-RUN] line {lineno}: {old_line!r} -> {new_line!r}")
        return None

    # Write output
    os.makedirs(outdir, exist_ok=True)
    if backup and os.path.exists(out_path):
        shutil.copy2(out_path, out_path + '.bak')

    with open(out_path, 'w', encoding=encoding) as fh:
        fh.writelines(new_lines)

    return out_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    args = parse_args(argv)

    # Validate inputs
    if not os.path.isfile(args.template):
        print(f"Error: Template file not found: {args.template}",
              file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(args.csv_file):
        print(f"Error: CSV file not found: {args.csv_file}", file=sys.stderr)
        sys.exit(1)

    # Read CSV
    try:
        rows = read_csv(args.csv_file, encoding=args.encoding)
    except (ValueError, IOError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print("Error: CSV file contains no data rows.", file=sys.stderr)
        sys.exit(1)

    # Process each scenario
    success_count = 0
    fail_count = 0

    for row in rows:
        scenario = row.get('scenario', '?')
        try:
            out_path = process_scenario(
                row,
                template_path=args.template,
                outdir=args.outdir,
                dry_run=args.dry_run,
                in_place=args.in_place,
                suffix=args.suffix,
                encoding=args.encoding,
                backup=args.backup,
            )
            if not args.dry_run:
                print(f"  -> wrote: {out_path}")
            success_count += 1
        except (ValueError, IOError, OSError) as exc:
            print(
                f"Error processing scenario '{scenario}': {exc}",
                file=sys.stderr
            )
            fail_count += 1

    print(f"\n{success_count} succeeded, {fail_count} failed")
    if fail_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
