"""Smoke tests: every dashboard page must render without raising an exception.

Skipped automatically when the optional `streamlit` package is not installed.
"""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

UI_FILE = str(Path(__file__).resolve().parents[2] / "ledgerly" / "ui.py")
PAGES = ["Dashboard", "Add transaction", "Transactions", "Budgets", "Recurring"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page, tmp_path, monkeypatch):
    monkeypatch.setenv("LEDGERLY_DB", str(tmp_path / "ui.db"))
    at = AppTest.from_file(UI_FILE, default_timeout=30).run()
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception
