"""
Unit tests for mfm_update.py / mfm_editor.py.

Tests cover:
  - Only the intended lines are changed.
  - Failure when [DREDGING] is missing.
  - Failure when [OUTPUTS] / [OUTPUT_1] is missing.
  - Failure when a key appears more than once inside a block.
  - CSV reading and validation helpers.
"""

import csv
import io
import os
import sys
import tempfile
import unittest

# Ensure both modules are importable when running from the repo root.
sys.path.insert(0, os.path.dirname(__file__))

from mfm_editor import (
    find_block,
    get_key_value_in_block,
    replace_key_in_block,
    update_mfm_content,
    validate_weights_fraction,
)
from mfm_update import process_scenario, read_csv, validate_row, REQUIRED_COLUMNS


# ---------------------------------------------------------------------------
# Minimal template used across tests
# ---------------------------------------------------------------------------

MINIMAL_TEMPLATE = """\
// MIKE FM test template
[DREDGING]
   [DREDGER_1]
      weights_fraction = 0.0, 0.0, 0.0, 0.0
      file_name = |placeholder.dfs0|
      time_step = 3600
   EndSect  // DREDGER_1
EndSect  // DREDGING

[OUTPUTS]
   [OUTPUT_1]
      file_name = |placeholder.dfsu|
      output_type = bed_level
   EndSect  // OUTPUT_1
EndSect  // OUTPUTS
"""

# CSV row used across tests
SAMPLE_ROW = {
    'scenario': '40_SI-CB2_9pm',
    'dredger_dfs0': r'\\server\share\40_SI-CB2_9pm.dfs0',
    'weights_fraction': '0.0, 0.0, 0.0, 49.0, 43.0, 8.0',
    'output_dfsu': r'\\server\share\SI-CB2_9pm_2D.dfsu',
}


def _lines(text):
    """Split template text into a list of lines (with newlines)."""
    return [ln + '\n' for ln in text.rstrip('\n').split('\n')]


# ---------------------------------------------------------------------------
# Tests: find_block
# ---------------------------------------------------------------------------

class TestFindBlock(unittest.TestCase):

    def test_finds_top_level_block(self):
        lines = _lines(MINIMAL_TEMPLATE)
        start, end = find_block(lines, 'DREDGING')
        self.assertEqual(lines[start].strip(), '[DREDGING]')
        self.assertIn('EndSect', lines[end])
        self.assertIn('DREDGING', lines[end])

    def test_finds_nested_block(self):
        lines = _lines(MINIMAL_TEMPLATE)
        ds, de = find_block(lines, 'DREDGING')
        d1s, d1e = find_block(lines, 'DREDGER_1', ds, de)
        self.assertEqual(lines[d1s].strip(), '[DREDGER_1]')

    def test_raises_when_block_missing(self):
        lines = _lines("// no sections here\n")
        with self.assertRaises(ValueError) as ctx:
            find_block(lines, 'DREDGING')
        self.assertIn('[DREDGING]', str(ctx.exception))

    def test_raises_when_block_not_closed(self):
        text = '[DREDGING]\n   file_name = |x.dfs0|\n'
        lines = _lines(text)
        with self.assertRaises(ValueError) as ctx:
            find_block(lines, 'DREDGING')
        self.assertIn('not closed', str(ctx.exception))

    def test_first_occurrence_returned_when_multiple(self):
        # Two OUTPUTS blocks; should return the first one.
        text = (
            '[OUTPUTS]\n'
            '   [OUTPUT_1]\n'
            '      file_name = |first.dfsu|\n'
            '   EndSect  // OUTPUT_1\n'
            'EndSect  // OUTPUTS\n'
            '[OUTPUTS]\n'
            '   [OUTPUT_1]\n'
            '      file_name = |second.dfsu|\n'
            '   EndSect  // OUTPUT_1\n'
            'EndSect  // OUTPUTS\n'
        )
        lines = _lines(text)
        start, end = find_block(lines, 'OUTPUTS')
        self.assertEqual(lines[start].strip(), '[OUTPUTS]')
        # First block ends before line 5 (0-based index 4)
        self.assertLess(end, 5)


# ---------------------------------------------------------------------------
# Tests: replace_key_in_block
# ---------------------------------------------------------------------------

class TestReplaceKeyInBlock(unittest.TestCase):

    def test_replaces_value_plain(self):
        lines = _lines(MINIMAL_TEMPLATE)
        ds, de = find_block(lines, 'DREDGING')
        d1s, d1e = find_block(lines, 'DREDGER_1', ds, de)
        replace_key_in_block(
            lines, d1s, d1e, 'weights_fraction', '1.0, 2.0, 3.0'
        )
        val = get_key_value_in_block(lines, d1s, d1e, 'weights_fraction')
        self.assertEqual(val, '1.0, 2.0, 3.0')

    def test_replaces_value_pipe_wrapped(self):
        lines = _lines(MINIMAL_TEMPLATE)
        ds, de = find_block(lines, 'DREDGING')
        d1s, d1e = find_block(lines, 'DREDGER_1', ds, de)
        replace_key_in_block(
            lines, d1s, d1e, 'file_name', r'\\srv\new.dfs0', pipe_wrap=True
        )
        val = get_key_value_in_block(lines, d1s, d1e, 'file_name')
        self.assertEqual(val, r'|\\srv\new.dfs0|')

    def test_raises_when_key_missing(self):
        lines = _lines(MINIMAL_TEMPLATE)
        ds, de = find_block(lines, 'DREDGING')
        d1s, d1e = find_block(lines, 'DREDGER_1', ds, de)
        with self.assertRaises(ValueError) as ctx:
            replace_key_in_block(lines, d1s, d1e, 'nonexistent_key', 'v')
        self.assertIn('nonexistent_key', str(ctx.exception))

    def test_raises_on_duplicate_key(self):
        # Two file_name entries inside DREDGER_1.
        text = (
            '[DREDGING]\n'
            '   [DREDGER_1]\n'
            '      weights_fraction = 0.0\n'
            '      file_name = |a.dfs0|\n'
            '      file_name = |b.dfs0|\n'
            '   EndSect  // DREDGER_1\n'
            'EndSect  // DREDGING\n'
        )
        lines = _lines(text)
        ds, de = find_block(lines, 'DREDGING')
        d1s, d1e = find_block(lines, 'DREDGER_1', ds, de)
        with self.assertRaises(ValueError) as ctx:
            replace_key_in_block(
                lines, d1s, d1e, 'file_name', 'new.dfs0', pipe_wrap=True
            )
        self.assertIn('Duplicate', str(ctx.exception))


# ---------------------------------------------------------------------------
# Tests: update_mfm_content – only intended lines change
# ---------------------------------------------------------------------------

class TestUpdateMfmContent(unittest.TestCase):

    def _apply(self, template_text=MINIMAL_TEMPLATE, row=None):
        if row is None:
            row = SAMPLE_ROW
        lines = _lines(template_text)
        return update_mfm_content(
            lines,
            row['dredger_dfs0'],
            row['weights_fraction'],
            row['output_dfsu'],
        )

    def test_dredger_file_name_updated(self):
        new_lines = self._apply()
        ds, de = find_block(new_lines, 'DREDGING')
        d1s, d1e = find_block(new_lines, 'DREDGER_1', ds, de)
        val = get_key_value_in_block(new_lines, d1s, d1e, 'file_name')
        self.assertEqual(val, f"|{SAMPLE_ROW['dredger_dfs0']}|")

    def test_weights_fraction_updated(self):
        new_lines = self._apply()
        ds, de = find_block(new_lines, 'DREDGING')
        d1s, d1e = find_block(new_lines, 'DREDGER_1', ds, de)
        val = get_key_value_in_block(new_lines, d1s, d1e, 'weights_fraction')
        self.assertEqual(val, SAMPLE_ROW['weights_fraction'])

    def test_output_file_name_updated(self):
        new_lines = self._apply()
        os_, oe = find_block(new_lines, 'OUTPUTS')
        o1s, o1e = find_block(new_lines, 'OUTPUT_1', os_, oe)
        val = get_key_value_in_block(new_lines, o1s, o1e, 'file_name')
        self.assertEqual(val, f"|{SAMPLE_ROW['output_dfsu']}|")

    def test_only_three_lines_changed(self):
        orig = _lines(MINIMAL_TEMPLATE)
        new_lines = self._apply()
        changed = [i for i in range(len(orig)) if orig[i] != new_lines[i]]
        self.assertEqual(len(changed), 3,
                         f"Expected 3 changed lines, got {len(changed)}: "
                         f"{changed}")

    def test_unchanged_lines_identical(self):
        orig = _lines(MINIMAL_TEMPLATE)
        new_lines = self._apply()
        for i, (o, n) in enumerate(zip(orig, new_lines)):
            if 'file_name' not in o and 'weights_fraction' not in o:
                self.assertEqual(o, n,
                                 f"Line {i + 1} changed unexpectedly: "
                                 f"{o!r} -> {n!r}")

    def test_indentation_preserved(self):
        new_lines = self._apply()
        ds, de = find_block(new_lines, 'DREDGING')
        d1s, d1e = find_block(new_lines, 'DREDGER_1', ds, de)
        for i in range(d1s, d1e + 1):
            if 'file_name' in new_lines[i]:
                self.assertTrue(
                    new_lines[i].startswith('      '),
                    f"Indentation lost: {new_lines[i]!r}"
                )


# ---------------------------------------------------------------------------
# Tests: update_mfm_content – structural failures
# ---------------------------------------------------------------------------

class TestUpdateMfmContentFailures(unittest.TestCase):

    def test_fails_when_dredging_missing(self):
        text = (
            '[OUTPUTS]\n'
            '   [OUTPUT_1]\n'
            '      file_name = |placeholder.dfsu|\n'
            '   EndSect  // OUTPUT_1\n'
            'EndSect  // OUTPUTS\n'
        )
        with self.assertRaises(ValueError) as ctx:
            update_mfm_content(
                _lines(text),
                SAMPLE_ROW['dredger_dfs0'],
                SAMPLE_ROW['weights_fraction'],
                SAMPLE_ROW['output_dfsu'],
            )
        self.assertIn('[DREDGING]', str(ctx.exception))

    def test_fails_when_dredger_1_missing(self):
        text = (
            '[DREDGING]\n'
            '   file_name = |x.dfs0|\n'
            'EndSect  // DREDGING\n'
            '[OUTPUTS]\n'
            '   [OUTPUT_1]\n'
            '      file_name = |placeholder.dfsu|\n'
            '   EndSect  // OUTPUT_1\n'
            'EndSect  // OUTPUTS\n'
        )
        with self.assertRaises(ValueError) as ctx:
            update_mfm_content(
                _lines(text),
                SAMPLE_ROW['dredger_dfs0'],
                SAMPLE_ROW['weights_fraction'],
                SAMPLE_ROW['output_dfsu'],
            )
        self.assertIn('[DREDGER_1]', str(ctx.exception))

    def test_fails_when_outputs_missing(self):
        text = (
            '[DREDGING]\n'
            '   [DREDGER_1]\n'
            '      weights_fraction = 0.0\n'
            '      file_name = |placeholder.dfs0|\n'
            '   EndSect  // DREDGER_1\n'
            'EndSect  // DREDGING\n'
        )
        with self.assertRaises(ValueError) as ctx:
            update_mfm_content(
                _lines(text),
                SAMPLE_ROW['dredger_dfs0'],
                SAMPLE_ROW['weights_fraction'],
                SAMPLE_ROW['output_dfsu'],
            )
        self.assertIn('[OUTPUTS]', str(ctx.exception))

    def test_fails_when_output1_missing(self):
        text = (
            '[DREDGING]\n'
            '   [DREDGER_1]\n'
            '      weights_fraction = 0.0\n'
            '      file_name = |placeholder.dfs0|\n'
            '   EndSect  // DREDGER_1\n'
            'EndSect  // DREDGING\n'
            '[OUTPUTS]\n'
            '   number_of_outputs = 0\n'
            'EndSect  // OUTPUTS\n'
        )
        with self.assertRaises(ValueError) as ctx:
            update_mfm_content(
                _lines(text),
                SAMPLE_ROW['dredger_dfs0'],
                SAMPLE_ROW['weights_fraction'],
                SAMPLE_ROW['output_dfsu'],
            )
        self.assertIn('[OUTPUT_1]', str(ctx.exception))

    def test_fails_on_duplicate_file_name_in_dredger_1(self):
        text = (
            '[DREDGING]\n'
            '   [DREDGER_1]\n'
            '      weights_fraction = 0.0\n'
            '      file_name = |a.dfs0|\n'
            '      file_name = |b.dfs0|\n'
            '   EndSect  // DREDGER_1\n'
            'EndSect  // DREDGING\n'
            '[OUTPUTS]\n'
            '   [OUTPUT_1]\n'
            '      file_name = |placeholder.dfsu|\n'
            '   EndSect  // OUTPUT_1\n'
            'EndSect  // OUTPUTS\n'
        )
        with self.assertRaises(ValueError) as ctx:
            update_mfm_content(
                _lines(text),
                SAMPLE_ROW['dredger_dfs0'],
                SAMPLE_ROW['weights_fraction'],
                SAMPLE_ROW['output_dfsu'],
            )
        self.assertIn('Duplicate', str(ctx.exception))

    def test_fails_on_invalid_weights_fraction(self):
        with self.assertRaises(ValueError) as ctx:
            update_mfm_content(
                _lines(MINIMAL_TEMPLATE),
                SAMPLE_ROW['dredger_dfs0'],
                'not, valid, numbers',
                SAMPLE_ROW['output_dfsu'],
            )
        self.assertIn('weights_fraction', str(ctx.exception))


# ---------------------------------------------------------------------------
# Tests: validate_weights_fraction
# ---------------------------------------------------------------------------

class TestValidateWeightsFraction(unittest.TestCase):

    def test_valid_floats(self):
        validate_weights_fraction('0.0, 0.0, 49.0, 43.0, 8.0')  # no error

    def test_valid_integers(self):
        validate_weights_fraction('0, 50, 50')  # no error

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            validate_weights_fraction('')

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            validate_weights_fraction('0.0, abc, 1.0')


# ---------------------------------------------------------------------------
# Tests: read_csv
# ---------------------------------------------------------------------------

class TestReadCsv(unittest.TestCase):

    def _write_csv(self, rows, fieldnames=None, tmpdir=None):
        if fieldnames is None:
            fieldnames = list(REQUIRED_COLUMNS)
        fd, path = tempfile.mkstemp(suffix='.csv', dir=tmpdir)
        with os.fdopen(fd, 'w', newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_reads_valid_csv(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_csv([SAMPLE_ROW], tmpdir=tmpdir)
            rows = read_csv(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['scenario'], SAMPLE_ROW['scenario'])

    def test_raises_on_missing_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fd, path = tempfile.mkstemp(suffix='.csv', dir=tmpdir)
            with os.fdopen(fd, 'w', newline='') as fh:
                fh.write('scenario,dredger_dfs0\ntest,x.dfs0\n')
            with self.assertRaises(ValueError) as ctx:
                read_csv(path)
        self.assertIn('missing required columns', str(ctx.exception))


# ---------------------------------------------------------------------------
# Tests: validate_row
# ---------------------------------------------------------------------------

class TestValidateRow(unittest.TestCase):

    def test_valid_row_no_warnings(self):
        warnings = validate_row(SAMPLE_ROW)
        self.assertEqual(warnings, [])

    def test_warns_on_non_dfs0(self):
        row = dict(SAMPLE_ROW, dredger_dfs0='path/to/file.txt')
        warnings = validate_row(row)
        self.assertTrue(any('.dfs0' in w for w in warnings))

    def test_warns_on_non_dfsu(self):
        row = dict(SAMPLE_ROW, output_dfsu='path/to/file.txt')
        warnings = validate_row(row)
        self.assertTrue(any('.dfsu' in w for w in warnings))

    def test_raises_on_bad_weights(self):
        row = dict(SAMPLE_ROW, weights_fraction='bad,data')
        with self.assertRaises(ValueError):
            validate_row(row)


# ---------------------------------------------------------------------------
# Tests: process_scenario (integration – writes to temp file)
# ---------------------------------------------------------------------------

class TestProcessScenario(unittest.TestCase):

    def _make_template(self, tmpdir, content=MINIMAL_TEMPLATE):
        path = os.path.join(tmpdir, 'template.mfm')
        with open(path, 'w') as fh:
            fh.write(content)
        return path

    def test_writes_output_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template = self._make_template(tmpdir)
            outdir = os.path.join(tmpdir, 'out')
            out_path = process_scenario(
                SAMPLE_ROW, template, outdir
            )
            self.assertIsNotNone(out_path)
            self.assertTrue(os.path.isfile(out_path))
            self.assertTrue(out_path.endswith(
                f"{SAMPLE_ROW['scenario']}.mfm"
            ))

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template = self._make_template(tmpdir)
            outdir = os.path.join(tmpdir, 'out')
            result = process_scenario(
                SAMPLE_ROW, template, outdir, dry_run=True
            )
            self.assertIsNone(result)
            self.assertFalse(os.path.exists(outdir))

    def test_output_contains_new_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template = self._make_template(tmpdir)
            outdir = os.path.join(tmpdir, 'out')
            out_path = process_scenario(SAMPLE_ROW, template, outdir)
            with open(out_path) as fh:
                content = fh.read()
            self.assertIn(SAMPLE_ROW['dredger_dfs0'], content)
            self.assertIn(SAMPLE_ROW['weights_fraction'], content)
            self.assertIn(SAMPLE_ROW['output_dfsu'], content)

    def test_output_does_not_contain_old_placeholder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template = self._make_template(tmpdir)
            outdir = os.path.join(tmpdir, 'out')
            out_path = process_scenario(SAMPLE_ROW, template, outdir)
            with open(out_path) as fh:
                content = fh.read()
            self.assertNotIn('placeholder.dfs0', content)
            self.assertNotIn('placeholder.dfsu', content)

    def test_suffix_applied_to_output_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template = self._make_template(tmpdir)
            outdir = os.path.join(tmpdir, 'out')
            out_path = process_scenario(
                SAMPLE_ROW, template, outdir, suffix='_v2'
            )
            self.assertTrue(
                os.path.basename(out_path).endswith('_v2.mfm')
            )

    def test_backup_created(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            template = self._make_template(tmpdir)
            outdir = os.path.join(tmpdir, 'out')
            # First run creates the file
            out_path = process_scenario(SAMPLE_ROW, template, outdir)
            # Second run with backup=True should create a .bak
            process_scenario(SAMPLE_ROW, template, outdir, backup=True)
            self.assertTrue(os.path.isfile(out_path + '.bak'))


if __name__ == '__main__':
    unittest.main()
