"""MiMo Token Plan 가격 파서 — 자체 JSON API 우선, 실패 시 검증된 fallback.

응답의 unit이 'per_1k_tokens'면 ×1000으로 1M 단위 정규화한다.
API가 실패하면 FALLBACK 데이터를 반환한다.
"""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import BaseProvider, fixed_entries, now_iso, usable


class MimoProvider(BaseProvider):
    name = "mimo"
    source_url = "https://token-plan-sgp.xiaomimimo.com/v1/models"

    # (모델, 입력가, 출력가, 컨텍스트) — USD / 1M tokens
    FALLBACK = [
        ("mimo-v2.5", 0.15, 0.15, 65536),
        ("mimo-v2.5-pro", 0.3, 0.3, 131072),
        ("mimo-v2-pro", 0.15, 0.15, 65536),
        ("mimo-v2-omni", 0.5, 0.5, 65536),
        ("mimo-v2-flash", 0.05, 0.05, 65536),
    ]

    def fetch(self) -> list[PriceEntry]:
        try:
            scraped = usable(self._scrape())
            if scraped:
                return scraped
        except Exception:  # noqa: BLE001 — API 실패 시 검증 데이터로 폴백
            pass
        return fixed_entries(self.name, self.source_url, self.FALLBACK)

    def _scrape(self) -> list[PriceEntry]:
        payload = self._get(self.source_url).json()
        mult = 1_000.0 if payload.get("unit") == "per_1k_tokens" else 1.0
        note = "1K→1M 정규화" if mult != 1.0 else None
        fetched = now_iso()
        entries: list[PriceEntry] = []
        for m in payload.get("models", []):
            entries.append(
                PriceEntry(
                    provider=self.name,
                    model=m["name"],
                    input_per_1m=round(float(m.get("input_price", 0)) * mult, 6),
                    output_per_1m=round(float(m.get("output_price", 0)) * mult, 6),
                    context_window=int(m.get("context") or 0),
                    source_url=self.source_url,
                    fetched_at=fetched,
                    notes=note,
                )
            )
        return entries
