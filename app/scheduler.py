"""예약 검색 스케줄러.

20초마다 현재 시각(HH:MM)이 설정된 검색 시각과 일치하는지 확인하고,
일치하면 수집을 1회 실행한다. 프로그램이 켜져 있는 동안만 동작한다.
"""
import threading
import time
from datetime import datetime, timedelta

from app.collector import run_collection
from app.config import load_settings

_last_fired: str | None = None


def _loop() -> None:
    global _last_fired
    while True:
        now = datetime.now().strftime("%H:%M")
        times = load_settings().get("search_times", [])
        if now in times and _last_fired != now:
            _last_fired = now
            threading.Thread(target=run_collection, daemon=True).start()
        time.sleep(20)


def start_scheduler() -> None:
    threading.Thread(target=_loop, daemon=True).start()


def next_run_time() -> str | None:
    """다음 예약 검색 시각 (메인 화면 표시용)."""
    times = sorted(load_settings().get("search_times", []))
    if not times:
        return None
    now = datetime.now()
    for t in times:
        if t > now.strftime("%H:%M"):
            return f"오늘 {t}"
    return f"내일 {times[0]}"
