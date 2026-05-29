"""Groq 가격 파서 — HTML 스크래핑 우선, 실패 시 검증된 fallback."""

from __future__ import annotations

from scripts.models import PriceEntry
from scripts.providers.base import (
    BaseProvider,
    fixed_entries,
    html_table_entries,
    usable,
)


class GroqProvider(BaseProvider):
    name = "groq"
    source_url = "https://groq.com/pricing/"

    # (모델, 입력가, 출력가, 컨텍스트) — USD / 1M tokens (Groq 공개 가격)
    FALLBACK = [
        ("llama-3.3-70b-versatile", 0.59, 0.79, 131072),
        ("llama-3.1-8b-instant", 0.05, 0.08, 131072),
        ("llama3-70b-8192", 0.59, 0.79, 8192),
        ("llama3-8b-8192", 0.05, 0.08, 8192),
        ("gemma2-9b-it", 0.20, 0.20, 8192),
        ("deepseek-r1-distill-llama-70b", 0.75, 0.99, 131072),
        ("qwen-2.5-32b", 0.29, 0.39, 131072),
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
