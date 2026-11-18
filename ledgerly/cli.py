"""Command-line interface (presentation layer). Contains no business logic."""
from datetime import date

import click
from tabulate import tabulate

from . import analytics, budgets, charts, io_handler, recurring, transactions
from .database import session_scope
from .errors import LedgerlyError

def _table(rows, headers):
    """Render a table keeping values exactly as formatted (e.g. 4000.00, +200.00)."""
    return tabulate(rows, headers=headers, disable_numparse=True)


STATUS_ICON = {"ok": "OK", "warning": "WARNING", "exceeded": "EXCEEDED"}


def _ym(month_str):
    """Parse 'YYYY-MM' (default: current month) into (year, month)."""
    if not month_str:
        today = date.today()
        return today.year, today.month
    try:
        y, m = month_str.split("-")
        return int(y), int(m)
    except ValueError:
        raise click.BadParameter("Use YYYY-MM, e.g. 2026-11")


class Ctx:
    def __init__(self, db):
        self.db = db


@click.group()
@click.option("--db", default=None, help="Path to SQLite file (or set LEDGERLY_DB).")
@click.pass_context
def main(ctx, db):
    """Ledgerly - a smart personal ledger for income, expenses and budgets."""
    ctx.obj = Ctx(db)


def run(fn):
    """Decorator: open a DB session, turn LedgerlyError into a clean CLI error."""
    @click.pass_obj
    def wrapper(obj, *args, **kwargs):
        try:
            with session_scope(obj.db) as session:
                return fn(session, *args, **kwargs)
        except LedgerlyError as exc:
            raise click.ClickException(str(exc))
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


# ---------------- transactions ----------------
@main.command()
@click.option("--amount", required=True, type=float)
@click.option("--type", "tx_type", default="expense", type=click.Choice(["income", "expense"]))
@click.option("--category", required=True)
@click.option("--date", "tx_date", default=None, help="YYYY-MM-DD (default today)")
@click.option("--note", default="")
@run
def add(session, amount, tx_type, category, tx_date, note):
    """Add an income or expense transaction."""
    tx = transactions.add_transaction(session, amount, tx_type, category, tx_date, note)
    click.echo(f"Added #{tx.id}: {tx.type} {tx.amount:.2f} [{tx.category.name}] on {tx.date}")
    today = tx.date
    if tx.type == "expense":
        try:
            st = budgets.budget_status(session, tx.category.name, today.year, today.month)
            if st["status"] != "ok":
                click.echo(f"  ! Budget {STATUS_ICON[st['status']]}: {st['percent_used']}% "
                           f"of {st['available']:.2f} used for '{st['category']}'")
        except LedgerlyError:
            pass  # no budget for this category


@main.command("list")
@click.option("--category", default=None)
@click.option("--type", "tx_type", default=None, type=click.Choice(["income", "expense"]))
@click.option("--from", "start", default=None)
@click.option("--to", "end", default=None)
@click.option("--limit", default=20, show_default=True)
@run
def list_cmd(session, category, tx_type, start, end, limit):
    """List transactions (newest first)."""
    rows = transactions.list_transactions(session, category, tx_type, start, end, limit)
    if not rows:
        click.echo("No transactions found.")
        return
    click.echo(_table([[t.id, t.date, t.type, t.category.name, f"{t.amount:.2f}", t.note]
                         for t in rows],
                        headers=["ID", "Date", "Type", "Category", "Amount", "Note"]))


@main.command()
@click.argument("tx_id", type=int)
@click.option("--amount", type=float, default=None)
@click.option("--type", "tx_type", default=None, type=click.Choice(["income", "expense"]))
@click.option("--category", default=None)
@click.option("--date", "tx_date", default=None)
@click.option("--note", default=None)
@run
def edit(session, tx_id, amount, tx_type, category, tx_date, note):
    """Edit an existing transaction."""
    tx = transactions.update_transaction(session, tx_id, amount, tx_type, category,
                                         tx_date, note)
    click.echo(f"Updated #{tx.id}")


@main.command()
@click.argument("tx_id", type=int)
@run
def delete(session, tx_id):
    """Delete a transaction."""
    transactions.delete_transaction(session, tx_id)
    click.echo(f"Deleted #{tx_id}")


# ---------------- budgets ----------------
@main.group()
def budget():
    """Manage monthly budgets."""


@budget.command("set")
@click.option("--category", required=True)
@click.option("--limit", required=True, type=float)
@click.option("--rollover/--no-rollover", default=False)
@run
def budget_set(session, category, limit, rollover):
    """Set (or update) a category's monthly budget."""
    b = budgets.set_budget(session, category, limit, rollover)
    click.echo(f"Budget for '{b.category.name}': {b.monthly_limit:.2f}/month "
               f"(rollover {'on' if b.rollover else 'off'})")


@budget.command("status")
@click.option("--month", default=None, help="YYYY-MM (default current)")
@run
def budget_status(session, month):
    """Show budget usage for a month."""
    y, m = _ym(month)
    rows = budgets.all_budget_statuses(session, y, m)
    if not rows:
        click.echo("No budgets set.")
        return
    click.echo(_table([[r["category"], f"{r['available']:.2f}", f"{r['spent']:.2f}",
                          f"{r['remaining']:.2f}", f"{r['percent_used']}%",
                          STATUS_ICON[r["status"]]] for r in rows],
                        headers=["Category", "Available", "Spent", "Remaining", "Used", "Status"]))


@budget.command("delete")
@click.option("--category", required=True)
@run
def budget_delete(session, category):
    """Remove a category budget."""
    budgets.delete_budget(session, category)
    click.echo(f"Budget for '{category}' removed")


# ---------------- recurring ----------------
@main.group("recurring")
def recurring_grp():
    """Manage recurring transactions."""


@recurring_grp.command("add")
@click.option("--amount", required=True, type=float)
@click.option("--type", "tx_type", default="expense", type=click.Choice(["income", "expense"]))
@click.option("--category", required=True)
@click.option("--frequency", required=True, type=click.Choice(["monthly", "weekly"]))
@click.option("--start", required=True, help="Start date YYYY-MM-DD")
@click.option("--day", "day_of_month", type=int, default=None)
@click.option("--end", default=None)
@click.option("--note", default="")
@run
def recurring_add(session, amount, tx_type, category, frequency, start, day_of_month,
                  end, note):
    """Add a recurring rule (e.g. rent on the 1st of every month)."""
    r = recurring.add_rule(session, amount, tx_type, category, frequency, start,
                           day_of_month, end, note)
    click.echo(f"Rule #{r.id}: {r.frequency} {r.type} {r.amount:.2f} [{r.category.name}]")


@recurring_grp.command("list")
@run
def recurring_list(session):
    """List recurring rules."""
    rules = recurring.list_rules(session)
    if not rules:
        click.echo("No recurring rules.")
        return
    click.echo(_table([[r.id, r.frequency, r.type, r.category.name, f"{r.amount:.2f}",
                          r.start_date, r.end_date or "-", r.last_generated or "-"]
                         for r in rules],
                        headers=["ID", "Freq", "Type", "Category", "Amount", "Start",
                                 "End", "Last run"]))


@recurring_grp.command("run")
@run
def recurring_run(session):
    """Generate all due recurring transactions up to today."""
    created = recurring.generate_due(session)
    click.echo(f"Generated {len(created)} transaction(s)")


@recurring_grp.command("delete")
@click.argument("rule_id", type=int)
@run
def recurring_delete(session, rule_id):
    """Delete a recurring rule."""
    recurring.delete_rule(session, rule_id)
    click.echo(f"Deleted rule #{rule_id}")


# ---------------- reports ----------------
@main.group()
def report():
    """Spending analytics."""


@report.command("monthly")
@click.option("--month", default=None)
@run
def report_monthly(session, month):
    """Monthly summary with category breakdown."""
    y, m = _ym(month)
    s = analytics.monthly_summary(session, y, m)
    click.echo(f"Report {y}-{m:02d}: income {s['income']:.2f} | expense "
               f"{s['expense']:.2f} | net {s['net']:.2f}")
    bd = analytics.category_breakdown(session, y, m)
    if bd:
        click.echo(_table([[c, f"{v:.2f}", f"{v / s['expense'] * 100:.1f}%"]
                             for c, v in bd.items()],
                            headers=["Category", "Spent", "Share"]))


@report.command("compare")
@click.option("--month", default=None)
@run
def report_compare(session, month):
    """Compare category spending with the previous month."""
    y, m = _ym(month)
    rows = analytics.month_over_month(session, y, m)
    if not rows:
        click.echo("No data to compare.")
        return
    click.echo(_table([[r["category"], f"{r['previous']:.2f}", f"{r['current']:.2f}",
                          f"{r['change']:+.2f}",
                          "n/a" if r["percent"] is None else f"{r['percent']:+.1f}%"]
                         for r in rows],
                        headers=["Category", "Previous", "Current", "Change", "%"]))


@report.command("forecast")
@click.option("--month", default=None)
@run
def report_forecast(session, month):
    """Forecast next month's total spending (linear trend)."""
    y, m = _ym(month)
    value = analytics.forecast_next_month(session, y, m)
    click.echo(f"Forecast for next month: {value:.2f}")


# ---------------- import / export / charts ----------------
@main.command("import")
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@run
def import_cmd(session, path):
    """Import transactions from a CSV file."""
    res = io_handler.import_csv(session, path)
    click.echo(f"Imported {res.imported} row(s), {len(res.errors)} error(s)")
    for line, msg in res.errors:
        click.echo(f"  line {line}: {msg}")


@main.command("export")
@click.argument("path", type=click.Path(dir_okay=False))
@click.option("--from", "start", default=None)
@click.option("--to", "end", default=None)
@run
def export_cmd(session, path, start, end):
    """Export transactions to a CSV file."""
    n = io_handler.export_csv(session, path, start, end)
    click.echo(f"Exported {n} transaction(s) to {path}")


@main.command()
@click.argument("kind", type=click.Choice(["pie", "trend"]))
@click.option("--month", default=None)
@click.option("--out", default=None, help="Output PNG path")
@run
def chart(session, kind, month, out):
    """Create a chart: 'pie' (category split) or 'trend' (monthly expenses)."""
    y, m = _ym(month)
    if kind == "pie":
        path = out or f"ledgerly_pie_{y}-{m:02d}.png"
        charts.category_pie(analytics.category_breakdown(session, y, m), path,
                            f"Spending {y}-{m:02d}")
    else:
        path = out or f"ledgerly_trend_{y}-{m:02d}.png"
        series = analytics.expense_series(session, y, m)
        try:
            fc = analytics.forecast_next_month(session, y, m)
        except LedgerlyError:
            fc = None
        charts.trend_line(series, path, fc)
    click.echo(f"Chart saved: {path}")


if __name__ == "__main__":
    main()
