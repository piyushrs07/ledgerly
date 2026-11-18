# Ledgerly — Problem Statement

**Project:** Ledgerly — a smart personal ledger for tracking income, expenses, and budgets
**Author:** Piyush Raj Singh · Roll No. 24P0051017 · Integrated M.Sc. Data Science, Goa University
**Course:** Software Engineering and Applications (SEA) · **SDLC model:** Incremental

## 1. Problem
Students and young professionals handle money across many small transactions (food, travel,
rent, subscriptions) and rarely have a clear picture of where it goes. Spreadsheets need manual
upkeep, and commercial apps are heavy, ad-driven, or tied to a cloud account. As a result:

1. Spending is not recorded consistently, so nobody knows the real monthly totals.
2. Budgets are set mentally and are overspent without warning.
3. Fixed monthly payments (rent, salary, subscriptions) must be re-entered every month.
4. Bank statements arrive as CSV files that cannot be used directly.
5. There is no simple way to see trends or estimate next month's spending.

## 2. Proposed Solution
Ledgerly is a lightweight, offline, Python application with a **command-line interface** and an
optional **Streamlit dashboard**, backed by a local **SQLite** database. It lets a user:

- record income and expenses with categories and notes,
- set monthly budgets per category (with optional rollover) and get warnings at 80% and when exceeded,
- define recurring transactions that are generated automatically (including month-end edge cases),
- import bank-statement CSVs with row-level validation and export data back to CSV,
- view monthly summaries, category breakdowns, month-over-month change and a linear-trend forecast,
- generate charts (category pie, monthly trend).

## 3. Objectives
- Deliver a **complete, tested** application, not a prototype.
- Apply a classical SDLC (Incremental) with full documentation (SRS, architecture, design spec, test plan).
- Demonstrate **high cohesion and low coupling** through a layered design.
- Achieve **≥ 90% automated test coverage** using Pytest (unit + integration).

## 4. Scope
**In scope:** single-user, single-currency, local storage, CLI + dashboard, CSV import/export, PNG charts.
**Out of scope:** multi-user accounts, cloud sync, multi-currency, bank API integration, machine learning.

## 5. Stakeholders
| Stakeholder | Interest |
|---|---|
| End user (student / individual) | Easy tracking, budget warnings, insights |
| Developer (author) | Maintainable, tested, documented code |
| Course evaluator | Evidence of SDLC discipline, testing and design quality |
