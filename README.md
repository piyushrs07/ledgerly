# 💰 Ledgerly

**A smart personal ledger for tracking income, expenses, and budgets.**

A Python command-line application (with an optional Streamlit dashboard) backed by SQLite.
Built for the *Software Engineering and Applications* course using the **Incremental SDLC model**,
with full documentation and a **Pytest** suite (121 tests, 97% coverage).

**Author:** Piyush Raj Singh · Roll No. 24P0051017 · Integrated M.Sc. Data Science, Goa University

## Features
- Add / list / edit / delete income and expense transactions, auto-created categories
- Monthly **budgets** per category with **rollover**, warnings at 80% and when exceeded
- **Recurring transactions** (monthly/weekly) with month-end clamping and leap-year handling, idempotent generation
- **CSV import** with per-row error reporting and **CSV export**
- **Analytics:** monthly summary, category breakdown, month-over-month comparison, linear-trend **forecast**
- **Charts:** category pie and monthly trend (PNG)
- Optional **Streamlit dashboard**

## Setup
```bash
git clone <your-repo-url> && cd ledgerly
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .                                      # gives the `ledgerly` command
```
Data is stored in `~/.ledgerly/ledgerly.db`. Override with `--db PATH` or the `LEDGERLY_DB` environment variable.

## Usage
```bash
ledgerly add --amount 500 --category food --note "groceries"
ledgerly add --amount 50000 --type income --category salary --date 2026-11-01
ledgerly list --category food --limit 10
ledgerly edit 1 --amount 450
ledgerly delete 1

ledgerly budget set --category food --limit 5000 --rollover
ledgerly budget status --month 2026-11

ledgerly recurring add --amount 10000 --category rent --frequency monthly --start 2026-01-31
ledgerly recurring run            # generate everything that is due (safe to repeat)

ledgerly report monthly --month 2026-11
ledgerly report compare --month 2026-11
ledgerly report forecast --month 2026-11

ledgerly import sample_data/bank_statement.csv
ledgerly export my_data.csv
ledgerly chart pie --month 2026-11 --out pie.png
ledgerly chart trend --month 2026-11 --out trend.png
```
(`python -m ledgerly ...` works too.) Dashboard: `streamlit run ledgerly/ui.py`

### Sample output
```
$ ledgerly import sample_data/bank_statement.csv
Imported 12 row(s), 1 error(s)
  line 14: Invalid date: 'bad-date' (use YYYY-MM-DD)

$ ledgerly budget status --month 2026-11
Category    Available    Spent    Remaining    Used    Status
----------  -----------  -------  -----------  ------  --------
food        4000.00      3900.00  100.00       97.5%   WARNING

$ ledgerly report compare --month 2026-11
Category       Previous    Current    Change    %
-------------  ----------  ---------  --------  ------
entertainment  2600.00     3400.00    +800.00   +30.8%
food           3100.00     3900.00    +800.00   +25.8%
transport      1500.00     1700.00    +200.00   +13.3%
```

## Architecture
Layered: **Presentation** (`cli.py`, `ui.py`) → **Core logic** (`transactions`, `budgets`, `recurring`,
`analytics`, `io_handler`, `charts`) → **Data** (`models`, `database`, SQLite). See `docs/03_architecture.md`.

```
ledgerly/
├── ledgerly/        # source code
├── tests/
│   ├── unit/        # per-module tests
│   └── integration/ # workflows + CLI end-to-end
├── docs/            # SDLC documents
├── sample_data/
└── requirements.txt
```

## Testing
```bash
pytest                          # run all tests
pytest --cov=ledgerly           # with coverage report
pytest tests/unit               # unit tests only
pytest tests/integration        # integration + CLI tests
```

## Documentation (`docs/`)
1. `01_problem_statement.md`
2. `02_SRS.md` — requirements FR-1…FR-20, NFR-1…NFR-8, use cases
3. `03_architecture.md` — layered design, ER diagram, SDLC increments
4. `04_design_specification.md` — every module and function with signatures
5. `05_cohesion_coupling.md` — high cohesion / low coupling analysis
6. `06_test_plan.md` — 40 documented test cases mapped to requirements

## Limitations
Single user, single currency, local storage; amounts are floats rounded to 2 decimals; forecast is a simple linear trend.
