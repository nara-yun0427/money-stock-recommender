from sqlalchemy.orm import Session

from .models import Category

DEFAULT_CATEGORIES = [
    {"name": "고정지출", "icon": "\U0001F3E0", "color": "#64748b"},
    {"name": "쇼핑", "icon": "\U0001F6CD", "color": "#a855f7"},
    {"name": "장보기", "icon": "\U0001F6D2", "color": "#22c55e"},
    {"name": "외식", "icon": "\U0001F35C", "color": "#f97316"},
    {"name": "카페", "icon": "☕", "color": "#b45309"},
    {"name": "문화생활", "icon": "\U0001F3AC", "color": "#6366f1"},
    {"name": "기타", "icon": "\U0001F4CE", "color": "#94a3b8"},
]


def ensure_default_categories(db: Session) -> None:
    if db.query(Category).count() > 0:
        return
    for i, c in enumerate(DEFAULT_CATEGORIES):
        db.add(Category(name=c["name"], icon=c["icon"], color=c["color"], sort_order=i))
    db.commit()
