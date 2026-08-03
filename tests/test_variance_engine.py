"""Tests for src/variance_engine.py"""

import pandas as pd
import pytest

from src.variance_engine import (
    compute_variance,
    classify_variance,
    ytd_summary,
    forecast_year_end,
    FAVORABLE, ON_BUDGET, WARNING, CRITICAL, NO_ACTUALS,
    WARN_THRESHOLD, CRITICAL_THRESHOLD,
)


def make_df(**overrides) -> pd.DataFrame:
    data = {
        "month":      pd.to_datetime(["2025-01-01", "2025-02-01",
                                      "2025-03-01", "2025-04-01"]),
        "department": ["IT",       "IT",       "HR",      "HR"],
        "category":   ["Software", "Software", "Salaries","Salaries"],
        "budgeted":   [10_000.0,   10_000.0,   5_000.0,   5_000.0],
        "actual":     [9_000.0,    11_500.0,   4_800.0,   float("nan")],  # last is future
    }
    data.update(overrides)
    return pd.DataFrame(data)


# ── classify_variance ──────────────────────────────────────────────────────────

class TestClassifyVariance:
    def test_favorable_above_threshold(self):
        assert classify_variance(0.10) == FAVORABLE

    def test_favorable_exactly_at_threshold(self):
        # strictly greater than WARN_THRESHOLD
        assert classify_variance(WARN_THRESHOLD + 0.001) == FAVORABLE

    def test_on_budget_positive(self):
        assert classify_variance(0.03) == ON_BUDGET

    def test_on_budget_zero(self):
        assert classify_variance(0.0) == ON_BUDGET

    def test_on_budget_small_negative(self):
        assert classify_variance(-0.03) == ON_BUDGET

    def test_warning_band(self):
        assert classify_variance(-0.10) == WARNING

    def test_critical_below_threshold(self):
        assert classify_variance(-0.20) == CRITICAL

    def test_critical_exactly_at_boundary(self):
        assert classify_variance(-CRITICAL_THRESHOLD - 0.001) == CRITICAL

    def test_nan_returns_no_actuals(self):
        assert classify_variance(float("nan")) == NO_ACTUALS


# ── compute_variance ───────────────────────────────────────────────────────────

class TestComputeVariance:
    def test_returns_dataframe(self):
        assert isinstance(compute_variance(make_df()), pd.DataFrame)

    def test_adds_required_columns(self):
        result = compute_variance(make_df())
        for col in ["variance", "variance_pct", "status"]:
            assert col in result.columns

    def test_does_not_mutate_input(self):
        raw = make_df()
        compute_variance(raw)
        assert "variance" not in raw.columns

    def test_variance_calculation(self):
        result = compute_variance(make_df())
        # Row 0: budgeted=10000, actual=9000 → variance=1000
        assert result["variance"].iloc[0] == pytest.approx(1000.0)

    def test_overspend_negative_variance(self):
        result = compute_variance(make_df())
        # Row 1: budgeted=10000, actual=11500 → variance=-1500
        assert result["variance"].iloc[1] == pytest.approx(-1500.0)

    def test_variance_pct_calculation(self):
        result = compute_variance(make_df())
        assert result["variance_pct"].iloc[0] == pytest.approx(0.10)

    def test_future_row_gets_no_actuals_status(self):
        result = compute_variance(make_df())
        assert result["status"].iloc[3] == NO_ACTUALS

    def test_favorable_status_assigned(self):
        result = compute_variance(make_df())
        # Row 0: 10% under budget → FAVORABLE
        assert result["status"].iloc[0] == FAVORABLE

    def test_warning_status_assigned(self):
        result = compute_variance(make_df())
        # Row 1: -15% → WARNING
        assert result["status"].iloc[1] == WARNING

    def test_zero_budget_handled(self):
        df = make_df(budgeted=[0.0, 10_000.0, 5_000.0, 5_000.0])
        result = compute_variance(df)
        # Row 0 has zero budget — variance_pct should be NaN or handled safely
        assert pd.isna(result["variance_pct"].iloc[0]) or result["status"].iloc[0] == NO_ACTUALS


# ── ytd_summary ────────────────────────────────────────────────────────────────

class TestYtdSummary:
    def test_returns_dataframe(self):
        assert isinstance(ytd_summary(make_df()), pd.DataFrame)

    def test_excludes_future_rows(self):
        result = ytd_summary(make_df())
        # HR Salaries: only 1 actual month (row 2), row 3 is NaN
        hr = result[result["department"] == "HR"]
        assert len(hr) == 1
        assert hr["actual_ytd"].iloc[0] == pytest.approx(4800.0)

    def test_aggregates_multiple_months(self):
        result = ytd_summary(make_df())
        it = result[result["department"] == "IT"]
        # IT: 9000 + 11500 = 20500 actual
        assert it["actual_ytd"].iloc[0] == pytest.approx(20_500.0)
        assert it["budgeted_ytd"].iloc[0] == pytest.approx(20_000.0)

    def test_has_status_column(self):
        result = ytd_summary(make_df())
        assert "status" in result.columns

    def test_variance_ytd_correct(self):
        result = ytd_summary(make_df())
        it = result[result["department"] == "IT"]
        # 20000 - 20500 = -500 → variance_ytd = -500
        assert it["variance_ytd"].iloc[0] == pytest.approx(-500.0)


# ── forecast_year_end ──────────────────────────────────────────────────────────

class TestForecastYearEnd:
    def test_returns_dataframe(self):
        assert isinstance(forecast_year_end(make_df()), pd.DataFrame)

    def test_has_required_columns(self):
        result = forecast_year_end(make_df())
        for col in ["monthly_run_rate", "forecast_year_end", "forecast_variance"]:
            assert col in result.columns

    def test_monthly_run_rate_for_two_months(self):
        result = forecast_year_end(make_df())
        it = result[result["department"] == "IT"]
        # (9000 + 11500) / 2 = 10250
        assert it["monthly_run_rate"].iloc[0] == pytest.approx(10_250.0)

    def test_forecast_year_end_is_run_rate_times_12(self):
        result = forecast_year_end(make_df())
        it = result[result["department"] == "IT"]
        assert it["forecast_year_end"].iloc[0] == pytest.approx(10_250.0 * 12)

    def test_forecast_variance_sign(self):
        result = forecast_year_end(make_df())
        it = result[result["department"] == "IT"]
        # Over budget → forecast_variance should be negative
        assert it["forecast_variance"].iloc[0] < 0

    def test_forecast_status_column_present(self):
        result = forecast_year_end(make_df())
        assert "forecast_status" in result.columns
