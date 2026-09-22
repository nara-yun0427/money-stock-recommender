from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import crud, models

TARGET_PAYMENT_METHOD_PCT = {
    "credit_card": 65,
    "debit_card": 25,
    "cash": 10,
}

VALID_PERIODS = {"week", "month", "year"}


def period_range(period: str, ref: date) -> tuple[date, date]:
    if period == "week":
        start = ref - timedelta(days=ref.weekday())
        end = start + timedelta(days=6)
    elif period == "month":
        start = ref.replace(day=1)
        end = start + relativedelta(months=1) - timedelta(days=1)
    elif period == "year":
        start = ref.replace(month=1, day=1)
        end = ref.replace(month=12, day=31)
    else:
        raise ValueError(f"invalid period: {period}")
    return start, end


def _shift_prev(period: str, start: date, end: date) -> tuple[date, date]:
    if period == "week":
        return start - timedelta(days=7), end - timedelta(days=7)
    if period == "month":
        return start - relativedelta(months=1), start - timedelta(days=1)
    return start - relativedelta(years=1), end - relativedelta(years=1)


def _shift_last_year(start: date, end: date) -> tuple[date, date]:
    return start - relativedelta(years=1), end - relativedelta(years=1)


def _sum_amount(db: Session, start: date, end: date) -> int:
    stmt = select(func.coalesce(func.sum(models.Transaction.amount), 0)).where(
        models.Transaction.date.between(start, end)
    )
    return int(db.scalar(stmt) or 0)


def _category_amounts(db: Session, start: date, end: date) -> dict[int, int]:
    stmt = (
        select(models.Transaction.category_id, func.sum(models.Transaction.amount))
        .where(models.Transaction.date.between(start, end))
        .group_by(models.Transaction.category_id)
    )
    return {cat_id: int(amt) for cat_id, amt in db.execute(stmt).all()}


def _payment_method_amounts(db: Session, start: date, end: date) -> dict[str, int]:
    stmt = (
        select(models.Transaction.payment_method, func.sum(models.Transaction.amount))
        .where(models.Transaction.date.between(start, end))
        .group_by(models.Transaction.payment_method)
    )
    result = {}
    for pm, amt in db.execute(stmt).all():
        key = pm.value if hasattr(pm, "value") else pm
        result[key] = int(amt)
    return result


def _trend_daily(db: Session, start: date, end: date) -> list[dict]:
    stmt = (
        select(models.Transaction.date, func.sum(models.Transaction.amount))
        .where(models.Transaction.date.between(start, end))
        .group_by(models.Transaction.date)
    )
    amounts = {d: int(amt) for d, amt in db.execute(stmt).all()}
    days = []
    d = start
    while d <= end:
        days.append({"label": d.isoformat(), "amount": amounts.get(d, 0)})
        d += timedelta(days=1)
    return days


def _trend_monthly(db: Session, year: int) -> list[dict]:
    start, end = date(year, 1, 1), date(year, 12, 31)
    rows = db.execute(
        select(models.Transaction.date, models.Transaction.amount).where(
            models.Transaction.date.between(start, end)
        )
    ).all()
    buckets = {m: 0 for m in range(1, 13)}
    for d, amt in rows:
        buckets[d.month] += amt
    return [{"label": f"{m}월", "amount": buckets[m]} for m in range(1, 13)]


def _make_comparison(label: str, start: date, end: date, prev_total: int, current_total: int) -> dict:
    diff = current_total - prev_total
    diff_pct = round(diff / prev_total * 100, 1) if prev_total else None
    return {
        "label": label,
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "amount": prev_total,
        "diff_amount": diff,
        "diff_pct": diff_pct,
    }


def get_summary(db: Session, period: str, ref: date) -> dict:
    if period not in VALID_PERIODS:
        raise ValueError(f"invalid period: {period}")

    start, end = period_range(period, ref)
    total = _sum_amount(db, start, end)

    cat_amounts = _category_amounts(db, start, end)
    by_category = []
    for c in crud.list_categories(db):
        amt = cat_amounts.get(c.id, 0)
        if amt == 0:
            continue
        by_category.append(
            {
                "category_id": c.id,
                "name": c.name,
                "icon": c.icon,
                "color": c.color,
                "amount": amt,
                "pct": round(amt / total * 100, 1) if total else 0,
            }
        )
    by_category.sort(key=lambda x: -x["amount"])

    pm_amounts = _payment_method_amounts(db, start, end)
    by_payment_method = [
        {
            "method": pm.value,
            "amount": pm_amounts.get(pm.value, 0),
            "pct": round(pm_amounts.get(pm.value, 0) / total * 100, 1) if total else 0,
            "target_pct": TARGET_PAYMENT_METHOD_PCT[pm.value],
        }
        for pm in models.PaymentMethod
    ]

    prev_start, prev_end = _shift_prev(period, start, end)
    prev_total = _sum_amount(db, prev_start, prev_end)
    prev_label = "지난주" if period == "week" else "지난달" if period == "month" else "작년"
    comparison_prev = _make_comparison(prev_label, prev_start, prev_end, prev_total, total)

    comparison_last_year = None
    if period != "year":
        ly_start, ly_end = _shift_last_year(start, end)
        ly_total = _sum_amount(db, ly_start, ly_end)
        comparison_last_year = _make_comparison("작년 동기간", ly_start, ly_end, ly_total, total)

    if period in ("week", "month"):
        trend = _trend_daily(db, start, end)
    else:
        trend = _trend_monthly(db, ref.year)

    return {
        "period": period,
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "total": total,
        "by_category": by_category,
        "by_payment_method": by_payment_method,
        "comparison_prev": comparison_prev,
        "comparison_last_year": comparison_last_year,
        "trend": trend,
    }
