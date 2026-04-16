"""Canonical directory and filename conventions for a Story Pack."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Entity subdirectories and the category they represent.
ENTITY_DIRS: dict[str, str] = {
    "characters": "character",
    "factions": "faction",
    "locations": "location",
    "systems": "system",
    "arcs": "arc",
    "events": "event",
}

# Top-level single-file pages with stable names.
META_FILES: tuple[str, ...] = (
    "index.md",
    "overview.md",
    "style_guide.md",
    "canon_guardrails.md",
    "timeline.md",
)

RELATIONSHIP_FILE = "relationships/relationship_matrix.md"
AMBIGUITIES_FILE = "contradictions/ambiguous_points.md"


@dataclass(frozen=True)
class PackPaths:
    root: Path

    @property
    def index(self) -> Path:
        return self.root / "index.md"

    @property
    def overview(self) -> Path:
        return self.root / "overview.md"

    @property
    def style_guide(self) -> Path:
        return self.root / "style_guide.md"

    @property
    def canon_guardrails(self) -> Path:
        return self.root / "canon_guardrails.md"

    @property
    def timeline(self) -> Path:
        return self.root / "timeline.md"

    @property
    def relationships(self) -> Path:
        return self.root / RELATIONSHIP_FILE

    @property
    def ambiguities(self) -> Path:
        return self.root / AMBIGUITIES_FILE

    def entity_dir(self, category_plural: str) -> Path:
        return self.root / category_plural
