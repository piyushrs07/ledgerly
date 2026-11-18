# Ledgerly — Cohesion and Coupling Analysis

**Goal of the design: HIGH cohesion inside modules, LOW coupling between modules.**

## 1. Cohesion (how focused is each module?)
| Module | Single responsibility | Cohesion type | Level |
|---|---|---|---|
| `transactions.py` | Validate and CRUD transactions/categories | Functional | High |
| `budgets.py` | Budget limits, usage, rollover, alerts | Functional | High |
| `recurring.py` | Schedule calculation and generation | Functional | High |
| `analytics.py` | Read-only reporting and forecasting | Functional | High |
| `io_handler.py` | CSV import/export | Functional | High |
| `charts.py` | Chart rendering only (no DB access) | Functional | High |
| `models.py` | Data structures only (no logic) | Functional | High |
| `database.py` | Engine/session lifecycle | Functional | High |
| `cli.py` / `ui.py` | User interaction and formatting only | Functional (presentation) | High |

**How high cohesion was achieved**
- One reason to change per module: a new budget rule touches only `budgets.py`.
- Pure helpers (`clamp_day`, `classify`, `month_bounds`, `forecast_next`) are separated from DB-touching functions, so they are testable without a database.
- No "utility dump" module — shared things are tiny and specific (`errors.py`).

**Counter-example avoided:** putting budget alerts inside `transactions.py` would mix two concerns (*logical/coincidental cohesion*). Instead, the CLI composes `add_transaction` + `budget_status`.

## 2. Coupling (how dependent are modules?)
| From → To | Coupling type | Level | Justification |
|---|---|---|---|
| `cli`/`ui` → logic modules | Data (arguments and return values) | Low | Only public functions are called; no shared globals |
| `recurring` → `transactions` | Data | Low | Reuses `add_transaction` rather than duplicating validation |
| `budgets` → `transactions` | Data | Low | Reuses validation/category helpers |
| `io_handler` → `transactions` | Data | Low | Imports rows via `add_transaction` |
| `analytics` → `budgets` | Data | Low | Reuses `month_bounds` / `prev_month` date helpers |
| logic → `models` | Stamp (ORM objects) | Medium-low | Unavoidable shared data structure |
| `charts` → others | None | Lowest | Receives plain dicts/lists, imports only `errors` |
| `models` → others | None | Lowest | Depends on nothing but SQLAlchemy |

**Why coupling stays low**
1. **Dependency injection:** logic functions receive `session`; they never create their own connection, so tests inject an in-memory DB.
2. **One-way dependencies:** presentation → logic → data; there are no circular imports.
3. **Exceptions instead of printing/exiting:** logic raises domain errors; presentation decides how to show them.
4. **No global state** besides the DB path (environment variable read in `database.py` only).
5. **Plain-data interfaces:** status/summary functions return dicts, so the UI and CLI can change independently.

## 3. Evidence
- Unit tests of each module run against an in-memory DB with **no other module mocked** except via public APIs — only possible because coupling is low.
- `charts.py` and `analytics.forecast_next` are tested with plain Python values (no DB at all).
