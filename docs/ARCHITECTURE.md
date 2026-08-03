# Architecture — Budget Variance Analyzer

## System Overview

```
                   data/sample/sample_budget.csv
                          (or user upload)
                                 │
                                 │ reads
                                 ▼
              ┌─────────────────────────────────────────┐
              │           src/data_loader.py            │
              │  load_csv · load_sample · _validate     │
              └─────────────────────────────────────────┘
                                 │ raw DataFrame
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                        app/main.py  (hub)                          │
│                   Streamlit Dashboard · 5 tabs                     │
│  imports directly from data_loader, variance_engine, and reporter  │
└──────────────────────────┬─────────────────────────┬──────────────┘
                           │                         │
                           ▼                         ▼
       ┌─────────────────────────────┐  ┌─────────────────────────────┐
       │   src/variance_engine.py    │  │      src/reporter.py        │
       │  compute_variance           │◄─│  department_summary         │
       │  classify_variance          │  │  category_summary           │
       │  forecast_year_end          │  │  monthly_trend              │
       │  STATUS_COLOR               │  │  top_variances              │
       │  WARN_THRESHOLD             │  │  portfolio_kpis             │
       └─────────────────────────────┘  └─────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │     CSV download       │
              │   (Line Items tab)     │
              └────────────────────────┘
```

**Import structure:** `app/main.py` imports directly from all three `src` modules simultaneously — it is not a linear pipeline. `src/reporter.py` also holds an internal dependency on `src/variance_engine` (the `◄─` arrow above) for `classify_variance` and `STATUS_ORDER` used in `top_variances`.

---

## Module Reference

| Module | Functions / Constants | Purpose |
|---|---|---|
| `src/data_loader.py` | `load_csv`, `load_sample`, `_validate`, `SAMPLE_PATH`, `REQUIRED_COLUMNS` | Reads and validates the budget CSV; coerces future-period rows to NaN actual |
| `src/variance_engine.py` | `compute_variance`, `classify_variance`, `ytd_summary`, `forecast_year_end`, `STATUS_COLOR`, `STATUS_ORDER`, `WARN_THRESHOLD`, `CRITICAL_THRESHOLD` | Core FP&A logic: variance math, status classification, year-end projection |
| `src/reporter.py` | `department_summary`, `category_summary`, `monthly_trend`, `top_variances`, `portfolio_kpis` | Aggregation layer: builds the view DataFrames and KPI dict consumed by each dashboard tab |
| `app/main.py` | — | Streamlit entry point; wires sidebar filters, tab rendering, and chart construction |
| `scripts/generate_sample_data.py` | — | Reproducible sample data generator (`random.seed(13)`) |

---

## Variance Classification Model

The classification model applies to `variance_pct = (budgeted − actual) / budgeted`.

**Sign convention:** A positive variance means spending is UNDER budget. A negative variance means spending is OVER budget.

| Status | Condition | Color | Meaning |
|---|---|---|---|
| FAVORABLE | `variance_pct > +0.05` | `#2ECC71` (green) | At least 5% under budget |
| ON BUDGET | `−0.05 ≤ variance_pct ≤ +0.05` | `#3498DB` (blue) | Within acceptable tolerance |
| WARNING | `−0.15 ≤ variance_pct < −0.05` | `#F39C12` (amber) | 5–15% over budget |
| CRITICAL | `variance_pct < −0.15` | `#E74C3C` (red) | More than 15% over budget |
| NO ACTUALS | `actual is NaN` | `#95A5A6` (grey) | Future period; not yet evaluated |

Threshold constants are defined in `variance_engine.py`:
- `WARN_THRESHOLD = 0.05` (5%)
- `CRITICAL_THRESHOLD = 0.15` (15%)

---

## Year-End Forecast Methodology

The forecast uses a simple run-rate approach:

```
monthly_run_rate = actual_ytd / months_with_actuals
forecast_year_end = monthly_run_rate × 12
forecast_variance = full_year_budget − forecast_year_end
```

This is computed per department/category pair. The forecast assumes uniform spending across the year. It does not account for seasonality, planned one-time expenditures, or step-changes in the second half of the year.

---

## Design Decisions

### 1. NaN for future periods, not zero

Future months (no actuals yet) have `actual = NaN` rather than `actual = 0`. This prevents future periods from being included in YTD aggregations or misclassified as 100% under budget. All reporter functions filter to `df["actual"].notna()` before computing YTD totals.

**Alternative considered:** Sentinel value (e.g., −1). Rejected because NaN propagates correctly through pandas arithmetic and is semantically unambiguous.

### 2. Thresholds as named constants, not sidebar sliders

`WARN_THRESHOLD` and `CRITICAL_THRESHOLD` are module-level constants rather than configurable UI parameters. This ensures that the classification model is stable for auditing purposes — the status of any given line item does not change based on who last moved a slider.

**Trade-off:** Power users cannot adjust sensitivity without editing source. Documented in README Limitations and Future Enhancements.

### 3. Reporter as aggregation-only layer

`reporter.py` functions do not call `compute_variance` (except `top_variances`, which needs row-level status). Department and category summaries recompute variance directly from budget and actual sums. This avoids double-aggregation artifacts when summarizing across months.

### 4. CSV-only input

The app loads flat CSV files via `load_csv`. This keeps the data pipeline transparent, testable, and free of authentication requirements. ERP integrations (Workday, SAP, QuickBooks) are documented as future work in the README.
