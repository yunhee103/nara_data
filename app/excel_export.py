"""조회 결과를 엑셀(.xlsx)로 내보내기. 파일은 exports/ 폴더에 생성된다."""
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from app.paths import EXPORT_DIR

COLUMNS = [
    ("category", "구분"),
    ("bid_type", "업무"),
    ("bid_no", "공고번호"),
    ("title", "공고명"),
    ("org_name", "공고기관"),
    ("demand_org", "수요기관"),
    ("budget", "예산(원)"),
    ("winner", "낙찰업체"),
    ("award_amount", "낙찰금액(원)"),
    ("award_rate", "낙찰률(%)"),
    ("posted_at", "게시일"),
    ("deadline", "마감일"),
    ("matched_keyword", "키워드"),
    ("url", "링크"),
]


def export_announcements(rows: list[dict]) -> Path:
    EXPORT_DIR.mkdir(exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "공고목록"
    ws.append([label for _, label in COLUMNS])
    for row in rows:
        ws.append([row.get(key) for key, _ in COLUMNS])

    path = EXPORT_DIR / f"나라장터_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    wb.save(path)
    return path
