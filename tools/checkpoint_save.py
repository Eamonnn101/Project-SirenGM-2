"""Apply a compact backup patch to a SirenGM save.

Usage:
    python tools/checkpoint_save.py --save <pack>/<save_id> --patch /tmp/patch.json --render --lint

The patch is intentionally small. It updates backup JSON, appends
detailed session-log entries in order, rewrites `context_summary.md`
whenever backed-up play has more than five turns, and can run render/lint
once at the end. It does not call an LLM.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _models import (
        OpenLoop,
        OpenLoops,
        Relationship,
        RelationshipState,
        Save,
        SessionLogEntry,
        WorldState,
    )
    from lint_save import lint_save
    from render_save import (
        CONTEXT_SUMMARY_FILENAME,
        SESSION_LOG_DETAIL_LIMIT,
        _read_pack_language,
        load_save,
        render_all,
    )
else:
    from ._models import (
        OpenLoop,
        OpenLoops,
        Relationship,
        RelationshipState,
        Save,
        SessionLogEntry,
        WorldState,
    )
    from .lint_save import lint_save
    from .render_save import (
        CONTEXT_SUMMARY_FILENAME,
        SESSION_LOG_DETAIL_LIMIT,
        _read_pack_language,
        load_save,
        render_all,
    )


PATCH_KEYS = {
    "world_state",
    "flags_merge",
    "relationship_updates",
    "open_loops_add",
    "open_loops_update",
    "open_loops_close",
    "hidden_truths_append",
    "session_log_entries",
    "context_summary_rewrite",
}
CONTEXT_PATCH_KEYS = {"context_summary_rewrite"}


def _read_patch(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - message is CLI-facing
        raise ValueError(f"failed to read patch: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("patch root must be a JSON object")
    return payload


def _turn_patches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if "turns" not in payload:
        return [payload]
    unknown = sorted(set(payload) - PATCH_KEYS - {"turns"})
    if unknown:
        raise ValueError(f"unknown patch keys: {', '.join(unknown)}")
    turns = payload["turns"]
    if not isinstance(turns, list) or not all(isinstance(t, dict) for t in turns):
        raise ValueError("patch.turns must be a list of objects")
    return turns


def _has_context_rewrite(payload: dict[str, Any], turns: list[dict[str, Any]]) -> bool:
    return "context_summary_rewrite" in payload or any(
        "context_summary_rewrite" in turn for turn in turns
    )


def _session_entries_count(payload: dict[str, Any], turns: list[dict[str, Any]]) -> int:
    patches = list(turns)
    if "turns" in payload:
        patches.append(payload)
    count = 0
    for patch in patches:
        rows = patch.get("session_log_entries", [])
        if rows is None:
            continue
        if not isinstance(rows, list):
            raise ValueError("session_log_entries must be a list")
        count += len(rows)
    return count


def _needs_context_rewrite(added_entries: int, new_count: int) -> bool:
    return added_entries > 0 and new_count > SESSION_LOG_DETAIL_LIMIT


def _validate_patch_keys(patch: dict[str, Any]) -> None:
    unknown = sorted(set(patch) - PATCH_KEYS)
    if unknown:
        raise ValueError(f"unknown patch keys: {', '.join(unknown)}")


def _apply_world_state(save: Save, update: Any) -> set[str]:
    if not isinstance(update, dict):
        raise ValueError("world_state patch must be an object")
    data = save.world.model_dump(mode="json")
    update = dict(update)
    if "player" in update:
        player_update = update.pop("player")
        if not isinstance(player_update, dict):
            raise ValueError("world_state.player patch must be an object")
        player_data = dict(data["player"])
        player_data.update(player_update)
        data["player"] = player_data
    data.update(update)
    save.world = WorldState(**data)
    return {"world_state"}


def _apply_flags_merge(save: Save, update: Any) -> set[str]:
    if not isinstance(update, dict):
        raise ValueError("flags_merge patch must be an object")
    data = save.world.model_dump(mode="json")
    flags = dict(data.get("flags") or {})
    flags.update(update)
    data["flags"] = flags
    save.world = WorldState(**data)
    return {"world_state"}


def _apply_relationship_updates(save: Save, updates: Any) -> set[str]:
    if not isinstance(updates, dict):
        raise ValueError("relationship_updates must be an object keyed by slug")
    by_slug = dict(save.relationships.by_slug)
    for slug, update in updates.items():
        if not isinstance(update, dict):
            raise ValueError(f"relationship update for {slug!r} must be an object")
        current = by_slug[slug].model_dump(mode="json") if slug in by_slug else {}
        current.update(update)
        by_slug[slug] = Relationship(**current)
    save.relationships = RelationshipState(by_slug=by_slug)
    return {"relationship_state"}


def _loop_index(save: Save, loop_id: str) -> int:
    for index, loop in enumerate(save.open_loops.items):
        if loop.id == loop_id:
            return index
    raise ValueError(f"open loop not found: {loop_id}")


def _apply_open_loops_add(save: Save, rows: Any) -> set[str]:
    if not isinstance(rows, list):
        raise ValueError("open_loops_add must be a list")
    existing = {loop.id for loop in save.open_loops.items}
    items = list(save.open_loops.items)
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("open_loops_add entries must be objects")
        loop = OpenLoop(**row)
        if loop.id in existing:
            raise ValueError(f"open loop already exists: {loop.id}")
        items.append(loop)
        existing.add(loop.id)
    save.open_loops = OpenLoops(items=items)
    return {"open_loops"}


def _apply_open_loops_update(save: Save, rows: Any) -> set[str]:
    if not isinstance(rows, list):
        raise ValueError("open_loops_update must be a list")
    items = list(save.open_loops.items)
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            raise ValueError("open_loops_update entries must be objects with id")
        index = _loop_index(save, row["id"])
        data = items[index].model_dump(mode="json")
        data.update(row)
        items[index] = OpenLoop(**data)
    save.open_loops = OpenLoops(items=items)
    return {"open_loops"}


def _apply_open_loops_close(save: Save, rows: Any) -> set[str]:
    if not isinstance(rows, list):
        raise ValueError("open_loops_close must be a list")
    items = list(save.open_loops.items)
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            raise ValueError("open_loops_close entries must be objects with id")
        index = _loop_index(save, row["id"])
        data = items[index].model_dump(mode="json")
        data["status"] = "closed"
        if "closed_turn" in row:
            data["closed_turn"] = row["closed_turn"]
        if "notes" in row:
            data["notes"] = row["notes"]
        items[index] = OpenLoop(**data)
    save.open_loops = OpenLoops(items=items)
    return {"open_loops"}


def _append_hidden_truths(save: Save, text: Any) -> set[str]:
    if not isinstance(text, str):
        raise ValueError("hidden_truths_append must be a string")
    stripped = text.strip()
    if stripped:
        save.hidden_truths = (
            save.hidden_truths.rstrip() + "\n\n" + stripped
            if save.hidden_truths.strip()
            else stripped
        )
    return {"meta"}


def _append_session_entries(save: Save, rows: Any) -> set[str]:
    if not isinstance(rows, list):
        raise ValueError("session_log_entries must be a list")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("session_log_entries entries must be objects")
        entry = SessionLogEntry(**row)
        expected_turn = len(save.session_log) + 1
        if entry.turn != expected_turn:
            raise ValueError(
                f"session log turn must be {expected_turn}; got {entry.turn}"
            )
        save.session_log.append(entry)
        data = save.world.model_dump(mode="json")
        data["turn"] = entry.turn
        save.world = WorldState(**data)
    return {"world_state", "session_log"}


def _write_context_summary(save_dir: Path, patch: dict[str, Any]) -> set[str]:
    changed: set[str] = set()
    path = save_dir / CONTEXT_SUMMARY_FILENAME
    if "context_summary_rewrite" in patch:
        value = patch["context_summary_rewrite"]
        if not isinstance(value, str):
            raise ValueError("context_summary_rewrite must be a string")
        path.write_text(value.strip() + "\n", encoding="utf-8")
        changed.add(CONTEXT_SUMMARY_FILENAME)
    return changed


def _apply_one_patch(save: Save, patch: dict[str, Any]) -> set[str]:
    _validate_patch_keys(patch)
    changed: set[str] = set()
    if "world_state" in patch:
        changed |= _apply_world_state(save, patch["world_state"])
    if "flags_merge" in patch:
        changed |= _apply_flags_merge(save, patch["flags_merge"])
    if "relationship_updates" in patch:
        changed |= _apply_relationship_updates(save, patch["relationship_updates"])
    if "open_loops_add" in patch:
        changed |= _apply_open_loops_add(save, patch["open_loops_add"])
    if "open_loops_update" in patch:
        changed |= _apply_open_loops_update(save, patch["open_loops_update"])
    if "open_loops_close" in patch:
        changed |= _apply_open_loops_close(save, patch["open_loops_close"])
    if "hidden_truths_append" in patch:
        changed |= _append_hidden_truths(save, patch["hidden_truths_append"])
    if "session_log_entries" in patch:
        changed |= _append_session_entries(save, patch["session_log_entries"])
    return changed


def _dump_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_save(save_dir: Path, save: Save) -> None:
    _dump_json(
        save_dir / "meta.json",
        {
            "save_id": save.save_id,
            "pack_name": save.pack_name,
            "hidden_truths": save.hidden_truths,
        },
    )
    _dump_json(save_dir / "world_state.json", save.world.model_dump(mode="json"))
    _dump_json(
        save_dir / "relationship_state.json",
        save.relationships.model_dump(mode="json"),
    )
    _dump_json(save_dir / "open_loops.json", save.open_loops.model_dump(mode="json"))
    _dump_json(save_dir / "player.json", save.world.player.model_dump(mode="json"))
    session_lines = [entry.model_dump_json() for entry in save.session_log]
    (save_dir / "session_log.jsonl").write_text(
        "\n".join(session_lines) + ("\n" if session_lines else ""),
        encoding="utf-8",
    )


def apply_checkpoint_patch(
    save_dir: Path,
    patch_path: Path,
    *,
    packs_root: Path,
    render: bool,
    lint: bool,
) -> tuple[int, list[str]]:
    payload = _read_patch(patch_path)
    turns = _turn_patches(payload)
    save = load_save(save_dir)
    added_entries = _session_entries_count(payload, turns)
    new_count = len(save.session_log) + added_entries
    if _needs_context_rewrite(added_entries, new_count):
        if not _has_context_rewrite(payload, turns):
            return (
                1,
                [
                    "error: backups beyond the latest "
                    f"{SESSION_LOG_DETAIL_LIMIT} turns require "
                    f"context_summary_rewrite before archiving turn {new_count}"
                ],
            )

    changed: set[str] = set()
    context_patches: list[dict[str, Any]] = []
    for turn_patch in turns:
        context_patches.append(
            {key: turn_patch[key] for key in CONTEXT_PATCH_KEYS if key in turn_patch}
        )
        state_patch = {
            key: value
            for key, value in turn_patch.items()
            if key not in CONTEXT_PATCH_KEYS
        }
        if state_patch:
            changed |= _apply_one_patch(save, state_patch)
    if "turns" in payload:
        global_patch = {key: payload[key] for key in PATCH_KEYS if key in payload}
        if global_patch:
            context_patches.append(
                {
                    key: global_patch[key]
                    for key in CONTEXT_PATCH_KEYS
                    if key in global_patch
                }
            )
            state_patch = {
                key: value
                for key, value in global_patch.items()
                if key not in CONTEXT_PATCH_KEYS
            }
            if state_patch:
                changed |= _apply_one_patch(save, state_patch)

    _write_save(save_dir, save)
    for context_patch in context_patches:
        if context_patch:
            changed |= _write_context_summary(save_dir, context_patch)
    messages = [
        "backup applied: "
        + (", ".join(sorted(changed)) if changed else "no state changes")
    ]

    if render:
        language = _read_pack_language(packs_root, save.pack_name)
        render_all(save_dir, save, language=language)
        messages.append("render: ok")

    if lint:
        issues = lint_save(save_dir, packs_root=packs_root)
        if issues:
            messages.append("lint: failed")
            messages.extend(f"- {issue}" for issue in issues)
            return 1, messages
        messages.append("lint: ok")

    return 0, messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--save", required=True, help="path under saves/, typically <pack>/<save_id>")
    parser.add_argument("--patch", required=True, type=Path, help="backup patch JSON")
    parser.add_argument("--saves-root", type=Path, default=Path("saves"))
    parser.add_argument("--packs-root", type=Path, default=Path("packs"))
    parser.add_argument("--render", action="store_true", help="run render_save after applying the patch")
    parser.add_argument("--lint", action="store_true", help="run lint_save after applying the patch")
    args = parser.parse_args(argv)

    save_dir = args.saves_root / args.save
    if not save_dir.is_dir():
        print(f"error: save dir not found: {save_dir}", file=sys.stderr)
        return 2
    try:
        code, messages = apply_checkpoint_patch(
            save_dir,
            args.patch,
            packs_root=args.packs_root,
            render=args.render,
            lint=args.lint,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    stream = sys.stderr if code else sys.stdout
    for message in messages:
        print(message, file=stream)
    return code


if __name__ == "__main__":
    sys.exit(main())
