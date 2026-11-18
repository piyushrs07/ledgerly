"""Recurring transaction engine: rules and idempotent transaction generation."""
import calendar
from datetime import date, timedelta

from sqlalchemy import select

from .errors import NotFoundError, ValidationError
from .models import RecurringRule
from .transactions import (add_transaction, get_or_create_category, parse_date,
                           validate_amount, validate_type)

FREQUENCIES = ("monthly", "weekly")


def clamp_day(year, month, day):
    """Return the date for `day` in the month, clamped to the month's last day.

    e.g. day=31 in February -> 28 (or 29 in a leap year).
    """
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def add_rule(session, amount, tx_type, category, frequency, start_date,
             day_of_month=None, end_date=None, note=""):
    frequency = str(frequency).strip().lower()
    if frequency not in FREQUENCIES:
        raise ValidationError(f"Frequency must be one of {FREQUENCIES}")
    start = parse_date(start_date)
    end = parse_date(end_date) if end_date else None
    if end and end < start:
        raise ValidationError("End date cannot be before start date")
    if frequency == "monthly":
        day_of_month = day_of_month or start.day
        if not 1 <= int(day_of_month) <= 31:
            raise ValidationError("Day of month must be between 1 and 31")
        day_of_month = int(day_of_month)
    else:
        day_of_month = None
    rule = RecurringRule(
        amount=validate_amount(amount), type=validate_type(tx_type),
        category=get_or_create_category(session, category), note=note or "",
        frequency=frequency, day_of_month=day_of_month, start_date=start, end_date=end,
    )
    session.add(rule)
    session.flush()
    return rule


def list_rules(session):
    return list(session.scalars(select(RecurringRule).order_by(RecurringRule.id)))


def delete_rule(session, rule_id):
    rule = session.get(RecurringRule, rule_id)
    if rule is None:
        raise NotFoundError(f"Recurring rule {rule_id} not found")
    session.delete(rule)
    session.flush()


def occurrences(rule, up_to):
    """All due dates of a rule from its start date up to and including `up_to`."""
    last = min(up_to, rule.end_date) if rule.end_date else up_to
    dates = []
    if rule.frequency == "weekly":
        d = rule.start_date
        while d <= last:
            dates.append(d)
            d += timedelta(days=7)
    else:
        y, m = rule.start_date.year, rule.start_date.month
        while date(y, m, 1) <= last:
            d = clamp_day(y, m, rule.day_of_month)
            if rule.start_date <= d <= last:
                dates.append(d)
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return dates


def generate_due(session, today=None):
    """Create transactions for every occurrence not yet generated.

    Idempotent: running it twice on the same day creates nothing new.
    Returns the list of created Transaction objects.
    """
    today = today or date.today()
    created = []
    for rule in list_rules(session):
        for d in occurrences(rule, today):
            if rule.last_generated and d <= rule.last_generated:
                continue
            created.append(add_transaction(
                session, rule.amount, rule.type, rule.category.name, d,
                rule.note, recurring_rule_id=rule.id))
            rule.last_generated = d
    session.flush()
    return created
