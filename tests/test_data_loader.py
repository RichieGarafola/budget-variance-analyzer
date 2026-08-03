"""Tests for src/data_loader.py"""

import io
import textwrap

import pandas as pd
import pytest

from src.data_loader import load_csv, load_sample, REQUIRED_COLUMNS, SAMPLE_PATH


# ── helpers ───────────────────────────────────────────────────────────────────

def csv_buffer(content: str):
    """Return a StringIO file-like object that pd.read_csv accepts."""
    return io.StringIO(textwrap.dedent(content).strip())


VALID_CSV = """
    month,department,category,budgeted,actual
    2025-01-01,IT,Software,10000,9000
    2025-02-01,IT,Software,10000,11500
    2025-03-01,HR,Salaries,5000,
"""

MISSING_COL_CSV = """
    month,department,budgeted,actual
    2025-01-01,IT,10000,9000
"""

EMPTY_CSV = """
    month,department,category,budgeted,actual
"""


# ── load_csv: happy path ───────────────────────────────────────────────────────

class TestLoadCsvHappyPath:
    def test_returns_dataframe(self):
        result = load_csv(csv_buffer(VALID_CSV))
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self):
        result = load_csv(csv_buffer(VALID_CSV))
        for col in REQUIRED_COLUMNS:
            assert col in result.columns

    def test_month_is_datetime(self):
        result = load_csv(csv_buffer(VALID_CSV))
        assert pd.api.types.is_datetime64_any_dtype(result["month"])

    def test_budgeted_is_numeric(self):
        result = load_csv(csv_buffer(VALID_CSV))
        assert pd.api.types.is_numeric_dtype(result["budgeted"])

    def test_future_row_actual_is_nan(self):
        result = load_csv(csv_buffer(VALID_CSV))
        # Row 3 (HR Salaries) has blank actual — must be NaN, not zero
        hr = result[result["department"] == "HR"]
        assert pd.isna(hr["actual"].iloc[0])

    def test_past_row_actual_is_numeric(self):
        result = load_csv(csv_buffer(VALID_CSV))
        it_jan = result[(result["department"] == "IT") & (result["month"] == pd.Timestamp("2025-01-01"))]
        assert it_jan["actual"].iloc[0] == pytest.approx(9000.0)

    def test_rows_sorted_by_month(self):
        result = load_csv(csv_buffer(VALID_CSV))
        months = result["month"].tolist()
        assert months == sorted(months)

    def test_budgeted_blank_coerced_to_zero(self):
        csv = csv_buffer("""
            month,department,category,budgeted,actual
            2025-01-01,IT,Software,,9000
        """)
        result = load_csv(csv)
        assert result["budgeted"].iloc[0] == pytest.approx(0.0)


# ── load_csv: validation errors ───────────────────────────────────────────────

class TestLoadCsvValidation:
    def test_missing_column_raises_value_error(self):
        with pytest.raises(ValueError, match="Missing required columns"):
            load_csv(csv_buffer(MISSING_COL_CSV))

    def test_empty_file_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            load_csv(csv_buffer(EMPTY_CSV))

    def test_error_message_names_missing_column(self):
        with pytest.raises(ValueError, match="category"):
            load_csv(csv_buffer(MISSING_COL_CSV))


# ── load_sample ────────────────────────────────────────────────────────────────

class TestLoadSample:
    def test_returns_dataframe(self):
        result = load_sample()
        assert isinstance(result, pd.DataFrame)

    def test_has_all_required_columns(self):
        result = load_sample()
        for col in REQUIRED_COLUMNS:
            assert col in result.columns

    def test_has_rows(self):
        result = load_sample()
        assert len(result) > 0

    def test_sample_path_exists(self):
        assert SAMPLE_PATH.exists(), f"Sample file not found: {SAMPLE_PATH}"

    def test_has_future_rows(self):
        result = load_sample()
        # Nov–Dec 2025 are future months with no actuals
        assert result["actual"].isna().any()

    def test_has_actual_rows(self):
        result = load_sample()
        # Jan–Oct 2025 have actuals
        assert result["actual"].notna().any()
