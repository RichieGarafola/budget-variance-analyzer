"""Summary report builders for budget variance analysis."""

import pandas as pd

from src.variance_engine import compute_variance, classify_variance, STATUS_ORDER


def department_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Total budget, actual, variance, and status per department (YTD actuals only)."""
    actual = df[df["actual"].notna()]
    agg = (
        actual.groupby("department", as_index=False)
        .agg(budgeted=("budgeted", "sum"), actual=("actual", "sum"))
    )
    agg["variance"]     = agg["budgeted"] - agg["actual"]
    agg["variance_pct"] = agg["variance"] / agg["budgeted"].replace(0, float("nan"))
    agg["status"]       = agg["variance_pct"].apply(classify_variance)
    return agg.sort_values("variance", ascending=True).reset_index(drop=True)


def category_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Total budget, actual, variance per category across all departments (YTD)."""
    actual = df[df["actual"].notna()]
    agg = (
        actual.groupby("category", as_index=False)
        .agg(budgeted=("budgeted", "sum"), actual=("actual", "sum"))
    )
    agg["variance"]     = agg["budgeted"] - agg["actual"]
    agg["variance_pct"] = agg["variance"] / agg["budgeted"].replace(0, float("nan"))
    agg["status"]       = agg["variance_pct"].apply(classify_variance)
    return agg.sort_values("variance", ascending=True).reset_index(drop=True)


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Month-level budget vs actual totals (all departments combined)."""
    agg = (
        df.groupby("month", as_index=False)
        .agg(
            budgeted=("budgeted", "sum"),
            actual  =("actual",   lambda s: s.sum() if s.notna().any() else float("nan")),
        )
    )
    agg["variance"]     = agg["budgeted"] - agg["actual"]
    agg["variance_pct"] = agg["variance"] / agg["budgeted"].replace(0, float("nan"))
    return agg.sort_values("month").reset_index(drop=True)


def top_variances(df: pd.DataFrame, n: int = 10, unfavorable_only: bool = False) -> pd.DataFrame:
    """
    Return the n line items (dept + category + month) with the largest absolute variance.
    If unfavorable_only=True, restrict to over-budget rows.
    """
    enriched = compute_variance(df)
    has_data = enriched[enriched["actual"].notna()].copy()
    if unfavorable_only:
        has_data = has_data[has_data["variance"] < 0]
    return (
        has_data.nlargest(n, "variance", keep="all")
        if not unfavorable_only
        else has_data.nsmallest(n, "variance", keep="all")
    ).reset_index(drop=True)


def portfolio_kpis(df: pd.DataFrame) -> dict:
    """Single-number KPIs for the dashboard header tiles."""
    actual_rows = df[df["actual"].notna()]
    total_budget  = actual_rows["budgeted"].sum()
    total_actual  = actual_rows["actual"].sum()
    total_variance= total_budget - total_actual
    variance_pct  = total_variance / total_budget if total_budget else 0

    enriched = compute_variance(df)
    has_data = enriched[enriched["actual"].notna()]
    status_counts = has_data["status"].value_counts().to_dict()

    return {
        "total_budget":    total_budget,
        "total_actual":    total_actual,
        "total_variance":  total_variance,
        "variance_pct":    variance_pct,
        "n_favorable":     status_counts.get("FAVORABLE",  0),
        "n_on_budget":     status_counts.get("ON BUDGET",  0),
        "n_warning":       status_counts.get("WARNING",    0),
        "n_critical":      status_counts.get("CRITICAL",   0),
        "months_with_actuals": actual_rows["month"].nunique(),
        "total_months":    df["month"].nunique(),
    }
