# Ledgerly — Test Plan and Test Cases

Framework: **Pytest** (+ `pytest-cov`). Every test uses an isolated in-memory SQLite database
(`tests/conftest.py::session`) or a temporary file (CLI tests). Run: `pytest --cov=ledgerly`.

## 1. Strategy
| Level | Location | What it proves |
|---|---|---|
| Unit | `tests/unit/` | Each function/module behaves correctly in isolation, including edge cases |
| Integration | `tests/integration/test_workflows.py` | Modules cooperate (e.g. recurring → budgets → analytics) |
| System / end-to-end | `tests/integration/test_cli.py` | Real CLI commands against a real SQLite file |

Techniques: equivalence partitioning, boundary-value analysis (79.9 / 80 / 100 / 100.1 %), parametrised
tests, negative testing (invalid input), idempotency checks, round-trip checks (export → import).

## 2. Test Cases (representative; all automated)
| TC | Requirement | Scenario | Input | Expected result | Test |
|---|---|---|---|---|---|
| TC-01 | FR-1 | Add valid expense | 250, expense, Food, 2026-11-01 | Saved; category `food` | `test_transactions::test_add_and_get` |
| TC-02 | FR-2 | Amount ≤ 0 / text / NaN / inf | 0, -5, "abc", None, nan, inf | `ValidationError` | `test_amount_invalid` |
| TC-03 | FR-2 | Amount rounding | "49.999" | 50.0 | `test_amount_valid_and_rounded` |
| TC-04 | FR-2 | Invalid date | "2026-02-30", "yesterday" | `ValidationError` | `test_parse_date_invalid` |
| TC-05 | FR-2 | Unknown type | "loan" | `ValidationError` | `test_type_invalid` |
| TC-06 | FR-3 | Filters by category/type/date/limit | mixed data | Only matching rows | `test_list_filters` |
| TC-07 | FR-3 | Newest first | 2 dates | Descending order | `test_list_newest_first` |
| TC-08 | FR-4 | Update then delete | id | Changed / removed | `test_update`, `test_delete` |
| TC-09 | FR-4 | Delete non-existent | id 999 | `NotFoundError` | `test_delete_missing` |
| TC-10 | FR-5 | Category case-insensitive reuse | "Food", "FOOD" | Same category id | `test_category_reused_case_insensitive` |
| TC-11 | FR-6 | Update existing budget | 5000 → 7000 | One budget, new limit | `test_set_updates_existing` |
| TC-12 | FR-7 | Only matching expenses counted | other month/category/income | Spent = 100 | `test_only_expenses_in_month_and_category_counted` |
| TC-13 | FR-8 | Status boundaries | 0, 79.9, 80, 100, 100.1 % | ok, ok, warning, warning, exceeded | `test_classify` |
| TC-14 | FR-8 | Warning on add (CLI) | budget 1000, add 900 | Output contains WARNING | `test_budget_alert_shown_on_add` |
| TC-15 | FR-9 | Rollover chains | 400, 1000 spent on limit 1000 | Carry 600 → 600 | `test_unused_budget_chains_across_months` |
| TC-16 | FR-9 | Overspend → no debt | 1500 of 1000 | Carry 0 | `test_overspend_does_not_carry_debt` |
| TC-17 | FR-9 | Rollover across year end | Dec → Jan | Carry 900 | `test_rollover_across_year_boundary` |
| TC-18 | FR-11 | Month-end clamping | monthly on 31st from Jan | Jan 31, Feb 28, Mar 31, Apr 30 | `test_monthly_month_end_clamping` |
| TC-19 | FR-11 | Leap year | 31st in Feb 2028 | Feb 29 | `test_monthly_leap_year` |
| TC-20 | FR-10 | Weekly rule | start 2026-11-01 | 1, 8, 15, 22 Nov | `test_weekly` |
| TC-21 | FR-10 | End date respected | end 2026-03-15 | 3 occurrences | `test_end_date_respected` |
| TC-22 | FR-12 | Idempotent generation | run twice | 3 created, then 0 | `test_idempotent` |
| TC-23 | FR-11 | Incremental generation | next month | exactly 1 new | `test_incremental_next_month` |
| TC-24 | FR-13 | Monthly summary | income 50000, expenses 14000 | net 36000 | `test_monthly_summary` |
| TC-25 | FR-14 | Breakdown sorted | rent 10000, food 4000 | rent first | `test_category_breakdown_sorted` |
| TC-26 | FR-15 | MoM change, new & vanished category | food 2000→4000; fun gone; gym new | +100%, −100%, percent `None` | `test_month_over_month*` |
| TC-27 | FR-15 | January compares with December | Dec 2025 vs Jan 2026 | change +50 | `test_month_over_month_january_uses_previous_december` |
| TC-28 | FR-16 | Forecast linear | 100,200,300 | 400 | `TestForecast::test_perfect_linear_trend` |
| TC-29 | FR-16 | Forecast never negative | 300,100 | 0 | `test_never_negative` |
| TC-30 | FR-16 | Forecast needs 2 points | [100] | `ValidationError` | `test_needs_two_points` |
| TC-31 | FR-17 | Import with bad rows | 5 invalid rows + 1 valid | 1 imported; errors at lines 3-7 | `test_import_reports_bad_rows_but_keeps_good_ones` |
| TC-32 | FR-17 | Missing columns / empty file / BOM / header case | various | Error or success as specified | `test_import_missing_columns`, `test_import_empty_file`, `test_import_header_case_and_bom` |
| TC-33 | FR-18 | Export round-trip and date filter | 2 rows | Correct CSV | `test_export_roundtrip`, `test_export_date_filter` |
| TC-34 | FR-19 | Charts created / empty rejected | data / none | PNG exists / error | `test_charts.py` |
| TC-35 | NFR-1 | Rollback on exception | raise inside scope | 0 rows saved | `test_session_scope_rolls_back_on_error` |
| TC-36 | NFR-2 | Friendly CLI errors | `add --amount -5` | `Error: ...`, exit 1, no traceback | `test_invalid_amount_gives_clean_error` |
| TC-37 | Integration | Expense → budget alert | 850 then 200 on 1000 | warning → exceeded | `test_expense_triggers_budget_alert` |
| TC-38 | Integration | Recurring → budget → analytics | rent + salary rules | warning status, net 40000, forecast 10000 | `test_recurring_feeds_budget_and_analytics` |
| TC-39 | Integration | CSV → report → export | bank.csv | 3 imported, top = food | `test_csv_import_then_report_and_export` |
| TC-40 | System | Full CLI flows | add/list/edit/delete/budget/recurring/report/import/export/chart | Expected output | `test_cli.py` |
| TC-41 | FR-20 | Every dashboard page renders | 5 pages | No exception | `test_ui_smoke.py` (skipped if streamlit missing) |

## 3. Results
Run `pytest --cov=ledgerly` — **121 tests passed, 97% line coverage** of the core package at the time of release.
Uncovered lines are a few CLI error branches. `ui.py` (Streamlit dashboard) and `__main__.py` are excluded from the line-coverage figure (see `.coveragerc`); the dashboard is verified by smoke tests that render every page (TC-41).

## 4. Known Limitations (documented, not defects)
- Single currency, single user.
- Amounts stored as floating point rounded to 2 decimals (acceptable for personal use; a production system would use integer minor units or `Decimal`).
- Forecast is a simple linear trend, not a statistical model.
