"""Transaction management: validation and CRUD (core logic layer)."""
from datetime import date, datetime

from sqlalchemy import select

from .errors import NotFoundError, ValidationError
from .models import TX_TYPES, Category, Transaction

DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")


def parse_date(value):
    """Accept a date object or a string in YYYY-MM-DD / DD-MM-YYYY / DD/MM/YYYY."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValidationError(f"Invalid date: {value!r} (use YYYY-MM-DD)")


def validate_amount(amount):
    """Return amount rounded to 2 decimals; must be a positive number."""
    try:
        value = float(amount)
    except (TypeError, ValueError):
        raise ValidationError(f"Amount must be a number, got {amount!r}")
    if value != value or value in (float("inf"), float("-inf")):
        raise ValidationError("Amount must be a finite number")
    if value <= 0:
        raise ValidationError("Amount must be greater than zero")
    return round(value, 2)


def validate_type(tx_type):
    tx_type = str(tx_type).strip().lower()
    if tx_type not in TX_TYPES:
        raise ValidationError(f"Type must be one of {TX_TYPES}, got {tx_type!r}")
    return tx_type


def normalize_category(name):
    name = str(name or "").strip().lower()
    if not name:
        raise ValidationError("Category name cannot be empty")
    if len(name) > 50:
        raise ValidationError("Category name too long (max 50 chars)")
    return name


def get_or_create_category(session, name):
    name = normalize_category(name)
    cat = session.scalar(select(Category).where(Category.name == name))
    if cat is None:
        cat = Category(name=name)
        session.add(cat)
        session.flush()
    return cat


def add_transaction(session, amount, tx_type, category, tx_date=None, note="",
                    recurring_rule_id=None):
    tx = Transaction(
        amount=validate_amount(amount),
        type=validate_type(tx_type),
        category=get_or_create_category(session, category),
        date=parse_date(tx_date) if tx_date else date.today(),
        note=(note or "")[:200],
        recurring_rule_id=recurring_rule_id,
    )
    session.add(tx)
    session.flush()
    return tx


def get_transaction(session, tx_id):
    tx = session.get(Transaction, tx_id)
    if tx is None:
        raise NotFoundError(f"Transaction {tx_id} not found")
    return tx


def list_transactions(session, category=None, tx_type=None, start=None, end=None,
                      limit=None):
    """List transactions newest-first with optional filters."""
    stmt = select(Transaction).order_by(Transaction.date.desc(), Transaction.id.desc())
    if category:
        stmt = stmt.join(Category).where(Category.name == normalize_category(category))
    if tx_type:
        stmt = stmt.where(Transaction.type == validate_type(tx_type))
    if start:
        stmt = stmt.where(Transaction.date >= parse_date(start))
    if end:
        stmt = stmt.where(Transaction.date <= parse_date(end))
    if limit:
        stmt = stmt.limit(limit)
    return list(session.scalars(stmt))


def update_transaction(session, tx_id, amount=None, tx_type=None, category=None,
                       tx_date=None, note=None):
    tx = get_transaction(session, tx_id)
    if amount is not None:
        tx.amount = validate_amount(amount)
    if tx_type is not None:
        tx.type = validate_type(tx_type)
    if category is not None:
        tx.category = get_or_create_category(session, category)
    if tx_date is not None:
        tx.date = parse_date(tx_date)
    if note is not None:
        tx.note = note[:200]
    session.flush()
    return tx


def delete_transaction(session, tx_id):
    session.delete(get_transaction(session, tx_id))
    session.flush()
