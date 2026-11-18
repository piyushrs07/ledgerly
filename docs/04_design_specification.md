# Ledgerly — Design Specification (Modules and Functions)

Author: Piyush Raj Singh (Roll No. 24P0051017)

Conventions: every logic function takes an SQLAlchemy `session` as its first argument where it touches the database; errors are raised as `ValidationError` / `NotFoundError`; functions never print (only `cli.py` / `ui.py` do).


## Module `transactions.py`
**Responsibility:** Validates input and performs CRUD on transactions and categories.

| Function | Signature | Purpose |
|---|---|---|
| `parse_date` | `parse_date(value)` | Convert a date object/string (YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY) to `date`; raise ValidationError if invalid. |
| `validate_amount` | `validate_amount(amount)` | Return amount rounded to 2 decimals; reject non-numeric, non-finite, zero or negative values. |
| `validate_type` | `validate_type(tx_type)` | Normalise and validate transaction type (income/expense). |
| `normalize_category` | `normalize_category(name)` | Trim/lower-case category name; reject empty or > 50 chars. |
| `get_or_create_category` | `get_or_create_category(session, name)` | Fetch a category by name or create it (FR-5). |
| `add_transaction` | `add_transaction(session, amount, tx_type, category, tx_date=None, note='', recurring_rule_id=None)` | Validate inputs and persist a new transaction (FR-1, FR-2). |
| `get_transaction` | `get_transaction(session, tx_id)` | Fetch by ID or raise NotFoundError. |
| `list_transactions` | `list_transactions(session, category=None, tx_type=None, start=None, end=None, limit=None)` | Newest-first list with optional category/type/date/limit filters (FR-3). |
| `update_transaction` | `update_transaction(session, tx_id, amount=None, tx_type=None, category=None, tx_date=None, note=None)` | Change any subset of fields of an existing transaction (FR-4). |
| `delete_transaction` | `delete_transaction(session, tx_id)` | Delete by ID or raise NotFoundError (FR-4). |

## Module `budgets.py`
**Responsibility:** Computes budget usage, rollover and alerts.

| Function | Signature | Purpose |
|---|---|---|
| `month_bounds` | `month_bounds(year, month)` | Return [first day, first day of next month) for a month; validates month 1-12. |
| `prev_month` | `prev_month(year, month)` | Return (year, month) of the previous month, wrapping across years. |
| `set_budget` | `set_budget(session, category, monthly_limit, rollover=False, start=None)` | Create or update a category's monthly limit and rollover flag (FR-6). |
| `get_budget` | `get_budget(session, category)` | Fetch a category's budget or raise NotFoundError. |
| `list_budgets` | `list_budgets(session)` | All budgets ordered by category name. |
| `delete_budget` | `delete_budget(session, category)` | Remove a category's budget. |
| `month_spend` | `month_spend(session, category_id, year, month)` | Sum of expenses for a category in a month (FR-7). |
| `rollover_carry` | `rollover_carry(session, budget, year, month)` | Unused budget carried into a month, chained from the budget's start month (FR-9). |
| `classify` | `classify(percent_used)` | Map percent used to ok / warning (>= 80) / exceeded (> 100) (FR-8). |
| `budget_status` | `budget_status(session, category, year, month)` | Limit, carry-in, available, spent, remaining, percent and status for one category-month (FR-7, FR-8). |
| `all_budget_statuses` | `all_budget_statuses(session, year, month)` | Status for every budget in a month. |
| `get_alerts` | `get_alerts(session, year, month)` | Only budgets in warning or exceeded state. |

## Module `recurring.py`
**Responsibility:** Defines schedules and generates due transactions.

| Function | Signature | Purpose |
|---|---|---|
| `clamp_day` | `clamp_day(year, month, day)` | Date for a day-of-month clamped to the month's last day (31 -> 28/29/30). |
| `add_rule` | `add_rule(session, amount, tx_type, category, frequency, start_date, day_of_month=None, end_date=None, note='')` | Validate and store a monthly/weekly recurring rule (FR-10). |
| `list_rules` | `list_rules(session)` | All rules ordered by ID. |
| `delete_rule` | `delete_rule(session, rule_id)` | Delete a rule or raise NotFoundError. |
| `occurrences` | `occurrences(rule, up_to)` | All due dates of a rule up to a given date, honouring start/end and clamping (FR-11). |
| `generate_due` | `generate_due(session, today=None)` | Create transactions for every ungenerated occurrence; idempotent (FR-11, FR-12). |

## Module `analytics.py`
**Responsibility:** Read-only reporting and forecasting.

| Function | Signature | Purpose |
|---|---|---|
| `monthly_summary` | `monthly_summary(session, year, month)` | Income, expense and net for a month (FR-13). |
| `category_breakdown` | `category_breakdown(session, year, month, tx_type='expense')` | Per-category totals for a month, largest first (FR-14). |
| `top_categories` | `top_categories(session, year, month, n=3)` | Top-N categories by spend (FR-14). |
| `month_over_month` | `month_over_month(session, year, month)` | Per-category change vs previous month, absolute and percent (FR-15). |
| `expense_series` | `expense_series(session, year, month, months=6)` | Monthly expense totals for the last N months, oldest first. |
| `forecast_next` | `forecast_next(values)` | Least-squares linear projection of the next value, floored at 0 (FR-16). |
| `forecast_next_month` | `forecast_next_month(session, year, month, months=6)` | Forecast from DB data, ignoring leading empty months (FR-16). |

## Module `io_handler.py`
**Responsibility:** CSV import/export with validation.

| Function | Signature | Purpose |
|---|---|---|
| `import_csv` | `import_csv(session, path)` | Import rows with per-row error reporting; valid rows still saved (FR-17). |
| `export_csv` | `export_csv(session, path, start=None, end=None)` | Write transactions (oldest first, optional date filter) to CSV (FR-18). |

## Module `charts.py`
**Responsibility:** Renders PNG charts with matplotlib.

| Function | Signature | Purpose |
|---|---|---|
| `category_pie` | `category_pie(breakdown, path, title='Spending by category')` | Save a category pie chart PNG (FR-19). |
| `trend_line` | `trend_line(series, path, forecast=None, title='Monthly expenses')` | Save a monthly trend line PNG with optional forecast point (FR-19). |

## Module `database.py`
**Responsibility:** Engine, schema and transactional session handling.

| Function | Signature | Purpose |
|---|---|---|
| `get_db_url` | `get_db_url(path=None)` | Resolve DB location: explicit path > LEDGERLY_DB > ~/.ledgerly/ledgerly.db. |
| `get_engine` | `get_engine(path=None)` | Create a SQLAlchemy engine. |
| `init_db` | `init_db(engine)` | Create tables if missing. |
| `make_session_factory` | `make_session_factory(engine)` | Build a session factory bound to an engine. |
| `session_scope` | `session_scope(path=None)` | Context manager: commit on success, rollback on error (NFR-1). |

## Module `models.py`
| Class | Fields |
|---|---|
| `Category` | id, name (unique) |
| `Transaction` | id, amount, type, category_id, date, note, recurring_rule_id |
| `Budget` | id, category_id (unique), monthly_limit, rollover, start_date |
| `RecurringRule` | id, amount, type, category_id, note, frequency, day_of_month, start_date, end_date, last_generated |

## Module `errors.py`
`LedgerlyError` (base) → `ValidationError`, `NotFoundError`.

## Module `cli.py` (presentation)
| Command | Maps to |
|---|---|
| `add`, `list`, `edit`, `delete` | `transactions.*` (+ `budgets.budget_status` for the add warning) |
| `budget set / status / delete` | `budgets.*` |
| `recurring add / list / run / delete` | `recurring.*` |
| `report monthly / compare / forecast` | `analytics.*` |
| `import`, `export` | `io_handler.*` |
| `chart pie / trend` | `analytics.*` + `charts.*` |

Global option: `--db PATH` (or env `LEDGERLY_DB`). Errors → `Error: <message>`, exit code 1.

## Module `ui.py` (presentation, optional)
Pages: Dashboard, Add transaction, Transactions, Budgets, Recurring — all call the same logic modules.

## Algorithms
**Month-end clamping:** `day' = min(day, calendar.monthrange(y, m)[1])`.
**Rollover:** starting at the budget's start month, `carry(next) = max(0, limit + carry - spent)`.
**Forecast:** least-squares line `y = a·x + b` over the last ≤ 6 non-empty months (`numpy.polyfit`), prediction at `x = n`, floored at 0.
**Budget status:** `percent = spent / (limit + carry) × 100`; ok < 80 ≤ warning ≤ 100 < exceeded.
