# Playbook · play-turn

One turn of gameplay against a save. Invoked implicitly whenever the
user types in-game text in the pack's declared language.

The active save lives at `saves/<pack>/<save_id>/`. Throughout this
playbook, `<pack>` and `<save_id>` refer to that save's pack and id as
recorded in its `meta.json`.

## Load context

Before reading the user's turn input, load:

1. `saves/<pack>/<save_id>/world_state.json`,
   `relationship_state.json`, `open_loops.json`, `meta.json`.
2. Last 6 entries of `saves/<pack>/<save_id>/session_log.jsonl`
   (`tail -n 6`).
3. `meta.json::hidden_truths` (the rendered `hidden_truths.md` is a
   display surface; do not read it for canonical state).
4. `packs/<pack>/index.md` — note the pack's `language` field; every
   subsequent narration and rendered label follows it.
5. `packs/<pack>/novel_rules.md` — the novel-specific power system,
   social order, tech level, tone, hard canon. This file is
   load-bearing; read it in full on every turn.
6. `packs/<pack>/canon_guardrails.md` — any novel-specific overrides
   on top of the universal guardrails.
7. For each slug in `world_state.present_entities` and
   `current_location`, read its entity page.
8. For each `active_threads[*].id` that maps to an arc slug, read
   that arc page (including its `flexibility` field).
9. `genre_packs/universal/style_guide.md`,
   `genre_packs/universal/canon_guardrails.md`, and
   `genre_packs/universal/prompts/gm_system_fragment.md`.

**Never** scrape `current_scene.md` or `session_log.md` for scene state.
Those are display surfaces; they can drift. The JSON files are canonical.

## Step 1 · Narrate

Using the loaded context, write 150–400 characters of prose **in the
pack's declared `language`** (from `packs/<name>/index.md`), responding
to the user's input. Style follows `genre_packs/universal/style_guide.md`
plus any novel-level overrides.

### Player agency (load-bearing)

The player's input has the highest weight in deciding what the next
beat is. `active_threads` and `current_objectives` are **soft
suggestions**, not a script.

- If the player's action contradicts an active thread — they leave
  the area, refuse the quest, pursue an unrelated goal — **follow the
  player**. Narrate the consequences of their choice, not a
  corrective nudge. In Step 2, emit `active_threads_remove` for the
  abandoned thread (or drop its priority to `background`). Log a
  `divergence` only when the patch cannot faithfully encode the move.
- Do not reintroduce a removed thread in the next turn's narration.
- Do not insert NPCs, dialogue, or setting detail for the sole
  purpose of steering the player back to a thread they've left.

### Flexibility gates

- `ArcPage.flexibility`:
  - `soft` (default): honor the arc when the scene invites it; let
    it go when the player moves on.
  - `hard`: the arc's core facts are novel-canon. The GM may delay
    or reroute but must not contradict established beats — narrate
    in-world obstacles instead.
- `EventPage.kind` + `can_skip`:
  - `intended` / `triggerable` with `can_skip: true` (default): never
    force. If triggers pass unobserved, the event simply does not
    fire; no divergence needed.
  - `player_boundary` (default `can_skip: false`): stage only when
    the player is about to break novel canon defined in
    `novel_rules.md` or `canon_guardrails.md`. These protect the
    world, not the plot.

### General guardrails

- Do not violate `canon_guardrails.md` (universal + pack) or
  `novel_rules.md`.
- Do not skip progression stages the novel defines in
  `novel_rules.md`. If the player attempts an ability beyond reach,
  narrate the cost or failure in the novel's own terms.
- Do not introduce modern technology (unless the novel's era
  warrants it), numeric combat stats, or meta-commentary.
- Do not introduce a novel entity slug without an `emergent:` prefix.
- Do not silently invent facts that should be in structured state
  (see Step 2).

## Step 2 · Patch structured state

Produce a patch that covers everything the narration implies. A patch is a
JSON object with these optional top-level keys:

- `world_state` — partial `WorldState` fields to overwrite (turn auto-advances
  by 1 unless `advance_turn: false`).
- `present_entities_add` / `present_entities_remove` — lists of slugs.
- `active_threads_add` / `active_threads_remove` — items / ids.
- `objectives_add` / `objectives_remove` — strings.
- `relationship_updates` — `{slug: {affinity_delta?, trust_delta?, status?, notes?}}`.
- `open_loops_add` — full `OpenLoop` entries.
- `open_loops_close` — list of loop ids.
- `inventory_add` / `inventory_remove` — items / slugs.
- `hidden_truths_append` — paragraph to append to `meta.json::hidden_truths` (the `.md` re-renders from it).
- `divergence` — `{reason, detail}` to append to `divergences.jsonl` when
  the narration implied something the patch can't faithfully encode.

Apply the patch to the in-memory state. Validate using the schemas in
`tools/_models.py` — if validation fails, drop the invalid sub-patch and
log a divergence; do not abort the turn.

Slug-existence rule: any slug referenced in a patch (entity, location,
thread arc id) must exist in `packs/<pack>/` or start with `emergent:`.
If neither holds, drop the sub-patch and log a divergence.

When the player has diverged from an active thread, the patch SHOULD
emit `active_threads_remove` for the abandoned thread in the same turn
— don't let dead threads linger and re-inject themselves into future
context.

## Step 3 · Persist

Write the updated:
- `world_state.json` (with `turn += 1`),
- `relationship_state.json`,
- `open_loops.json`,
- `player.json` (mirror of `world_state.player`),
- append one entry to `session_log.jsonl`:
  `{turn, at, player_input, narration, summary}`.

If `hidden_truths_append` was used, append to `meta.json::hidden_truths`
(do **not** write `hidden_truths.md` directly — Step 4 regenerates it).
If `divergence` was used, append to `divergences.jsonl`.

## Step 4 · Re-render markdown and lint the save

```bash
python tools/render_save.py --save <pack>/<save_id>
python tools/lint_save.py --save <pack>/<save_id>
```

`render_save.py` regenerates `current_scene.md`, `player.md`,
`session_log.md`, `hidden_truths.md` from JSON, in the pack's
declared language. `lint_save.py` then catches any drift (turn vs
session_log length, player mirror out of sync, rendered-surface
drift, missing slug). Exit 0 = safe to reply. Exit 1 = fix before
talking to the user.

## Step 5 · Respond to the user

Output **only** the narration from Step 1 to the user. The JSON writes
and `render_save.py` call happen before the reply; the user sees
prose, not state. On request, the user can run
`python tools/inspect_save.py --save <pack>/<save_id>` to inspect.

## Failure handling

- If the user's input is out-of-character (meta, tool-use, debugging),
  handle it as a tooling request — do not treat it as in-world action and
  do not advance the turn counter.
- If state validation fails catastrophically (e.g. the on-disk JSON is
  malformed), stop and tell the user. Never overwrite a malformed state
  with a guess.
