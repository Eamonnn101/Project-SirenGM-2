"""Re-render markdown surfaces of a save from its JSON state.

Usage:
    python tools/render_save.py --save <pack>/<save_id>

The `--save` argument is resolved as `saves_root / <arg>`, so the
canonical layout is `saves/<pack>/<save_id>/`. A bare `<save_id>`
(legacy flat layout) still works if that directory exists.

Reads the authoritative JSON files under the save dir
(`world_state.json`, `relationship_state.json`, `open_loops.json`,
`meta.json`, `session_log.jsonl`, `divergences.jsonl`) and overwrites
the markdown surfaces (`current_scene.md`, `player.md`,
`session_log.md`, `hidden_truths.md`) plus `session_log.jsonl`
re-normalized.

Labels in the rendered surfaces are picked from a per-language dictionary
keyed by the pack's declared `language` (from `packs/<pack>/index.md`).
Only `zh` and `en` are supported; when the language is missing or the
save has no resolvable pack, rendering defaults to `zh`.

These markdown surfaces are display-only. JSON wins if the two disagree.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import frontmatter

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _models import (
        DivergenceNote,
        OpenLoops,
        PackMetaProgress,
        RelationshipState,
        Save,
        SessionLogEntry,
        WorldState,
    )
    from _hud import (
        hud_labels,
        render_compact_turn_hud,
        render_full_build_hud,
    )
else:
    from ._models import (
        DivergenceNote,
        OpenLoops,
        PackMetaProgress,
        RelationshipState,
        Save,
        SessionLogEntry,
        WorldState,
    )
    from ._hud import (
        hud_labels,
        render_compact_turn_hud,
        render_full_build_hud,
    )


# ---------------------------------------------------------------------------
# Localized labels. Only 'zh' and 'en' are supported; 'zh' is the default.
# ---------------------------------------------------------------------------

LABELS: dict[str, dict[str, str]] = {
    "zh": {
        "current_scene": "当前场景",
        "turn": "回合",
        "day": "天",
        "location": "地点",
        "risk": "风险",
        "present": "在场",
        "active_threads": "活跃线索",
        "objectives": "目标",
        "last_narration": "最近叙事",
        "no_narration": "（暂无叙事）",
        "player_progression": "修为",
        "player_affiliation": "所属",
        "player_status": "状态",
        "player_titles": "称号",
        "player_inventory": "物品",
        "session_log": "本局日志",
        "turn_label": "回合",
        "player_input": "玩家",
        "options": "选项",
        "hidden_truths": "暗线",
        "hidden_truths_empty": "（暂无）",
        "current_conflict": "当前冲突",
        "conflict_stake": "争点",
        "conflict_kind": "类型",
        "conflict_momentum": "势头",
        "conflict_sides": "各方",
        "conflict_side_want": "想要",
        "conflict_side_paid": "付出",
        "conflict_side_members": "成员",
        "conflict_escalation": "升级要点",
        "last_conflict": "上一场冲突",
        "last_conflict_outcome": "结果",
        "last_conflict_resolved_at": "结束于回合",
        "conflict_momentum_endgame": "收束在即",
    },
    "en": {
        "current_scene": "Current Scene",
        "turn": "Turn",
        "day": "Day",
        "location": "Location",
        "risk": "Risk",
        "present": "Present",
        "active_threads": "Active threads",
        "objectives": "Objectives",
        "last_narration": "Last narration",
        "no_narration": "(no narration yet)",
        "player_progression": "Progression",
        "player_affiliation": "Affiliation",
        "player_status": "Status",
        "player_titles": "Titles",
        "player_inventory": "Inventory",
        "session_log": "Session Log",
        "turn_label": "turn",
        "player_input": "Player",
        "options": "Options",
        "hidden_truths": "Hidden Truths",
        "hidden_truths_empty": "(empty)",
        "current_conflict": "Current Conflict",
        "conflict_stake": "Stake",
        "conflict_kind": "Kind",
        "conflict_momentum": "Momentum",
        "conflict_sides": "Sides",
        "conflict_side_want": "wants",
        "conflict_side_paid": "paid",
        "conflict_side_members": "members",
        "conflict_escalation": "Escalation beats",
        "last_conflict": "Last Conflict",
        "last_conflict_outcome": "Outcome",
        "last_conflict_resolved_at": "Resolved on turn",
        "conflict_momentum_endgame": "Endgame",
    },
}


def _labels_for(language: str | None) -> dict[str, str]:
    return LABELS.get(language or "zh", LABELS["zh"])


def _read_pack_language(packs_root: Path, pack_name: str) -> str | None:
    """Read `language` from `packs/<pack_name>/index.md` frontmatter. None if unavailable."""
    index_path = packs_root / pack_name / "index.md"
    if not index_path.is_file():
        return None
    try:
        post = frontmatter.load(index_path)
    except Exception:
        return None
    lang = post.metadata.get("language")
    return str(lang) if lang else None


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
# Rendering
# ---------------------------------------------------------------------------

def load_meta_progress(save_dir: Path) -> PackMetaProgress | None:
    """Load `saves/<pack>/meta_progress.json` if present.

    `save_dir` is the per-save directory; the meta lives in its parent
    (`saves/<pack>/`). Returns None when the file is missing.
    """
    meta_path = save_dir.parent / "meta_progress.json"
    if not meta_path.is_file():
        return None
    try:
        return PackMetaProgress(**json.loads(meta_path.read_text(encoding="utf-8")))
    except Exception:
        return None


def render_all(save_dir: Path, save: Save, *, language: str | None) -> None:
    L = _labels_for(language)
    HL = hud_labels(language)
    meta = load_meta_progress(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "current_scene.md").write_text(
        render_current_scene(save, L, HL), encoding="utf-8"
    )
    (save_dir / "player.md").write_text(
        render_player_md(save, L, HL, meta), encoding="utf-8"
    )
    session_md, session_jsonl = render_session_log(save, L)
    (save_dir / "session_log.md").write_text(session_md, encoding="utf-8")
    (save_dir / "session_log.jsonl").write_text(session_jsonl, encoding="utf-8")
    hidden = save.hidden_truths.strip()
    hidden_body = hidden if hidden else L["hidden_truths_empty"]
    (save_dir / "hidden_truths.md").write_text(
        f"# {L['hidden_truths']}\n\n{hidden_body}\n",
        encoding="utf-8",
    )


def render_current_scene(save: Save, L: dict[str, str], HL: dict[str, str]) -> str:
    w = save.world
    compact_hud = render_compact_turn_hud(save, HL)
    lines: list[str] = [
        "---",
        f"turn: {w.turn}",
        f"day: {w.day}",
        f"time_of_day: {w.time_of_day}",
        f"location: {w.current_location}",
        f"risk_level: {w.risk_level}",
        "---",
        "",
        compact_hud,
        "",
        f"# {L['current_scene']}",
        "",
        f"- **{L['turn']}**: {w.turn} · {L['day']} {w.day} · {w.time_of_day}",
        f"- **{L['location']}**: `{w.current_location}`",
        f"- **{L['risk']}**: {w.risk_level}",
    ]
    if w.present_entities:
        lines.append(f"- **{L['present']}**: " + ", ".join(f"`{s}`" for s in w.present_entities))
    if w.active_threads:
        lines.append(f"- **{L['active_threads']}**:")
        for t in w.active_threads:
            lines.append(f"  - `{t.id}` · {t.title} ({t.priority})")
    if w.current_objectives:
        lines.append(f"- **{L['objectives']}**:")
        for o in w.current_objectives:
            lines.append(f"  - {o}")
    if w.current_conflict is not None:
        lines += _render_conflict_block(w.current_conflict, L, w.turn)
    elif w.last_conflict_summary is not None:
        lines += _render_last_conflict_block(w.last_conflict_summary, L)
    if save.session_log:
        last = save.session_log[-1]
        lines += ["", f"## {L['last_narration']}", "", last.narration.strip(), ""]
    else:
        lines += ["", f"_{L['no_narration']}_", ""]
    return "\n".join(lines) + "\n"


def _render_conflict_block(conflict, L: dict[str, str], current_turn: int) -> list[str]:
    lines: list[str] = ["", f"## {L['current_conflict']}", ""]
    lines.append(f"- **{L['conflict_stake']}**: {conflict.stake}")
    lines.append(f"- **{L['conflict_kind']}**: {conflict.kind}")
    if conflict.is_endgame(current_turn):
        momentum_display = L["conflict_momentum_endgame"]
    else:
        momentum_display = conflict.momentum
    lines.append(f"- **{L['conflict_momentum']}**: {momentum_display}")
    lines.append(f"- **{L['conflict_sides']}**:")
    for side in conflict.sides:
        paid = ", ".join(side.paid) if side.paid else "—"
        members = ", ".join(f"`{m}`" for m in side.members) if side.members else "—"
        lines.append(
            f"  - `{side.label}` · {L['conflict_side_want']}: {side.want} · "
            f"{L['conflict_side_paid']}: {paid}"
        )
        lines.append(f"    {L['conflict_side_members']}: {members}")
    if conflict.escalation_notes:
        lines.append(f"- **{L['conflict_escalation']}**:")
        for note in conflict.escalation_notes:
            lines.append(f"  - {note}")
    return lines


def _render_last_conflict_block(summary, L: dict[str, str]) -> list[str]:
    lines: list[str] = ["", f"## {L['last_conflict']}", ""]
    lines.append(f"- **{L['conflict_kind']}**: {summary.kind}")
    lines.append(f"- **{L['conflict_stake']}**: {summary.stake}")
    lines.append(f"- **{L['last_conflict_outcome']}**: {summary.outcome}")
    lines.append(f"- **{L['conflict_momentum']}**: {summary.momentum_final}")
    lines.append(f"- **{L['last_conflict_resolved_at']}**: {summary.resolved_turn}")
    return lines


def render_player_md(
    save: Save,
    L: dict[str, str],
    HL: dict[str, str],
    meta: PackMetaProgress | None,
) -> str:
    """Render `player.md` as the full build HUD (Layer B)."""
    p = save.world.player
    fm_lines = [
        "---",
        f"slug: {p.slug}",
        f"name: {p.name}",
        f"status: {p.status}",
        f"stage_index: {p.stage_index}",
        f"health_state: {p.health_state}",
    ]
    if p.stage_label:
        fm_lines.append(f"stage_label: {p.stage_label}")
    if p.progression:
        fm_lines.append(f"progression: {p.progression}")
    if p.affiliation:
        fm_lines.append(f"affiliation: {p.affiliation}")
    fm_lines += ["---", ""]

    body = render_full_build_hud(save, HL, meta=meta)
    return "\n".join(fm_lines) + "\n```\n" + body + "\n```\n"


def render_session_log(save: Save, L: dict[str, str]) -> tuple[str, str]:
    """Return (markdown, jsonl) for the session log.

    The jsonl is the canonical re-loadable form; the markdown is human-readable.
    """
    md_lines = [f"# {L['session_log']}", ""]
    jsonl_lines: list[str] = []
    for entry in save.session_log:
        md_lines.append(f"## {L['turn_label']} {entry.turn} · {entry.at.isoformat(timespec='seconds')}")
        md_lines.append("")
        md_lines.append(f"**{L['player_input']}**: " + entry.player_input.strip())
        md_lines.append("")
        md_lines.append(entry.narration.strip())
        if entry.options:
            md_lines.append("")
            md_lines.append(f"**{L['options']}**")
            md_lines.append("")
            for opt in entry.options:
                md_lines.append(f"- {opt.strip()}")
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
    render_all(save_dir, save, language=language)
    print(f"re-rendered markdown surfaces for {save_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
