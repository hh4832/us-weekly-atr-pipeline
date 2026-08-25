import pandas as pd

from google_sheets_store import _json_safe_cell


def test_json_safe_cell_replaces_non_finite_values():
    assert _json_safe_cell(float("nan")) == ""
    assert _json_safe_cell(float("inf")) == ""
    assert _json_safe_cell(float("-inf")) == ""
    assert _json_safe_cell(pd.NA) == ""


def test_json_safe_cell_preserves_normal_values():
    assert _json_safe_cell(12.5) == 12.5
    assert _json_safe_cell("LIMIT") == "LIMIT"
