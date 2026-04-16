"""Phase 1 smoke tests: package imports, CLI instantiates, MockProvider works."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from sirengm.cli import app
from sirengm.config import AppConfig
from sirengm.llm.base import LLMMessage
from sirengm.llm.mock_client import MockProvider


class _Echo(BaseModel):
    said: str


def test_package_imports() -> None:
    import sirengm

    assert sirengm.__version__


def test_cli_registers_commands() -> None:
    names = {(cmd.name or cmd.callback.__name__.replace("_cmd", "").replace("_", "-")) for cmd in app.registered_commands}
    assert {"new-game", "play", "load", "inspect", "ingest", "lint-pack", "lint-save", "version"} <= names


def test_mock_provider_text(mock_llm: MockProvider) -> None:
    mock_llm.set("greet", "hi there")
    out = mock_llm.complete([LLMMessage(role="user", content="hello")], tag="greet")
    assert out.text == "hi there"
    assert out.tag == "greet"


def test_mock_provider_structured(mock_llm: MockProvider) -> None:
    mock_llm.set("echo", json.dumps({"said": "hello"}))
    out = mock_llm.complete_structured([LLMMessage(role="user", content="x")], _Echo, tag="echo")
    assert out == _Echo(said="hello")


def test_mock_provider_rejects_unknown_tag(mock_llm: MockProvider) -> None:
    with pytest.raises(LookupError):
        mock_llm.complete([LLMMessage(role="user", content="x")], tag="missing")


def test_tmp_config_fixture_shape(tmp_config: AppConfig) -> None:
    assert tmp_config.provider == "mock"
    assert tmp_config.packs_dir.is_dir()
    assert tmp_config.saves_dir.is_dir()
