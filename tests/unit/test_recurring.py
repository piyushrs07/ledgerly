from datetime import date

import pytest

from ledgerly import recurring as rc
from ledgerly import transactions as tx
from ledgerly.errors import NotFoundError, ValidationError


class TestClampDay:
    @pytest.mark.parametrize("y,m,d,expected", [
        (2026, 2, 31, date(2026, 2, 28)),
        (2028, 2, 31, date(2028, 2, 29)),   # leap year
        (2026, 4, 31, date(2026, 4, 30)),
        (2026, 1, 31, date(2026, 1, 31)),
        (2026, 6, 15, date(2026, 6, 15)),
    ])
    def test_clamp(self, y, m, d, expected):
        assert rc.clamp_day(y, m, d) == expected


class TestRuleValidation:
    def test_bad_frequency(self, session):
        with pytest.raises(ValidationError):
            rc.add_rule(session, 10, "expense", "x", "daily", "2026-01-01")

    def test_end_before_start(self, session):
        with pytest.raises(ValidationError):
            rc.add_rule(session, 10, "expense", "x", "monthly", "2026-05-01",
                        end_date="2026-04-01")

    def test_bad_day_of_month(self, session):
        with pytest.raises(ValidationError):
            rc.add_rule(session, 10, "expense", "x", "monthly", "2026-05-01", day_of_month=32)

    def test_day_defaults_to_start_day(self, session):
        r = rc.add_rule(session, 10, "expense", "x", "monthly", "2026-05-17")
        assert r.day_of_month == 17

    def test_delete_missing(self, session):
        with pytest.raises(NotFoundError):
            rc.delete_rule(session, 42)


class TestOccurrences:
    def test_monthly_month_end_clamping(self, session):
        r = rc.add_rule(session, 10, "expense", "x", "monthly", "2026-01-31")
        got = rc.occurrences(r, date(2026, 4, 30))
        assert got == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31),
                       date(2026, 4, 30)]

    def test_monthly_leap_year(self, session):
        r = rc.add_rule(session, 10, "expense", "x", "monthly", "2028-01-31")
        assert date(2028, 2, 29) in rc.occurrences(r, date(2028, 3, 1))

    def test_monthly_not_due_yet_this_month(self, session):
        r = rc.add_rule(session, 10, "expense", "x", "monthly", "2026-01-15")
        assert rc.occurrences(r, date(2026, 2, 10)) == [date(2026, 1, 15)]

    def test_monthly_crosses_year(self, session):
        r = rc.add_rule(session, 10, "expense", "x", "monthly", "2026-11-05")
        assert rc.occurrences(r, date(2027, 1, 10))[-1] == date(2027, 1, 5)

    def test_weekly(self, session):
        r = rc.add_rule(session, 10, "expense", "x", "weekly", "2026-11-01")
        assert rc.occurrences(r, date(2026, 11, 22)) == [
            date(2026, 11, 1), date(2026, 11, 8), date(2026, 11, 15), date(2026, 11, 22)]

    def test_end_date_respected(self, session):
        r = rc.add_rule(session, 10, "expense", "x", "monthly", "2026-01-01",
                        end_date="2026-03-15")
        assert len(rc.occurrences(r, date(2026, 12, 31))) == 3

    def test_start_in_future_yields_nothing(self, session):
        r = rc.add_rule(session, 10, "expense", "x", "monthly", "2027-01-01")
        assert rc.occurrences(r, date(2026, 11, 18)) == []


class TestGenerate:
    def test_generates_transactions(self, session):
        rc.add_rule(session, 10000, "expense", "rent", "monthly", "2026-09-01")
        created = rc.generate_due(session, date(2026, 11, 18))
        assert len(created) == 3
        assert all(t.recurring_rule_id for t in created)

    def test_idempotent(self, session):
        rc.add_rule(session, 10, "expense", "x", "monthly", "2026-09-01")
        rc.generate_due(session, date(2026, 11, 18))
        assert rc.generate_due(session, date(2026, 11, 18)) == []
        assert len(tx.list_transactions(session)) == 3

    def test_incremental_next_month(self, session):
        rc.add_rule(session, 10, "expense", "x", "monthly", "2026-09-01")
        rc.generate_due(session, date(2026, 11, 18))
        assert len(rc.generate_due(session, date(2026, 12, 2))) == 1

    def test_income_rule(self, session):
        rc.add_rule(session, 50000, "income", "salary", "monthly", "2026-11-01")
        t = rc.generate_due(session, date(2026, 11, 30))[0]
        assert t.type == "income" and t.amount == 50000
