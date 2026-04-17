# Playbook · new-game

Bootstrap a fresh save from a compiled user pack. Each pack keeps its
own save directory under `saves/<pack>/`, so multiple packs can coexist
without collisions.

## Invocation forms

All three forms land in the same pipeline. The agent fills in whatever
the user left implicit.

- **Bare** — "start a new game" / "开始游戏"
  - If exactly one pack exists under `packs/`, use it.
  - If multiple packs exist, list them and ask which to play.
  - If none exist, tell the user to run `playbooks/ingest.md` first.
  - Auto-assign `<save_id>` (see below).
- **Pack explicit** — "start a new game against pack `<name>`"
  - Use `packs/<name>/`; auto-assign `<save_id>`.
- **Fully explicit** — "start a new game against pack `<name>`, save as `<save_id>`"
  - Use the given pack and id verbatim.

### Save-id auto-assignment

Scan `saves/<pack>/` for existing directories matching `save_<NNN>`
(three-digit, zero-padded). The new id is `save_<N+1>` where `N` is
the highest existing number, or `save_001` if none exist. The chosen
id must not collide with an existing `saves/<pack>/<save_id>/`
directory.

## Preconditions

- `packs/<pack>/` exists and passes `python tools/lint_pack.py --pack <pack>`.
- `saves/<pack>/<save_id>/` does not exist.

## Step 1 · Pick a protagonist

Read `packs/<pack>/characters/*.md`. Prefer the character with
`role: protagonist` in its frontmatter. If multiple, ask the user
to pick.

## Step 2 · Propose an opening scene

Based on the protagonist's `location` (if set), the pack's
`timeline.md`, `novel_rules.md`, and `overview.md`, propose:

- `current_location` (slug, must exist in `packs/<pack>/locations/`),
- 1–3 `present_entities` (slugs),
- 1–2 `active_threads` (short titles; `priority: active`). **Any arc
  you author here should be marked `flexibility: soft` unless the
  novel explicitly fixes the beat.** These are starters the player
  may dismiss outright; the GM will not drag them back to them.
- 1–2 `current_objectives` (short strings) — treat as soft nudges,
  not obligations.
- `risk_level` (`calm` / `tense` / `dangerous` / `lethal`).

Ask the user to confirm before writing anything.

## Step 3 · Write the canonical save JSONs

Create `saves/<pack>/<save_id>/` and write:

- `meta.json` — `{"save_id": "<save_id>", "pack_name": "<pack>", "hidden_truths": ""}`
- `world_state.json` — the schema is defined in `tools/_models.py::WorldState`.
  Fields: `turn: 0`, `day: 0`, `time_of_day: "morning"`, `current_location`,
  `present_entities`, `active_threads`, `current_objectives`, `risk_level`,
  `player` (mirrors chosen protagonist entity), `flags: {}`.
- `relationship_state.json` — `{"by_slug": {}}` (empty; populated as
  the player meets NPCs).
- `open_loops.json` — `{"items": []}`.
- `player.json` — duplicate of `world_state.json::player`.
- `session_log.jsonl` — empty file (`touch` it).
- `divergences.jsonl` — empty file.

`meta.json::save_id` stores only the short id (`save_001`), not the
pack-qualified form — the pack is encoded in the directory path and
mirrored in `meta.json::pack_name`.

## Step 4 · Render markdown surfaces

```bash
python tools/render_save.py --save <pack>/<save_id>
```

This creates `current_scene.md`, `player.md`, `session_log.md`,
`hidden_truths.md` inside `saves/<pack>/<save_id>/`.

## Step 5 · Confirm

```bash
python tools/lint_save.py --save <pack>/<save_id>
python tools/inspect_save.py --save <pack>/<save_id>
```

`lint_save.py` must exit 0 before you tell the user the save is ready.
Paste `inspect_save.py` output back to the user. Then wait for the
first turn per `playbooks/play-turn.md`.
