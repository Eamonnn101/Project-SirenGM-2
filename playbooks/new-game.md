# Playbook · new-game

Bootstrap a fresh save from a compiled user pack. Each pack keeps its
own save directory under `saves/<pack>/`, so multiple packs can coexist
without collisions.

## Invocation forms

All three forms land in the same pipeline. The agent fills in whatever
the user left implicit.

- **Bare** — "start a new game" / "开始游戏"
  - Enumerate packs: count only non-hidden subdirectories of `packs/`
    that contain an `index.md` with `kind: user`. Files at the top
    level (`packs/.gitkeep`, stray notes), hidden dirs (`.obsidian/`,
    `.cache/`), and half-written directories without `index.md` are
    **not** packs and must not be counted.
  - If exactly one such pack exists, use it.
  - If multiple exist, list them and ask which to play.
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

## Step 1.5 · Pick artifact

Read `packs/<pack>/progression_rules.md` §3 (artifact archetypes)
and, if it exists, `saves/<pack>/meta_progress.json`.

Emit the **Artifact pick block** per
`genre_packs/universal/prompts/new_game_build_picks.md`. Three
options are shown, one per universal archetype (`insight`,
`bond_rescue`, `companion`); ordering follows
`artifact_draw_order(meta)` from `tools/_progression.py` so the
most-unseen archetype in this pack's history surfaces first.

On the player's reply (A / B / C / D-as-free-form), emit the
`player_artifact_set` patch with the chosen archetype + the
novel-themed slug, name, and `notes` (activation rule) from
`progression_rules.md`. Free-form (D) replies are classified to
the nearest universal archetype; tell the player briefly how you
classified.

## Step 1.6 · Pick 3 innate traits

Read `packs/<pack>/progression_rules.md` §4 (innate archetypes).

Emit the **Innate pick block** per
`prompts/new_game_build_picks.md`. All 5 archetype options are
shown, ordered per `innate_draw_order(meta)`. The player picks
**3 distinct archetypes**.

On valid picks (3 distinct archetype keys), emit
`player_innate_traits_set` with exactly 3 `Trait` dicts — `kind:
"innate"`, `archetype: <universal key>`, `slug`/`name`/`notes`
from `progression_rules.md`. Reject and restate the block if the
player picks fewer than 3 or duplicates an archetype.

After both picks:

- `world_state.player.artifact` is populated.
- `world_state.player.innate_traits` has exactly 3 entries.
- Set `world_state.player.stage_index = 0` and
  `world_state.player.stage_label = <stage 0 label from
  progression_rules.md §1>`.
- Set `world_state.player.health_state = "healthy"`.

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
  `player` (mirrors chosen protagonist entity + the artifact + innate traits
  picked in Steps 1.5/1.6 + `stage_index: 0`, `stage_label` from
  `progression_rules.md`, `health_state: "healthy"`, empty `destiny_traits`),
  `flags: {}`.
- `relationship_state.json` — `{"by_slug": {}}` (empty; populated as
  the player meets NPCs).
- `open_loops.json` — `{"items": []}`.
- `player.json` — duplicate of `world_state.json::player`.
- `session_log.jsonl` — empty file (`touch` it).
- `context_summary.md` — initial key-node memory in the pack's language,
  e.g. `## 关键经过` followed by
  `**开局（0 回）**：新局开始，尚无长期剧情记忆。`
- `divergences.jsonl` — empty file.

**Also** update (or create) `saves/<pack>/meta_progress.json`:

- If the file does not exist: initialize
  `PackMetaProgress(pack_name="<pack>", runs_started=1)` and write.
- If it exists: load it, increment `runs_started`, preserve all
  other fields (seen lists, counters, deaths history), and write
  back. `tools/_models.py::PackMetaProgress` defines the shape.

`meta.json::save_id` stores only the short id (`save_001`), not
the pack-qualified form — the pack is encoded in the directory
path and mirrored in `meta.json::pack_name`.

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
