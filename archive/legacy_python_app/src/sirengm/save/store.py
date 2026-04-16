"""Save persistence: create/load/save a directory under saves/.

Layout on disk::

    saves/<save_id>/
      world_state.json           canonical
      relationship_state.json    canonical
      open_loops.json            canonical
      player.json                canonical (mirrored in WorldState.player for convenience)
      session_log.md             re-rendered narrative
      current_scene.md           re-rendered narrative
      player.md                  re-rendered narrative
      divergence_log.md          append-only log of rejected patches
      hidden_truths.md           GM-only facts (markdown, append-only)
      meta.json                  {save_id, pack_name}
"""

from __future__ import annotations

import json
from pathlib import Path

from sirengm.save.models import (
    DivergenceNote,
    OpenLoops,
    PlayerState,
    RelationshipState,
    Save,
    SessionLogEntry,
    WorldState,
)


def save_dir(saves_root: Path, save_id: str) -> Path:
    return saves_root / save_id


def new_save(
    saves_root: Path,
    *,
    save_id: str,
    pack_name: str,
    player: PlayerState,
    starting_location: str,
    starting_entities: list[str] | None = None,
    starting_objective: str | None = None,
) -> Save:
    """Build an initial Save and persist it. Caller passes player/scene basics."""
    world = WorldState(
        turn=0,
        day=0,
        current_location=starting_location,
        present_entities=list(starting_entities or []),
        current_objectives=[starting_objective] if starting_objective else [],
        risk_level="calm",
        player=player,
    )
    save = Save(save_id=save_id, pack_name=pack_name, world=world)
    persist(saves_root, save)
    return save


def persist(saves_root: Path, save: Save) -> None:
    """Write all canonical JSON files. Markdown surfaces are rendered separately."""
    d = save_dir(saves_root, save.save_id)
    d.mkdir(parents=True, exist_ok=True)
    _write_json(d / "world_state.json", save.world)
    _write_json(d / "relationship_state.json", save.relationships)
    _write_json(d / "open_loops.json", save.open_loops)
    _write_json(d / "player.json", save.world.player)
    _write_json(d / "meta.json", {"save_id": save.save_id, "pack_name": save.pack_name})


def load_save(saves_root: Path, save_id: str) -> Save:
    d = save_dir(saves_root, save_id)
    if not d.is_dir():
        raise FileNotFoundError(f"Save not found: {d}")
    meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    world = WorldState.model_validate_json((d / "world_state.json").read_text(encoding="utf-8"))
    relationships = RelationshipState.model_validate_json((d / "relationship_state.json").read_text(encoding="utf-8"))
    open_loops = OpenLoops.model_validate_json((d / "open_loops.json").read_text(encoding="utf-8"))

    session_log = _read_session_log(d / "session_log.md")
    divergences = _read_divergences(d / "divergence_log.md")
    hidden_truths = (d / "hidden_truths.md").read_text(encoding="utf-8") if (d / "hidden_truths.md").is_file() else ""

    return Save(
        save_id=meta["save_id"],
        pack_name=meta["pack_name"],
        world=world,
        relationships=relationships,
        open_loops=open_loops,
        session_log=session_log,
        divergences=divergences,
        hidden_truths=hidden_truths,
    )


def append_divergence(saves_root: Path, save_id: str, note: DivergenceNote) -> None:
    """Append-only write to divergence_log.md. Safe to call even mid-turn."""
    d = save_dir(saves_root, save_id)
    d.mkdir(parents=True, exist_ok=True)
    log = d / "divergence_log.md"
    new_block = _format_divergence(note)
    if log.is_file():
        existing = log.read_text(encoding="utf-8")
        log.write_text(existing.rstrip() + "\n\n" + new_block + "\n", encoding="utf-8")
    else:
        log.write_text("# Divergence Log\n\n" + new_block + "\n", encoding="utf-8")


def _write_json(path: Path, obj) -> None:
    if hasattr(obj, "model_dump_json"):
        path.write_text(obj.model_dump_json(indent=2) + "\n", encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_session_log(path: Path) -> list[SessionLogEntry]:
    """Read the session log via a sidecar JSON; the .md is display-only.

    We keep a sidecar `session_log.jsonl` next to the rendered markdown so we
    don't have to parse markdown back. The markdown is written by render.py.
    """
    jsonl = path.with_suffix(".jsonl")
    if not jsonl.is_file():
        return []
    entries: list[SessionLogEntry] = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(SessionLogEntry.model_validate_json(line))
    return entries


def _read_divergences(path: Path) -> list[DivergenceNote]:
    """Divergences are append-only markdown with a sidecar jsonl for round-trip."""
    jsonl = path.with_suffix(".jsonl")
    if not jsonl.is_file():
        return []
    notes: list[DivergenceNote] = []
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if line.strip():
            notes.append(DivergenceNote.model_validate_json(line))
    return notes


def _format_divergence(note: DivergenceNote) -> str:
    detail = f"\n\n> {note.detail}" if note.detail else ""
    return f"## turn {note.turn} · {note.at.isoformat(timespec='seconds')}\n\n{note.reason}{detail}"
