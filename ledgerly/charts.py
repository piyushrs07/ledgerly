"""Chart generation (matplotlib, saved as PNG files)."""
import matplotlib

matplotlib.use("Agg")  # headless backend: no display needed
import matplotlib.pyplot as plt  # noqa: E402

from .errors import ValidationError  # noqa: E402


def category_pie(breakdown, path, title="Spending by category"):
    if not breakdown:
        raise ValidationError("No expense data to chart")
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(list(breakdown.values()), labels=list(breakdown.keys()), autopct="%1.1f%%")
    ax.set_title(title)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return path


def trend_line(series, path, forecast=None, title="Monthly expenses"):
    if not series:
        raise ValidationError("No data to chart")
    labels = [l for l, _ in series]
    values = [v for _, v in series]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(labels, values, marker="o", label="Actual")
    if forecast is not None:
        ax.plot([labels[-1], "next"], [values[-1], forecast], "--", marker="o",
                label="Forecast")
    ax.set_title(title)
    ax.set_ylabel("Amount")
    ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=30)
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return path
