import pytest

from ledgerly import analytics as an
from ledgerly import transactions as tx
from ledgerly.errors import ValidationError


def add(session, amount, cat, d, kind="expense"):
    tx.add_transaction(session, amount, kind, cat, d)


@pytest.fixture
def data(session):
    add(session, 50000, "salary", "2026-11-01", "income")
    add(session, 3000, "food", "2026-11-03")
    add(session, 1000, "food", "2026-11-20")
    add(session, 10000, "rent", "2026-11-01")
    add(session, 2000, "food", "2026-10-10")
    add(session, 10000, "rent", "2026-10-01")
    add(session, 700, "fun", "2026-10-15")
    return session


def test_monthly_summary(data):
    assert an.monthly_summary(data, 2026, 11) == {"income": 50000, "expense": 14000,
                                                  "net": 36000}


def test_monthly_summary_empty_month(session):
    assert an.monthly_summary(session, 2026, 1) == {"income": 0.0, "expense": 0.0, "net": 0.0}


def test_category_breakdown_sorted(data):
    bd = an.category_breakdown(data, 2026, 11)
    assert list(bd.items()) == [("rent", 10000), ("food", 4000)]


def test_top_categories(data):
    assert an.top_categories(data, 2026, 11, n=1) == [("rent", 10000)]


def test_month_over_month(data):
    rows = {r["category"]: r for r in an.month_over_month(data, 2026, 11)}
    assert rows["food"]["change"] == 2000 and rows["food"]["percent"] == 100.0
    assert rows["rent"]["change"] == 0
    assert rows["fun"]["change"] == -700 and rows["fun"]["percent"] == -100.0


def test_month_over_month_new_category_has_no_percent(session):
    add(session, 500, "gym", "2026-11-05")
    rows = an.month_over_month(session, 2026, 11)
    assert rows[0]["percent"] is None


def test_month_over_month_january_uses_previous_december(session):
    add(session, 100, "food", "2025-12-10")
    add(session, 150, "food", "2026-01-10")
    assert an.month_over_month(session, 2026, 1)[0]["change"] == 50


def test_expense_series_order_and_length(data):
    s = an.expense_series(data, 2026, 11, months=3)
    assert [l for l, _ in s] == ["2026-09", "2026-10", "2026-11"]
    assert [v for _, v in s] == [0.0, 12700.0, 14000.0]


class TestForecast:
    def test_perfect_linear_trend(self):
        assert an.forecast_next([100, 200, 300]) == 400.0

    def test_flat(self):
        assert an.forecast_next([500, 500, 500]) == 500.0

    def test_never_negative(self):
        assert an.forecast_next([300, 100]) == 0.0

    def test_needs_two_points(self):
        with pytest.raises(ValidationError):
            an.forecast_next([100])

    def test_from_db_ignores_leading_empty_months(self, session):
        add(session, 100, "a", "2026-10-05")
        add(session, 200, "a", "2026-11-05")
        assert an.forecast_next_month(session, 2026, 11) == 300.0
