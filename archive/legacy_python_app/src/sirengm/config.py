"""Runtime configuration: resolve project root, LLM provider, and API credentials."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def project_root() -> Path:
    env_root = os.environ.get("SIRENGM_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return Path.cwd().resolve()


@dataclass(frozen=True)
class AppConfig:
    root: Path
    provider: str
    anthropic_api_key: str | None
    anthropic_model: str

    @property
    def packs_dir(self) -> Path:
        return self.root / "packs"

    @property
    def saves_dir(self) -> Path:
        return self.root / "saves"

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"


def load_config() -> AppConfig:
    provider = os.environ.get("SIRENGM_PROVIDER", "").strip().lower()
    if not provider:
        provider = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "mock"
    return AppConfig(
        root=project_root(),
        provider=provider,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
        anthropic_model=os.environ.get("SIRENGM_ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    )
