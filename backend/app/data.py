"""국내 상장종목 시세 데이터 수집 및 캐싱.

FinanceDataReader로 KOSPI/KOSDAQ 종목 목록과 가격(OHLCV) 히스토리를 받아
로컬 parquet 캐시에 저장한다. 전체 종목(약 2,500개)의 가격 히스토리를 받는 데
시간이 걸리므로, 서버 시작 시 백그라운드 스레드에서 비동기로 구축하고
캐시가 준비되기 전까지는 /api/status 로 진행률을 확인할 수 있게 한다.
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import FinanceDataReader as fdr
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

LISTING_CACHE = CACHE_DIR / "listing.parquet"
PRICES_CACHE = CACHE_DIR / "prices.parquet"
STATUS_CACHE = CACHE_DIR / "status.json"

PRICE_HISTORY_DAYS = 1400  # 3년 이상 지표(750거래일) 계산에 필요한 여유 확보
LIQUIDITY_TOP_N = 300
FETCH_WORKERS = 24
CACHE_MAX_AGE_HOURS = 20

EXCLUDE_DEPTS = {
    "관리종목(소속부없음)",
    "SPAC(소속부없음)",
    "투자주의환기종목(소속부없음)",
    "외국기업(소속부없음)",
}

_status_lock = threading.Lock()
_build_lock = threading.Lock()


def _write_status(**kwargs) -> None:
    with _status_lock:
        status = {}
        if STATUS_CACHE.exists():
            try:
                status = json.loads(STATUS_CACHE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                status = {}
        status.update(kwargs)
        STATUS_CACHE.write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def get_status() -> dict:
    if STATUS_CACHE.exists():
        try:
            return json.loads(STATUS_CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"state": "empty"}
    return {"state": "empty"}


def fetch_filtered_listing() -> pd.DataFrame:
    df = fdr.StockListing("KRX")
    df = df[df["Market"].isin(["KOSPI", "KOSDAQ", "KOSDAQ GLOBAL"])]
    df = df[~df["Dept"].isin(EXCLUDE_DEPTS)]
    df = df[~df["Name"].str.contains("스팩", na=False)]
    df = df[~df["Name"].str.match(r".*\d?우[A-Z]?$", na=False)]  # 우선주 제외
    df = df[["Code", "Name", "Market"]].drop_duplicates(subset="Code")
    return df.reset_index(drop=True)


def _fetch_one(code: str, start: str):
    try:
        d = fdr.DataReader(code, start)
    except Exception:
        return None
    if d is None or d.empty:
        return None
    d = d.reset_index()
    if "Date" not in d.columns or "Close" not in d.columns:
        return None
    d = d[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    d["Code"] = code
    return d


def build_cache(limit_codes: int | None = None) -> None:
    if not _build_lock.acquire(blocking=False):
        return  # 이미 빌드 중
    try:
        _write_status(
            state="building",
            started_at=datetime.now().isoformat(),
            progress=0,
        )
        listing = fetch_filtered_listing()
        codes = listing["Code"].tolist()
        if limit_codes:
            codes = codes[:limit_codes]
        start_date = (datetime.now() - timedelta(days=PRICE_HISTORY_DAYS)).strftime(
            "%Y-%m-%d"
        )

        frames = []
        done = 0
        total = len(codes)
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
            futures = {ex.submit(_fetch_one, c, start_date): c for c in codes}
            for fut in as_completed(futures):
                res = fut.result()
                if res is not None and len(res) >= 40:
                    frames.append(res)
                done += 1
                if done % 50 == 0 or done == total:
                    _write_status(state="building", progress=round(done / total * 100, 1))

        if not frames:
            _write_status(state="error", error="가격 데이터를 하나도 가져오지 못했습니다.")
            return

        prices = pd.concat(frames, ignore_index=True)

        recent = prices.sort_values("Date").groupby("Code").tail(20)
        liquidity = (recent["Close"] * recent["Volume"]).groupby(recent["Code"]).mean()
        top_codes = liquidity.sort_values(ascending=False).head(LIQUIDITY_TOP_N).index

        final_listing = listing[listing["Code"].isin(top_codes)].copy()
        final_listing["avg_trading_value_20d"] = final_listing["Code"].map(liquidity)
        final_listing = final_listing.sort_values(
            "avg_trading_value_20d", ascending=False
        ).reset_index(drop=True)

        prices = prices[prices["Code"].isin(top_codes)].reset_index(drop=True)

        final_listing.to_parquet(LISTING_CACHE, index=False)
        prices.to_parquet(PRICES_CACHE, index=False)

        _write_status(
            state="ready",
            built_at=datetime.now().isoformat(),
            progress=100,
            universe_size=len(final_listing),
            error=None,
        )
    finally:
        _build_lock.release()


def ensure_cache_async(force: bool = False) -> None:
    status = get_status()
    is_stale = True
    if status.get("state") == "ready" and status.get("built_at"):
        built_at = datetime.fromisoformat(status["built_at"])
        is_stale = (datetime.now() - built_at) > timedelta(hours=CACHE_MAX_AGE_HOURS)

    if status.get("state") == "building":
        return
    if force or status.get("state") in (None, "empty", "error") or is_stale:
        threading.Thread(target=build_cache, daemon=True).start()


def load_universe() -> pd.DataFrame:
    if not LISTING_CACHE.exists():
        return pd.DataFrame(columns=["Code", "Name", "Market", "avg_trading_value_20d"])
    return pd.read_parquet(LISTING_CACHE)


def load_prices() -> pd.DataFrame:
    if not PRICES_CACHE.exists():
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume", "Code"])
    return pd.read_parquet(PRICES_CACHE)
