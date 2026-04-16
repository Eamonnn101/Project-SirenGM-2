"""Re-render markdown surfaces of a save from its JSON state.

Usage:
    python tools/render_save.py --save <save_id>

Reads the authoritative JSON files under saves/<save_id>/
(`world_state.json`, `relationship_state.json`, `open_loops.json`,
`meta.json`, `session_log.jsonl`, `divergences.jsonl`) and overwrites the
markdown surfaces (`current_scene.md`, `player.md`, `session_log.md`,
`hidden_truths.md`) plus `session_log.jsonl` re-normalized.

These markdown surfaces are display-only. JSON wins if the two disagree.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _models import (
        DivergenceNote,
        OpenLoops,
        RelationshipState,
        Save,
        SessionLogEntry,
        WorldState,
    )
else:
    from ._models import (
        DivergenceNote,
        OpenLoops,
        RelationshipState,
        Save,
        SessionLogEntry,
        WorldState,
    )


# ---------------------------------------------------------------------------
# Save loader
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_save(save_dir: Path) -> Save:
    meta = _read_json(save_dir / "meta.json")
    world = WorldState(**_read_json(save_dir / "world_state.json"))
    relationships = (
        RelationshipState(**_read_json(save_dir / "relationship_state.json"))
        if (save_dir / "relationship_state.json").is_file()
        else RelationshipState()
    )
    open_loops = (
        OpenLoops(**_read_json(save_dir / "open_loops.json"))
        if (save_dir / "open_loops.json").is_file()
        else OpenLoops()
    )
    session_log = [
        SessionLogEntry(**row) for row in _read_jsonl(save_dir / "session_log.jsonl")
    ]
    divergences = [
        DivergenceNote(**row) for row in _read_jsonl(save_dir / "divergences.jsonl")
    ]
    return Save(
        save_id=meta["save_id"],
        pack_name=meta["pack_name"],
        world=world,
        relationships=relationships,
        open_loops=open_loops,
        session_log=session_log,
        divergences=divergences,
        hidden_truths=meta.get("hidden_truths", ""),
    )


# ---------------------------------------------------------------------------
# Rendering (ported from sirengm/save/render.py)
# ---------------------------------------------------------------------------

def render_all(save_dir: Path, save: Save) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "current_scene.md").write_text(render_current_scene(save), encoding="utf-8")
    (save_dir / "player.md").write_text(render_player_md(save), encoding="utf-8")
    session_md, session_jsonl = render_session_log(save)
    (save_dir / "session_log.md").write_text(session_md, encoding="utf-8")
    (save_dir / "session_log.jsonl").write_text(session_jsonl, encoding="utf-8")
    hidden = save.hidden_truths.strip()
    (save_dir / "hidden_truths.md").write_text(
        ("# Hidden Truths\n\n" + hidden + "\n") if hidden else "# Hidden Truths\n\n(empty)\n",
        encoding="utf-8",
    )


def render_current_scene(save: Save) -> str:
    w = save.world
    lines: list[str] = [
        "---",
        f"turn: {w.turn}",
        f"day: {w.day}",
        f"time_of_day: {w.time_of_day}",
        f"location: {w.current_location}",
        f"risk_level: {w.risk_level}",
        "---",
        "",
        "# Current Scene",
        "",
        f"- **Turn**: {w.turn} · Day {w.day} · {w.time_of_day}",
        f"- **Location**: `{w.current_location}`",
        f"- **Risk**: {w.risk_level}",
    ]
    if w.present_entities:
        lines.append("- **Present**: " + ", ".join(f"`{s}`" for s in w.present_entities))
    if w.active_threads:
        lines.append("- **Active threads**:")
        for t in w.active_threads:
            lines.append(f"  - `{t.id}` · {t.title} ({t.priority})")
    if w.current_objectives:
        lines.append("- **Objectives**:")
        for o in w.current_objectives:
            lines.append(f"  - {o}")
    if save.session_log:
        last = save.session_log[-1]
        lines += ["", "## Last narration", "", last.narration.strip(), ""]
    else:
        lines += ["", "_(no narration yet)_", ""]
    return "\n".join(lines) + "\n"


def render_player_md(save: Save) -> str:
    p = save.world.player
    lines = [
        "---",
        f"slug: {p.slug}",
        f"name: {p.name}",
        f"cultivation_stage: {p.cultivation_stage}",
        f"status: {p.status}",
    ]
    if p.sect:
        lines.append(f"sect: {p.sect}")
    lines += ["---", "", f"# {p.name}", ""]
    lines.append(f"- 修为：**{p.cultivation_stage}**")
    lines.append(f"- 状态：{p.status}")
    if p.sect:
        lines.append(f"- 宗门：{p.sect}")
    if p.titles:
        lines.append(f"- 称号：{', '.join(p.titles)}")
    if p.inventory:
        lines.append("- 物品：")
        for item in p.inventory:
            note = f" — {item.notes}" if item.notes else ""
            lines.append(f"  - {item.name} (`{item.slug}`){note}")
    return "\n".join(lines) + "\n"


def render_session_log(save: Save) -> tuple[str, str]:
    """Return (markdown, jsonl) for the session log.

    The jsonl is the canonical re-loadable form; the markdown is human-readable.
    """
    md_lines = ["# Session Log", ""]
    jsonl_lines: list[str] = []
    for entry in save.session_log:
        md_lines.append(f"## turn {entry.turn} · {entry.at.isoformat(timespec='seconds')}")
        md_lines.append("")
        md_lines.append("**玩家**: " + entry.player_input.strip())
        md_lines.append("")
        md_lines.append(entry.narration.strip())
        if entry.summary:
            md_lines.append("")
            md_lines.append(f"> _{entry.summary}_")
        md_lines.append("")
        jsonl_lines.append(_entry_to_json(entry))
    return (
        "\n".join(md_lines).rstrip() + "\n",
        "\n".join(jsonl_lines) + ("\n" if jsonl_lines else ""),
    )


def _entry_to_json(entry: SessionLogEntry) -> str:
    return entry.model_dump_json()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Re-render markdown surfaces of a save from its JSON state.")
    p.add_argument("--save", required=True, help="save id under saves/")
    p.add_argument("--saves-root", type=Path, default=Path("saves"))
    args = p.parse_args(argv)
    save_dir = args.saves_root / args.save
    if not save_dir.is_dir():
        print(f"error: save dir not found: {save_dir}", file=sys.stderr)
        return 2
    save = load_save(save_dir)
    render_all(save_dir, save)
    print(f"re-rendered markdown surfaces for {save_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
