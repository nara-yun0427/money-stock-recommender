from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from . import models, schemas


def list_categories(db: Session) -> list[models.Category]:
    return db.scalars(
        select(models.Category).order_by(models.Category.sort_order)
    ).all()


def list_transactions(
    db: Session,
    start: date | None = None,
    end: date | None = None,
    category_id: int | None = None,
    limit: int = 200,
) -> list[models.Transaction]:
    stmt = select(models.Transaction).options(joinedload(models.Transaction.category))
    if start is not None:
        stmt = stmt.where(models.Transaction.date >= start)
    if end is not None:
        stmt = stmt.where(models.Transaction.date <= end)
    if category_id is not None:
        stmt = stmt.where(models.Transaction.category_id == category_id)
    stmt = stmt.order_by(models.Transaction.date.desc(), models.Transaction.id.desc()).limit(limit)
    return db.scalars(stmt).all()


def get_transaction(db: Session, transaction_id: int) -> models.Transaction | None:
    return db.get(models.Transaction, transaction_id)


def create_transaction(db: Session, payload: schemas.TransactionCreate) -> models.Transaction:
    tx = models.Transaction(**payload.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def update_transaction(
    db: Session, tx: models.Transaction, payload: schemas.TransactionUpdate
) -> models.Transaction:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, tx: models.Transaction) -> None:
    db.delete(tx)
    db.commit()


def last_payment_method_for_category(
    db: Session, category_id: int
) -> models.PaymentMethod | None:
    stmt = (
        select(models.Transaction.payment_method)
        .where(models.Transaction.category_id == category_id)
        .order_by(models.Transaction.date.desc(), models.Transaction.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()
