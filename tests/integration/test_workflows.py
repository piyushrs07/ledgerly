"""Integration tests: several modules working together through the real stack."""
from datetime import date

from ledgerly import analytics, budgets, io_handler, recurring, transactions


def test_expense_triggers_budget_alert(session):
    budgets.set_budget(session, "food", 1000, start="2026-11-01")
    transactions.add_transaction(session, 850, "expense", "food", "2026-11-05")
    alerts = budgets.get_alerts(session, 2026, 11)
    assert alerts and alerts[0]["status"] == "warning"
    transactions.add_transaction(session, 200, "expense", "food", "2026-11-06")
    assert budgets.get_alerts(session, 2026, 11)[0]["status"] == "exceeded"


def test_recurring_feeds_budget_and_analytics(session):
    budgets.set_budget(session, "rent", 10000, start="2026-09-01")
    recurring.add_rule(session, 10000, "expense", "rent", "monthly", "2026-09-01")
    recurring.add_rule(session, 50000, "income", "salary", "monthly", "2026-09-01")
    recurring.generate_due(session, date(2026, 11, 18))
    assert budgets.budget_status(session, "rent", 2026, 11)["status"] == "warning"
    assert analytics.monthly_summary(session, 2026, 11)["net"] == 40000
    assert analytics.forecast_next_month(session, 2026, 11) == 10000


def test_csv_import_then_report_and_export(session, tmp_path):
    src = tmp_path / "bank.csv"
    src.write_text("date,amount,type,category,note\n"
                   "2026-10-02,1000,expense,food,\n"
                   "2026-11-02,1500,expense,food,\n"
                   "2026-11-03,500,expense,fun,\n"
                   "bad,1,expense,x,\n")
    res = io_handler.import_csv(session, str(src))
    assert res.imported == 3 and len(res.errors) == 1
    top = analytics.top_categories(session, 2026, 11, n=1)
    assert top == [("food", 1500)]
    out = tmp_path / "export.csv"
    assert io_handler.export_csv(session, str(out)) == 3


def test_edit_and_delete_update_reports(session):
    t = transactions.add_transaction(session, 100, "expense", "food", "2026-11-05")
    transactions.update_transaction(session, t.id, amount=300)
    assert analytics.monthly_summary(session, 2026, 11)["expense"] == 300
    transactions.delete_transaction(session, t.id)
    assert analytics.monthly_summary(session, 2026, 11)["expense"] == 0
