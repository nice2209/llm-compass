"""Together AI 가격 파서 — 공식 JSON API 우선, 실패 시 검증된 fallback.

pricing.input/output는 1M 토큰당 USD. 채팅 모델만 수집(임베딩 등 제외).
API가 인증 등으로 실패하면 FALLBACK 데이터를 반환한다.
"""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import BaseProvider, fixed_entries, now_iso, usable


class TogetherProvider(BaseProvider):
    name = "together"
    source_url = "https://api.together.xyz/v1/models"

    # (모델, 입력가, 출력가, 컨텍스트) — USD / 1M tokens (공식 모델 ID)
    FALLBACK = [
        ("meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8", 0.27, 0.85, 524288),
        ("meta-llama/Llama-4-Scout-17B-16E-Instruct", 0.18, 0.59, 327680),
        ("deepseek-ai/DeepSeek-V3", 1.25, 1.25, 131072),
        ("deepseek-ai/DeepSeek-R1", 3.0, 7.0, 163840),
        ("meta-llama/Llama-3.3-70B-Instruct-Turbo", 0.88, 0.88, 131072),
        ("Qwen/Qwen2.5-72B-Instruct-Turbo", 1.2, 1.2, 131072),
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
        data = self._get(self.source_url).json()
        fetched = now_iso()
        entries: list[PriceEntry] = []
        for m in data:
            if m.get("type") not in (None, "chat", "language"):
                continue  # 임베딩/이미지 등 비대화형 제외
            pricing = m.get("pricing") or {}
            input_per_1m = float(pricing.get("input", 0) or 0)
            output_per_1m = float(pricing.get("output", 0) or 0)
            if input_per_1m <= 0 and output_per_1m <= 0:
                continue
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
