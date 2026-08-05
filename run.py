"""나라장터 입찰정보 시스템 진입점.

실행 흐름:
1) 로컬 FastAPI 서버를 백그라운드 스레드로 시작
2) 예약 검색 스케줄러 시작
3) pywebview로 자체 프로그램 창을 열어 화면 표시
   (WebView2가 없는 PC에서는 기본 브라우저로 대체)
"""
import socket
import threading
import time

import uvicorn

from app.scheduler import start_scheduler
from app.server import app

HOST = "127.0.0.1"


def find_free_port() -> int:
    with socket.socket() as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def wait_until_ready(port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def main() -> None:
    port = find_free_port()
    config = uvicorn.Config(app, host=HOST, port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    if not wait_until_ready(port):
        raise RuntimeError("로컬 서버가 시작되지 않았습니다.")

    start_scheduler()
    url = f"http://{HOST}:{port}"

    try:
        import webview

        webview.create_window(
            "나라장터 입찰정보 시스템",
            url,
            width=1440,
            height=900,
            min_size=(1100, 700),
        )
        webview.start()
    except Exception:
        # WebView2 런타임이 없는 환경 대비 폴백
        import webbrowser

        webbrowser.open(url)
        print(f"자체 창을 열 수 없어 브라우저로 실행합니다: {url}")
        print("종료하려면 이 창을 닫으세요 (Ctrl+C)")
        while True:
            time.sleep(3600)


if __name__ == "__main__":
    main()
