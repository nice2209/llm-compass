"""provider 파서 공통 기반."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx
from selectolax.parser import HTMLParser

from scripts.models import PriceEntry

_UA = (
    "Mozilla/5.0 (compatible; llm-compass-bot/0.1; "
    "+https://github.com/llm-compass)"
)
_TIMEOUT = 15.0
_RETRIES = 2


def now_iso() -> str:
    """현재 시각을 초 단위 ISO8601 UTC(Z)로 반환."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


_NUM = re.compile(r"[-+]?\d*\.?\d+")


def parse_money(text: str) -> float:
    """'$2.50 / 1M' 같은 문자열에서 첫 숫자를 float로 추출. 통화/단위 텍스트 무시."""
    m = _NUM.search(text.replace(",", ""))
    return float(m.group()) if m else 0.0


def parse_context(text: str) -> int:
    """'128k', '1M', '200,000' 등을 정수 토큰 수로 정규화."""
    t = text.strip().lower().replace(",", "")
    m = re.search(r"(\d+(?:\.\d+)?)\s*([km])?", t)
    if not m:
        return 0
    value = float(m.group(1))
    suffix = m.group(2)
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    return int(value)


def parse_table(html: str, table_selector: str = "table") -> list[list[str]]:
    """HTML에서 첫 매칭 테이블의 <tr>×<td> 텍스트를 2차원 리스트로 추출.

    헤더(<th>만 있는 행)는 건너뛴다. 셀렉터 변동에 대비해 파서별로 호출한다.
    """
    tree = HTMLParser(html)
    table = tree.css_first(table_selector)
    if table is None:
        return []
    rows: list[list[str]] = []
    for tr in table.css("tr"):
        cells = tr.css("td")
        if not cells:
            continue  # 헤더 행
        rows.append([c.text(strip=True) for c in cells])
    return rows


def html_table_entries(
    provider: str,
    source_url: str,
    html: str,
    *,
    table_selector: str = "table",
    price_mult: float = 1.0,
) -> list[PriceEntry]:
    """[모델, 입력가, 출력가, 컨텍스트] 4열 가격표를 PriceEntry 목록으로 매핑.

    ``price_mult``: 페이지가 1K 단위면 1000을 넘겨 1M 단위로 정규화한다.
    """
    fetched = now_iso()
    entries: list[PriceEntry] = []
    for row in parse_table(html, table_selector):
        if len(row) < 4:
            continue
        model, raw_in, raw_out, raw_ctx = row[0], row[1], row[2], row[3]
        if not model:
            continue
        entries.append(
            PriceEntry(
                provider=provider,
                model=model,
                input_per_1m=round(parse_money(raw_in) * price_mult, 6),
                output_per_1m=round(parse_money(raw_out) * price_mult, 6),
                context_window=parse_context(raw_ctx),
                source_url=source_url,
                fetched_at=fetched,
            )
        )
    return entries


def usable(entries: list[PriceEntry]) -> list[PriceEntry]:
    """온전한 가격표 행만 남긴다: 입력·출력 단가가 양수이고 컨텍스트가 있음.

    스크래핑이 헤더 조각('PRICING')이나 본문 텍스트('AI ModelGPT OSS...')를
    엔트리로 잡아내는 경우를 거른다. 이런 잡음 행은 컨텍스트 창을 파싱하지
    못해 0으로 남으므로, 정상 행과 구분하는 신뢰 신호로 쓴다.
    하나도 남지 않으면 호출부는 하드코딩 fallback으로 넘어간다.
    """
    return [
        e
        for e in entries
        if e.input_per_1m > 0 and e.output_per_1m > 0 and e.context_window > 0
    ]


VERIFIED_NOTE = "Verified pricing as of 2026-05-29"


def fixed_entries(
    provider: str,
    source_url: str,
    rows: list[tuple[str, float, float, int]],
    *,
    note: str = VERIFIED_NOTE,
) -> list[PriceEntry]:
    """하드코딩된 (모델, 입력가, 출력가, 컨텍스트) 행을 PriceEntry 목록으로.

    스크래핑이 실패하거나 잡음만 반환할 때 쓰는 검증된 fallback 데이터.
    가격 단위는 항상 USD / 1M tokens.
    """
    fetched = now_iso()
    return [
        PriceEntry(
            provider=provider,
            model=model,
            input_per_1m=in_price,
            output_per_1m=out_price,
            context_window=ctx,
            source_url=source_url,
            fetched_at=fetched,
            notes=note,
        )
        for model, in_price, out_price, ctx in rows
    ]


class BaseProvider(ABC):
    """모든 provider 파서의 추상 기반.

    하위 클래스는 ``name``/``source_url`` 클래스 속성과 ``fetch()``를 정의한다.
    네트워크 접근은 ``_get``으로 통일해 테스트에서 monkeypatch 가능하게 한다.
    """

    name: str
    source_url: str

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    @abstractmethod
    def fetch(self) -> list[PriceEntry]:
        """공식 페이지를 파싱해 정규화된 가격 목록 반환. 실패 시 예외."""
        raise NotImplementedError

    def _get(self, url: str, **kw: object) -> httpx.Response:
        """타임아웃·재시도·UA를 포함한 공통 GET."""
        headers = {"User-Agent": _UA, **dict(kw.pop("headers", {}) or {})}
        last_exc: Exception | None = None
        for attempt in range(_RETRIES + 1):
            try:
                resp = self._client.get(
                    url, headers=headers, timeout=_TIMEOUT, **kw
                )
                resp.raise_for_status()
                return resp
            except Exception as exc:  # noqa: BLE001 — 재시도 후 재전파
                last_exc = exc
                if attempt < _RETRIES:
                    time.sleep(0.5 * (attempt + 1))
        assert last_exc is not None
        raise last_exc
