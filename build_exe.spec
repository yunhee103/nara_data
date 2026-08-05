# -*- mode: python ; coding: utf-8 -*-
# exe 패키징 레시피 (PyInstaller)
#
# 사용법 (코드 수정 후 재패키징할 때마다 아래 두 줄):
#   .venv\Scripts\pyinstaller build_exe.spec --noconfirm
#   copy 사용설명서.txt dist\나라장터입찰정보\
#
# 결과물: dist\나라장터입찰정보\나라장터입찰정보.exe
#   - ui/ 화면 파일은 exe 안에 함께 포장됨
#   - data/(설정·DB)와 exports/(엑셀)는 exe "옆"에 생성 — 재패키징해도 유지됨

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[("ui", "ui")],                 # 화면(HTML/CSS/JS)을 번들에 포함
    hiddenimports=[
        "webview.platforms.winforms",     # pywebview Windows 백엔드 (자동 탐지 안 됨)
        "webview.platforms.edgechromium",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="나라장터입찰정보",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                        # 검은 콘솔창 없이 GUI만
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="나라장터입찰정보",
)
