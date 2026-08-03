# Engineering Decisions — Budget Variance Analyzer

---

## ED-1: NaN for future periods, not zero

**Decision:** Future months — those where actual spending data has not yet been recorded — store `actual = NaN` in the DataFrame. The `load_csv()` function coerces future-period rows to NaN during load; all reporter functions filter to `df["actual"].notna()` before computing YTD totals.

**Alternative considered:** Use a sentinel value such as `−1` or `0` to distinguish future periods from months that genuinely had zero actual spend.

**Why NaN was chosen:** `NaN` propagates correctly through pandas arithmetic without requiring additional guard conditions at every aggregation site. A zero in `actual` would be treated as 100% under budget by `classify_variance()`, producing spurious FAVORABLE statuses for every future period and inflating the YTD under-budget percentage. A sentinel like `−1` would require explicit guards in every function that computes `actual / budgeted`. NaN is the pandas-idiomatic way to represent "not yet known" and triggers NaN propagation rather than silent incorrect results throughout the reporting layer.

---

## ED-2: Variance thresholds as named constants, not configurable sliders

**Decision:** `WARN_THRESHOLD = 0.05` and `CRITICAL_THRESHOLD = 0.15` are module-level constants in `variance_engine.py`. They are not exposed as UI parameters or sidebar sliders.

**Alternative considered:** Expose threshold sliders in the sidebar, allowing analysts to adjust the boundaries between WARNING, ON BUDGET, and FAVORABLE at runtime.

**Why constants were chosen:** Configurable thresholds mean the status of any line item changes depending on who last moved the slider, making the dashboard unsuitable for audit or governance reporting. A Contracting Officer's Representative who reviews the same report twice — once with the default thresholds and once after an analyst adjusted them — would see different status colors for the same data. Fixed constants ensure the classification model is stable and reproducible. The 5% / 15% boundaries are a common FP&A convention for government contract oversight and are documented in the README as the model's explicit parameters.

---

## ED-3: Reporter layer recomputes variance from aggregated sums

**Decision:** `department_summary()` and `category_summary()` compute variance directly from aggregated budget and actual totals — not by calling `compute_variance()` on individual rows and then summing the results.

**Alternative considered:** Call `compute_variance()` on each row first, then group by department/category and sum the variance column.

**Why sum-first was chosen:** Summing row-level variances and then computing a percentage variance on the sum is not mathematically equivalent to computing variance on the sum directly. Row-level variance percentages weight each row equally, so a department with one $5,000 row and one $500,000 row would have its summary distorted by the smaller row's potentially large percentage variance. Computing variance from aggregated totals — `variance_pct = (total_budget - total_actual) / total_budget` — produces the department-level view that a finance reviewer expects: how far is the department's total spend from its total budget?

---

## ED-4: Sign convention — positive variance means under budget (FAVORABLE)

**Decision:** `compute_variance()` uses the formula `variance_pct = (budgeted - actual) / budgeted`. A positive value means actual spending is below budget (FAVORABLE); a negative value means actual spending exceeds budget (CRITICAL/WARNING).

**Alternative considered:** Reverse the sign: `variance_pct = (actual - budgeted) / budgeted`, which is the conventional "actual minus plan" formula used in some FP&A contexts.

**Why budgeted-minus-actual was chosen:** In a government contract oversight context, the primary concern is whether spending is over budget (a compliance risk), not whether it is under budget (which is generally acceptable). Using `(budgeted - actual)` makes the sign of the variance intuitive: positive means you have budget remaining, negative means you have overrun. The `classify_variance()` thresholds then read naturally — a positive variance above `WARN_THRESHOLD` is FAVORABLE, and a negative variance below `−WARN_THRESHOLD` is WARNING or CRITICAL. This matches how most government FP&A dashboards present contract variance.

---

## ED-5: CSV-only input, no ERP integration

**Decision:** The data pipeline reads flat CSV files only. The app does not connect to ERP systems (Workday, SAP, QuickBooks) or databases. The required column schema (`department`, `category`, `period`, `budgeted`, `actual`) is documented and enforced by `_validate()`.

**Alternative considered:** Provide direct integration with Workday or SAP via API connectors so analysts can pull live data without exporting a CSV first.

**Why CSV-only was chosen:** ERP API integration requires authentication credentials, API key management, network access, and ongoing maintenance as vendor APIs change. These dependencies make the tool unsuitable for air-gapped environments, evaluation by portfolio reviewers, and CI testing — all of which require the tool to run standalone. A CSV export step is a one-click operation in all major ERP systems. The `_validate()` function enforces the required schema at load time, producing a clear error message if the export format does not match. ERP integration is documented in the README Roadmap for future development.

---

## ED-6: Run-rate year-end forecast, not seasonality-adjusted

**Decision:** `forecast_year_end()` uses a simple run-rate formula: `monthly_run_rate = actual_ytd / months_with_actuals`, then `forecast_year_end = monthly_run_rate × 12`. It does not adjust for seasonal spending patterns, planned one-time expenditures, or known step-changes.

**Alternative considered:** Implement a seasonality-adjusted forecast using historical spend ratios per period (e.g., if November historically accounts for 15% of annual spend, weight November projections accordingly).

**Why run-rate was chosen:** Seasonality-adjusted forecasting requires historical data (at least one prior year) to compute per-period ratios. The tool's input is a single-year budget file with YTD actuals — no prior year data is available to derive seasonal factors. The run-rate approach produces a conservative, explainable projection: it assumes the current spending pattern continues for the remainder of the year. For government contract oversight, a simple and auditable forecast is preferable to a complex model whose assumptions a reviewer cannot verify. The limitation is documented in ARCHITECTURE.md and the README.

---

*This document is a repository artifact and may be committed to the published repository.*
