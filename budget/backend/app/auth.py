import hmac
import os

from fastapi import Cookie, HTTPException, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

BUDGET_PIN = os.environ.get("BUDGET_PIN", "1234")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-change-me")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
COOKIE_NAME = "budget_session"

_signer = URLSafeTimedSerializer(SECRET_KEY, salt="budget-session")


def verify_pin(pin: str) -> bool:
    return hmac.compare_digest(pin, BUDGET_PIN)


def issue_session_cookie(response: Response) -> None:
    token = _signer.dumps({"ok": True})
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME)


def require_session(budget_session: str | None = Cookie(default=None)) -> None:
    if not budget_session:
        raise HTTPException(401, "로그인이 필요합니다.")
    try:
        _signer.loads(budget_session, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "세션이 만료되었습니다. 다시 로그인해주세요.")


def is_session_valid(budget_session: str | None) -> bool:
    if not budget_session:
        return False
    try:
        _signer.loads(budget_session, max_age=SESSION_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False
