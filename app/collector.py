"""수집 파이프라인: 나라장터 API 호출 → DB 적재 → 신규 건 알림.

진행 상황은 progress 딕셔너리에 기록되어 화면의 업데이트 게이지에 표시된다.
"""
import threading
from datetime import datetime, timedelta

from app import database, g2b_api, notifier
from app.config import load_settings

CATEGORIES = ["발주계획", "입찰공고", "낙찰결과"]
BID_TYPES = ["물품", "공사", "용역", "외자"]

progress = {
    "running": False,
    "total": 0,
    "done": 0,
    "current": "",       # 예: "입찰공고 · 용역 · 경관조명"
    "new_count": 0,
    "errors": [],
    "last_run": None,
    "last_result": "",
}
_run_lock = threading.Lock()


def run_collection(notify: bool = True) -> None:
    """전체 수집 1회 실행 (예약/수동 공용). 이미 실행 중이면 무시."""
    if not _run_lock.acquire(blocking=False):
        return
    try:
        _collect(notify)
    finally:
        _run_lock.release()


def _collect(notify: bool) -> None:
    settings = load_settings()
    keywords = [k.strip() for k in settings["keywords"] if k.strip()]
    excludes = [k.strip() for k in settings.get("exclude_keywords", []) if k.strip()]

    if not settings["api_key"].strip():
        progress.update(
            running=False,
            last_result="API 인증키가 없습니다. [설정]에서 입력해 주세요.",
        )
        return
    if not keywords:
        progress.update(running=False, last_result="검색 키워드가 없습니다.")
        return

    days = int(settings.get("search_date_range_days", 7))
    end = datetime.now()
    begin = end - timedelta(days=days)
    begin_dt, end_dt = begin.strftime("%Y%m%d0000"), end.strftime("%Y%m%d2359")

    steps = [(c, t) for c in CATEGORIES for t in BID_TYPES]
    progress.update(
        running=True, total=len(steps), done=0, new_count=0,
        errors=[], current="", last_result="",
    )

    new_items: list[dict] = []
    with database.get_conn() as conn:
        for category, bid_type in steps:
            progress["current"] = f"{category} · {bid_type}"
            try:
                for item in g2b_api.search(category, bid_type, keywords, begin_dt, end_dt):
                    if any(x in item["title"] for x in excludes):
                        continue  # 제외 키워드가 제목에 있으면 버림
                    if database.insert_announcement(conn, item):
                        new_items.append(item)
            except g2b_api.G2bApiError as e:
                progress["errors"].append(f"{category}/{bid_type}: {e}")
            progress["done"] += 1
            conn.commit()  # 단계마다 커밋 — 쓰기 잠금을 짧게 유지

    progress.update(
        running=False,
        current="",
        new_count=len(new_items),
        last_run=datetime.now().strftime("%Y-%m-%d %H:%M"),
        last_result=f"신규 {len(new_items)}건 수집"
        + (f" (오류 {len(progress['errors'])}건)" if progress["errors"] else ""),
    )

    if notify and new_items:
        notifier.notify_new(new_items)
