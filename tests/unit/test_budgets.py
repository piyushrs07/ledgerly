import pytest

from ledgerly import budgets as bd
from ledgerly import transactions as tx
from ledgerly.errors import NotFoundError, ValidationError


def spend(session, amount, cat="food", d="2026-11-05"):
    tx.add_transaction(session, amount, "expense", cat, d)


class TestHelpers:
    def test_month_bounds_december(self):
        s, e = bd.month_bounds(2026, 12)
        assert (s.isoformat(), e.isoformat()) == ("2026-12-01", "2027-01-01")

    def test_month_bounds_invalid(self):
        with pytest.raises(ValidationError):
            bd.month_bounds(2026, 13)

    def test_prev_month_wraps_year(self):
        assert bd.prev_month(2026, 1) == (2025, 12)
        assert bd.prev_month(2026, 5) == (2026, 4)

    @pytest.mark.parametrize("pct,expected", [(0, "ok"), (79.9, "ok"), (80, "warning"),
                                              (100, "warning"), (100.1, "exceeded")])
    def test_classify(self, pct, expected):
        assert bd.classify(pct) == expected


class TestBudgetCrud:
    def test_set_and_get(self, session):
        bd.set_budget(session, "Food", 5000, start="2026-11-10")
        b = bd.get_budget(session, "food")
        assert b.monthly_limit == 5000 and b.start_date.day == 1

    def test_set_updates_existing(self, session):
        bd.set_budget(session, "food", 5000)
        bd.set_budget(session, "food", 7000, rollover=True)
        assert len(bd.list_budgets(session)) == 1
        assert bd.get_budget(session, "food").monthly_limit == 7000

    def test_invalid_limit(self, session):
        with pytest.raises(ValidationError):
            bd.set_budget(session, "food", 0)

    def test_missing_budget(self, session):
        with pytest.raises(NotFoundError):
            bd.get_budget(session, "ghost")

    def test_delete(self, session):
        bd.set_budget(session, "food", 100)
        bd.delete_budget(session, "food")
        assert bd.list_budgets(session) == []


class TestStatus:
    def test_ok_warning_exceeded(self, session):
        bd.set_budget(session, "food", 1000, start="2026-11-01")
        spend(session, 500)
        assert bd.budget_status(session, "food", 2026, 11)["status"] == "ok"
        spend(session, 350)
        assert bd.budget_status(session, "food", 2026, 11)["status"] == "warning"
        spend(session, 200)
        st = bd.budget_status(session, "food", 2026, 11)
        assert st["status"] == "exceeded" and st["remaining"] == -50

    def test_only_expenses_in_month_and_category_counted(self, session):
        bd.set_budget(session, "food", 1000, start="2026-11-01")
        spend(session, 100)
        spend(session, 999, d="2026-10-31")          # previous month
        spend(session, 999, cat="rent")              # other category
        tx.add_transaction(session, 999, "income", "food", "2026-11-05")  # income
        assert bd.budget_status(session, "food", 2026, 11)["spent"] == 100

    def test_alerts_only_non_ok(self, session):
        bd.set_budget(session, "food", 1000, start="2026-11-01")
        bd.set_budget(session, "fun", 1000, start="2026-11-01")
        spend(session, 900, "food")
        spend(session, 100, "fun")
        alerts = bd.get_alerts(session, 2026, 11)
        assert [a["category"] for a in alerts] == ["food"]


class TestRollover:
    def test_no_rollover_by_default(self, session):
        bd.set_budget(session, "food", 1000, start="2026-09-01")
        spend(session, 200, d="2026-09-10")
        assert bd.budget_status(session, "food", 2026, 10)["carry_in"] == 0

    def test_unused_budget_chains_across_months(self, session):
        bd.set_budget(session, "food", 1000, rollover=True, start="2026-09-01")
        spend(session, 400, d="2026-09-10")   # carry 600 into Oct
        spend(session, 1000, d="2026-10-10")  # available 1600, carry 600 into Nov
        st = bd.budget_status(session, "food", 2026, 11)
        assert st["carry_in"] == 600 and st["available"] == 1600

    def test_overspend_does_not_carry_debt(self, session):
        bd.set_budget(session, "food", 1000, rollover=True, start="2026-09-01")
        spend(session, 1500, d="2026-09-10")
        assert bd.budget_status(session, "food", 2026, 10)["carry_in"] == 0

    def test_rollover_across_year_boundary(self, session):
        bd.set_budget(session, "food", 1000, rollover=True, start="2026-12-01")
        spend(session, 100, d="2026-12-05")
        assert bd.budget_status(session, "food", 2027, 1)["carry_in"] == 900
