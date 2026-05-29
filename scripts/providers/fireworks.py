"""Fireworks AI 가격 파서 — HTML 스크래핑 우선, 실패 시 검증된 fallback."""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import (
    BaseProvider,
    fixed_entries,
    html_table_entries,
    usable,
)


class FireworksProvider(BaseProvider):
    name = "fireworks"
    source_url = "https://fireworks.ai/pricing"

    # (모델, 입력가, 출력가, 컨텍스트) — USD / 1M tokens
    FALLBACK = [
        ("llama-v4-scout", 0.2, 0.2, 1048576),
        ("llama-v4-maverick", 0.2, 0.2, 1048576),
        ("deepseek-v3", 0.9, 0.9, 131072),
        ("deepseek-r1", 3.0, 8.0, 163840),
        ("qwen3-235b", 0.22, 0.88, 131072),
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
