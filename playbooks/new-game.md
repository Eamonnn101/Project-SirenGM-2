# Playbook · new-game

Bootstrap a fresh save from a compiled user pack. Invoked when the user says
"start a new game against pack `<name>`, save as `<save_id>`."

**Preconditions:**
- `packs/<name>/` exists and passes `python tools/lint_pack.py --pack <name>`.
- `saves/<save_id>/` does not exist.

## Step 1 · Pick a protagonist

Read `packs/<name>/characters/*.md`. Prefer the character with
`role: protagonist` in its frontmatter. If multiple, ask the user to pick.

## Step 2 · Propose an opening scene

Based on the protagonist's `location` (if set), the pack's `timeline.md`,
and the pack's `overview.md`, propose:

- `current_location` (slug, must exist in `packs/<name>/locations/`),
- 1–3 `present_entities` (slugs),
- 1–2 `active_threads` (short titles; `priority: active`),
- 1–2 `current_objectives` (short strings),
- `risk_level` (`calm` / `tense` / `dangerous` / `lethal`).

Ask the user to confirm before writing anything.

## Step 3 · Write the canonical save JSONs

Create `saves/<save_id>/` and write:

- `meta.json` — `{"save_id": "<save_id>", "pack_name": "<name>", "hidden_truths": ""}`
- `world_state.json` — the schema is defined in `tools/_models.py::WorldState`.
  Fields: `turn: 0`, `day: 0`, `time_of_day: "morning"`, `current_location`,
  `present_entities`, `active_threads`, `current_objectives`, `risk_level`,
  `player` (mirrors chosen protagonist entity), `flags: {}`.
- `relationship_state.json` — `{"by_slug": {}}` (empty; populated as the
  player meets NPCs).
- `open_loops.json` — `{"items": []}`.
- `player.json` — duplicate of `world_state.json::player`.
- `session_log.jsonl` — empty file (`touch` it).
- `divergences.jsonl` — empty file.

## Step 4 · Render markdown surfaces

```bash
python tools/render_save.py --save <save_id>
```

This creates `current_scene.md`, `player.md`, `session_log.md`,
`hidden_truths.md`.

## Step 5 · Confirm

```bash
python tools/lint_save.py --save <save_id>
python tools/inspect_save.py --save <save_id>
```

`lint_save.py` must exit 0 before you tell the user the save is ready.
Paste `inspect_save.py` output back to the user. Then wait for the first
turn per `playbooks/play-turn.md`.
