"""Rule-based lint for a save directory.

Usage:
    python tools/lint_save.py --save <pack>/<save_id>

The `--save` argument is resolved as `saves_root / <arg>`; the
canonical layout is `saves/<pack>/<save_id>/`. A bare `<save_id>`
still works for legacy flat layouts.

Exits 0 when clean, 1 when issues are found, 2 on usage error.

Checks:
- Every canonical JSON file exists and parses.
- Pydantic models (`Save`, `WorldState`, `RelationshipState`, `OpenLoops`,
  `SessionLogEntry`, `DivergenceNote`) validate.
- `world_state.turn == len(session_log.jsonl)`.
- `player.json` equals `world_state.player`.
- `current_scene.md` frontmatter matches `world_state` (turn/day/time_of_day/
  location/risk_level). Drift means someone edited markdown without re-running
  `render_save.py`.
- `hidden_truths.md` body equals the render of `meta.json::hidden_truths`.
- If `--pack <name>` is given (or `meta.pack_name` resolves under
  `packs/`), every slug referenced in state (`current_location`,
  `present_entities`, `active_threads[*].id`, inventory, `relationships.by_slug`
  keys) either exists in the pack or starts with `emergent:`.
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
        PackMetaProgress,
        RelationshipState,
        SessionLogEntry,
        STAGE_INDEX_MAX,
        WorldState,
    )
    from _hud import hud_labels, render_compact_turn_hud
    from lint_pack import load_pack
    from render_save import (
        SESSION_LOG_DETAIL_LIMIT,
        _labels_for,
        _read_pack_language,
        load_meta_progress,
        load_save,
    )
else:
    from ._models import (
        DivergenceNote,
        OpenLoops,
        PackMetaProgress,
        RelationshipState,
        SessionLogEntry,
        STAGE_INDEX_MAX,
        WorldState,
    )
    from ._hud import hud_labels, render_compact_turn_hud
    from .lint_pack import load_pack
    from .render_save import (
        SESSION_LOG_DETAIL_LIMIT,
        _labels_for,
        _read_pack_language,
        load_meta_progress,
        load_save,
    )


def lint_save(save_dir: Path, *, packs_root: Path | None = None) -> list[str]:
    if not save_dir.is_dir():
        return [f"save dir not found: {save_dir}"]

    issues: list[str] = []

    # 1. JSON validity and Pydantic validation.
    try:
        save = load_save(save_dir)
    except Exception as e:
        return [f"failed to load save: {type(e).__name__}: {e}"]

    # 2. turn vs session_log length.
    if save.world.turn != len(save.session_log):
        issues.append(
            f"world_state.turn={save.world.turn} but session_log.jsonl has "
            f"{len(save.session_log)} entries (expected equal)"
        )

    # 3. player.json equals world_state.player.
    player_path = save_dir / "player.json"
    if player_path.is_file():
        try:
            on_disk = json.loads(player_path.read_text(encoding="utf-8"))
        except Exception as e:
            issues.append(f"player.json failed to parse: {type(e).__name__}: {e}")
        else:
            canonical = json.loads(save.world.player.model_dump_json())
            if on_disk != canonical:
                issues.append("player.json is out of sync with world_state.player")
    else:
        issues.append("player.json missing (should mirror world_state.player)")

    # 4. Rendered-surface drift: current_scene.md frontmatter vs world_state.
    issues.extend(_lint_current_scene_drift(save_dir, save))

    # 5. hidden_truths.md vs meta.json::hidden_truths, using the pack's language
    #    so a zh pack's localized "# 暗线 / （暂无）" render isn't flagged as drift.
    language = _read_pack_language(packs_root, save.pack_name) if packs_root else None
    issues.extend(_lint_hidden_truths(save_dir, save, _labels_for(language)))

    # 6. Slug existence (optional — only when pack is resolvable).
    pack = _resolve_pack(save, packs_root)
    if pack is not None:
        issues.extend(_lint_slugs(save, pack))
    elif packs_root is not None:
        issues.append(f"could not load pack {save.pack_name!r} under {packs_root}/ for slug check")

    # 7. Conflict frame freshness.
    issues.extend(_lint_conflict_frame(save))

    # 8. Progression-layer invariants (stage / health / traits / artifact).
    issues.extend(_lint_progression(save, save_dir))

    # 9. Compact turn HUD drift inside current_scene.md.
    issues.extend(
        _lint_compact_hud_drift(
            save_dir,
            save,
            _read_pack_language(packs_root, save.pack_name) if packs_root else None,
        )
    )

    # 10. meta_progress.json (optional sibling file).
    issues.extend(_lint_meta_progress(save_dir, save))

    # 11. context_summary cursor consistency.
    issues.extend(_lint_context_summary(save_dir, save))

    return issues


def _lint_context_summary(save_dir: Path, save) -> list[str]:
    """Cursor in meta.json must agree with session_log length and the on-disk file."""
    issues: list[str] = []
    cursor = save.context_summary_through_turn
    total = len(save.session_log)
    out_of_window = max(0, total - SESSION_LOG_DETAIL_LIMIT)
    if cursor > total:
        issues.append(
            f"meta.json::context_summary_through_turn={cursor} exceeds "
            f"session_log length {total}"
        )
    elif cursor > out_of_window:
        issues.append(
            f"meta.json::context_summary_through_turn={cursor} exceeds the "
            f"out-of-window boundary ({out_of_window}); the cursor must only "
            f"cover turns that have slid out of the latest "
            f"{SESSION_LOG_DETAIL_LIMIT}-turn detail window"
        )
    summary_path = save_dir / "context_summary.md"
    if cursor > 0:
        if not summary_path.is_file():
            issues.append(
                f"context_summary_through_turn={cursor} but context_summary.md is missing"
            )
        elif not summary_path.read_text(encoding="utf-8").strip():
            issues.append(
                f"context_summary_through_turn={cursor} but context_summary.md is empty"
            )
    return issues


def _lint_current_scene_drift(save_dir: Path, save) -> list[str]:
    scene_path = save_dir / "current_scene.md"
    if not scene_path.is_file():
        return ["current_scene.md missing (run render_save.py)"]
    text = scene_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ["current_scene.md missing frontmatter header"]
    try:
        fm_block = text.split("---", 2)[1]
    except IndexError:
        return ["current_scene.md frontmatter malformed"]
    fm: dict[str, str] = {}
    for raw_line in fm_block.strip().splitlines():
        if ":" in raw_line:
            k, _, v = raw_line.partition(":")
            fm[k.strip()] = v.strip()
    w = save.world
    expected = {
        "turn": str(w.turn),
        "day": str(w.day),
        "time_of_day": w.time_of_day,
        "location": w.current_location,
        "risk_level": w.risk_level,
    }
    issues: list[str] = []
    for key, want in expected.items():
        got = fm.get(key)
        if got != want:
            issues.append(
                f"current_scene.md frontmatter drift: {key}={got!r} but world_state has {want!r} "
                f"(re-run render_save.py)"
            )
    return issues


def _lint_hidden_truths(save_dir: Path, save, labels: dict[str, str]) -> list[str]:
    path = save_dir / "hidden_truths.md"
    if not path.is_file():
        return ["hidden_truths.md missing (run render_save.py)"]
    hidden = save.hidden_truths.strip()
    body = hidden if hidden else labels["hidden_truths_empty"]
    expected = f"# {labels['hidden_truths']}\n\n{body}\n"
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        return [
            "hidden_truths.md content differs from render of meta.json::hidden_truths "
            "(someone wrote the .md directly, or render_save.py was not run)"
        ]
    return []


def _resolve_pack(save, packs_root: Path | None):
    if packs_root is None:
        return None
    pack_dir = packs_root / save.pack_name
    if not pack_dir.is_dir():
        return None
    try:
        return load_pack(pack_dir)
    except Exception:
        return None


def _lint_slugs(save, pack) -> list[str]:
    known = (
        {c.slug for c in pack.characters}
        | {f.slug for f in pack.factions}
        | {l.slug for l in pack.locations}
        | {s.slug for s in pack.systems}
        | {a.slug for a in pack.arcs}
        | {e.slug for e in pack.events}
    )
    location_slugs = {l.slug for l in pack.locations}
    arc_slugs = {a.slug for a in pack.arcs}
    issues: list[str] = []

    def _check(slug: str, context: str, allowed: set[str]) -> None:
        if slug.startswith("emergent:"):
            return
        if slug not in allowed:
            issues.append(f"unknown slug {slug!r} in {context}")

    w = save.world
    _check(w.current_location, "world_state.current_location", location_slugs)
    for slug in w.present_entities:
        _check(slug, "world_state.present_entities", known)
    for thread in w.active_threads:
        # thread.id is free-form; only flag when it looks like a slug reference
        # (no colon, no spaces) and collides with arc naming.
        if (
            ":" not in thread.id
            and " " not in thread.id
            and thread.id in known
            and thread.id not in arc_slugs
        ):
            issues.append(
                f"active thread id {thread.id!r} collides with a non-arc entity slug; "
                f"prefer arc slugs or free-form ids (e.g. 't_...')"
            )
    for item in w.player.inventory:
        _check(item.slug, "world_state.player.inventory", known)
    for slug in save.relationships.by_slug:
        _check(slug, "relationship_state.by_slug", known)
    if w.current_conflict is not None:
        for side in w.current_conflict.sides:
            for member in side.members:
                if member == "player":
                    continue
                _check(member, f"current_conflict.sides[{side.label!r}].members", known)
    return issues


def _lint_progression(save, save_dir: Path) -> list[str]:
    """Progression-layer invariants (stage, health, traits, artifact, terminal)."""
    issues: list[str] = []
    p = save.world.player

    # Innate length: must be exactly 3 on every persisted save.
    # `playbooks/new-game.md` writes the save only AFTER Step 1.6 sets
    # innates; if the bootstrap was skipped the save is broken from
    # turn 0, so there is no `turn > 0` exemption.
    if len(p.innate_traits) != 3:
        issues.append(
            f"player.innate_traits must be exactly 3; got {len(p.innate_traits)} "
            f"(did new-game Step 1.6 run before persisting?)"
        )

    # Destiny count must not exceed the current stage_index (at most one per
    # breakthrough, stages 1..STAGE_INDEX_MAX). Model validates source_stage
    # per-entry; lint enforces the simpler count invariant.
    if len(p.destiny_traits) > p.stage_index:
        issues.append(
            f"player.destiny_traits has {len(p.destiny_traits)} entries but "
            f"stage_index={p.stage_index} allows at most {p.stage_index}"
        )

    # Artifact: must be set on every persisted save. new-game Step 1.5
    # populates it before Step 3 writes any JSON, so a null artifact on
    # disk means the bootstrap was skipped.
    if p.artifact is None:
        issues.append(
            "player.artifact is null (did new-game Step 1.5 run before persisting?)"
        )

    # Stage_label should be set whenever the player has advanced past stage 0.
    if p.stage_index > 0 and not p.stage_label:
        issues.append(
            f"player.stage_label is empty but stage_index={p.stage_index}; "
            f"set the novel-themed label from progression_rules.md"
        )

    # Terminal save invariants: on death, expect run_summary.md.
    if p.health_state == "dead":
        run_summary = save_dir / "run_summary.md"
        if not run_summary.is_file():
            issues.append(
                "player.health_state='dead' but run_summary.md is missing; "
                "death flow (playbooks/death-and-restart.md) did not run"
            )

    return issues


def _lint_compact_hud_drift(save_dir: Path, save, language: str | None) -> list[str]:
    """Confirm the compact turn HUD inside current_scene.md matches current state."""
    scene_path = save_dir / "current_scene.md"
    if not scene_path.is_file():
        # Already reported by _lint_current_scene_drift.
        return []
    text = scene_path.read_text(encoding="utf-8")
    HL = hud_labels(language)
    expected = render_compact_turn_hud(save, HL)
    if expected not in text:
        return [
            "current_scene.md compact-HUD block is stale or missing "
            "(re-run render_save.py)"
        ]
    return []


def _lint_meta_progress(save_dir: Path, save) -> list[str]:
    """Validate saves/<pack>/meta_progress.json if it exists."""
    meta_path = save_dir.parent / "meta_progress.json"
    if not meta_path.is_file():
        return []
    try:
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        return [f"meta_progress.json failed to parse: {type(e).__name__}: {e}"]
    try:
        meta = PackMetaProgress(**raw)
    except Exception as e:
        return [f"meta_progress.json failed validation: {type(e).__name__}: {e}"]
    if meta.pack_name != save.pack_name:
        return [
            f"meta_progress.json pack_name={meta.pack_name!r} but this save's "
            f"pack_name={save.pack_name!r}"
        ]
    if meta.best_stage_index > STAGE_INDEX_MAX:
        return [
            f"meta_progress.json best_stage_index={meta.best_stage_index} "
            f"exceeds STAGE_INDEX_MAX={STAGE_INDEX_MAX}"
        ]
    return []


def _lint_conflict_frame(save) -> list[str]:
    conflict = save.world.current_conflict
    if conflict is None:
        return []
    issues: list[str] = []
    remaining = conflict.beats_remaining(save.world.turn)
    if remaining <= -2:
        overshoot = -remaining
        issues.append(
            f"current_conflict {conflict.id!r} overshoots beat_budget "
            f"by {overshoot} turns (budget {conflict.beat_budget}, "
            f"opened turn {conflict.opened_turn}, now {save.world.turn}); "
            f"resolve or revise the frame"
        )
    return issues


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rule-based lint for a save directory.")
    p.add_argument("--save", required=True, help="path under saves/, typically <pack>/<save_id>")
    p.add_argument("--saves-root", type=Path, default=Path("saves"))
    p.add_argument(
        "--packs-root",
        type=Path,
        default=Path("packs"),
        help="resolve meta.pack_name under this dir for slug-existence checks",
    )
    args = p.parse_args(argv)

    save_dir = args.saves_root / args.save
    issues = lint_save(save_dir, packs_root=args.packs_root)
    if not issues:
        print(f"ok: {save_dir} has no lint issues")
        return 0
    print(f"{len(issues)} issue(s) in {save_dir}:")
    for i in issues:
        print(f"  - {i}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
