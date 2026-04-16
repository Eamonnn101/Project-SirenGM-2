"""Structured patch contract between the state-updater LLM and the save store.

The LLM emits a `StatePatch` after every turn. `apply_patch` validates each
sub-patch semantically (entity slugs must exist in the stacked pack unless
flagged emergent) and mutates a Save in place. Failures do **not** corrupt
state: the invalid sub-patch is skipped and a DivergenceNote is appended.

Canonical-state-wins rule lives here: if the narrator claims something the
state updater can't express, the updater logs a divergence rather than
silently accepting narrative facts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sirengm.pack.stacked import StackedPack
from sirengm.save.models import (
    ActiveThread,
    DivergenceNote,
    InventoryItem,
    OpenLoop,
    Relationship,
    RiskLevel,
    Save,
    SessionLogEntry,
)


# --- Patch sub-types -------------------------------------------------------


class WorldStatePatch(BaseModel):
    """Partial update to WorldState. Omitted fields mean 'leave unchanged'."""

    model_config = ConfigDict(extra="forbid")

    advance_turn: bool = Field(
        default=True,
        description="If true (default), WorldState.turn += 1 after apply. The LLM should usually not override.",
    )
    day: int | None = None
    time_of_day: Literal["dawn", "morning", "noon", "afternoon", "dusk", "night", "midnight"] | None = None
    current_location: str | None = None
    present_entities: list[str] | None = Field(
        default=None,
        description="If provided, replaces the full list. Prefer full replacement for clarity.",
    )
    current_objectives: list[str] | None = None
    risk_level: RiskLevel | None = None
    flags_set: dict[str, str | int | bool] = Field(default_factory=dict)
    flags_unset: list[str] = Field(default_factory=list)


class PlayerStatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cultivation_stage: str | None = None
    status: Literal["alive", "injured", "unconscious", "dead"] | None = None
    inventory_add: list[InventoryItem] = Field(default_factory=list)
    inventory_remove: list[str] = Field(default_factory=list, description="Inventory slugs to drop.")
    titles_add: list[str] = Field(default_factory=list)


class RelationshipDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    affinity_delta: int = 0
    trust_delta: int = 0
    status: str | None = None
    notes: str | None = None


class ActiveThreadChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    op: Literal["add", "remove", "update"]
    thread: ActiveThread


class StatePatch(BaseModel):
    """Top-level patch emitted by the state-updater LLM."""

    model_config = ConfigDict(extra="forbid")

    world: WorldStatePatch = Field(default_factory=WorldStatePatch)
    player: PlayerStatePatch | None = None
    relationships: dict[str, RelationshipDelta] = Field(default_factory=dict)
    open_loops_add: list[OpenLoop] = Field(default_factory=list)
    open_loops_close: list[str] = Field(default_factory=list, description="IDs of loops to close.")
    active_thread_changes: list[ActiveThreadChange] = Field(default_factory=list)
    session_log_entry: SessionLogEntry
    divergences: list[DivergenceNote] = Field(default_factory=list)
    hidden_truths_append: str | None = None


# --- Apply -----------------------------------------------------------------


def apply_patch(save: Save, patch: StatePatch, pack: StackedPack) -> list[DivergenceNote]:
    """Mutate `save` in place. Returns a list of divergence notes produced while applying.

    Invariants:
        - Never raises for semantic issues; logs a divergence and skips the sub-patch.
        - Always appends the session_log entry (it's the canonical record of the turn).
        - Turn counter advances at the end (unless advance_turn=False).
    """
    divergences: list[DivergenceNote] = list(patch.divergences)
    known_slugs = pack.all_entity_slugs()

    # --- World state ---
    wp = patch.world
    if wp.current_location is not None:
        if _entity_exists_or_emergent(wp.current_location, known_slugs, save):
            save.world.current_location = wp.current_location
        else:
            divergences.append(DivergenceNote(
                turn=save.world.turn,
                reason="current_location references unknown slug",
                detail=f"slug={wp.current_location!r}; not in stacked pack and not marked emergent",
            ))
    if wp.present_entities is not None:
        sanitized: list[str] = []
        for slug in wp.present_entities:
            if _entity_exists_or_emergent(slug, known_slugs, save):
                sanitized.append(slug)
            else:
                divergences.append(DivergenceNote(
                    turn=save.world.turn,
                    reason="present_entities contains unknown slug",
                    detail=f"slug={slug!r}; dropped from present_entities",
                ))
        save.world.present_entities = sanitized
    if wp.day is not None:
        save.world.day = wp.day
    if wp.time_of_day is not None:
        save.world.time_of_day = wp.time_of_day
    if wp.current_objectives is not None:
        save.world.current_objectives = list(wp.current_objectives)
    if wp.risk_level is not None:
        save.world.risk_level = wp.risk_level
    for k, v in wp.flags_set.items():
        save.world.flags[k] = v
    for k in wp.flags_unset:
        save.world.flags.pop(k, None)

    # --- Player state ---
    if patch.player is not None:
        pp = patch.player
        if pp.cultivation_stage is not None:
            save.world.player.cultivation_stage = pp.cultivation_stage
        if pp.status is not None:
            save.world.player.status = pp.status
        for item in pp.inventory_add:
            save.world.player.inventory.append(item)
        if pp.inventory_remove:
            keep = [i for i in save.world.player.inventory if i.slug not in pp.inventory_remove]
            save.world.player.inventory = keep
        for t in pp.titles_add:
            if t not in save.world.player.titles:
                save.world.player.titles.append(t)

    # --- Relationships ---
    for slug, delta in patch.relationships.items():
        if slug not in known_slugs and not _has_emergent_slug(slug, save):
            divergences.append(DivergenceNote(
                turn=save.world.turn,
                reason="relationship update on unknown slug",
                detail=f"slug={slug!r}; skipped",
            ))
            continue
        rel = save.relationships.by_slug.setdefault(slug, Relationship())
        rel.affinity += delta.affinity_delta
        rel.trust += delta.trust_delta
        if delta.status is not None:
            # Leave status type widening to caller's schema; store string.
            rel.status = delta.status  # type: ignore[assignment]
        if delta.notes is not None:
            rel.notes = delta.notes
        rel.last_interaction_turn = save.world.turn

    # --- Open loops ---
    existing_ids = {l.id for l in save.open_loops.items}
    for loop in patch.open_loops_add:
        if loop.id in existing_ids:
            divergences.append(DivergenceNote(
                turn=save.world.turn,
                reason="duplicate open_loop id",
                detail=f"id={loop.id!r}; skipped",
            ))
            continue
        save.open_loops.items.append(loop)
        existing_ids.add(loop.id)
    for loop_id in patch.open_loops_close:
        found = next((l for l in save.open_loops.items if l.id == loop_id), None)
        if found is None:
            divergences.append(DivergenceNote(
                turn=save.world.turn,
                reason="close on unknown open_loop id",
                detail=f"id={loop_id!r}; skipped",
            ))
            continue
        if found.status == "closed":
            continue
        found.status = "closed"
        found.closed_turn = save.world.turn

    # --- Active threads ---
    for chg in patch.active_thread_changes:
        if chg.op == "add":
            if any(t.id == chg.thread.id for t in save.world.active_threads):
                divergences.append(DivergenceNote(
                    turn=save.world.turn,
                    reason="duplicate active_thread id",
                    detail=f"id={chg.thread.id!r}; skipped add",
                ))
                continue
            save.world.active_threads.append(chg.thread)
        elif chg.op == "remove":
            save.world.active_threads = [t for t in save.world.active_threads if t.id != chg.thread.id]
        elif chg.op == "update":
            for i, t in enumerate(save.world.active_threads):
                if t.id == chg.thread.id:
                    save.world.active_threads[i] = chg.thread
                    break

    # --- Session log (always written; canonical per-turn record) ---
    save.session_log.append(patch.session_log_entry)

    # --- Hidden truths append ---
    if patch.hidden_truths_append:
        addition = patch.hidden_truths_append.strip()
        if addition:
            save.hidden_truths = (save.hidden_truths.rstrip() + "\n\n" + addition + "\n").lstrip()

    # --- Divergences into the save record itself ---
    save.divergences.extend(divergences)

    # --- Advance turn ---
    if patch.world.advance_turn:
        save.world.turn += 1

    return divergences


# --- Helpers ---------------------------------------------------------------


def _entity_exists_or_emergent(slug: str, known: set[str], save: Save) -> bool:
    if slug in known:
        return True
    return _has_emergent_slug(slug, save)


def _has_emergent_slug(slug: str, save: Save) -> bool:
    """Slugs prefixed `emergent:` or explicitly declared in hidden_truths."""
    if slug.startswith("emergent:"):
        return True
    # Lightweight check: the hidden_truths file can declare `- origin: emergent slug=foo`
    # and we trust it. This is by design lenient — divergences catch real mistakes.
    return f"emergent slug={slug}" in save.hidden_truths
