"""FastAPI 라우트: 화면(정적 파일) 제공 + 데이터 API."""
import threading

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import collector, database, excel_export, scheduler
from app.config import load_settings, save_settings
from app.paths import UI_DIR

app = FastAPI(title="나라장터 입찰정보 시스템")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


# ── 상태/수집 ──────────────────────────────────────────────


@app.get("/api/status")
def status() -> dict:
    settings = load_settings()
    return {
        "has_api_key": bool(settings["api_key"].strip()),
        "today": database.count_today_new(),
        "next_run": scheduler.next_run_time(),
        "progress": collector.progress,
    }


@app.post("/api/collect")
def collect() -> dict:
    """수집을 백그라운드로 시작. 진행 상황은 /api/status의 progress로 확인."""
    threading.Thread(target=collector.run_collection, daemon=True).start()
    return {"started": True}


# ── 조회 ──────────────────────────────────────────────────


@app.get("/api/announcements")
def announcements(
    category: str | None = None,
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    keyword_tag: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
) -> list[dict]:
    return database.list_announcements(
        category, keyword, date_from, date_to, keyword_tag, budget_min, budget_max
    )


@app.get("/api/keywords")
def keyword_tags() -> list[str]:
    """수집된 데이터에 존재하는 분야(키워드) 목록."""
    return database.list_keyword_tags()


@app.get("/api/keywords/suggest")
def keyword_suggest() -> list[str]:
    """공고 제목 빈출 단어 기반 추천 키워드."""
    current = set(load_settings().get("keywords", []))
    return database.suggest_keywords(current)


@app.get("/api/awards/monthly")
def awards_monthly(keyword: str | None = None) -> list[dict]:
    return database.award_monthly(keyword)


@app.get("/api/awards/orgs")
def awards_orgs(keyword: str | None = None) -> list[dict]:
    return database.demand_org_summary(keyword)


@app.get("/api/awards/summary")
def awards_summary(keyword: str | None = None) -> list[dict]:
    return database.award_summary(keyword)


@app.get("/api/notifications")
def notifications(
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    return database.list_notifications(keyword, date_from, date_to)


# ── 엑셀 내보내기 ─────────────────────────────────────────


class ExportRequest(BaseModel):
    category: str | None = None
    keyword: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    keyword_tag: str | None = None
    budget_min: int | None = None
    budget_max: int | None = None


@app.post("/api/export")
def export(req: ExportRequest) -> dict:
    rows = database.list_announcements(
        req.category, req.keyword, req.date_from, req.date_to,
        req.keyword_tag, req.budget_min, req.budget_max, limit=10000,
    )
    path = excel_export.export_announcements(rows)
    return {"path": str(path), "count": len(rows)}


# ── 설정 ──────────────────────────────────────────────────


class Settings(BaseModel):
    api_key: str
    keywords: list[str]
    exclude_keywords: list[str] = []
    search_date_range_days: int
    search_times: list[str]


@app.get("/api/settings")
def get_settings() -> dict:
    return load_settings()


@app.put("/api/settings")
def put_settings(s: Settings) -> dict:
    save_settings(s.model_dump())
    return {"saved": True}


# 정적 파일(css/js)은 맨 마지막에 마운트
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")
