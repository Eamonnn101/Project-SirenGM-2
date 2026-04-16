"""Resolve an LLMClient instance from AppConfig."""

from __future__ import annotations

from sirengm.config import AppConfig
from sirengm.llm.base import LLMClient
from sirengm.llm.mock_client import MockProvider


def build_client(config: AppConfig) -> LLMClient:
    provider = config.provider
    if provider == "mock":
        return MockProvider()
    if provider == "anthropic":
        if not config.anthropic_api_key:
            raise RuntimeError(
                "SIRENGM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set."
            )
        from sirengm.llm.anthropic_client import AnthropicClient

        return AnthropicClient(
            api_key=config.anthropic_api_key,
            model=config.anthropic_model,
        )
    raise ValueError(f"Unknown provider: {provider!r}")
