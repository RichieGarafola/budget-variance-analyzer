# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-18

### Added
- Five-tab Streamlit dashboard: Monthly Trend, By Department, By Category, Line Items, Year-End Forecast
- `src/variance_engine.py` — variance computation, threshold-based status classification (FAVORABLE / ON BUDGET / WARNING / CRITICAL / NO ACTUALS), YTD summary, year-end run-rate forecasting
- `src/reporter.py` — department summary, category summary, monthly trend, top variances, portfolio KPIs
- `src/data_loader.py` — CSV loading with column validation and NaN coercion for future-period rows
- Sample dataset: 12-month FP&A data (Jan–Dec 2025) across six departments and multiple expense categories; actuals through October; November–December as future-period rows
- CSV line-item export via `st.download_button`
- Sidebar filters for department and category that update all tabs simultaneously
- KPI tiles: total YTD budget, total YTD actual, aggregate variance (dollar and percent), line item status counts, month coverage
- `scripts/generate_sample_data.py` — reproducible sample data generator (`random.seed(13)`, 324 rows)
- Full test suite: 72 tests across `test_data_loader.py`, `test_reporter.py`, and `test_variance_engine.py`
- `docs/ARCHITECTURE.md`, `docs/TESTING.md`, `docs/DATA_DICTIONARY.md`
- CI workflow (`.github/workflows/tests.yml`) — Python 3.11, pytest
- Streamlit theme configuration (`.streamlit/config.toml`)
