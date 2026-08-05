"""신규 공고 알림: notifications 테이블 기록 + Windows 토스트."""
from app import database

MAX_TITLES_IN_TOAST = 3


def notify_new(items: list[dict]) -> None:
    with database.get_conn() as conn:
        for it in items:
            conn.execute(
                "INSERT INTO notifications (keyword, message) VALUES (?, ?)",
                (
                    it.get("matched_keyword"),
                    f"[{it['category']}·{it['bid_type']}] {it['title']}",
                ),
            )
        conn.commit()

    _show_toast(items)


def _show_toast(items: list[dict]) -> None:
    """토스트는 실패해도 수집이 중단되지 않도록 방어적으로 처리한다."""
    try:
        from winotify import Notification

        titles = [it["title"][:40] for it in items[:MAX_TITLES_IN_TOAST]]
        more = len(items) - len(titles)
        msg = "\n".join(titles) + (f"\n외 {more}건" if more > 0 else "")
        # 클릭하면 첫 번째 공고의 나라장터 페이지가 열린다 (URL 없는 공고면 동작 없음)
        first_url = next((it["url"] for it in items if it.get("url")), "")
        Notification(
            app_id="나라장터 입찰정보 시스템",
            title=f"신규 공고 {len(items)}건 검출",
            msg=msg,
            launch=first_url,
        ).show()
    except Exception:
        pass
