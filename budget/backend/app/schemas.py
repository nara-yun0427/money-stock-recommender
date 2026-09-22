import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from .models import PaymentMethod


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    icon: str
    color: str
    sort_order: int


class TransactionBase(BaseModel):
    date: dt.date
    amount: int = Field(gt=0)
    category_id: int
    payment_method: PaymentMethod
    memo: str | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    date: dt.date | None = None
    amount: int | None = Field(default=None, gt=0)
    category_id: int | None = None
    payment_method: PaymentMethod | None = None
    memo: str | None = None


class TransactionOut(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: dt.datetime
    updated_at: dt.datetime
    category: CategoryOut


class PinLogin(BaseModel):
    pin: str
