"""provider 레지스트리 — 새 provider 추가 시 PROVIDERS에만 등록하면 된다."""

from __future__ import annotations

from scripts.providers.anthropic import AnthropicProvider
from scripts.providers.base import BaseProvider
from scripts.providers.deepseek import DeepSeekProvider
from scripts.providers.fireworks import FireworksProvider
from scripts.providers.google import GoogleProvider
from scripts.providers.groq import GroqProvider
from scripts.providers.mimo import MimoProvider
from scripts.providers.mistral import MistralProvider
from scripts.providers.openai import OpenAIProvider
from scripts.providers.openrouter import OpenRouterProvider
from scripts.providers.together import TogetherProvider

PROVIDERS: dict[str, type[BaseProvider]] = {
    OpenAIProvider.name: OpenAIProvider,
    AnthropicProvider.name: AnthropicProvider,
    GoogleProvider.name: GoogleProvider,
    DeepSeekProvider.name: DeepSeekProvider,
    MistralProvider.name: MistralProvider,
    MimoProvider.name: MimoProvider,
    OpenRouterProvider.name: OpenRouterProvider,
    TogetherProvider.name: TogetherProvider,
    FireworksProvider.name: FireworksProvider,
    GroqProvider.name: GroqProvider,
}


def get_all_providers() -> list[type[BaseProvider]]:
    """등록된 모든 provider 클래스 목록."""
    return list(PROVIDERS.values())
