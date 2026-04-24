"""Compact, read-only summary of a save's canonical state.

Usage:
    python tools/inspect_save.py --save <pack>/<save_id>

The `--save` argument is resolved as `saves_root / <arg>`; the
canonical layout is `saves/<pack>/<save_id>/`.

Prints turn/day/location/risk, player status, present entities,
active threads, objectives, open loops (count + titles), last
narration preview, and divergence count. Output is plain text, one
save per invocation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _hud import hud_labels, render_full_build_hud
    from render_save import _read_pack_language, load_meta_progress, load_save
else:
    from ._hud import hud_labels, render_full_build_hud
    from .render_save import _read_pack_language, load_meta_progress, load_save


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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--save", required=True, help="path under saves/, typically <pack>/<save_id>")
    p.add_argument("--saves-root", type=Path, default=Path("saves"))
    p.add_argument("--packs-root", type=Path, default=Path("packs"))
    args = p.parse_args(argv)
    save_dir = args.saves_root / args.save
    if not save_dir.is_dir():
        print(f"error: save dir not found: {save_dir}", file=sys.stderr)
        return 2
    save = load_save(save_dir)
    language = _read_pack_language(args.packs_root, save.pack_name)
    sys.stdout.write(format_summary(save, save_dir=save_dir, language=language))
    return 0


if __name__ == "__main__":
    sys.exit(main())
