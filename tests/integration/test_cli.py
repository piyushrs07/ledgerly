"""End-to-end tests driving the real CLI against a temporary SQLite file."""
import pytest
from click.testing import CliRunner

from ledgerly.cli import main


@pytest.fixture
def run(tmp_path):
    db = str(tmp_path / "cli.db")
    runner = CliRunner()

    def _run(*args, ok=True):
        result = runner.invoke(main, ["--db", db, *args])
        if ok:
            assert result.exit_code == 0, result.output
        return result
    return _run


def test_add_and_list(run):
    run("add", "--amount", "250", "--category", "food", "--date", "2026-11-02",
        "--note", "lunch")
    out = run("list").output
    assert "food" in out and "250" in out and "lunch" in out


def test_list_empty(run):
    assert "No transactions" in run("list").output


def test_invalid_amount_gives_clean_error(run):
    r = run("add", "--amount", "-5", "--category", "food", ok=False)
    assert r.exit_code == 1 and "greater than zero" in r.output
    assert "Traceback" not in r.output


def test_invalid_date_gives_clean_error(run):
    r = run("add", "--amount", "5", "--category", "food", "--date", "2026-02-30", ok=False)
    assert r.exit_code == 1 and "Invalid date" in r.output


def test_budget_alert_shown_on_add(run):
    run("budget", "set", "--category", "food", "--limit", "1000")
    r = run("add", "--amount", "900", "--category", "food")
    assert "WARNING" in r.output


def test_budget_status_table(run):
    run("budget", "set", "--category", "food", "--limit", "1000")
    run("add", "--amount", "1200", "--category", "food")
    assert "EXCEEDED" in run("budget", "status").output


def test_edit_and_delete(run):
    run("add", "--amount", "10", "--category", "a", "--date", "2026-11-01")
    run("edit", "1", "--amount", "99")
    assert "99" in run("list").output
    run("delete", "1")
    assert "No transactions" in run("list").output
    assert run("delete", "1", ok=False).exit_code == 1


def test_recurring_flow(run):
    run("recurring", "add", "--amount", "10000", "--category", "rent",
        "--frequency", "monthly", "--start", "2026-01-31")
    assert "rent" in run("recurring", "list").output
    assert "Generated" in run("recurring", "run").output
    assert "Generated 0" in run("recurring", "run").output  # idempotent


def test_report_monthly_and_compare(run):
    run("add", "--amount", "100", "--category", "food", "--date", "2026-10-05")
    run("add", "--amount", "300", "--category", "food", "--date", "2026-11-05")
    assert "expense 300.00" in run("report", "monthly", "--month", "2026-11").output
    assert "+200.00" in run("report", "compare", "--month", "2026-11").output
    assert "Forecast" in run("report", "forecast", "--month", "2026-11").output


def test_bad_month_format(run):
    assert run("report", "monthly", "--month", "nov", ok=False).exit_code == 2


def test_import_export_roundtrip(run, tmp_path):
    src = tmp_path / "in.csv"
    src.write_text("date,amount,type,category\n2026-11-01,10,expense,food\nbad,1,expense,x\n")
    out = run("import", str(src)).output
    assert "Imported 1" in out and "1 error" in out and "line 3" in out
    dest = tmp_path / "out.csv"
    run("export", str(dest))
    assert "food" in dest.read_text()


def test_charts(run, tmp_path):
    run("add", "--amount", "100", "--category", "food", "--date", "2026-10-05")
    run("add", "--amount", "300", "--category", "food", "--date", "2026-11-05")
    pie, trend = tmp_path / "p.png", tmp_path / "t.png"
    run("chart", "pie", "--month", "2026-11", "--out", str(pie))
    run("chart", "trend", "--month", "2026-11", "--out", str(trend))
    assert pie.exists() and trend.exists()


def test_chart_with_no_data_errors(run, tmp_path):
    r = run("chart", "pie", "--month", "2026-11", "--out", str(tmp_path / "p.png"), ok=False)
    assert r.exit_code == 1 and "No expense data" in r.output
