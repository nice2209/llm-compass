"""Anthropic 가격 파서 — HTML 스크래핑 우선, 실패 시 검증된 fallback."""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import (
    BaseProvider,
    fixed_entries,
    html_table_entries,
    usable,
)


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    source_url = "https://www.anthropic.com/pricing#anthropic-api"

    # (모델, 입력가, 출력가, 컨텍스트) — USD / 1M tokens
    FALLBACK = [
        ("claude-opus-4", 15.0, 75.0, 200000),
        ("claude-sonnet-4", 3.0, 15.0, 200000),
        ("claude-haiku-3.5", 0.8, 4.0, 200000),
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
