"""공용 데이터 모델 — 전 Phase가 공유하는 가격 표현."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class PriceEntry:
    """단일 모델의 정규화된 가격. 통화는 항상 USD / 1M tokens."""

    provider: str
    model: str
    input_per_1m: float
    output_per_1m: float
    context_window: int
    source_url: str
    fetched_at: str  # ISO8601 UTC
    currency: str = "USD"
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProviderResult:
    """한 provider 크롤링 결과. ok=False면 entries는 무시하고 previous를 유지한다."""

    provider: str
    entries: list[PriceEntry] = field(default_factory=list)
    ok: bool = True
    error: Optional[str] = None
