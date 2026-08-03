"""Tests for src/reporter.py"""

import pandas as pd
import pytest

from src.reporter import (
    department_summary,
    category_summary,
    monthly_trend,
    top_variances,
    portfolio_kpis,
)


def make_df() -> pd.DataFrame:
    return pd.DataFrame({
        "month":      pd.to_datetime([
            "2025-01-01", "2025-01-01", "2025-02-01", "2025-02-01", "2025-03-01",
        ]),
        "department": ["IT",   "HR",   "IT",   "HR",   "IT"],
        "category":   ["SW",   "Sal",  "SW",   "Sal",  "SW"],
        "budgeted":   [10_000, 5_000,  10_000, 5_000,  10_000],
        "actual":     [9_000,  5_500,  11_000, 4_800,  float("nan")],
    })


# ── department_summary ─────────────────────────────────────────────────────────

class TestDepartmentSummary:
    def test_returns_dataframe(self):
        assert isinstance(department_summary(make_df()), pd.DataFrame)

    def test_one_row_per_department(self):
        result = department_summary(make_df())
        assert len(result) == 2

    def test_it_totals(self):
        result = department_summary(make_df())
        it = result[result["department"] == "IT"]
        # Only Jan & Feb have actuals (9000+11000=20000 actual, 20000 budget)
        assert it["actual"].iloc[0] == pytest.approx(20_000.0)
        assert it["budgeted"].iloc[0] == pytest.approx(20_000.0)

    def test_variance_computed(self):
        result = department_summary(make_df())
        assert "variance" in result.columns

    def test_status_column_present(self):
        result = department_summary(make_df())
        assert "status" in result.columns

    def test_excludes_future_rows(self):
        result = department_summary(make_df())
        # IT has 3 rows but only 2 have actuals → budget should be 20000, not 30000
        it = result[result["department"] == "IT"]
        assert it["budgeted"].iloc[0] == pytest.approx(20_000.0)


# ── category_summary ───────────────────────────────────────────────────────────

class TestCategorySummary:
    def test_returns_dataframe(self):
        assert isinstance(category_summary(make_df()), pd.DataFrame)

    def test_one_row_per_category(self):
        result = category_summary(make_df())
        assert len(result) == 2   # SW, Sal

    def test_sw_totals(self):
        result = category_summary(make_df())
        sw = result[result["category"] == "SW"]
        assert sw["actual"].iloc[0] == pytest.approx(20_000.0)


# ── monthly_trend ──────────────────────────────────────────────────────────────

class TestMonthlyTrend:
    def test_returns_dataframe(self):
        assert isinstance(monthly_trend(make_df()), pd.DataFrame)

    def test_one_row_per_month(self):
        result = monthly_trend(make_df())
        assert len(result) == 3   # Jan, Feb, Mar

    def test_sorted_by_month(self):
        result = monthly_trend(make_df())
        assert result["month"].is_monotonic_increasing

    def test_jan_totals(self):
        result = monthly_trend(make_df())
        jan = result[result["month"] == pd.Timestamp("2025-01-01")]
        assert jan["budgeted"].iloc[0] == pytest.approx(15_000.0)
        assert jan["actual"].iloc[0]   == pytest.approx(14_500.0)

    def test_future_month_actual_is_nan(self):
        result = monthly_trend(make_df())
        mar = result[result["month"] == pd.Timestamp("2025-03-01")]
        assert pd.isna(mar["actual"].iloc[0])


# ── top_variances ──────────────────────────────────────────────────────────────

class TestTopVariances:
    def test_returns_dataframe(self):
        assert isinstance(top_variances(make_df()), pd.DataFrame)

    def test_excludes_future_rows(self):
        result = top_variances(make_df())
        assert result["actual"].notna().all()

    def test_unfavorable_only_flag(self):
        result = top_variances(make_df(), unfavorable_only=True)
        assert (result["variance"] < 0).all()

    def test_respects_n_limit(self):
        result = top_variances(make_df(), n=1)
        assert len(result) <= 1


# ── portfolio_kpis ─────────────────────────────────────────────────────────────

class TestPortfolioKpis:
    def test_returns_dict(self):
        assert isinstance(portfolio_kpis(make_df()), dict)

    def test_total_budget(self):
        kpis = portfolio_kpis(make_df())
        # Only actuals rows: Jan IT(10k), Jan HR(5k), Feb IT(10k), Feb HR(5k) = 30000
        assert kpis["total_budget"] == pytest.approx(30_000.0)

    def test_total_actual(self):
        kpis = portfolio_kpis(make_df())
        # 9000 + 5500 + 11000 + 4800 = 30300
        assert kpis["total_actual"] == pytest.approx(30_300.0)

    def test_variance_negative(self):
        kpis = portfolio_kpis(make_df())
        assert kpis["total_variance"] == pytest.approx(-300.0)

    def test_months_with_actuals(self):
        kpis = portfolio_kpis(make_df())
        assert kpis["months_with_actuals"] == 2

    def test_total_months(self):
        kpis = portfolio_kpis(make_df())
        assert kpis["total_months"] == 3

    def test_status_counts_present(self):
        kpis = portfolio_kpis(make_df())
        for key in ("n_favorable", "n_on_budget", "n_warning", "n_critical"):
            assert key in kpis
