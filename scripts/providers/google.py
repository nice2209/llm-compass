"""Google Gemini 가격 파서 — HTML 스크래핑 우선, 실패 시 검증된 fallback."""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import (
    BaseProvider,
    fixed_entries,
    html_table_entries,
    usable,
)


class GoogleProvider(BaseProvider):
    name = "google"
    source_url = "https://ai.google.dev/gemini-api/docs/pricing"

    # (모델, 입력가, 출력가, 컨텍스트) — USD / 1M tokens
    FALLBACK = [
        ("gemini-2.5-pro", 1.25, 10.0, 1048576),
        ("gemini-2.5-flash", 0.15, 0.6, 1048576),
        ("gemini-2.0-flash", 0.1, 0.4, 1048576),
    ]

    def fetch(self) -> list[PriceEntry]:
        try:
            scraped = usable(
                html_table_entries(
                    self.name, self.source_url, self._get(self.source_url).text
                )
            )
            if scraped:
                return scraped
        except Exception:  # noqa: BLE001 — 스크래핑 실패 시 검증 데이터로 폴백
            pass
        return fixed_entries(self.name, self.source_url, self.FALLBACK)
