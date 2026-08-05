"""설정 파일(data/settings.json) 로드/저장.

API 인증키는 코드가 아니라 설정 파일에 보관한다.
(코드에 넣으면 프로그램 공유 시 키가 함께 유출되기 때문)
"""
import json

from app.paths import DATA_DIR

SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULTS = {
    "api_key": "",                        # 공공데이터포털 일반 인증키(Decoding)
    "keywords": ["경관조명", "전시관"],     # 검색 키워드 (예시, 설정 화면에서 수정)
    "exclude_keywords": [],               # 제외 키워드 — 제목에 포함되면 수집하지 않음
    "search_date_range_days": 7,          # 최근 N일 공고를 검색 (최대 365)
    "search_times": ["09:00", "16:30"],   # 예약 검색 시각 (HH:MM)
}


def load_settings() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if SETTINGS_PATH.exists():
        saved = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        return {**DEFAULTS, **saved}
    save_settings(dict(DEFAULTS))
    return dict(DEFAULTS)


def save_settings(settings: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
