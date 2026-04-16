"""Smoke tests for the CLI entry point and the Anthropic client factory."""

from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

from sirengm.cli import app
from sirengm.config import AppConfig
from sirengm.llm.factory import build_client
from sirengm.llm.mock_client import MockProvider


def test_cli_help_exits_zero() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "play" in result.stdout
    assert "lint-pack" in result.stdout


def test_cli_version_prints_provider_info(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SIRENGM_PROVIDER", raising=False)
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "sirengm" in result.stdout
    assert "provider" in result.stdout


def test_factory_builds_mock_when_unconfigured(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg = AppConfig(root=tmp_path, provider="mock", anthropic_api_key=None, anthropic_model="claude-sonnet-4-6")
    client = build_client(cfg)
    assert isinstance(client, MockProvider)


def test_factory_requires_api_key_for_anthropic(tmp_path) -> None:
    cfg = AppConfig(root=tmp_path, provider="anthropic", anthropic_api_key=None, anthropic_model="claude-sonnet-4-6")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        build_client(cfg)


def test_factory_builds_anthropic_with_key(tmp_path) -> None:
    cfg = AppConfig(
        root=tmp_path,
        provider="anthropic",
        anthropic_api_key="sk-dummy",
        anthropic_model="claude-sonnet-4-6",
    )
    # Construction should succeed (makes no network call).
    client = build_client(cfg)
    assert client.name == "anthropic"
