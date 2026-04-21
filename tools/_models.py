"""Canonical Pydantic schemas for SirenGM 2 save state and pack entities.

Kept in sync with the shapes the agent writes under
saves/<pack>/<save_id>/ and packs/<pack>/. Imported by
tools/lint_pack.py, tools/render_save.py, tools/inspect_save.py.
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
ConflictMomentum = Literal[
    "setup",
    "player_pressing",
    "even",
    "opposition_pressing",
    "reversal_imminent",
]


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
    affiliation: str | None = Field(default=None, description="Slug of an affiliated faction, if any.")
    progression: str | None = Field(
        default=None,
        description="Free-form progression label, e.g. '筑基中期', 'Lieutenant', 'Level 12 Ranger'.",
    )
    status: Literal["alive", "injured", "unconscious", "dead", "missing", "unknown"] = "alive"
    inventory: list[InventoryItem] = Field(default_factory=list)
    titles: list[str] = Field(default_factory=list)
    stats: dict[str, str] = Field(
        default_factory=dict,
        description="Novel-specific attributes the renderer surfaces verbatim.",
    )


class ActiveThread(BaseModel):
    """An active plotline currently shaping the scene."""

    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    priority: Literal["background", "active", "urgent"] = "active"


class ConflictSide(BaseModel):
    """One party in a conflict frame."""

    model_config = ConfigDict(extra="forbid")
    label: str = Field(..., description="Display name for this side, e.g. '玩家方', '叛军'.")
    members: list[str] = Field(
        default_factory=list,
        description="Entity slugs aligned with this side. 'player' is reserved for the PC.",
    )
    want: str = Field(..., description="One-line description of this side's goal.")
    paid: list[str] = Field(
        default_factory=list,
        description="Short descriptions of costs this side has already absorbed.",
    )


class ConflictFrame(BaseModel):
    """A scene of tension tracked by the conflict engine.

    Cross-genre: `kind` is free-form (combat, debate, chase, trial, ...).
    Momentum is a discrete label, never a number — consistent with the
    no-numeric-combat-stats guardrail.

    `beat_budget` is the initial pacing budget set at conflict_open and
    never changes thereafter. Remaining beats are derived from the
    current world turn via `beats_remaining`.
    """

    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., description="Free-form id, e.g. 'c_bianlun_01'.")
    kind: str = Field(..., description="Free-form conflict kind the GM chose for this scene.")
    stake: str = Field(..., description="One-line 'what both sides are fighting over'.")
    sides: list[ConflictSide] = Field(..., description="Two or more parties with opposing wants.")
    momentum: ConflictMomentum = "setup"
    escalation_notes: list[str] = Field(default_factory=list)
    opened_turn: int
    beat_budget: int = Field(
        default=4,
        ge=3,
        le=6,
        description=(
            "Initial pacing budget set at conflict_open. "
            "Remaining beats = beat_budget - (current_turn - opened_turn). "
            "Lint warns when remaining drops below -1."
        ),
    )

    @model_validator(mode="after")
    def _validate_sides(self) -> "ConflictFrame":
        if len(self.sides) < 2:
            raise ValueError("ConflictFrame.sides must have at least 2 entries")
        labels = [s.label for s in self.sides]
        if len(set(labels)) != len(labels):
            raise ValueError(f"ConflictFrame.sides has duplicate labels: {labels}")
        return self

    def beats_remaining(self, current_turn: int) -> int:
        """Beats left before budget is exhausted. Can go negative on overshoot."""
        return self.beat_budget - (current_turn - self.opened_turn)

    def is_endgame(self, current_turn: int) -> bool:
        """True when the HUD should display endgame; i.e. remaining <= 1."""
        return self.beats_remaining(current_turn) <= 1


class ConflictSummary(BaseModel):
    """Compact trace of the most recently resolved conflict.

    Written by `conflict_resolve` alongside clearing `current_conflict`.
    Overwritten by the next resolve — only the most recent conflict is
    retained. Rendered in `current_scene.md` as a "last conflict" block
    so the post-resolution state doesn't feel empty to the player.
    """

    model_config = ConfigDict(extra="forbid")
    id: str
    kind: str
    stake: str
    outcome: str = Field(..., description="One-line summary of how the conflict ended.")
    momentum_final: ConflictMomentum
    resolved_turn: int


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
    current_conflict: ConflictFrame | None = Field(
        default=None,
        description="Active conflict frame, if a scene of tension is live. Null when not in conflict.",
    )
    last_conflict_summary: ConflictSummary | None = Field(
        default=None,
        description="Trace of the most recently resolved conflict. Cleared to null only by a new conflict_open; overwritten by the next resolve.",
    )

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
    options: list[str] = Field(
        default_factory=list,
        description="The four option strings (A/B/C/D) the GM showed the player this turn, verbatim.",
    )
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
    role: str | None = Field(default=None, description="Free-form role label: protagonist, mentor, rival, ...")
    affiliation: str | None = Field(default=None, description="Slug of an affiliated faction, if any.")
    progression: str | None = Field(
        default=None,
        description="Free-form progression label whose space is defined in the novel's novel_rules.md.",
    )
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
    flexibility: Literal["soft", "hard"] = Field(
        default="soft",
        description="'soft' arcs may be sidelined by player agency; 'hard' arcs are canon.",
    )


class EventPage(PageBase):
    category: Literal["event"] = "event"
    kind: Literal["intended", "triggerable", "player_boundary"] = "intended"
    preconditions: list[str] = Field(default_factory=list)
    can_skip: bool | None = Field(
        default=None,
        description=(
            "Skippability override. When omitted, defaults by kind: True for "
            "intended/triggerable, False for player_boundary. Set explicitly to override."
        ),
    )

    @model_validator(mode="after")
    def _default_can_skip_by_kind(self) -> "EventPage":
        if self.can_skip is None:
            self.can_skip = self.kind != "player_boundary"
        return self


class MetaPage(BaseModel):
    """A top-level reference page (index.md, overview.md, etc.) with optional frontmatter."""

    model_config = ConfigDict(extra="allow")

    name: str
    body: str = ""


class Pack(BaseModel):
    """A fully loaded Story Pack (either the universal genre template or a user pack)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Pack directory name.")
    kind: PackKind = Field(..., description="'genre' for the shipped universal template; 'user' for novel-generated packs.")
    inherits_genre: str | None = Field(
        default=None,
        description="Required for user packs (typically 'universal'). Must be None for genre packs.",
    )
    language: Literal["zh", "en"] | None = Field(
        default=None,
        description="User-pack language. Must be 'zh' or 'en'; required on user packs, None on genre packs.",
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
            # The universal genre pack is language-agnostic by design; per-novel
            # language lives on user packs.
            # Systems are optional genre-level mechanics and are permitted.
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
            if not self.language:
                raise ValueError("user packs must declare language in their index.md frontmatter")
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
