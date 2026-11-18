import csv

import pytest

from ledgerly import io_handler as io
from ledgerly import transactions as tx
from ledgerly.errors import ValidationError


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_import_valid(session, tmp_path):
    p = write(tmp_path / "a.csv",
              "date,amount,type,category,note\n2026-11-01,100,expense,food,lunch\n"
              "2026-11-02,5000,income,salary,\n")
    res = io.import_csv(session, p)
    assert res.imported == 2 and res.errors == []
    assert len(tx.list_transactions(session)) == 2


def test_import_reports_bad_rows_but_keeps_good_ones(session, tmp_path):
    p = write(tmp_path / "a.csv",
              "date,amount,type,category\n"
              "2026-11-01,100,expense,food\n"
              "not-a-date,100,expense,food\n"
              "2026-11-03,-5,expense,food\n"
              "2026-11-04,abc,expense,food\n"
              "2026-11-05,10,gift,food\n"
              "2026-11-06,10,expense,\n")
    res = io.import_csv(session, p)
    assert res.imported == 1
    assert [line for line, _ in res.errors] == [3, 4, 5, 6, 7]


def test_import_missing_columns(session, tmp_path):
    p = write(tmp_path / "a.csv", "date,amount\n2026-11-01,5\n")
    with pytest.raises(ValidationError, match="type"):
        io.import_csv(session, p)


def test_import_header_case_and_bom(session, tmp_path):
    p = tmp_path / "a.csv"
    p.write_bytes("\ufeffDate,Amount,Type,Category\n2026-11-01,5,expense,food\n".encode())
    assert io.import_csv(session, str(p)).imported == 1


def test_import_empty_file(session, tmp_path):
    p = write(tmp_path / "a.csv", "")
    with pytest.raises(ValidationError):
        io.import_csv(session, p)


def test_export_roundtrip(session, tmp_path):
    tx.add_transaction(session, 12.5, "expense", "food", "2026-11-02", "tea")
    tx.add_transaction(session, 100, "income", "salary", "2026-11-01")
    out = tmp_path / "out.csv"
    assert io.export_csv(session, str(out)) == 2
    rows = list(csv.DictReader(out.open()))
    assert [r["date"] for r in rows] == ["2026-11-01", "2026-11-02"]
    assert rows[1]["amount"] == "12.50"


def test_export_date_filter(session, tmp_path):
    tx.add_transaction(session, 1, "expense", "a", "2026-10-01")
    tx.add_transaction(session, 1, "expense", "a", "2026-11-01")
    assert io.export_csv(session, str(tmp_path / "o.csv"), start="2026-11-01") == 1
