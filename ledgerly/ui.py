"""Optional Streamlit dashboard (presentation layer).

Run with:  streamlit run ledgerly/ui.py
Uses the same core modules as the CLI - no business logic is duplicated here.
"""
from datetime import date

import pandas as pd
import streamlit as st

from ledgerly import analytics, budgets, recurring, transactions
from ledgerly.database import session_scope
from ledgerly.errors import LedgerlyError

st.set_page_config(page_title="Ledgerly", page_icon="💰", layout="wide")
st.title("💰 Ledgerly")
st.caption("A smart personal ledger for tracking income, expenses, and budgets")

page = st.sidebar.radio("Go to", ["Dashboard", "Add transaction", "Transactions",
                                  "Budgets", "Recurring"])
today = date.today()


def month_picker():
    c1, c2 = st.columns(2)
    year = c1.number_input("Year", 2000, 2100, today.year)
    month = c2.selectbox("Month", list(range(1, 13)), index=today.month - 1)
    return int(year), int(month)


def show_error(exc):
    st.error(str(exc))


if page == "Dashboard":
    year, month = month_picker()
    with session_scope() as s:
        summary = analytics.monthly_summary(s, year, month)
        breakdown = analytics.category_breakdown(s, year, month)
        statuses = budgets.all_budget_statuses(s, year, month)
        series = analytics.expense_series(s, year, month)
        try:
            forecast = analytics.forecast_next_month(s, year, month)
        except LedgerlyError:
            forecast = None
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Income", f"{summary['income']:.2f}")
    m2.metric("Expense", f"{summary['expense']:.2f}")
    m3.metric("Net", f"{summary['net']:.2f}")
    m4.metric("Next-month forecast", "n/a" if forecast is None else f"{forecast:.2f}")
    left, right = st.columns(2)
    left.subheader("Spending by category")
    if breakdown:
        left.bar_chart(pd.Series(breakdown))
    else:
        left.info("No expenses this month.")
    right.subheader("Monthly expense trend")
    right.line_chart(pd.DataFrame(series, columns=["month", "expense"]).set_index("month"))
    st.subheader("Budget status")
    for stt in statuses:
        label = f"{stt['category']}: {stt['spent']:.2f} / {stt['available']:.2f} " \
                f"({stt['percent_used']}%) - {stt['status'].upper()}"
        st.progress(min(stt["percent_used"] / 100, 1.0), text=label)
    if not statuses:
        st.info("No budgets set yet.")

elif page == "Add transaction":
    with st.form("add_tx", clear_on_submit=True):
        amount = st.number_input("Amount", min_value=0.0, step=10.0)
        kind = st.selectbox("Type", ["expense", "income"])
        category = st.text_input("Category")
        tx_date = st.date_input("Date", today)
        note = st.text_input("Note")
        submitted = st.form_submit_button("Add")
    if submitted:
        try:
            with session_scope() as s:
                t = transactions.add_transaction(s, amount, kind, category, tx_date, note)
                st.success(f"Added #{t.id}: {t.type} {t.amount:.2f} [{t.category.name}]")
                if t.type == "expense":
                    try:
                        stt = budgets.budget_status(s, t.category.name, t.date.year, t.date.month)
                        if stt["status"] != "ok":
                            st.warning(f"Budget {stt['status']}: {stt['percent_used']}% used")
                    except LedgerlyError:
                        pass
        except LedgerlyError as exc:
            show_error(exc)

elif page == "Transactions":
    with session_scope() as s:
        rows = transactions.list_transactions(s, limit=200)
        df = pd.DataFrame([{"ID": t.id, "Date": t.date, "Type": t.type,
                            "Category": t.category.name, "Amount": t.amount,
                            "Note": t.note} for t in rows])
    if df.empty:
        st.info("No transactions yet.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        del_id = st.number_input("Delete transaction ID", min_value=1, step=1)
        if st.button("Delete"):
            try:
                with session_scope() as s:
                    transactions.delete_transaction(s, int(del_id))
                st.success(f"Deleted #{int(del_id)}")
            except LedgerlyError as exc:
                show_error(exc)

elif page == "Budgets":
    with st.form("set_budget"):
        category = st.text_input("Category")
        limit = st.number_input("Monthly limit", min_value=0.0, step=100.0)
        rollover = st.checkbox("Roll over unused budget")
        if st.form_submit_button("Save budget"):
            try:
                with session_scope() as s:
                    budgets.set_budget(s, category, limit, rollover)
                st.success("Budget saved")
            except LedgerlyError as exc:
                show_error(exc)
    year, month = month_picker()
    with session_scope() as s:
        statuses = budgets.all_budget_statuses(s, year, month)
    if statuses:
        st.dataframe(pd.DataFrame(statuses), use_container_width=True, hide_index=True)

elif page == "Recurring":
    with st.form("add_rule"):
        amount = st.number_input("Amount", min_value=0.0, step=10.0)
        kind = st.selectbox("Type", ["expense", "income"])
        category = st.text_input("Category")
        freq = st.selectbox("Frequency", ["monthly", "weekly"])
        start = st.date_input("Start date", today)
        if st.form_submit_button("Add rule"):
            try:
                with session_scope() as s:
                    recurring.add_rule(s, amount, kind, category, freq, start)
                st.success("Rule added")
            except LedgerlyError as exc:
                show_error(exc)
    if st.button("Generate due transactions"):
        with session_scope() as s:
            st.success(f"Generated {len(recurring.generate_due(s))} transaction(s)")
    with session_scope() as s:
        rules = [{"ID": r.id, "Frequency": r.frequency, "Type": r.type,
                  "Category": r.category.name, "Amount": r.amount, "Start": r.start_date}
                 for r in recurring.list_rules(s)]
    if rules:
        st.dataframe(pd.DataFrame(rules), use_container_width=True, hide_index=True)
