"""Analytics: summaries, category breakdowns, trends and a linear forecast."""
import numpy as np
from sqlalchemy import func, select

from .budgets import month_bounds, prev_month
from .errors import ValidationError
from .models import EXPENSE, INCOME, Category, Transaction


def monthly_summary(session, year, month):
    """Total income, expense and net for a month."""
    start, end = month_bounds(year, month)
    rows = session.execute(
        select(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0.0))
        .where(Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.type)
    ).all()
    totals = {t: round(v, 2) for t, v in rows}
    income, expense = totals.get(INCOME, 0.0), totals.get(EXPENSE, 0.0)
    return {"income": income, "expense": expense, "net": round(income - expense, 2)}


def category_breakdown(session, year, month, tx_type=EXPENSE):
    """{category: total} for the month, sorted by amount (largest first)."""
    start, end = month_bounds(year, month)
    rows = session.execute(
        select(Category.name, func.sum(Transaction.amount))
        .join(Transaction, Transaction.category_id == Category.id)
        .where(Transaction.type == tx_type, Transaction.date >= start,
               Transaction.date < end)
        .group_by(Category.name)
    ).all()
    data = {name: round(total, 2) for name, total in rows}
    return dict(sorted(data.items(), key=lambda kv: kv[1], reverse=True))


def top_categories(session, year, month, n=3):
    return list(category_breakdown(session, year, month).items())[:n]


def month_over_month(session, year, month):
    """Per-category expense change versus the previous month."""
    py, pm = prev_month(year, month)
    cur = category_breakdown(session, year, month)
    prev = category_breakdown(session, py, pm)
    result = []
    for cat in sorted(set(cur) | set(prev)):
        c, p = cur.get(cat, 0.0), prev.get(cat, 0.0)
        change = round(c - p, 2)
        pct = round(change / p * 100, 1) if p else None  # None = no previous spend
        result.append({"category": cat, "current": c, "previous": p,
                       "change": change, "percent": pct})
    result.sort(key=lambda r: abs(r["change"]), reverse=True)
    return result


def expense_series(session, year, month, months=6):
    """Total expense for the `months` months ending at (year, month), oldest first."""
    points = []
    y, m = year, month
    for _ in range(months):
        points.append((f"{y}-{m:02d}", monthly_summary(session, y, m)["expense"]))
        y, m = prev_month(y, m)
    return list(reversed(points))


def forecast_next(values):
    """Linear-trend (least squares) projection of the next value; never below 0."""
    if len(values) < 2:
        raise ValidationError("At least 2 months of data are needed for a forecast")
    x = np.arange(len(values))
    slope, intercept = np.polyfit(x, values, 1)
    return round(max(0.0, float(slope * len(values) + intercept)), 2)


def forecast_next_month(session, year, month, months=6):
    """Forecast next month's expense using months that actually have data."""
    values = [v for _, v in expense_series(session, year, month, months)]
    while values and values[0] == 0:  # drop leading empty months
        values.pop(0)
    return forecast_next(values)
