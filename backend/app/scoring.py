"""키워드(투자 기간)별 종목 추천 스코어링.

재무제표(PER/PBR/배당 등)는 로그인 없이 안정적으로 받을 무료 소스가 없어서,
가격·거래량 히스토리만으로 계산되는 기술적/정량 지표(추세, 변동성, 낙폭,
거래량 변화)로 종목을 스크리닝한다. 개인 참고용 스크리너이며 투자 조언이 아니다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# 아무리 추세/패턴이 좋아도 실제로 사고팔기 어려우면 의미가 없으므로,
# 모든 키워드 공통으로 "최근에도 실제 거래가 살아있는 종목"만 추천 대상에 남긴다.
MIN_RECENT_TRADING_VALUE = 3_000_000_000  # 최근 5거래일 평균 거래대금 30억원 이상
MIN_VOL_RATIO = 0.3  # 최근 거래량이 60일 평균의 30% 밑으로 식은 종목은 제외

KEYWORD_CONFIG = {
    "단타": {
        "label": "단타",
        "min_days": 30,
        "factors": [("vol20", 1, 0.35), ("vol_ratio", 1, 0.35), ("ret5", 1, 0.30)],
        "desc": "최근 변동성과 거래량 급증, 단기 모멘텀이 큰 종목",
    },
    "3개월이상": {
        "label": "3개월 이상",
        "min_days": 70,
        "factors": [("trend_20_60", 1, 0.40), ("ret60", 1, 0.35), ("vol20", -1, 0.25)],
        "desc": "20일선이 60일선 위에서 상승 추세를 보이는 종목",
    },
    "6개월이상": {
        "label": "6개월 이상",
        "min_days": 130,
        "factors": [("trend_60_120", 1, 0.35), ("ret120", 1, 0.35), ("vol20", -1, 0.30)],
        "desc": "60일선이 120일선 위에서 중기 추세가 안정적인 종목",
    },
    "1년이상": {
        "label": "1년 이상",
        "min_days": 260,
        "factors": [("ret250", 1, 0.45), ("mdd250", 1, 0.30), ("vol20", -1, 0.25)],
        "desc": "최근 1년 수익률이 높고 낙폭이 상대적으로 작은 종목",
    },
    "3년이상": {
        "label": "3년 이상",
        "min_days": 700,
        "factors": [("ret750", 1, 0.40), ("mdd250", 1, 0.30), ("vol20", -1, 0.30)],
        "desc": "장기 수익률이 꾸준하고 변동성·낙폭이 작은 종목",
    },
    "스윙": {
        "label": "스윙",
        "min_days": 130,
        "factors": [
            ("swing_pullback", 1, 0.40),
            ("ret120", 1, 0.25),
            ("above_ma120", 1, 0.20),
            ("swing_amplitude", 1, 0.15),
        ],
        "desc": "상승 추세 속에서 스윙 저점(눌림목) 부근까지 조정을 받아, 다음 스윙 고점까지의 반등을 노려볼 만한 종목",
    },
}

FACTOR_LABELS = {
    "vol20": "변동성",
    "vol_ratio": "거래량 증가",
    "ret5": "5일 수익률",
    "trend_20_60": "20/60일선 추세",
    "ret60": "60일 수익률",
    "trend_60_120": "60/120일선 추세",
    "ret120": "120일 수익률",
    "ret250": "1년 수익률",
    "mdd250": "낙폭 방어",
    "ret750": "3년 수익률",
    "swing_pullback": "스윙 저점 근접",
    "above_ma120": "추세 유지(120일선 위)",
    "swing_amplitude": "스윙 변동폭",
    "avg_trading_value_5d": "최근 거래대금",
}


def _indicators(g: pd.DataFrame) -> dict | None:
    g = g.sort_values("Date")
    close = g["Close"].to_numpy(dtype=float)
    high = g["High"].to_numpy(dtype=float)
    low = g["Low"].to_numpy(dtype=float)
    volume = g["Volume"].to_numpy(dtype=float)
    n = len(close)
    if n < 30 or close[-1] <= 0:
        return None

    def ret(days: int):
        if n <= days:
            return np.nan
        prev = close[-1 - days]
        return close[-1] / prev - 1 if prev > 0 else np.nan

    def ma(days: int):
        if n < days:
            return np.nan
        return float(np.mean(close[-days:]))

    with np.errstate(divide="ignore", invalid="ignore"):
        log_ret = np.diff(np.log(np.clip(close, 1e-9, None)))
    vol20 = float(np.std(log_ret[-20:]) * np.sqrt(252)) if n > 21 else np.nan

    ma20, ma60, ma120 = ma(20), ma(60), ma(120)
    trend_20_60 = (ma20 / ma60 - 1) if ma20 and ma60 else np.nan
    trend_60_120 = (ma60 / ma120 - 1) if ma60 and ma120 else np.nan

    if n > 60 and np.mean(volume[-60:]) > 0:
        vol_ratio = float(np.mean(volume[-5:]) / np.mean(volume[-60:]))
    else:
        vol_ratio = np.nan

    avg_trading_value_5d = float(np.mean(close[-5:] * volume[-5:]))

    def mdd(days: int):
        window = close[-days:] if n >= days else close
        peak = np.maximum.accumulate(window)
        dd = (window - peak) / peak
        return float(dd.min())

    mdd250 = mdd(250)

    # 스윙(눌림목) 지표: 최근 20거래일의 고점/저점 대비 현재 위치
    if n >= 20:
        high20, low20 = float(np.max(high[-20:])), float(np.min(low[-20:]))
        if high20 > low20 and low20 > 0:
            pos_in_range20 = (close[-1] - low20) / (high20 - low20)
            swing_pullback = 1 - pos_in_range20  # 저점에 가까울수록 1에 가까움
            swing_amplitude = (high20 - low20) / low20
        else:
            swing_pullback = np.nan
            swing_amplitude = np.nan
    else:
        swing_pullback = np.nan
        swing_amplitude = np.nan

    above_ma120 = (close[-1] / ma120 - 1) if ma120 else np.nan

    return {
        "n_days": n,
        "close": float(close[-1]),
        "ret5": ret(5),
        "ret20": ret(20),
        "ret60": ret(60),
        "ret120": ret(120),
        "ret250": ret(250),
        "ret750": ret(750),
        "vol20": vol20,
        "trend_20_60": trend_20_60,
        "trend_60_120": trend_60_120,
        "vol_ratio": vol_ratio,
        "mdd250": mdd250,
        "swing_pullback": swing_pullback,
        "swing_amplitude": swing_amplitude,
        "above_ma120": above_ma120,
        "avg_trading_value_5d": avg_trading_value_5d,
    }


def _zscore(s: pd.Series) -> pd.Series:
    mean = s.mean(skipna=True)
    std = s.std(skipna=True)
    if not std or np.isnan(std):
        return pd.Series(0.0, index=s.index)
    return ((s - mean) / std).fillna(0.0)


def build_indicator_table(prices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code, g in prices.groupby("Code"):
        ind = _indicators(g)
        if ind is None:
            continue
        ind["Code"] = code
        rows.append(ind)
    return pd.DataFrame(rows)


def recommend(
    keyword: str, universe: pd.DataFrame, prices: pd.DataFrame, top_n: int = 8
) -> list[dict]:
    cfg = KEYWORD_CONFIG[keyword]
    ind = build_indicator_table(prices)
    if ind.empty:
        return []

    ind = ind[ind["n_days"] >= cfg["min_days"]]
    primary_metric = cfg["factors"][0][0]
    ind = ind[ind[primary_metric].notna()]
    if ind.empty:
        return []

    ind = ind.merge(universe[["Code", "Name", "Market"]], on="Code", how="inner")

    # 공통 유동성 필터: 최근 거래대금이 충분하고, 거래량이 최근에 심하게 식지 않은 종목만 남긴다.
    ind = ind[ind["avg_trading_value_5d"] >= MIN_RECENT_TRADING_VALUE]
    ind = ind[ind["vol_ratio"].fillna(1.0) >= MIN_VOL_RATIO]
    if ind.empty:
        return []

    score = pd.Series(0.0, index=ind.index)
    for metric, direction, weight in cfg["factors"]:
        score = score + direction * weight * _zscore(ind[metric])
    ind = ind.assign(score=score)

    ind = ind.sort_values("score", ascending=False).head(top_n)

    items = []
    for _, r in ind.iterrows():
        top_factor = max(cfg["factors"], key=lambda f: f[1] * (r[f[0]] if pd.notna(r[f[0]]) else 0))
        items.append(
            {
                "code": r["Code"],
                "name": r["Name"],
                "market": r["Market"],
                "close": round(r["close"]),
                "score": round(float(r["score"]), 2),
                "reason": f"{FACTOR_LABELS.get(top_factor[0], top_factor[0])} 우수",
                "metrics": {
                    "ret5": _pct(r.get("ret5")),
                    "ret20": _pct(r.get("ret20")),
                    "ret60": _pct(r.get("ret60")),
                    "ret120": _pct(r.get("ret120")),
                    "ret250": _pct(r.get("ret250")),
                    "vol20": _pct(r.get("vol20")),
                    "mdd250": _pct(r.get("mdd250")),
                    "vol_ratio": None
                    if pd.isna(r.get("vol_ratio"))
                    else round(float(r["vol_ratio"]), 2),
                    "swing_pullback": None
                    if pd.isna(r.get("swing_pullback"))
                    else round(float(r["swing_pullback"]) * 100, 1),
                    "swing_amplitude": _pct(r.get("swing_amplitude")),
                    "above_ma120": _pct(r.get("above_ma120")),
                    "avg_trading_value_5d": None
                    if pd.isna(r.get("avg_trading_value_5d"))
                    else round(float(r["avg_trading_value_5d"]) / 1e8, 1),
                },
            }
        )
    return items


def _pct(v) -> float | None:
    if v is None or pd.isna(v):
        return None
    return round(float(v) * 100, 2)
