"""
Pure functions for section-aware editing of MIKE FM .mfm text files.

This module provides utilities to locate, read, and replace specific keys
inside specific nested sections of a .mfm file without touching anything
else in the file.

Targeted edits:
  [DREDGING] > [DREDGER_1]  ->  file_name, weights_fraction
  [OUTPUTS]  > [OUTPUT_1]   ->  file_name

Path values are wrapped with pipe characters in .mfm format:
  file_name = |\\server\\share\\file.dfs0|
"""

import re


def find_block(lines, section_name, search_start=0, search_end=None):
    """
    Find the first [section_name] ... EndSect // section_name block within
    lines[search_start : search_end + 1].

    Args:
        lines:         List of file lines (strings).
        section_name:  Name without brackets, e.g. 'DREDGING'.
        search_start:  Start index (inclusive) to search from.
        search_end:    End index (inclusive) to search up to; defaults to
                       len(lines) - 1.

    Returns:
        (start_idx, end_idx) - both absolute indices into *lines*, inclusive.

    Raises:
        ValueError: if the block is not found or is not closed.
    """
    if search_end is None:
        search_end = len(lines) - 1

    header_re = re.compile(r'^\s*\[' + re.escape(section_name) + r'\]\s*$')
    footer_re = re.compile(
        r'^\s*EndSect\s+//\s*' + re.escape(section_name) + r'\s*$'
    )

    start = None
    for i in range(search_start, search_end + 1):
        if header_re.match(lines[i]):
            start = i
            break

    if start is None:
        raise ValueError(
            f"[{section_name}] block not found "
            f"(searched lines {search_start + 1}–{search_end + 1})"
        )

    for i in range(start + 1, search_end + 1):
        if footer_re.match(lines[i]):
            return (start, i)

    raise ValueError(
        f"[{section_name}] block starting at line {start + 1} is not closed "
        f"(missing 'EndSect  // {section_name}')"
    )


def get_key_value_in_block(lines, start, end, key):
    """
    Return the raw value of *key* within lines[start : end + 1].

    The returned string is the entire right-hand side after ``key =``,
    stripped of leading/trailing whitespace.  Returns ``None`` if the key
    is not present.

    Args:
        lines:  List of file lines.
        start:  Block start index (inclusive).
        end:    Block end index (inclusive).
        key:    Key name, e.g. 'file_name'.

    Returns:
        Value string, or None.
    """
    key_re = re.compile(r'^\s*' + re.escape(key) + r'\s*=\s*(.+?)\s*$')
    for i in range(start, end + 1):
        m = key_re.match(lines[i])
        if m:
            return m.group(1)
    return None


def replace_key_in_block(lines, start, end, key, new_value, pipe_wrap=False):
    """
    Replace exactly one ``key = <value>`` line within lines[start : end + 1].

    The replacement preserves the original indentation and spacing around
    the ``=`` sign.  The original line ending (``\\r\\n`` or ``\\n``) is
    also preserved.

    Args:
        lines:      List of file lines (modified *in-place*).
        start:      Block start index (inclusive).
        end:        Block end index (inclusive).
        key:        Key name to replace, e.g. 'file_name'.
        new_value:  New value string.
        pipe_wrap:  If True, wrap *new_value* in pipe characters:
                    ``|new_value|``.

    Raises:
        ValueError: if zero or more than one matching lines are found.
    """
    key_re = re.compile(
        r'^(\s*)' + re.escape(key) + r'(\s*=\s*)(.*)$'
    )

    matches = []
    for i in range(start, end + 1):
        if key_re.match(lines[i]):
            matches.append(i)

    if len(matches) == 0:
        raise ValueError(
            f"Key '{key}' not found in block "
            f"(lines {start + 1}–{end + 1})"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Duplicate '{key}' entries found in block at lines "
            f"{[m + 1 for m in matches]} — expected exactly one"
        )

    idx = matches[0]
    m = key_re.match(lines[idx])
    indent = m.group(1)
    eq_part = m.group(2)   # preserves spacing around '='

    # Preserve original line ending
    orig = lines[idx]
    eol = '\r\n' if orig.endswith('\r\n') else '\n'

    if pipe_wrap:
        lines[idx] = f"{indent}{key}{eq_part}|{new_value}|{eol}"
    else:
        lines[idx] = f"{indent}{key}{eq_part}{new_value}{eol}"


def validate_weights_fraction(value):
    """
    Validate that *value* is a comma-separated list of numbers (int or float).

    Args:
        value: String from the CSV weights_fraction column.

    Raises:
        ValueError: if the string is empty or contains non-numeric tokens.
    """
    parts = [p.strip() for p in value.split(',')]
    if not parts or parts == ['']:
        raise ValueError("weights_fraction is empty")
    for part in parts:
        try:
            float(part)
        except ValueError:
            raise ValueError(
                f"weights_fraction '{value}' is invalid: "
                f"'{part}' is not a number"
            )


def update_mfm_content(lines, dredger_dfs0, weights_fraction, output_dfsu):
    """
    Apply section-aware edits to a list of .mfm file lines.

    Edits performed:
      1. [DREDGING] > [DREDGER_1]: replace ``file_name`` with *dredger_dfs0*
         (pipe-wrapped) and ``weights_fraction`` with *weights_fraction*.
      2. [OUTPUTS] > [OUTPUT_1]: replace ``file_name`` with *output_dfsu*
         (pipe-wrapped).

    Args:
        lines:             List of file lines (not modified; a copy is made).
        dredger_dfs0:      New path for the dredger .dfs0 file.
        weights_fraction:  New weights_fraction string (comma-separated).
        output_dfsu:       New path for the output .dfsu file.

    Returns:
        New list of lines with the edits applied.

    Raises:
        ValueError: on any structural issue (missing block, duplicate key,
                    invalid weights_fraction).
    """
    validate_weights_fraction(weights_fraction)

    lines = list(lines)  # work on a copy

    # 1. Locate [DREDGING] block
    dredging_start, dredging_end = find_block(lines, 'DREDGING')

    # 2. Locate [DREDGER_1] within [DREDGING]
    dredger_start, dredger_end = find_block(
        lines, 'DREDGER_1', dredging_start, dredging_end
    )

    # 3. Update file_name in [DREDGER_1]
    replace_key_in_block(
        lines, dredger_start, dredger_end,
        'file_name', dredger_dfs0, pipe_wrap=True
    )

    # 4. Update weights_fraction in [DREDGER_1]
    replace_key_in_block(
        lines, dredger_start, dredger_end,
        'weights_fraction', weights_fraction, pipe_wrap=False
    )

    # 5. Locate [OUTPUTS] block (first occurrence)
    outputs_start, outputs_end = find_block(lines, 'OUTPUTS')

    # 6. Locate [OUTPUT_1] within [OUTPUTS]
    output1_start, output1_end = find_block(
        lines, 'OUTPUT_1', outputs_start, outputs_end
    )

    # 7. Update file_name in [OUTPUT_1]
    replace_key_in_block(
        lines, output1_start, output1_end,
        'file_name', output_dfsu, pipe_wrap=True
    )

    return lines
