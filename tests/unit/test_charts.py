import pytest

from ledgerly import charts
from ledgerly.errors import ValidationError


def test_pie_creates_file(tmp_path):
    out = charts.category_pie({"food": 10, "rent": 20}, str(tmp_path / "p.png"))
    assert (tmp_path / "p.png").stat().st_size > 0 and out.endswith("p.png")


def test_pie_empty_rejected(tmp_path):
    with pytest.raises(ValidationError):
        charts.category_pie({}, str(tmp_path / "p.png"))


def test_trend_with_and_without_forecast(tmp_path):
    s = [("2026-09", 1.0), ("2026-10", 2.0)]
    charts.trend_line(s, str(tmp_path / "a.png"), forecast=3.0)
    charts.trend_line(s, str(tmp_path / "b.png"))
    assert (tmp_path / "a.png").exists() and (tmp_path / "b.png").exists()


def test_trend_empty_rejected(tmp_path):
    with pytest.raises(ValidationError):
        charts.trend_line([], str(tmp_path / "t.png"))
