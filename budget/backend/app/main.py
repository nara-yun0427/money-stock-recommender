from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import crud, dashboard, schemas
from .auth import (
    clear_session_cookie,
    is_session_valid,
    issue_session_cookie,
    require_session,
    verify_pin,
)
from .database import Base, SessionLocal, engine, get_db
from .seed import ensure_default_categories

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_categories(db)
    finally:
        db.close()
    yield


app = FastAPI(title="가계부 API", lifespan=lifespan)


@app.post("/api/auth/login")
def login(payload: schemas.PinLogin, response: Response):
    if not verify_pin(payload.pin):
        raise HTTPException(401, "PIN이 올바르지 않습니다.")
    issue_session_cookie(response)
    return {"ok": True}


@app.post("/api/auth/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@app.get("/api/auth/check")
def check_auth(budget_session: str | None = Cookie(default=None)):
    return {"authenticated": is_session_valid(budget_session)}


@app.get("/api/categories", response_model=list[schemas.CategoryOut], dependencies=[Depends(require_session)])
def get_categories(db: Session = Depends(get_db)):
    return crud.list_categories(db)


@app.get("/api/transactions", response_model=list[schemas.TransactionOut], dependencies=[Depends(require_session)])
def get_transactions(
    start: date | None = None,
    end: date | None = None,
    category_id: int | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    return crud.list_transactions(db, start=start, end=end, category_id=category_id, limit=limit)


@app.post("/api/transactions", response_model=schemas.TransactionOut, dependencies=[Depends(require_session)])
def create_transaction(payload: schemas.TransactionCreate, db: Session = Depends(get_db)):
    if not db.get(crud.models.Category, payload.category_id):
        raise HTTPException(400, "존재하지 않는 카테고리입니다.")
    return crud.create_transaction(db, payload)


@app.put("/api/transactions/{transaction_id}", response_model=schemas.TransactionOut, dependencies=[Depends(require_session)])
def update_transaction(transaction_id: int, payload: schemas.TransactionUpdate, db: Session = Depends(get_db)):
    tx = crud.get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(404, "거래를 찾을 수 없습니다.")
    return crud.update_transaction(db, tx, payload)


@app.delete("/api/transactions/{transaction_id}", dependencies=[Depends(require_session)])
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    tx = crud.get_transaction(db, transaction_id)
    if not tx:
        raise HTTPException(404, "거래를 찾을 수 없습니다.")
    crud.delete_transaction(db, tx)
    return {"ok": True}


@app.get("/api/transactions/default-payment-method", dependencies=[Depends(require_session)])
def default_payment_method(category_id: int, db: Session = Depends(get_db)):
    pm = crud.last_payment_method_for_category(db, category_id)
    return {"payment_method": pm.value if pm else None}


@app.get("/api/dashboard/summary", dependencies=[Depends(require_session)])
def dashboard_summary(
    period: str = Query("month", pattern="^(week|month|year)$"),
    ref_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
):
    return dashboard.get_summary(db, period, ref_date)


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
