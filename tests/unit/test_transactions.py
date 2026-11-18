from datetime import date

import pytest

from ledgerly import transactions as tx
from ledgerly.errors import NotFoundError, ValidationError


class TestValidation:
    @pytest.mark.parametrize("raw,expected", [(100, 100.0), ("49.999", 50.0), (0.005, 0.01)])
    def test_amount_valid_and_rounded(self, raw, expected):
        assert tx.validate_amount(raw) == expected

    @pytest.mark.parametrize("bad", [0, -5, "abc", None, float("nan"), float("inf")])
    def test_amount_invalid(self, bad):
        with pytest.raises(ValidationError):
            tx.validate_amount(bad)

    def test_type_normalised(self):
        assert tx.validate_type(" Income ") == "income"

    def test_type_invalid(self):
        with pytest.raises(ValidationError):
            tx.validate_type("loan")

    @pytest.mark.parametrize("text", ["2026-02-28", "28-02-2026", "28/02/2026"])
    def test_parse_date_formats(self, text):
        assert tx.parse_date(text) == date(2026, 2, 28)

    @pytest.mark.parametrize("bad", ["2026-02-30", "yesterday", "", "31/31/2026"])
    def test_parse_date_invalid(self, bad):
        with pytest.raises(ValidationError):
            tx.parse_date(bad)

    def test_category_empty_rejected(self):
        with pytest.raises(ValidationError):
            tx.normalize_category("   ")


class TestCrud:
    def test_add_and_get(self, session):
        t = tx.add_transaction(session, 250, "expense", "Food", "2026-11-01", "lunch")
        assert t.id is not None
        assert tx.get_transaction(session, t.id).category.name == "food"

    def test_category_reused_case_insensitive(self, session):
        a = tx.add_transaction(session, 1, "expense", "Food", "2026-11-01")
        b = tx.add_transaction(session, 1, "expense", "FOOD", "2026-11-02")
        assert a.category_id == b.category_id

    def test_default_date_is_today(self, session):
        assert tx.add_transaction(session, 1, "expense", "x").date == date.today()

    def test_list_newest_first(self, session):
        tx.add_transaction(session, 1, "expense", "a", "2026-11-01")
        tx.add_transaction(session, 1, "expense", "a", "2026-11-05")
        dates = [t.date for t in tx.list_transactions(session)]
        assert dates == sorted(dates, reverse=True)

    def test_list_filters(self, session):
        tx.add_transaction(session, 10, "expense", "food", "2026-11-01")
        tx.add_transaction(session, 20, "income", "salary", "2026-11-02")
        tx.add_transaction(session, 30, "expense", "rent", "2026-12-01")
        assert len(tx.list_transactions(session, category="food")) == 1
        assert len(tx.list_transactions(session, tx_type="income")) == 1
        assert len(tx.list_transactions(session, start="2026-11-15")) == 1
        assert len(tx.list_transactions(session, end="2026-11-30")) == 2
        assert len(tx.list_transactions(session, limit=1)) == 1

    def test_update(self, session):
        t = tx.add_transaction(session, 10, "expense", "food", "2026-11-01")
        tx.update_transaction(session, t.id, amount=99, category="snacks", note="n")
        t = tx.get_transaction(session, t.id)
        assert (t.amount, t.category.name, t.note) == (99.0, "snacks", "n")

    def test_update_rejects_bad_amount(self, session):
        t = tx.add_transaction(session, 10, "expense", "food", "2026-11-01")
        with pytest.raises(ValidationError):
            tx.update_transaction(session, t.id, amount=-1)

    def test_delete(self, session):
        t = tx.add_transaction(session, 10, "expense", "food", "2026-11-01")
        tx.delete_transaction(session, t.id)
        with pytest.raises(NotFoundError):
            tx.get_transaction(session, t.id)

    def test_delete_missing(self, session):
        with pytest.raises(NotFoundError):
            tx.delete_transaction(session, 999)

    def test_note_truncated(self, session):
        t = tx.add_transaction(session, 1, "expense", "x", "2026-11-01", "a" * 500)
        assert len(t.note) == 200
