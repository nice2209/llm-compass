"""DeepSeek 가격 파서 — HTML 스크래핑 우선, 실패 시 검증된 fallback."""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import (
    BaseProvider,
    fixed_entries,
    html_table_entries,
    usable,
)


class DeepSeekProvider(BaseProvider):
    name = "deepseek"
    source_url = "https://api-docs.deepseek.com/quick_start/pricing"

    # (모델, 입력가, 출력가, 컨텍스트) — USD / 1M tokens
    # deepseek-chat=V3, deepseek-reasoner=R1 (공식 API 모델명)
    FALLBACK = [
        ("deepseek-chat", 0.27, 1.1, 65536),
        ("deepseek-reasoner", 0.55, 2.19, 65536),
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
