"""Budget engine: monthly limits, spend tracking, rollover and alerts."""
from datetime import date

from sqlalchemy import func, select

from .errors import NotFoundError, ValidationError
from .models import EXPENSE, Budget, Category, Transaction
from .transactions import get_or_create_category, normalize_category, parse_date, validate_amount

WARNING_THRESHOLD = 80.0  # percent of available budget at which a warning is raised


def month_bounds(year, month):
    if not 1 <= month <= 12:
        raise ValidationError(f"Month must be 1-12, got {month}")
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end  # [start, end)


def prev_month(year, month):
    return (year - 1, 12) if month == 1 else (year, month - 1)


def set_budget(session, category, monthly_limit, rollover=False, start=None):
    """Create or update the monthly budget of a category."""
    limit = validate_amount(monthly_limit)
    cat = get_or_create_category(session, category)
    start_day = parse_date(start) if start else date.today()
    budget = session.scalar(select(Budget).where(Budget.category_id == cat.id))
    if budget is None:
        budget = Budget(category=cat, monthly_limit=limit, rollover=bool(rollover),
                        start_date=start_day.replace(day=1))
        session.add(budget)
    else:
        budget.monthly_limit = limit
        budget.rollover = bool(rollover)
    session.flush()
    return budget


def get_budget(session, category):
    name = normalize_category(category)
    budget = session.scalar(select(Budget).join(Category).where(Category.name == name))
    if budget is None:
        raise NotFoundError(f"No budget set for category {name!r}")
    return budget


def list_budgets(session):
    return list(session.scalars(select(Budget).join(Category).order_by(Category.name)))


def delete_budget(session, category):
    session.delete(get_budget(session, category))
    session.flush()


def month_spend(session, category_id, year, month):
    start, end = month_bounds(year, month)
    total = session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.category_id == category_id,
            Transaction.type == EXPENSE,
            Transaction.date >= start,
            Transaction.date < end,
        )
    )
    return round(total, 2)


def rollover_carry(session, budget, year, month):
    """Unused budget carried into (year, month); 0 if rollover is disabled.

    Carry chains month by month from the budget's start month, so an
    overspent month carries 0 (debt is not carried forward).
    """
    if not budget.rollover:
        return 0.0
    y, m = budget.start_date.year, budget.start_date.month
    carry = 0.0
    while (y, m) < (year, month):
        available = budget.monthly_limit + carry
        carry = max(0.0, available - month_spend(session, budget.category_id, y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return round(carry, 2)


def classify(percent_used):
    if percent_used > 100:
        return "exceeded"
    if percent_used >= WARNING_THRESHOLD:
        return "warning"
    return "ok"


def budget_status(session, category, year, month):
    budget = get_budget(session, category)
    spent = month_spend(session, budget.category_id, year, month)
    carry = rollover_carry(session, budget, year, month)
    available = round(budget.monthly_limit + carry, 2)
    percent = round(spent / available * 100, 1) if available else 0.0
    return {
        "category": budget.category.name,
        "limit": budget.monthly_limit,
        "carry_in": carry,
        "available": available,
        "spent": spent,
        "remaining": round(available - spent, 2),
        "percent_used": percent,
        "status": classify(percent),
    }


def all_budget_statuses(session, year, month):
    return [budget_status(session, b.category.name, year, month)
            for b in list_budgets(session)]


def get_alerts(session, year, month):
    """Statuses for budgets that are at warning level or exceeded."""
    return [s for s in all_budget_statuses(session, year, month) if s["status"] != "ok"]
