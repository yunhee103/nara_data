# 나라장터 입찰정보 시스템

영업 담당자와 취업준비생이 **나라장터(g2b)의 발주계획·입찰공고·낙찰결과**를
키워드 하나로 검색·감시·알림받기 위한 Windows 프로그램입니다.

공공데이터포털(data.go.kr)의 조달청 나라장터 OpenAPI만 사용하며, 서버 없이 PC 한 대에서 동작합니다.

---

## 주요 기능

- **키워드 기반 자동 수집** — 등록한 키워드로 발주계획/입찰공고/낙찰결과를 수집해 로컬 DB에 누적 적재
- **예약 검색 + 알림** — 지정한 시각(예: 09:00, 16:30)에 자동 수집, 신규 공고 검출 시 Windows 토스트 알림 + 앱 내 알림 패널
- **낙찰 결과 시각화** — 업체별 수주 순위, 월별 낙찰 추이, 수요기관별 발주 순위를 차트로 확인
- **조회 필터** — 구분/분야/공고명/날짜/예산 범위로 수집된 DB를 거르고, 마감 임박 공고에 D-day 배지 표시
- **엑셀 내보내기** — 조회 결과를 `.xlsx`로 저장
- **제외 키워드 / 추천 키워드** — 노이즈 제거, 빈출 단어 칩 클릭으로 키워드 추가

## 기술 구성

| 구분 | 선택 |
|---|---|
| 언어 | Python |
| 백엔드 | FastAPI (로컬 전용) |
| 화면 | pywebview 자체 창 + 순수 HTML/CSS/JS (HTS 스타일 다크 테마) |
| 데이터 저장 | SQLite (파일 DB) |
| 알림 | Windows 토스트(winotify) + 앱 내 패널 |
| 데이터 취득 | 나라장터 OpenAPI (requests) |

## 프로젝트 구조

```
API_나라장터/
├── requirements.txt     파이썬 의존성
├── run.py               진입점: 서버 + 스케줄러 + 자체 창 실행
├── build_exe.spec       exe 패키징 레시피 (PyInstaller)
├── app/                 백엔드
│   ├── paths.py         경로 일괄 관리 (개발/exe 환경 자동 구분)
│   ├── config.py        설정 로드/저장 (API 키 위치)
│   ├── database.py      SQLite 스키마 + 조회/저장
│   ├── g2b_api.py       나라장터 OpenAPI 클라이언트
│   ├── collector.py     수집 파이프라인 (API → DB → 알림)
│   ├── scheduler.py     예약 검색
│   ├── notifier.py      토스트 알림 + 알림 내역
│   ├── excel_export.py  엑셀 내보내기
│   └── server.py        FastAPI 라우트
├── ui/                  화면 (HTML/CSS/JS)
├── data/                SQLite DB + settings.json (자동 생성, git 제외)
└── exports/             내보낸 엑셀 (자동 생성, git 제외)
```

---

## 설치 및 실행

### 1. 가상환경 생성 및 의존성 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. API 인증키 발급

1. [공공데이터포털(data.go.kr)](https://www.data.go.kr) 로그인
2. **"나라장터"** 검색 후 아래 3개 서비스 각각 **[활용신청]**
   - 조달청_나라장터 **입찰공고**정보서비스
   - 조달청_나라장터 **낙찰**정보서비스
   - 조달청_나라장터 **발주계획**정보서비스
3. 마이페이지 → **일반 인증키(Decoding)** 확인 (인증키 1개로 3개 서비스 공용)
   - ⚠️ 반드시 **Decoding** 버전 사용 (Encoding 버전은 이중 인코딩 오류)
   - 발급 직후 반영까지 최대 1~2시간 소요될 수 있음

### 3. 실행

```bash
python run.py
```

실행하면 자체 프로그램 창이 뜹니다. 처음 실행 시 [설정] 화면에서 발급받은 API 키를 입력하세요.
(WebView2 런타임이 없는 PC에서는 자동으로 기본 브라우저로 대체 실행됩니다.)

### 4. exe로 패키징 (배포용, 선택)

```bash
.venv\Scripts\pyinstaller build_exe.spec --noconfirm
copy 사용설명서.txt dist\나라장터입찰정보\
```

- 결과물: `dist\나라장터입찰정보\` 폴더 — 통째로 복사하면 **파이썬 없는 PC에서도 실행** 가능
- 다른 사람에게 줄 때는 폴더 안 `data/` 폴더를 삭제하고 전달 (본인 API 키 포함되어 있음)
- 설정·DB(`data/`)와 엑셀(`exports/`)은 exe 옆에 생성되므로 재패키징해도 유지됩니다
- 코드를 수정하면 위 명령으로 다시 패키징해야 합니다 (개발 중에는 `python run.py`로 확인)

---

## ⚠️ 보안 주의

- **API 인증키는 `data/settings.json`에 저장되며, 이 파일은 `.gitignore`로 커밋에서 제외됩니다.**
- 인증키를 코드에 직접 넣지 마세요. 실수로 키가 담긴 커밋을 올렸다면 즉시 키를 재발급하세요.

## 라이선스

개인/사내 사용 목적. 데이터 출처: 공공데이터포털(data.go.kr) 조달청 나라장터 OpenAPI.
