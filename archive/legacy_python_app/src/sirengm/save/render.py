"""Re-render markdown surfaces of a save from its canonical structured state.

These files are **not authoritative**. They exist for human inspection and
for GM prompt context. Every successful patch triggers a full re-render so
structured state and markdown never drift.
"""

from __future__ import annotations

from pathlib import Path

from sirengm.save.models import Save, SessionLogEntry
from sirengm.save.store import save_dir


def render_all(saves_root: Path, save: Save) -> None:
    d = save_dir(saves_root, save.save_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "current_scene.md").write_text(render_current_scene(save), encoding="utf-8")
    (d / "player.md").write_text(render_player_md(save), encoding="utf-8")
    session_md, session_jsonl = render_session_log(save)
    (d / "session_log.md").write_text(session_md, encoding="utf-8")
    (d / "session_log.jsonl").write_text(session_jsonl, encoding="utf-8")
    hidden = save.hidden_truths.strip()
    (d / "hidden_truths.md").write_text(
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
    return "\n".join(md_lines).rstrip() + "\n", "\n".join(jsonl_lines) + ("\n" if jsonl_lines else "")


def _entry_to_json(entry: SessionLogEntry) -> str:
    return entry.model_dump_json()
