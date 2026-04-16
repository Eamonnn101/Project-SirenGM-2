"""Canonical Pydantic schemas for SirenGM 2 save state and pack entities.

Kept in sync with the shapes the agent writes under saves/<id>/ and
packs/<name>/. Imported by tools/lint_pack.py, tools/render_save.py,
tools/inspect_save.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ---------------------------------------------------------------------------
# Save-state models (ported from sirengm/save/models.py)
# ---------------------------------------------------------------------------

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
    status: Literal["alive", "injured", "unconscious", "dead", "missing", "unknown"] = "alive"
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
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    player_input: str
    narration: str
    summary: str = Field(default="", description="One-line summary of what changed.")


class DivergenceNote(BaseModel):
    """A record of something the updater rejected, or a soft-failure during apply."""

    model_config = ConfigDict(extra="forbid")
    turn: int
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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


# ---------------------------------------------------------------------------
# Pack models (ported from sirengm/pack/models.py)
# ---------------------------------------------------------------------------

EntityCategory = Literal["character", "faction", "location", "system", "arc", "event"]
PackKind = Literal["genre", "user"]


class PageBase(BaseModel):
    """Envelope common to every page type: slug, body, and pass-through extras."""

    model_config = ConfigDict(extra="allow")

    slug: str = Field(..., description="Unique snake_case id within its category.")
    name: str = Field(..., description="Display name.")
    body: str = Field("", description="Markdown prose body (after frontmatter).")


class CharacterPage(PageBase):
    category: Literal["character"] = "character"
    aliases: list[str] = Field(default_factory=list)
    role: str | None = Field(default=None, description="Free-form role label: protagonist, master, rival, ...")
    sect: str | None = Field(default=None, description="Slug of affiliated faction, if any.")
    cultivation_stage: str | None = None
    status: Literal["alive", "injured", "unconscious", "dead", "missing", "unknown"] = "alive"
    location: str | None = Field(default=None, description="Slug of a location page, if resident.")


class FactionPage(PageBase):
    category: Literal["faction"] = "faction"
    alignment: str | None = None
    seat: str | None = Field(default=None, description="Slug of a location page.")
    leaders: list[str] = Field(default_factory=list)


class LocationPage(PageBase):
    category: Literal["location"] = "location"
    region: str | None = None
    controlled_by: str | None = Field(default=None, description="Faction slug.")
    danger: Literal["safe", "guarded", "hostile", "deadly"] = "safe"


class SystemPage(PageBase):
    category: Literal["system"] = "system"
    kind: str | None = Field(default=None, description="e.g. cultivation, items, social_rules.")


class ArcPage(PageBase):
    category: Literal["arc"] = "arc"
    summary: str = ""
    status: Literal["opening", "active", "suspended", "closed"] = "opening"
    driving_entities: list[str] = Field(default_factory=list)


class EventPage(PageBase):
    category: Literal["event"] = "event"
    kind: Literal["key", "triggerable", "dangerous_divergence"] = "key"
    preconditions: list[str] = Field(default_factory=list)


class MetaPage(BaseModel):
    """A top-level reference page (index.md, overview.md, etc.) with optional frontmatter."""

    model_config = ConfigDict(extra="allow")

    name: str
    body: str = ""


class Pack(BaseModel):
    """A fully loaded Story Pack (either a genre template or a user pack)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Pack directory name.")
    kind: PackKind = Field(..., description="'genre' for reusable templates; 'user' for novel-generated packs.")
    inherits_genre: str | None = Field(
        default=None,
        description="Required for user packs: the genre pack name to stack against. Must be None for genre packs.",
    )

    # Top-level meta pages
    index: MetaPage | None = None
    overview: MetaPage | None = None
    style_guide: MetaPage | None = None
    canon_guardrails: MetaPage | None = None
    timeline: MetaPage | None = None
    relationships: MetaPage | None = None
    ambiguities: MetaPage | None = None

    # Entity pages (user packs only; genre packs forbid these)
    characters: list[CharacterPage] = Field(default_factory=list)
    factions: list[FactionPage] = Field(default_factory=list)
    locations: list[LocationPage] = Field(default_factory=list)
    systems: list[SystemPage] = Field(default_factory=list)
    arcs: list[ArcPage] = Field(default_factory=list)
    events: list[EventPage] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_kind_rules(self) -> "Pack":
        if self.kind == "genre":
            if self.inherits_genre is not None:
                raise ValueError("genre packs must not declare inherits_genre")
            # Systems are genre-level mechanics (cultivation, social_rules) and are permitted.
            # Characters, factions, locations, arcs, events are novel-specific and forbidden.
            if any((self.characters, self.factions, self.locations, self.arcs, self.events)):
                raise ValueError(
                    "genre packs must not contain novel-specific entity pages "
                    "(characters/factions/locations/arcs/events). "
                    "Those belong in a user pack generated by ingest."
                )
        else:  # user
            if not self.inherits_genre:
                raise ValueError("user packs must declare inherits_genre in their index.md frontmatter")
        return self

    def find_entity(self, slug: str) -> PageBase | None:
        """Look up any entity by slug across all categories."""
        for bucket in (self.characters, self.factions, self.locations, self.systems, self.arcs, self.events):
            for page in bucket:
                if page.slug == slug:
                    return page
        return None

    def all_entity_slugs(self) -> set[str]:
        slugs: set[str] = set()
        for bucket in (self.characters, self.factions, self.locations, self.systems, self.arcs, self.events):
            slugs.update(p.slug for p in bucket)
        return slugs
