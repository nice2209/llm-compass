"""Mistral AI 가격 파서 — HTML 스크래핑 우선, 실패 시 검증된 fallback."""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import (
    BaseProvider,
    fixed_entries,
    html_table_entries,
    usable,
)


class MistralProvider(BaseProvider):
    name = "mistral"
    source_url = "https://mistral.ai/pricing#api-pricing"

    # (모델, 입력가, 출력가, 컨텍스트) — USD / 1M tokens (공식 API 모델명)
    FALLBACK = [
        ("mistral-large-latest", 2.0, 6.0, 131072),
        ("mistral-small-latest", 0.2, 0.6, 32768),
        ("open-mistral-nemo", 0.15, 0.15, 131072),
        ("codestral-latest", 0.3, 0.9, 262144),
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
