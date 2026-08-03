# Data Dictionary — Budget Variance Analyzer

## Input Schema

The application reads a CSV with the following five required columns. Additional columns are permitted but ignored.

| Column | Type | Required | Notes |
|---|---|---|---|
| `month` | Date | Yes | Any pandas-parseable date format: `2025-01-01`, `2025-01`, `Jan 2025`. Parsed as period-start date. |
| `department` | String | Yes | Cost center or department name. Used as grouping key. |
| `category` | String | Yes | Expense category within the department (Salaries, Travel, Software Licenses, etc.). |
| `budgeted` | Numeric | Yes | Planned spend for this department/category/month. Blank values are coerced to `0.0`. |
| `actual` | Numeric or blank | Yes | Actual spend. Leave blank for future months — blank values are loaded as `NaN` (not zero). |

**Required columns:** `month`, `department`, `category`, `budgeted`, `actual`. Missing any one raises `ValueError`.

---

## Computed Columns

These columns are added by `src/variance_engine.py` via `compute_variance`.

| Column | Type | Formula | Notes |
|---|---|---|---|
| `variance` | Float | `budgeted − actual` | Positive = under budget. NaN if no actual. |
| `variance_pct` | Float | `variance / budgeted` | Positive = under budget. NaN if no actual or zero budget. |
| `status` | String | See classification table below | One of five status labels. |

---

## Status Classification

Applied by `classify_variance(variance_pct)` in `variance_engine.py`.

| Status | Condition | Color |
|---|---|---|
| `FAVORABLE` | `variance_pct > 0.05` (> +5%) | `#2ECC71` |
| `ON BUDGET` | `−0.05 ≤ variance_pct ≤ 0.05` (within ±5%) | `#3498DB` |
| `WARNING` | `−0.15 ≤ variance_pct < −0.05` (5–15% over) | `#F39C12` |
| `CRITICAL` | `variance_pct < −0.15` (> 15% over) | `#E74C3C` |
| `NO ACTUALS` | `actual is NaN` | `#95A5A6` |

**Threshold constants** (defined in `variance_engine.py`):
- `WARN_THRESHOLD = 0.05`
- `CRITICAL_THRESHOLD = 0.15`

---

## Aggregation Outputs

### Department Summary (`department_summary`)

One row per department. Computed from rows that have actuals (YTD only).

| Column | Type | Notes |
|---|---|---|
| `department` | String | Department name |
| `budgeted` | Float | Sum of budgeted across all categories and months with actuals |
| `actual` | Float | Sum of actual across all categories and months with actuals |
| `variance` | Float | `budgeted − actual` |
| `variance_pct` | Float | `variance / budgeted` |
| `status` | String | Status classification for the department as a whole |

### Category Summary (`category_summary`)

One row per category across all departments. Same schema as department summary with `category` in place of `department`.

### Monthly Trend (`monthly_trend`)

One row per month (all departments combined).

| Column | Type | Notes |
|---|---|---|
| `month` | Datetime | Month start date |
| `budgeted` | Float | Total budgeted across all departments and categories |
| `actual` | Float | Total actual; NaN for future months (no actuals in that month) |
| `variance` | Float | `budgeted − actual`; NaN for future months |
| `variance_pct` | Float | `variance / budgeted`; NaN for future months |

### Portfolio KPIs (`portfolio_kpis`)

A Python dict with the following keys:

| Key | Type | Notes |
|---|---|---|
| `total_budget` | Float | Sum of budgeted for all rows with actuals |
| `total_actual` | Float | Sum of actual for all rows with actuals |
| `total_variance` | Float | `total_budget − total_actual` |
| `variance_pct` | Float | `total_variance / total_budget` |
| `n_favorable` | Int | Count of line items with FAVORABLE status |
| `n_on_budget` | Int | Count of line items with ON BUDGET status |
| `n_warning` | Int | Count of line items with WARNING status |
| `n_critical` | Int | Count of line items with CRITICAL status |
| `months_with_actuals` | Int | Number of distinct months that have any actual data |
| `total_months` | Int | Number of distinct months in the dataset (includes future) |

---

## Forecast Output (`forecast_year_end`)

One row per department/category pair.

| Column | Type | Notes |
|---|---|---|
| `department` | String | Department name |
| `category` | String | Category name |
| `full_year_budget` | Float | Total budgeted across all 12 months |
| `actual_ytd` | Float | Total actual through the most recent actuals month |
| `months_actual` | Int | Number of months with actuals for this dept/category |
| `monthly_run_rate` | Float | `actual_ytd / months_actual` |
| `forecast_year_end` | Float | `monthly_run_rate × 12` |
| `forecast_variance` | Float | `full_year_budget − forecast_year_end` |
| `forecast_variance_pct` | Float | `forecast_variance / full_year_budget` |
| `forecast_status` | String | Classification of forecast_variance_pct using same thresholds |

---

## Sample Dataset

**File:** `data/sample/sample_budget.csv`
**Generator:** `scripts/generate_sample_data.py` (`random.seed(13)`)

| Property | Value |
|---|---|
| Total rows | 324 |
| Months | January–December 2025 |
| Months with actuals | January–October 2025 (10 months) |
| Future months (budget only) | November–December 2025 (2 months) |
| Departments | 6: Operations, IT, HR, Finance, Business Dev, R&D |
| Categories per department | 4–5 |
| Annual budget range | $360,000 (Finance) – $1,800,000 (Operations) |
| Variance profile | Per dept/category bias in range −18% to +12% (seeded by combo key) |

**Column definitions (same as input schema above).**

---

## Export Schema

**CSV download** (Line Items tab): The full `enriched` DataFrame from `compute_variance`, filtered by the status multiselect. Contains all input columns plus `variance`, `variance_pct`, `status`. Downloaded as `budget_variance.csv`.
