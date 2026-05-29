"""OpenAI 가격 파서 — HTML 스크래핑 우선, 실패 시 검증된 fallback."""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import (
    BaseProvider,
    fixed_entries,
    html_table_entries,
    usable,
)


class OpenAIProvider(BaseProvider):
    name = "openai"
    source_url = "https://openai.com/api/pricing/"

    # (모델, 입력가, 출력가, 컨텍스트) — USD / 1M tokens
    FALLBACK = [
        ("gpt-4o", 2.5, 10.0, 128000),
        ("gpt-4o-mini", 0.15, 0.6, 128000),
        ("o3", 10.0, 40.0, 200000),
        ("o4-mini", 1.1, 4.4, 200000),
        ("gpt-4.1", 2.0, 8.0, 1047576),
        ("gpt-4.1-mini", 0.4, 1.6, 1047576),
        ("gpt-4.1-nano", 0.1, 0.4, 1047576),
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
