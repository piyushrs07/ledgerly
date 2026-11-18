# Ledgerly — Software Requirements Specification (SRS)

Version 1.0 · Author: Piyush Raj Singh (Roll No. 24P0051017)

## 1. Introduction
### 1.1 Purpose
This document specifies the functional and non-functional requirements of **Ledgerly**, a
personal finance tracker with budgeting, recurring transactions, analytics and CSV import/export.
### 1.2 Scope
Ledgerly runs locally on one machine for one user and stores data in SQLite. It is operated through
a CLI (`ledgerly ...`) and an optional Streamlit dashboard. See the Problem Statement for exclusions.
### 1.3 Definitions
| Term | Meaning |
|---|---|
| Transaction | A single income or expense record |
| Budget | Monthly spending limit for one category |
| Rollover | Unused budget of a month added to the next month's available budget |
| Recurring rule | A template that generates transactions on a schedule |
| Month-end clamping | Using the last valid day of a month when the requested day does not exist (31 → 28/29) |
### 1.4 References
IEEE 830 SRS structure; SQLAlchemy 2.x, Click, Pytest documentation.

## 2. Overall Description
### 2.1 Product perspective
Stand-alone desktop/terminal application. Layers: Presentation (CLI/UI) → Core logic → Data (SQLite).
### 2.2 User classes
Single user class: an individual tracking personal finances (basic command-line familiarity).
### 2.3 Operating environment
Python ≥ 3.10 on Windows, macOS or Linux. No network required.
### 2.4 Constraints and assumptions
- One currency; amounts are positive numbers rounded to 2 decimals.
- Dates are calendar dates (no time or time-zone component).
- Developed solo within two months, using the Incremental SDLC model.
- Pytest is the mandatory testing framework.

## 3. Functional Requirements
| ID | Requirement | Priority |
|---|---|---|
| **FR-1** | The system shall add a transaction with amount, type (income/expense), category, date (default today) and optional note. | High |
| FR-2 | The system shall reject non-positive, non-numeric or non-finite amounts, unknown types, empty categories and invalid dates with a clear message. | High |
| FR-3 | The system shall list transactions newest-first with filters (category, type, date range, limit). | High |
| FR-4 | The system shall edit and delete a transaction by ID, and report an error if the ID does not exist. | High |
| FR-5 | Categories shall be created automatically on first use and matched case-insensitively. | Medium |
| **FR-6** | The system shall set/update/delete a monthly budget per category with an optional rollover flag. | High |
| FR-7 | The system shall compute spent, available, remaining and percent used per budget per month, counting only expenses of that category and month. | High |
| FR-8 | The system shall classify a budget as OK (< 80%), WARNING (≥ 80% to 100%) or EXCEEDED (> 100%) and show a warning when an expense is added. | High |
| FR-9 | With rollover on, unused budget shall carry into following months; overspending shall not create negative carry. | Medium |
| **FR-10** | The system shall define recurring rules (monthly or weekly, optional end date) for income or expenses. | High |
| FR-11 | The system shall generate all due transactions up to today from recurring rules, applying month-end clamping and leap-year handling. | High |
| FR-12 | Generation shall be idempotent: running it repeatedly shall not create duplicates. | High |
| **FR-13** | The system shall report monthly income, expense and net. | High |
| FR-14 | The system shall report expense per category (largest first) and top-N categories. | Medium |
| FR-15 | The system shall compare each category with the previous month (absolute and percent change). | Medium |
| FR-16 | The system shall forecast next month's total expense using a least-squares linear trend over up to 6 months, never below zero, requiring ≥ 2 months of data. | Medium |
| **FR-17** | The system shall import transactions from CSV (columns date, amount, type, category; optional note), reporting each invalid row with its line number while still importing valid rows. | High |
| FR-18 | The system shall export transactions (optionally date-filtered) to CSV. | Medium |
| FR-19 | The system shall generate a category pie chart and a monthly trend chart (with forecast) as PNG files. | Low |
| FR-20 | The system shall provide a Streamlit dashboard offering the main features (dashboard, add, list/delete, budgets, recurring). | Low |

## 4. Non-Functional Requirements
| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Reliability | A failed operation shall roll back; no partial data is saved (transactional sessions). |
| NFR-2 | Usability | Errors shall be human-readable messages (never Python tracebacks) with a non-zero exit code. |
| NFR-3 | Performance | Common commands shall respond in under 1 second for up to 50,000 transactions. |
| NFR-4 | Maintainability | Modules shall have high cohesion and low coupling; business logic shall not live in CLI/UI code. |
| NFR-5 | Testability | Automated test coverage shall be ≥ 90%; tests run on an isolated in-memory database. |
| NFR-6 | Portability | Runs on Windows, macOS and Linux with `pip install -r requirements.txt`. |
| NFR-7 | Data safety | Data stays on the local machine in a single SQLite file (path configurable via `--db` or `LEDGERLY_DB`). |
| NFR-8 | Accuracy | Monetary values are rounded to 2 decimals at the boundary of every calculation. |

## 5. Use Cases
| ID | Use case | Actor | Main flow | Alternate / exception |
|---|---|---|---|---|
| UC-1 | Record expense | User | `add` → validate → save → show confirmation | Invalid input → error message; over 80% budget → warning |
| UC-2 | Set budget | User | `budget set` → save/update limit | Limit ≤ 0 → error |
| UC-3 | Check budgets | User | `budget status --month` → table with status | No budgets → informative message |
| UC-4 | Automate rent/salary | User | `recurring add` then `recurring run` | Run again → 0 new transactions |
| UC-5 | Import bank CSV | User | `import file.csv` → summary | Bad rows listed with line numbers; missing columns → error |
| UC-6 | Review month | User | `report monthly / compare / forecast` | Fewer than 2 months → forecast error |
| UC-7 | Visualise | User | `chart pie` / `chart trend` | No data → error message |

## 6. Data Requirements
Entities: **Category**, **Transaction**, **Budget**, **RecurringRule** (ER diagram in the Architecture document).

## 7. Requirement → Test Traceability
See `06_test_plan.md`; every functional requirement is mapped to at least one test case.
