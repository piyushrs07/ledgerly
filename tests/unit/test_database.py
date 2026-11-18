import pytest

from ledgerly import database as db
from ledgerly import transactions as tx
from ledgerly.models import Transaction


def test_url_memory():
    assert db.get_db_url(":memory:") == "sqlite://"


def test_url_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("LEDGERLY_DB", str(tmp_path / "x.db"))
    assert db.get_db_url().endswith("x.db")


def test_url_creates_parent_dir(tmp_path):
    db.get_db_url(str(tmp_path / "sub" / "x.db"))
    assert (tmp_path / "sub").is_dir()


def test_session_scope_commits(tmp_path):
    path = str(tmp_path / "t.db")
    with db.session_scope(path) as s:
        tx.add_transaction(s, 5, "expense", "a", "2026-11-01")
    with db.session_scope(path) as s:
        assert s.query(Transaction).count() == 1


def test_session_scope_rolls_back_on_error(tmp_path):
    path = str(tmp_path / "t.db")
    with pytest.raises(RuntimeError):
        with db.session_scope(path) as s:
            tx.add_transaction(s, 5, "expense", "a", "2026-11-01")
            raise RuntimeError("boom")
    with db.session_scope(path) as s:
        assert s.query(Transaction).count() == 0
