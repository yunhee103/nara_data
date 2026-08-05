"""공공데이터포털 나라장터 OpenAPI 클라이언트.

2026-08-05 실제 인증키로 호출해 확정한 스펙 (PRD 9.3 참고):
- 입찰공고/낙찰결과: 키워드(bidNtceNm)가 서버에서 필터링됨. 기간은 일시(YYYYMMDDHHMM).
  ※ 낙찰결과는 기간이 약 1개월을 넘으면 '입력범위값 초과' 에러 → 검색기간 30일 이하 유지
- 발주계획: 기간이 발주년월(YYYYMM)이고 키워드 필터가 없음 → 전체를 받아 사업명으로 로컬 필터
"""
from datetime import datetime, timedelta

import requests

from app.config import load_settings

TIMEOUT = 15
ROWS_PER_PAGE = 999
MAX_PAGES = 5   # 폭주 방지 (999건 × 5페이지)
CHUNK_DAYS = 30  # 낙찰결과 API의 기간 제한(약 1개월)에 맞춘 분할 단위

# 업무구분 → 오퍼레이션명 접미사
TYPE_SUFFIX = {"물품": "Thng", "공사": "Cnstwk", "용역": "Servc", "외자": "Frgcpt"}

# 카테고리별 엔드포인트 ({type} 자리에 TYPE_SUFFIX가 들어감)
SERVICES = {
    "발주계획": "http://apis.data.go.kr/1230000/ao/OrderPlanSttusService/getOrderPlanSttusList{type}",
    "입찰공고": "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfo{type}PPSSrch",
    "낙찰결과": "http://apis.data.go.kr/1230000/as/ScsbidInfoService/getScsbidListSttus{type}PPSSrch",
}


class ApiKeyMissingError(Exception):
    """설정에 API 인증키가 없다."""


class G2bApiError(Exception):
    """나라장터 API 호출 실패."""


def search(
    category: str,
    bid_type: str,
    keywords: list[str],
    begin_dt: str,  # YYYYMMDDHHMM
    end_dt: str,    # YYYYMMDDHHMM
) -> list[dict]:
    """키워드에 걸리는 공고 목록을 DB 컬럼 형태로 정규화해 돌려준다."""
    url = SERVICES[category].format(type=TYPE_SUFFIX[bid_type])

    if category == "발주계획":
        # 서버 키워드 필터 미지원 → 기간 전체를 받아 사업명으로 거른다 (호출 1회)
        params = {"inqryDiv": 1, "orderBgnYm": begin_dt[:6], "orderEndYm": end_dt[:6]}
        results = []
        for item in _fetch_all(url, params):
            matched = next((k for k in keywords if k in (item.get("bizNm") or "")), None)
            if matched:
                results.append(_norm_plan(item, bid_type, matched))
        return results

    # 입찰공고/낙찰결과: 키워드×30일단위 구간별로 호출 (서버 필터)
    # 긴 검색기간(예: 150일)도 API 기간 제한에 걸리지 않도록 구간을 쪼갠다
    norm = _norm_bid if category == "입찰공고" else _norm_award
    results = []
    for kw in keywords:
        for chunk_begin, chunk_end in _date_chunks(begin_dt, end_dt):
            params = {"inqryDiv": 1, "inqryBgnDt": chunk_begin, "inqryEndDt": chunk_end, "bidNtceNm": kw}
            results += [norm(item, bid_type, kw) for item in _fetch_all(url, params)]
    return results


def _date_chunks(begin_dt: str, end_dt: str):
    """YYYYMMDDHHMM 구간을 CHUNK_DAYS 단위로 쪼갠다."""
    begin = datetime.strptime(begin_dt, "%Y%m%d%H%M")
    end = datetime.strptime(end_dt, "%Y%m%d%H%M")
    while begin < end:
        chunk_end = min(begin + timedelta(days=CHUNK_DAYS), end)
        yield begin.strftime("%Y%m%d%H%M"), chunk_end.strftime("%Y%m%d%H%M")
        begin = chunk_end + timedelta(minutes=1)


# ── 내부 구현 ──────────────────────────────────────────────


def _fetch_all(url: str, extra_params: dict) -> list[dict]:
    """페이지를 넘기며 전체 항목을 수집한다."""
    api_key = load_settings().get("api_key", "").strip()
    if not api_key:
        raise ApiKeyMissingError("API 인증키가 설정되지 않았습니다.")

    items, page = [], 1
    while page <= MAX_PAGES:
        params = {
            "serviceKey": api_key, "type": "json",
            "pageNo": page, "numOfRows": ROWS_PER_PAGE, **extra_params,
        }
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            raise G2bApiError(f"호출 실패: {e}") from e
        except ValueError as e:
            raise G2bApiError("응답 해석 실패 (인증키/파라미터 확인 필요)") from e

        # 정상은 "response", 에러는 "nkoneps.com.response.ResponseError" 루트로 온다
        root = next(iter(data.values()), {})
        header = root.get("header", {})
        if header.get("resultCode") != "00":
            raise G2bApiError(f"API 오류: {header.get('resultMsg', '알 수 없음')}")

        body = root.get("body", {})
        page_items = body.get("items") or []
        if isinstance(page_items, dict):  # 1건이면 dict로 오는 경우 대응
            page_items = [page_items]
        items += page_items

        if len(items) >= int(body.get("totalCount") or 0):
            break
        page += 1
    return items


def _to_int(value) -> int | None:
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _norm_bid(item: dict, bid_type: str, keyword: str) -> dict:
    """입찰공고 응답 → DB 컬럼 (필드명은 실호출로 확인됨)."""
    return {
        "category": "입찰공고", "bid_type": bid_type, "matched_keyword": keyword,
        "bid_no": item.get("bidNtceNo") or "",
        "title": item.get("bidNtceNm") or "(제목 없음)",
        "org_name": item.get("ntceInsttNm"),
        "demand_org": item.get("dminsttNm"),
        "budget": _to_int(item.get("asignBdgtAmt") or item.get("presmptPrce")),
        "winner": None, "award_amount": None, "award_rate": None,
        "posted_at": item.get("bidNtceDt"),
        "deadline": item.get("bidClseDt"),
        "url": item.get("bidNtceDtlUrl") or item.get("bidNtceUrl"),
    }


def _norm_award(item: dict, bid_type: str, keyword: str) -> dict:
    """낙찰결과 응답 → DB 컬럼. 공고기관/예산/링크는 이 API에 없음."""
    return {
        "category": "낙찰결과", "bid_type": bid_type, "matched_keyword": keyword,
        "bid_no": item.get("bidNtceNo") or "",
        "title": item.get("bidNtceNm") or "(제목 없음)",
        "org_name": None,
        "demand_org": item.get("dminsttNm"),
        "budget": None,
        "winner": item.get("bidwinnrNm"),
        "award_amount": _to_int(item.get("sucsfbidAmt")),
        "award_rate": _to_float(item.get("sucsfbidRate")),
        "posted_at": item.get("fnlSucsfDate") or item.get("rgstDt"),
        "deadline": None,
        "url": None,
    }


def _norm_plan(item: dict, bid_type: str, keyword: str) -> dict:
    """발주계획 응답 → DB 컬럼. 공고번호가 없어 기관코드+연도+일련번호로 만든다."""
    return {
        "category": "발주계획", "bid_type": bid_type, "matched_keyword": keyword,
        "bid_no": f"{item.get('orderInsttCd', '')}-{item.get('orderYear', '')}-{item.get('orderPlanSno', '')}",
        "title": item.get("bizNm") or "(사업명 없음)",
        "org_name": item.get("orderInsttNm"),
        "demand_org": item.get("totlmngInsttNm"),
        "budget": _to_int(item.get("sumOrderAmt")),
        "winner": None, "award_amount": None, "award_rate": None,
        "posted_at": item.get("nticeDt") or f"{item.get('orderYear', '')}-{str(item.get('orderMnth', '')).zfill(2)}",
        "deadline": None,
        "url": None,
    }
