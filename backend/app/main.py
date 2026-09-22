from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import data, scoring

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    data.ensure_cache_async()
    yield


app = FastAPI(title="국내주식 추천 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
def status():
    return data.get_status()


@app.post("/api/refresh")
def refresh():
    data.refresh_now()
    return {"ok": True}


@app.get("/api/keywords")
def keywords():
    return [
        {"keyword": k, "label": v["label"], "desc": v["desc"]}
        for k, v in scoring.KEYWORD_CONFIG.items()
    ]


@app.get("/api/recommend")
def recommend(keyword: str = Query(...), top_n: int = 8):
    if keyword not in scoring.KEYWORD_CONFIG:
        raise HTTPException(400, f"알 수 없는 키워드입니다: {keyword}")

    st = data.get_status()
    if st.get("state") != "ready":
        raise HTTPException(
            503,
            f"데이터 준비 중입니다 ({st.get('state', 'empty')}, {st.get('progress', 0)}%). 잠시 후 다시 시도하세요.",
        )

    universe = data.load_universe()
    prices = data.load_prices()
    top_n = max(5, min(10, top_n))
    items = scoring.recommend(keyword, universe, prices, top_n=top_n)
    return {
        "keyword": keyword,
        "label": scoring.KEYWORD_CONFIG[keyword]["label"],
        "desc": scoring.KEYWORD_CONFIG[keyword]["desc"],
        "count": len(items),
        "items": items,
        "as_of": st.get("built_at"),
        "universe_size": st.get("universe_size"),
    }


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
