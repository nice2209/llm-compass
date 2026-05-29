"""OpenRouter 가격 파서 — 공식 JSON API.

pricing.prompt/completion은 토큰당 USD(문자열)이므로 ×1e6으로 1M 단위 정규화.
"""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import BaseProvider, now_iso


class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    source_url = "https://openrouter.ai/api/v1/models"

    def fetch(self) -> list[PriceEntry]:
        data = self._get(self.source_url).json().get("data", [])
        fetched = now_iso()
        entries: list[PriceEntry] = []
        for m in data:
            pricing = m.get("pricing") or {}
            input_per_1m = float(pricing.get("prompt", 0) or 0) * 1_000_000
            output_per_1m = float(pricing.get("completion", 0) or 0) * 1_000_000
            if input_per_1m <= 0 and output_per_1m <= 0:
                continue  # 무료/플레이스홀더 모델 제외
            entries.append(
                PriceEntry(
                    provider=self.name,
                    model=m["id"],
                    input_per_1m=round(input_per_1m, 6),
                    output_per_1m=round(output_per_1m, 6),
                    context_window=int(m.get("context_length") or 0),
                    source_url=self.source_url,
                    fetched_at=fetched,
                )
            )
        return entries
