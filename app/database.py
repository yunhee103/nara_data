"""SQLite 저장소. 파일 하나(data/g2b.db)에 모든 수집 데이터를 보관한다."""
import sqlite3

from app.paths import DATA_DIR

DB_PATH = DATA_DIR / "g2b.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS announcements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    category        TEXT NOT NULL,   -- 발주계획 / 입찰공고 / 낙찰결과
    bid_type        TEXT NOT NULL,   -- 물품 / 공사 / 용역 / 외자
    bid_no          TEXT NOT NULL,   -- 공고번호
    title           TEXT NOT NULL,   -- 공고명
    org_name        TEXT,            -- 공고기관
    demand_org      TEXT,            -- 수요기관
    budget          INTEGER,         -- 예산/기초금액(원)
    winner          TEXT,            -- 낙찰업체 (낙찰결과에만)
    award_amount    INTEGER,         -- 낙찰금액(원) (낙찰결과에만)
    award_rate      REAL,            -- 낙찰률(%) (낙찰결과에만, API 제공값)
    posted_at       TEXT,            -- 게시일시
    deadline        TEXT,            -- 입찰마감일시
    url             TEXT,            -- 나라장터 상세 링크
    matched_keyword TEXT,            -- 검출된 키워드
    collected_at    TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE (category, bid_no)
);

CREATE TABLE IF NOT EXISTS notifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    announcement_id INTEGER REFERENCES announcements(id),
    keyword         TEXT,
    message         TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now', 'localtime')),
    is_read         INTEGER DEFAULT 0
);
"""


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def insert_announcement(conn: sqlite3.Connection, item: dict) -> bool:
    """공고 1건 저장. 새로 추가된 경우 True, 이미 있던 공고면 False."""
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO announcements
            (category, bid_type, bid_no, title, org_name, demand_org,
             budget, winner, award_amount, award_rate, posted_at, deadline, url, matched_keyword)
        VALUES
            (:category, :bid_type, :bid_no, :title, :org_name, :demand_org,
             :budget, :winner, :award_amount, :award_rate, :posted_at, :deadline, :url, :matched_keyword)
        """,
        item,
    )
    return cur.rowcount > 0


def list_announcements(
    category: str | None = None,
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    keyword_tag: str | None = None,   # 수집 당시 매칭된 키워드(분야)로 정확히 거름
    budget_min: int | None = None,
    budget_max: int | None = None,
    limit: int = 500,
) -> list[dict]:
    where, params = [], []
    if category:
        where.append("category = ?")
        params.append(category)
    if keyword_tag:
        where.append("matched_keyword = ?")
        params.append(keyword_tag)
    if budget_min is not None:
        where.append("COALESCE(budget, award_amount) >= ?")
        params.append(budget_min)
    if budget_max is not None:
        where.append("COALESCE(budget, award_amount) <= ?")
        params.append(budget_max)
    if keyword:
        where.append("(title LIKE ? OR matched_keyword LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    if date_from:
        where.append("posted_at >= ?")
        params.append(date_from)
    if date_to:
        where.append("posted_at <= ?")
        params.append(date_to + " 23:59")
    sql = "SELECT * FROM announcements"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY posted_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_keyword_tags() -> list[str]:
    """수집된 데이터에 존재하는 분야(키워드) 목록 (필터 드롭다운용)."""
    sql = "SELECT DISTINCT matched_keyword FROM announcements WHERE matched_keyword IS NOT NULL ORDER BY 1"
    with get_conn() as conn:
        return [r[0] for r in conn.execute(sql).fetchall()]


def award_summary(keyword: str | None = None, limit: int = 20) -> list[dict]:
    """낙찰 업체별 수주 건수/총액 순위."""
    where = "category = '낙찰결과' AND winner IS NOT NULL AND winner != ''"
    params: list = []
    if keyword:
        where += " AND (title LIKE ? OR matched_keyword LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql = f"""
        SELECT winner,
               COUNT(*)                        AS award_count,
               COALESCE(SUM(award_amount), 0)  AS total_amount
        FROM announcements
        WHERE {where}
        GROUP BY winner
        ORDER BY total_amount DESC
        LIMIT ?
    """
    params.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def award_monthly(keyword: str | None = None, months: int = 12) -> list[dict]:
    """월별 낙찰 건수/총액 추이 (오래된 달부터)."""
    where = "category = '낙찰결과' AND posted_at IS NOT NULL"
    params: list = []
    if keyword:
        where += " AND (title LIKE ? OR matched_keyword LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql = f"""
        SELECT substr(posted_at, 1, 7)            AS month,
               COUNT(*)                           AS award_count,
               COALESCE(SUM(award_amount), 0)     AS total_amount
        FROM announcements
        WHERE {where}
        GROUP BY month ORDER BY month DESC LIMIT ?
    """
    params.append(months)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()][::-1]


def demand_org_summary(keyword: str | None = None, limit: int = 10) -> list[dict]:
    """수요기관별 낙찰 발주 순위 (총액 기준)."""
    where = "category = '낙찰결과' AND demand_org IS NOT NULL"
    params: list = []
    if keyword:
        where += " AND (title LIKE ? OR matched_keyword LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql = f"""
        SELECT demand_org,
               COUNT(*)                       AS award_count,
               COALESCE(SUM(award_amount), 0) AS total_amount
        FROM announcements
        WHERE {where}
        GROUP BY demand_org ORDER BY total_amount DESC LIMIT ?
    """
    params.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# 추천 키워드에서 걸러낼 범용 단어 (공고 제목에 늘 나오는 말들)
_SUGGEST_STOPWORDS = {
    "사업", "구축", "구매", "구입", "설치", "제작", "용역", "공사", "물품",
    "및", "위한", "관련", "지원", "운영", "관리", "개선", "조성", "공고",
    "재공고", "긴급", "제한", "일반", "협상", "수의", "단가", "연간", "기타",
}


def suggest_keywords(current: set[str], limit: int = 12) -> list[str]:
    """수집된 공고 제목에서 자주 나오는 단어를 추천 키워드로 뽑는다."""
    import re
    from collections import Counter

    counts: Counter = Counter()
    with get_conn() as conn:
        for (title,) in conn.execute("SELECT title FROM announcements"):
            for word in re.findall(r"[가-힣A-Za-z]{2,}", title):
                counts[word] += 1
    return [
        w for w, _ in counts.most_common(200)
        if w not in _SUGGEST_STOPWORDS and w not in current
    ][:limit]


def list_notifications(
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 300,
) -> list[dict]:
    where, params = [], []
    if keyword:
        where.append("(keyword LIKE ? OR message LIKE ?)")
        params += [f"%{keyword}%", f"%{keyword}%"]
    if date_from:
        where.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        where.append("created_at <= ?")
        params.append(date_to + " 23:59")
    sql = "SELECT * FROM notifications"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def count_today_new() -> dict:
    """오늘 수집된 신규 공고/낙찰 건수 (메인 화면 상단 요약용)."""
    sql = """
        SELECT
          SUM(CASE WHEN category != '낙찰결과' THEN 1 ELSE 0 END) AS new_bids,
          SUM(CASE WHEN category  = '낙찰결과' THEN 1 ELSE 0 END) AS new_awards
        FROM announcements
        WHERE date(collected_at) = date('now', 'localtime')
    """
    with get_conn() as conn:
        row = dict(conn.execute(sql).fetchone())
    return {"new_bids": row["new_bids"] or 0, "new_awards": row["new_awards"] or 0}
