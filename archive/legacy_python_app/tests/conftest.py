"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from sirengm.config import AppConfig
from sirengm.llm.mock_client import MockProvider


@pytest.fixture
def mock_llm() -> MockProvider:
    return MockProvider()


@pytest.fixture
def tmp_config(tmp_path: Path) -> AppConfig:
    (tmp_path / "packs").mkdir()
    (tmp_path / "saves").mkdir()
    (tmp_path / "raw" / "novel").mkdir(parents=True)
    return AppConfig(
        root=tmp_path,
        provider="mock",
        anthropic_api_key=None,
        anthropic_model="claude-sonnet-4-6",
    )


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
