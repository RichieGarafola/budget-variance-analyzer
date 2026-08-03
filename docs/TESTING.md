# Testing — Budget Variance Analyzer

## Summary

| Metric | Value |
|---|---|
| Total tests | 72 |
| Passing | 72 |
| Failing | 0 |
| Test files | 3 |
| Test classes | 9 |
| Runtime | ~2.3 seconds |

Run with:

```bash
pytest tests/ -v
```

---

## Test File Inventory

### `tests/test_data_loader.py` — 17 tests, 3 classes

| Class | Tests | What is covered |
|---|---|---|
| `TestLoadCsvHappyPath` | 8 | Returns DataFrame; required columns present; month parsed as datetime; budgeted numeric; future-row actual is NaN; past-row actual is numeric; sort order (month → department → category); blank budgeted coerced to 0.0 |
| `TestLoadCsvValidation` | 3 | Missing column raises ValueError with message; empty file raises ValueError; error message names the missing column |
| `TestLoadSample` | 6 | Returns DataFrame; all required columns present; non-empty; SAMPLE_PATH file exists on disk; has NaN actual rows (future periods); has non-NaN actual rows (past periods) |

### `tests/test_variance_engine.py` — 30 tests, 4 classes

| Class | Tests | What is covered |
|---|---|---|
| `TestClassifyVariance` | 9 | FAVORABLE above threshold; FAVORABLE at exact boundary (strictly > 5%); ON BUDGET positive; ON BUDGET zero; ON BUDGET small negative; WARNING band; CRITICAL below threshold; CRITICAL at exact boundary; NaN returns NO ACTUALS |
| `TestComputeVariance` | 10 | Returns DataFrame; adds required columns (variance, variance_pct, status); does not mutate input; variance calculation (budgeted − actual); overspend negative variance; variance_pct calculation; future row gets NO ACTUALS; FAVORABLE status assigned; WARNING status assigned; zero budget handled safely |
| `TestYtdSummary` | 5 | Returns DataFrame; excludes future rows; aggregates multiple months correctly; has status column; variance_ytd correct |
| `TestForecastYearEnd` | 6 | Returns DataFrame; has required columns; monthly run rate for two months; forecast is run rate × 12; forecast variance sign; forecast_status column present |

### `tests/test_reporter.py` — 25 tests, 5 classes

| Class | Tests | What is covered |
|---|---|---|
| `TestDepartmentSummary` | 6 | Returns DataFrame; one row per department; IT budget and actual totals; variance column present; status column present; excludes future rows from budget totals |
| `TestCategorySummary` | 3 | Returns DataFrame; one row per category; SW actual total correct |
| `TestMonthlyTrend` | 5 | Returns DataFrame; one row per month; sorted by month; January totals correct; future month actual is NaN |
| `TestTopVariances` | 4 | Returns DataFrame; excludes future rows; unfavorable_only flag restricts to over-budget rows; n parameter caps result size |
| `TestPortfolioKpis` | 7 | Returns dict; total_budget correct (actuals rows only); total_actual correct; variance_negative for over-budget scenario; months_with_actuals correct; total_months correct; all status count keys present |

---

## Known Gaps

| Gap | Reason not tested | Risk |
|---|---|---|
| `generate_sample_data.py` output | Script is a one-time data generator; its output is the sample CSV, not library logic | LOW — the generated file is committed and tested via `TestLoadSample` |
| `app/main.py` rendering | Streamlit rendering requires a display environment; no headless test framework is included | LOW — all computation logic is in src/ modules, which are fully tested |
| Multi-column edge cases in `_validate` | Only single-column missing tested; multiple simultaneous missing columns would produce a different error message format | VERY LOW — the set difference is deterministic |
| Forecast with zero months of actuals | If no rows have actuals, `forecast_year_end` groupby produces empty result | LOW — sample data always has actuals for Jan–Oct |
