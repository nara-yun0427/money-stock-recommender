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
LIQUIDITY_SCAN_DAYS = 35  # 1차 유동성 스캔은 짧은 기간만 받아 메모리를 아낀다
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


def _fetch_recent_liquidity(code: str, start: str) -> float | None:
    """가벼운 1차 스캔: 최근 20거래일 평균 거래대금만 계산하고 나머지는 버린다."""
    try:
        d = fdr.DataReader(code, start)
    except Exception:
        return None
    if d is None or d.empty or "Close" not in d.columns:
        return None
    tail = d.tail(20)
    if tail.empty:
        return None
    value = float((tail["Close"] * tail["Volume"]).mean())
    if not value or value <= 0:
        return None
    return value


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

        # 1단계: 전 종목을 짧은 기간(35일)만 훑어서 유동성 상위 종목만 추린다.
        # 2,500개 전 종목을 3년치씩 한꺼번에 메모리에 올리면(무료 서버 512MB 기준)
        # 메모리 초과로 죽을 수 있어서, 무거운 전체 히스토리는 상위 종목만 받는다.
        scan_start = (datetime.now() - timedelta(days=LIQUIDITY_SCAN_DAYS)).strftime("%Y-%m-%d")
        liquidity: dict[str, float] = {}
        done = 0
        total = len(codes)
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
            futures = {ex.submit(_fetch_recent_liquidity, c, scan_start): c for c in codes}
            for fut in as_completed(futures):
                code = futures[fut]
                value = fut.result()
                if value is not None:
                    liquidity[code] = value
                done += 1
                if done % 100 == 0 or done == total:
                    _write_status(state="building", progress=round(done / total * 30, 1))

        if not liquidity:
            _write_status(state="error", error="유동성 데이터를 하나도 가져오지 못했습니다.")
            return

        top_codes = sorted(liquidity, key=liquidity.get, reverse=True)[:LIQUIDITY_TOP_N]

        # 2단계: 유동성 상위 종목만 3년치 전체 히스토리를 받는다.
        start_date = (datetime.now() - timedelta(days=PRICE_HISTORY_DAYS)).strftime("%Y-%m-%d")
        frames = []
        done = 0
        total2 = len(top_codes)
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
            futures = {ex.submit(_fetch_one, c, start_date): c for c in top_codes}
            for fut in as_completed(futures):
                res = fut.result()
                if res is not None and len(res) >= 40:
                    frames.append(res)
                done += 1
                if done % 20 == 0 or done == total2:
                    _write_status(state="building", progress=round(30 + done / total2 * 70, 1))

        if not frames:
            _write_status(state="error", error="가격 데이터를 하나도 가져오지 못했습니다.")
            return

        prices = pd.concat(frames, ignore_index=True)
        fetched_codes = set(prices["Code"].unique())

        final_listing = listing[listing["Code"].isin(fetched_codes)].copy()
        final_listing["avg_trading_value_20d"] = final_listing["Code"].map(liquidity)
        final_listing = final_listing.sort_values(
            "avg_trading_value_20d", ascending=False
        ).reset_index(drop=True)

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


REFRESH_RECENT_DAYS = 10  # 새로고침은 이 기간만 다시 받아서 기존 캐시에 이어붙인다


def refresh_recent_prices() -> None:
    """'새로고침' 버튼용: 이미 확보한 유니버스의 최근 시세만 빠르게 갱신한다.

    build_cache()처럼 전체 종목을 다시 스캔하지 않고, 이미 캐시에 있는 약 300개
    종목에 대해서만 최근 며칠치 시세를 받아 기존 데이터에 이어붙인다. 전체 재구축
    대비 요청 수가 훨씬 적어서(2,500+300 -> 300) 몇 분이 아니라 수십 초 안에 끝난다.
    """
    if not _build_lock.acquire(blocking=False):
        return  # 이미 다른 빌드/새로고침이 진행 중
    try:
        listing = load_universe()
        if listing.empty:
            # 캐시가 아예 없으면 새로고침으로는 부족하니 전체 재구축으로 넘어간다.
            _build_lock.release()
            build_cache()
            return

        _write_status(state="building", started_at=datetime.now().isoformat(), progress=0)

        codes = listing["Code"].tolist()
        start_date = (datetime.now() - timedelta(days=REFRESH_RECENT_DAYS)).strftime("%Y-%m-%d")

        frames = []
        done = 0
        total = len(codes)
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as ex:
            futures = {ex.submit(_fetch_one, c, start_date): c for c in codes}
            for fut in as_completed(futures):
                res = fut.result()
                if res is not None:
                    frames.append(res)
                done += 1
                if done % 20 == 0 or done == total:
                    _write_status(state="building", progress=round(done / total * 100, 1))

        if not frames:
            # 새 데이터를 못 받았으면 기존 캐시를 그대로 유지한다.
            _write_status(state="ready", error=None)
            return

        new_prices = pd.concat(frames, ignore_index=True)
        old_prices = load_prices()
        combined = pd.concat([old_prices, new_prices], ignore_index=True)
        combined = combined.drop_duplicates(subset=["Code", "Date"], keep="last")

        cutoff = pd.Timestamp(datetime.now() - timedelta(days=PRICE_HISTORY_DAYS))
        combined = combined[combined["Date"] >= cutoff].sort_values(["Code", "Date"])
        combined = combined.reset_index(drop=True)

        combined.to_parquet(PRICES_CACHE, index=False)

        _write_status(
            state="ready",
            built_at=datetime.now().isoformat(),
            progress=100,
            universe_size=len(listing),
            error=None,
        )
    finally:
        try:
            _build_lock.release()
        except RuntimeError:
            pass  # 위에서 이미 넘겨준 경우(전체 재구축 폴백)


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


def refresh_now() -> None:
    """'새로고침' 버튼이 호출하는 진입점. 캐시가 있으면 가볍게, 없으면 전체 재구축."""
    status = get_status()
    if status.get("state") == "building":
        return
    if LISTING_CACHE.exists():
        threading.Thread(target=refresh_recent_prices, daemon=True).start()
    else:
        threading.Thread(target=build_cache, daemon=True).start()


def load_universe() -> pd.DataFrame:
    if not LISTING_CACHE.exists():
        return pd.DataFrame(columns=["Code", "Name", "Market", "avg_trading_value_20d"])
    return pd.read_parquet(LISTING_CACHE)


def load_prices() -> pd.DataFrame:
    if not PRICES_CACHE.exists():
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume", "Code"])
    return pd.read_parquet(PRICES_CACHE)
