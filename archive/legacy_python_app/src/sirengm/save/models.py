"""Save-file Pydantic models.

**Canonical state lives in JSON, not in markdown.** These models define the
load-bearing per-run state. Markdown surfaces (current_scene.md,
session_log.md, etc.) are re-rendered from these objects on every successful
patch and have no authority.

The explicit required fields on `WorldState` (current_location, present_entities,
active_threads, current_objectives, risk_level) are the scene-context primitive
that the runtime context builder queries directly — never by scraping markdown.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["calm", "tense", "dangerous", "lethal"]
RelationshipStatus = Literal["unknown", "acquainted", "friendly", "close", "trusted", "hostile", "enemy"]
OpenLoopStatus = Literal["open", "closed", "abandoned"]


class InventoryItem(BaseModel):
    """An item in the player's possession. Free-form; no numeric stats."""

    model_config = ConfigDict(extra="forbid")
    slug: str
    name: str
    notes: str | None = None


class PlayerState(BaseModel):
    """Player-character canonical state."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., description="Matches the protagonist entity slug in the user pack.")
    name: str
    sect: str | None = None
    cultivation_stage: str = "气感期一层"
    status: Literal["alive", "injured", "unconscious", "dead"] = "alive"
    inventory: list[InventoryItem] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)


class ActiveThread(BaseModel):
    """An active plotline currently shaping the scene."""

    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    priority: Literal["background", "active", "urgent"] = "active"


class WorldState(BaseModel):
    """Canonical world state. All runtime scene context derives from this.

    The explicit fields (current_location, present_entities, active_threads,
    current_objectives, risk_level) are required. Context builders must read
    these and must NOT scrape markdown surfaces.
    """

    model_config = ConfigDict(extra="forbid")

    turn: int = 0
    day: int = 0
    time_of_day: Literal["dawn", "morning", "noon", "afternoon", "dusk", "night", "midnight"] = "morning"

    current_location: str = Field(..., description="Slug in the stacked pack (or emergent id recorded in hidden_truths.md).")
    present_entities: list[str] = Field(
        default_factory=list,
        description="Entity slugs currently in scene. Used directly by the context builder.",
    )
    active_threads: list[ActiveThread] = Field(default_factory=list)
    current_objectives: list[str] = Field(
        default_factory=list,
        description="Short objective strings that the GM should keep live.",
    )
    risk_level: RiskLevel = "calm"

    player: PlayerState
    flags: dict[str, str | int | bool] = Field(default_factory=dict)


class Relationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    affinity: int = Field(default=0, description="Integer scale, typically -5..+5.")
    trust: int = Field(default=0, description="Integer scale, typically 0..+5.")
    status: RelationshipStatus = "unknown"
    last_interaction_turn: int | None = None
    notes: str | None = None


class RelationshipState(BaseModel):
    """Per-NPC dynamic relationships, keyed by entity slug."""

    model_config = ConfigDict(extra="forbid")
    by_slug: dict[str, Relationship] = Field(default_factory=dict)


class OpenLoop(BaseModel):
    """A plot hook that's been opened and awaits closure."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source_arc: str | None = None
    status: OpenLoopStatus = "open"
    opened_turn: int
    closed_turn: int | None = None
    notes: str | None = None


class OpenLoops(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[OpenLoop] = Field(default_factory=list)


class SessionLogEntry(BaseModel):
    """One turn's structured record. session_log.md is re-rendered from these."""

    model_config = ConfigDict(extra="forbid")
    turn: int
    at: datetime = Field(default_factory=datetime.utcnow)
    player_input: str
    narration: str
    summary: str = Field(default="", description="One-line summary of what changed.")


class DivergenceNote(BaseModel):
    """A record of something the updater rejected, or a soft-failure during apply."""

    model_config = ConfigDict(extra="forbid")
    turn: int
    at: datetime = Field(default_factory=datetime.utcnow)
    reason: str
    detail: str | None = None


class Save(BaseModel):
    """All per-run canonical state, in one aggregate."""

    model_config = ConfigDict(extra="forbid")

    save_id: str
    pack_name: str = Field(..., description="User pack this save plays against.")
    world: WorldState
    relationships: RelationshipState = Field(default_factory=RelationshipState)
    open_loops: OpenLoops = Field(default_factory=OpenLoops)
    session_log: list[SessionLogEntry] = Field(default_factory=list)
    divergences: list[DivergenceNote] = Field(default_factory=list)
    hidden_truths: str = Field(default="", description="GM-only facts, free-form markdown.")
