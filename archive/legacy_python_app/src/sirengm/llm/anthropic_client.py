"""Anthropic (Claude) client. Default provider in the MVP.

Minimal wrapper: one `messages.create` call per complete(). Structured output is
obtained by appending a JSON-only instruction and validating the response.
Prompt caching is applied to the system prompt when the caller passes one.
"""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from sirengm.llm.base import LLMMessage, LLMResponse

T = TypeVar("T", bound=BaseModel)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class AnthropicClient:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as e:  # pragma: no cover - dependency is declared
            raise RuntimeError(
                "The 'anthropic' package is required for the Anthropic provider."
            ) from e
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def _split(self, messages: list[LLMMessage]) -> tuple[str | None, list[dict]]:
        system: str | None = None
        convo: list[dict] = []
        for m in messages:
            if m.role == "system":
                system = (system + "\n\n" + m.content) if system else m.content
            else:
                convo.append({"role": m.role, "content": m.content})
        return system, convo

    def _call(self, messages: list[LLMMessage]) -> str:
        system, convo = self._split(messages)
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": convo or [{"role": "user", "content": "continue"}],
        }
        if system:
            kwargs["system"] = [
                {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
            ]
        resp = self._client.messages.create(**kwargs)
        parts: list[str] = []
        for block in resp.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts)

    def complete(self, messages: list[LLMMessage], *, tag: str | None = None) -> LLMResponse:
        return LLMResponse(text=self._call(messages), tag=tag)

    def complete_structured(
        self,
        messages: list[LLMMessage],
        schema: type[T],
        *,
        tag: str | None = None,
    ) -> T:
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        nudged = list(messages) + [
            LLMMessage(
                role="user",
                content=(
                    "Reply with a single JSON object matching this schema. "
                    "Emit ONLY JSON, no prose, no code fence.\n\nSchema:\n" + schema_hint
                ),
            )
        ]
        raw = self._call(nudged)
        data = _parse_json(raw)
        try:
            return schema.model_validate(data)
        except ValidationError as e:
            raise ValueError(
                f"Anthropic[{tag}] JSON failed {schema.__name__} validation: {e}"
            ) from e


def _parse_json(raw: str) -> object:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]) if len(lines) >= 2 else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_BLOCK_RE.search(raw)
        if not m:
            raise
        return json.loads(m.group(0))
