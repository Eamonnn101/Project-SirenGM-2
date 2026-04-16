"""Deterministic mock LLM client for tests and offline demos.

Responses are scripted by `tag` (the caller tags each call site) or by a fallback
callable that inspects the messages. Structured responses are validated through
the target Pydantic model before being returned, exactly like real clients.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from sirengm.llm.base import LLMMessage, LLMResponse

T = TypeVar("T", bound=BaseModel)

Responder = Callable[[list[LLMMessage]], str]


class MockProvider:
    """Scripted LLM.

    `scripts` maps a call tag -> either a literal string response or a Responder
    callable. `fallback` handles un-tagged calls. Unmatched calls raise so tests
    fail loudly instead of silently returning empty strings.
    """

    name = "mock"

    def __init__(
        self,
        scripts: dict[str, str | Responder] | None = None,
        fallback: Responder | None = None,
    ) -> None:
        self._scripts: dict[str, str | Responder] = dict(scripts or {})
        self._fallback = fallback
        self.calls: list[tuple[str | None, list[LLMMessage]]] = []

    def set(self, tag: str, response: str | Responder) -> None:
        self._scripts[tag] = response

    def _resolve(self, tag: str | None, messages: list[LLMMessage]) -> str:
        self.calls.append((tag, messages))
        if tag and tag in self._scripts:
            resolver = self._scripts[tag]
            return resolver(messages) if callable(resolver) else resolver
        if self._fallback is not None:
            return self._fallback(messages)
        raise LookupError(
            f"MockProvider has no script for tag={tag!r}; "
            f"set one via MockProvider(scripts=...) or .set(tag, response)."
        )

    def complete(self, messages: list[LLMMessage], *, tag: str | None = None) -> LLMResponse:
        return LLMResponse(text=self._resolve(tag, messages), tag=tag)

    def complete_structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        tag: str | None = None,
    ) -> T:
        raw = self._resolve(tag, messages)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"MockProvider[{tag}] produced non-JSON: {raw[:200]!r}") from e
        try:
            return schema.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"MockProvider[{tag}] JSON failed {schema.__name__} validation: {e}") from e
