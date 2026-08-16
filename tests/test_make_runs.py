from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "make_runs.py"
spec = spec_from_file_location("make_runs_impl", MODULE_PATH)
make_runs = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(make_runs)


def test_normalize_weights_accepts_commas_and_spaces():
    assert make_runs.normalize_weights("40 40,20 0 0 0") == "40.0, 40.0, 20.0, 0.0, 0.0, 0.0"


def test_normalize_pipe_path_is_idempotent():
    assert make_runs.normalize_pipe_path("foo.dfsu") == "|foo.dfsu|"
    assert make_runs.normalize_pipe_path("|foo.dfsu|") == "|foo.dfsu|"


def test_get_dredger_columns_supports_numbered_columns():
    fields = [
        "run_name",
        "weights_fraction",
        "output_file_name",
        "dredger_2_file_name",
        "dredger_1_file_name",
        "dredger_2_weights",
    ]
    assert make_runs.get_dredger_columns(fields) == [
        ("dredger_1_file_name", None),
        ("dredger_2_file_name", "dredger_2_weights"),
    ]


def test_patch_dredger_and_output_updates_counts_and_files():
    template = """[DREDGING]\n   number_of_dredgers = 1\n   MzSEPfsListItemCount = 1\nEndSect  // DREDGING\n[DREDGER_1]\n   name = 'Dredger 1'\n   weights_fraction = 1, 0\n   file_name = |old.dfsu|\nEndSect  // DREDGER_1\n[OUTPUT_1]\n   file_name = |old-output.dfsu|\nEndSect  // OUTPUT_1\n"""

    patched, counts = make_runs.patch_dredger_and_output(
        template,
        [("|a.dfsu|", "50.0, 50.0"), ("|b.dfsu|", "25.0, 75.0")],
        "|out.dfsu|",
    )

    assert "number_of_dredgers = 2" in patched
    assert "MzSEPfsListItemCount = 2" in patched
    assert "[DREDGER_2]" in patched
    assert "file_name = |a.dfsu|" in patched
    assert "file_name = |b.dfsu|" in patched
    assert "file_name = |out.dfsu|" in patched
    assert counts["DREDGING.number_of_dredgers"] == 2
