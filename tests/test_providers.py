"""fixture 기반 파서 테스트 — 네트워크 호출 없이 _get을 monkeypatch한다."""

from __future__ import annotations

import json
import pathlib

import pytest

from scripts.fetch_prices import merge_results, run_provider
from scripts.models import PriceEntry, ProviderResult
from scripts.providers import PROVIDERS, get_all_providers
from scripts.providers.anthropic import AnthropicProvider
from scripts.providers.deepseek import DeepSeekProvider
from scripts.providers.fireworks import FireworksProvider
from scripts.providers.google import GoogleProvider
from scripts.providers.groq import GroqProvider
from scripts.providers.mimo import MimoProvider
from scripts.providers.mistral import MistralProvider
from scripts.providers.openai import OpenAIProvider
from scripts.providers.openrouter import OpenRouterProvider
from scripts.providers.together import TogetherProvider

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class FakeResponse:
    """httpx.Response 대역 — .text/.json()/raise_for_status만 제공."""

    def __init__(self, text: str) -> None:
        self._text = text

    @property
    def text(self) -> str:
        return self._text

    def json(self) -> object:
        return json.loads(self._text)

    def raise_for_status(self) -> None:
        return None


def _build(cls, fixture_name: str, monkeypatch):
    """provider 인스턴스를 만들고 _get을 fixture 반환으로 교체."""
    content = (FIXTURES / fixture_name).read_text(encoding="utf-8")
    provider = cls(client=None)
    monkeypatch.setattr(provider, "_get", lambda url, **kw: FakeResponse(content))
    return provider


# (provider 클래스, fixture 파일, 기대 모델 수, {모델: (입력, 출력, 컨텍스트)})
CASES = [
    (OpenAIProvider, "openai.html", 4, {"gpt-4o": (2.5, 10.0, 128000)}),
    (AnthropicProvider, "anthropic.html", 2, {"claude-sonnet-4": (3.0, 15.0, 200000)}),
    (GoogleProvider, "google.html", 2, {"gemini-2.5-pro": (1.25, 10.0, 1000000)}),
    (DeepSeekProvider, "deepseek.html", 2, {"deepseek-chat": (0.27, 1.10, 64000)}),
    (MistralProvider, "mistral.html", 2, {"mistral-large-latest": (2.0, 6.0, 128000)}),
    (FireworksProvider, "fireworks.html", 3, {"llama-v4-maverick": (0.22, 0.88, 1000000)}),
    (GroqProvider, "groq.html", 2, {"llama-3.3-70b-versatile": (0.59, 0.79, 128000)}),
    (OpenRouterProvider, "openrouter.json", 3, {"openai/gpt-4o": (2.5, 10.0, 128000)}),
    (TogetherProvider, "together.json", 2, {"deepseek-ai/DeepSeek-V3": (1.25, 1.25, 131072)}),
    (MimoProvider, "mimo.json", 3, {"mimo-v2.5": (0.3, 1.2, 65536)}),
]


@pytest.mark.parametrize("cls, fixture, count, expected", CASES, ids=[c[0].name for c in CASES])
def test_parser_returns_normalized_entries(cls, fixture, count, expected, monkeypatch):
    provider = _build(cls, fixture, monkeypatch)
    entries = provider.fetch()

    assert len(entries) == count
    assert all(isinstance(e, PriceEntry) for e in entries)
    for e in entries:
        assert e.provider == cls.name
        assert e.currency == "USD"
        assert e.fetched_at
        assert e.source_url == cls.source_url
        assert e.input_per_1m >= 0 and e.output_per_1m >= 0
        assert e.context_window >= 0

    by_model = {e.model: e for e in entries}
    for model, (inp, out, ctx) in expected.items():
        assert model in by_model, f"{model} 누락"
        e = by_model[model]
        assert e.input_per_1m == pytest.approx(inp)
        assert e.output_per_1m == pytest.approx(out)
        assert e.context_window == ctx


def test_openrouter_skips_free_model(monkeypatch):
    provider = _build(OpenRouterProvider, "openrouter.json", monkeypatch)
    models = {e.model for e in provider.fetch()}
    assert "openrouter/free-model" not in models


def test_together_skips_embeddings(monkeypatch):
    provider = _build(TogetherProvider, "together.json", monkeypatch)
    models = {e.model for e in provider.fetch()}
    assert "BAAI/bge-large-en-v1.5" not in models


def test_mimo_normalizes_per_1k(monkeypatch):
    provider = _build(MimoProvider, "mimo.json", monkeypatch)
    entries = provider.fetch()
    # fixture는 per_1k_tokens → ×1000 정규화 + notes 표기
    assert all(e.notes for e in entries)


def test_registry_has_ten_providers():
    assert len(PROVIDERS) == 10
    assert len(get_all_providers()) == 10


def test_run_provider_isolates_failure():
    class Boom(OpenAIProvider):
        name = "boom"

        def fetch(self):
            raise RuntimeError("network down")

    result = run_provider(Boom, client=None)
    assert result.ok is False
    assert result.error and "network down" in result.error
    assert result.entries == []


def test_merge_results_keeps_previous_on_failure():
    entry = PriceEntry(
        provider="openai",
        model="gpt-4o",
        input_per_1m=2.5,
        output_per_1m=10.0,
        context_window=128000,
        source_url="https://example.com",
        fetched_at="2026-05-29T00:00:00Z",
    )
    previous = {"providers": {"groq": [entry.to_dict()]}}
    results = [
        ProviderResult(provider="openai", entries=[entry], ok=True),
        ProviderResult(provider="groq", entries=[], ok=False, error="boom"),
    ]
    merged = merge_results(results, previous)
    # 성공분은 갱신, 실패분(groq)은 previous 유지
    assert len(merged["providers"]["openai"]) == 1
    assert merged["providers"]["groq"] == previous["providers"]["groq"]
    assert merged["schema_version"] == 1


def test_merge_results_empty_when_failure_and_no_previous():
    results = [ProviderResult(provider="groq", entries=[], ok=False, error="x")]
    merged = merge_results(results, None)
    assert merged["providers"]["groq"] == []
