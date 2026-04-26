"""Compact, read-only summary of a save's canonical state.

Usage:
    python tools/inspect_save.py --save <pack>/<save_id>
    python tools/inspect_save.py --save <pack>/<save_id> --active-summary

The `--save` argument is resolved as `saves_root / <arg>`; the
canonical layout is `saves/<pack>/<save_id>/`.

Prints turn/day/location/risk, player status, present entities,
active threads, objectives, open loops (count + titles), and divergence
count. Output is plain text, one save per invocation.

With `--active-summary`, prints a compact recovery seed. It does not
read `session_log.jsonl`; use the rendered `session_log.md` file for
the latest ten detailed turns when recovering from lost context.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _hud import hud_labels, render_compact_turn_hud, render_full_build_hud
    from render_save import (
        CONTEXT_SUMMARY_FILENAME,
        CONTEXT_SUMMARY_ACTIVE_PREVIEW_CHARS,
        CONTEXT_SUMMARY_SOFT_CHARS,
        _read_pack_language,
        load_meta_progress,
        load_save,
    )
else:
    from ._hud import hud_labels, render_compact_turn_hud, render_full_build_hud
    from .render_save import (
        CONTEXT_SUMMARY_FILENAME,
        CONTEXT_SUMMARY_ACTIVE_PREVIEW_CHARS,
        CONTEXT_SUMMARY_SOFT_CHARS,
        _read_pack_language,
        load_meta_progress,
        load_save,
    )


def format_summary(save, *, save_dir: Path | None = None, language: str | None = None) -> str:
    """Compact terminal summary + full progression build HUD."""
    w = save.world
    p = w.player
    progression = f"  {p.progression}" if p.progression else ""
    affiliation = f"  affiliation={p.affiliation}" if p.affiliation else ""
    lines: list[str] = [
        f"save:     {save.save_id}",
        f"pack:     {save.pack_name}",
        f"turn:     {w.turn}   day: {w.day}   time: {w.time_of_day}   risk: {w.risk_level}",
        f"location: {w.current_location}",
        f"player:   {p.name} ({p.slug}){progression}  {p.status}{affiliation}",
        f"health:   {p.health_state}   stage: {p.stage_index}"
        + (f"  ({p.stage_label})" if p.stage_label else ""),
    ]
    if w.present_entities:
        lines.append("present:  " + ", ".join(w.present_entities))
    if w.active_threads:
        lines.append("threads:")
        for t in w.active_threads:
            lines.append(f"  - [{t.priority}] {t.id}: {t.title}")
    if w.current_objectives:
        lines.append("objectives:")
        for o in w.current_objectives:
            lines.append(f"  - {o}")
    open_items = [l for l in save.open_loops.items if l.status == "open"]
    if open_items:
        lines.append(f"open_loops ({len(open_items)}):")
        for l in open_items:
            lines.append(f"  - {l.id}: {l.title}")
    if save.session_log:
        last = save.session_log[-1]
        preview = last.narration.strip().splitlines()[0] if last.narration.strip() else ""
        lines.append(f"last turn {last.turn}: {preview[:80]}")
    if save.divergences:
        lines.append(f"divergences: {len(save.divergences)}")

    # Full progression build HUD (mirrors player.md layer B).
    meta = load_meta_progress(save_dir) if save_dir is not None else None
    HL = hud_labels(language)
    build = render_full_build_hud(save, HL, meta=meta)
    lines.append("")
    lines.append(build)
    return "\n".join(lines) + "\n"


def _format_artifact(player) -> str:
    artifact = player.artifact
    if artifact is None:
        return "none"
    status = " used" if artifact.used else ""
    return f"{artifact.name} [{artifact.archetype}{status}]"


def _format_traits(traits) -> str:
    if not traits:
        return "none"
    parts: list[str] = []
    for trait in traits:
        status = " exhausted" if trait.exhausted else ""
        parts.append(f"{trait.name} [{trait.archetype}{status}]")
    return ", ".join(parts)


def _format_conflict(world) -> str:
    conflict = world.current_conflict
    if conflict is None:
        return "none"
    remaining = conflict.beats_remaining(world.turn)
    return (
        f"{conflict.id} ({conflict.kind}) "
        f"momentum={conflict.momentum} "
        f"remaining={remaining} "
        f"stake={conflict.stake}"
    )


def _join_or_none(values: list[str]) -> str:
    return "; ".join(values) if values else "none"


def _read_context_summary(save_dir: Path | None) -> str:
    if save_dir is None:
        return "(not loaded)"
    path = save_dir / CONTEXT_SUMMARY_FILENAME
    if not path.is_file():
        return "(missing; create or update at the next backup)"
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return "(empty; update at the next backup)"
    if len(text) <= CONTEXT_SUMMARY_SOFT_CHARS:
        return text
    preview = text[:CONTEXT_SUMMARY_ACTIVE_PREVIEW_CHARS].rstrip()
    return (
        preview
        + "\n"
        + (
            f"(context_summary is {len(text)} chars; exceeds "
            f"{CONTEXT_SUMMARY_SOFT_CHARS}. 需在下一次 backup 先压缩旧记忆，"
            "再追加新关键节点。)"
        )
    )


def format_active_summary(save, *, save_dir: Path | None = None, language: str | None = None) -> str:
    """Compact recovery seed for diagnostics.

    `effective_turn` and `last_backup_turn` are equal because this tool
    reads only backup JSON. Ongoing play should normally continue from
    conversation context rather than this output.
    """
    w = save.world
    p = w.player
    HL = hud_labels(language)
    open_items = [loop for loop in save.open_loops.items if loop.status == "open"]
    stage = f"{p.stage_index}" + (f" ({p.stage_label})" if p.stage_label else "")
    affiliation = f" affiliation={p.affiliation}" if p.affiliation else ""
    lines: list[str] = [
        "Active State Summary",
        f"save: {save.save_id}",
        f"pack: {save.pack_name}",
        f"language: {language or 'unknown'}",
        f"effective_turn: {w.turn}",
        f"last_backup_turn: {w.turn}",
        f"hud: {render_compact_turn_hud(save, HL)}",
        f"scene: {w.current_location}",
        f"time: day {w.day} {w.time_of_day}",
        f"risk: {w.risk_level}",
        f"conflict: {_format_conflict(w)}",
        f"player: {p.name} ({p.slug}) status={p.status}{affiliation}",
        f"health: {p.health_state}",
        f"stage: {stage}",
        f"artifact: {_format_artifact(p)}",
        f"innate: {_format_traits(p.innate_traits)}",
        f"destiny: {_format_traits(p.destiny_traits)}",
        f"present: {', '.join(w.present_entities) if w.present_entities else 'none'}",
        "threads: "
        + _join_or_none(
            [
                f"{thread.priority} {thread.id} - {thread.title}"
                for thread in w.active_threads
            ]
        ),
        "objectives: " + _join_or_none(w.current_objectives),
        "open_loops: "
        + _join_or_none([f"{loop.id} - {loop.title}" for loop in open_items]),
        "context_summary:",
        _read_context_summary(save_dir),
        "recent_turns:",
        "read session_log.md for the latest ten detailed turns; "
        "do not read session_log.jsonl unless auditing the archive.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--save", required=True, help="path under saves/, typically <pack>/<save_id>")
    p.add_argument("--saves-root", type=Path, default=Path("saves"))
    p.add_argument("--packs-root", type=Path, default=Path("packs"))
    p.add_argument(
        "--active-summary",
        action="store_true",
        help="print a compact recovery seed (not for ordinary turn context)",
    )
    args = p.parse_args(argv)
    save_dir = args.saves_root / args.save
    if not save_dir.is_dir():
        print(f"error: save dir not found: {save_dir}", file=sys.stderr)
        return 2
    if args.active_summary:
        save = load_save(save_dir, session_log_limit=0)
        language = _read_pack_language(args.packs_root, save.pack_name)
        sys.stdout.write(format_active_summary(save, save_dir=save_dir, language=language))
        return 0
    save = load_save(save_dir, session_log_limit=0)
    language = _read_pack_language(args.packs_root, save.pack_name)
    sys.stdout.write(format_summary(save, save_dir=save_dir, language=language))
    return 0


if __name__ == "__main__":
    sys.exit(main())
