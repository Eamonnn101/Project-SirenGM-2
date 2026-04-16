"""LLM client protocol. Providers implement complete() and complete_structured()."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class LLMResponse:
    text: str
    tag: str | None = None  # provider-specific call tag for debugging


class LLMClient(Protocol):
    name: str

    def complete(self, messages: list[LLMMessage], *, tag: str | None = None) -> LLMResponse:
        """Plain text completion."""
        ...

    def complete_structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        tag: str | None = None,
    ) -> T:
        """Completion validated against a Pydantic schema. Raises on repeated failure."""
        ...
