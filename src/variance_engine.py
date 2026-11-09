"""
Budget variance computation and classification.

Convention (expense budgets):
  variance     = budgeted - actual   (positive = under budget = FAVORABLE)
  variance_pct = variance / budgeted (when budgeted > 0)

Status thresholds (applied to variance_pct):
  FAVORABLE   variance_pct  >  0.05   (>5% under budget)
  ON BUDGET   |variance_pct| <= 0.05
  WARNING     -0.15 <= variance_pct < -0.05  (5–15% over budget)
  CRITICAL    variance_pct  < -0.15   (>15% over budget)
"""

import pandas as pd

# Status labels
FAVORABLE  = "FAVORABLE"
ON_BUDGET  = "ON BUDGET"
WARNING    = "WARNING"
CRITICAL   = "CRITICAL"
NO_ACTUALS = "NO ACTUALS"

STATUS_ORDER = [CRITICAL, WARNING, ON_BUDGET, FAVORABLE, NO_ACTUALS]

STATUS_COLOR = {
    FAVORABLE:  "#2ECC71",
    ON_BUDGET:  "#3498DB",
    WARNING:    "#F39C12",
    CRITICAL:   "#E74C3C",
    NO_ACTUALS: "#95A5A6",
}

WARN_THRESHOLD     = 0.05    # 5%
CRITICAL_THRESHOLD = 0.15    # 15%


def compute_variance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add variance, variance_pct, and status columns.
    Rows where actual is NaN (no actuals yet) get status NO_ACTUALS.
    """
    df = df.copy()
    has_actual = df["actual"].notna()

    df["variance"]     = float("nan")
    df["variance_pct"] = float("nan")
    df["status"]       = NO_ACTUALS

    df.loc[has_actual, "variance"] = (
        df.loc[has_actual, "budgeted"] - df.loc[has_actual, "actual"]
    )
    safe_budget = df["budgeted"].where(df["budgeted"] != 0, other=float("nan"))
    df.loc[has_actual, "variance_pct"] = (
        df.loc[has_actual, "variance"] / safe_budget.loc[has_actual]
    )
    df.loc[has_actual, "status"] = df.loc[has_actual, "variance_pct"].apply(classify_variance)
    return df


def classify_variance(variance_pct: float) -> str:
    """Classify a single variance_pct value."""
    if pd.isna(variance_pct):
        return NO_ACTUALS
    if variance_pct > WARN_THRESHOLD:
        return FAVORABLE
    if variance_pct >= -WARN_THRESHOLD:
        return ON_BUDGET
    if variance_pct >= -CRITICAL_THRESHOLD:
        return WARNING
    return CRITICAL


def ytd_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate only rows that have actuals (YTD view)."""
    actual_rows = df[df["actual"].notna()].copy()
    return actual_rows.groupby(["department", "category"], as_index=False).agg(
        budgeted_ytd=("budgeted", "sum"),
        actual_ytd  =("actual",   "sum"),
    ).assign(
        variance_ytd    =lambda d: d["budgeted_ytd"] - d["actual_ytd"],
        variance_pct_ytd=lambda d: (d["budgeted_ytd"] - d["actual_ytd"]) / d["budgeted_ytd"].replace(0, pd.NA),
        status          =lambda d: d["variance_pct_ytd"].apply(classify_variance),
    )


def forecast_year_end(df: pd.DataFrame) -> pd.DataFrame:
    """
    Project full-year actuals based on average monthly burn rate (YTD).
    Returns one row per department/category with:
      full_year_budget, actual_ytd, months_with_actuals,
      monthly_run_rate, forecast_year_end, forecast_variance
    """
    has_actual = df[df["actual"].notna()].copy()
    agg = has_actual.groupby(["department", "category"], as_index=False).agg(
        full_year_budget=("budgeted", lambda s: df.loc[s.index, "budgeted"].sum()),
        actual_ytd      =("actual",   "sum"),
        months_actual   =("actual",   "count"),
    )
    agg["monthly_run_rate"]   = agg["actual_ytd"] / agg["months_actual"].clip(lower=1)
    agg["forecast_year_end"]  = agg["monthly_run_rate"] * 12
    agg["forecast_variance"]  = agg["full_year_budget"] - agg["forecast_year_end"]
    agg["forecast_variance_pct"] = agg["forecast_variance"] / agg["full_year_budget"].replace(0, pd.NA)
    agg["forecast_status"]    = agg["forecast_variance_pct"].apply(classify_variance)
    return agg
