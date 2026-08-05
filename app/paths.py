"""실행 환경별 경로를 한 곳에서 관리한다.

- 개발 중: 프로젝트 폴더 기준
- exe 패키징 후:
  · 번들 리소스(ui/) → PyInstaller가 풀어놓는 내부 폴더(sys._MEIPASS)
  · 쓰기 데이터(data/, exports/) → exe 파일 옆 (재패키징해도 데이터 유지)
"""
import sys
from pathlib import Path

_FROZEN = getattr(sys, "frozen", False)          # PyInstaller로 묶였는지 여부
_PROJECT = Path(__file__).resolve().parent.parent

UI_DIR = Path(getattr(sys, "_MEIPASS", _PROJECT)) / "ui"

_WRITE_BASE = Path(sys.executable).parent if _FROZEN else _PROJECT
DATA_DIR = _WRITE_BASE / "data"
EXPORT_DIR = _WRITE_BASE / "exports"
