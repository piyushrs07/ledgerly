"""CSV import / export with row-level validation."""
import csv
from dataclasses import dataclass, field

from .errors import LedgerlyError, ValidationError
from .transactions import add_transaction, list_transactions

REQUIRED_COLUMNS = ("date", "amount", "type", "category")
EXPORT_COLUMNS = ("date", "amount", "type", "category", "note")


@dataclass
class ImportResult:
    imported: int = 0
    errors: list = field(default_factory=list)  # [(row_number, message)]


def import_csv(session, path):
    """Import transactions; bad rows are reported, valid rows are still saved."""
    result = ImportResult()
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing:
            raise ValidationError(f"CSV missing required columns: {', '.join(missing)}")
        for line_no, raw in enumerate(reader, start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            try:
                add_transaction(session, row["amount"], row["type"], row["category"],
                                row["date"], row.get("note", ""))
                result.imported += 1
            except LedgerlyError as exc:
                result.errors.append((line_no, str(exc)))
    return result


def export_csv(session, path, start=None, end=None):
    """Write transactions (oldest first) to CSV; returns number of rows."""
    txs = list(reversed(list_transactions(session, start=start, end=end)))
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(EXPORT_COLUMNS)
        for t in txs:
            writer.writerow([t.date.isoformat(), f"{t.amount:.2f}", t.type,
                             t.category.name, t.note])
    return len(txs)
