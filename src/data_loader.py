"""Load and validate the budget vs. actuals CSV."""

from pathlib import Path

import pandas as pd

SAMPLE_PATH = Path(__file__).parent.parent / "data" / "sample" / "sample_budget.csv"
REQUIRED_COLUMNS = {"month", "department", "category", "budgeted", "actual"}


def load_csv(path=None) -> pd.DataFrame:
    """
    Load budget data. Rows with blank `actual` (future months) get actual=NaN.
    Returns a DataFrame sorted by month, department, category.
    """
    path = path or SAMPLE_PATH
    df = pd.read_csv(path, parse_dates=["month"])
    _validate(df)
    df["budgeted"] = pd.to_numeric(df["budgeted"], errors="coerce").fillna(0.0)
    df["actual"]   = pd.to_numeric(df["actual"],   errors="coerce")   # NaN = no actuals yet
    return df.sort_values(["month", "department", "category"]).reset_index(drop=True)


def load_sample() -> pd.DataFrame:
    return load_csv(SAMPLE_PATH)


def _validate(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Budget file is empty.")
