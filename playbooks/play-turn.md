# Playbook · play-turn

One turn of gameplay against a save. Invoked implicitly whenever the user
types in-game text (e.g. "我走进药阁问掌柜").

## Load context

Before reading the user's turn input, load:

1. `saves/<id>/world_state.json`, `relationship_state.json`, `open_loops.json`, `meta.json`.
2. Last 6 entries of `saves/<id>/session_log.jsonl` (`tail -n 6`).
3. `meta.json::hidden_truths` (the rendered `hidden_truths.md` is a display surface; do not read it for canonical state).
4. `packs/<name>/index.md`; then, for each slug in
   `world_state.present_entities` and `current_location`, read its page.
5. For each `active_threads[*].id`, if it maps to an arc slug, read that
   arc page.
6. `genre_packs/<genre>/style_guide.md`,
   `genre_packs/<genre>/canon_guardrails.md`,
   `genre_packs/<genre>/prompts/gm_system_fragment.md`, and
   `packs/<name>/canon_guardrails.md`.

**Never** scrape `current_scene.md` or `session_log.md` for scene state.
Those are display surfaces; they can drift. The JSON files are canonical.

## Step 1 · Narrate

Using the loaded context, write 150–400 characters of Chinese prose
responding to the user's input. Style follows `style_guide.md`. Guardrails:

- Do not violate `canon_guardrails.md` (genre or pack).
- Do not skip cultivation stages.
- Do not introduce modern technology, numeric combat stats, or
  meta-commentary.
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
thread arc id) must exist in `packs/<name>/` or start with `emergent:`.
If neither holds, drop the sub-patch and log a divergence.

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
python tools/render_save.py --save <id>
python tools/lint_save.py --save <id>
```

`render_save.py` regenerates `current_scene.md`, `player.md`,
`session_log.md`, `hidden_truths.md` from JSON. `lint_save.py` then
catches any drift (turn vs session_log length, player mirror out of
sync, rendered-surface drift, missing slug). Exit 0 = safe to reply.
Exit 1 = fix before talking to the user.

## Step 5 · Respond to the user

Output **only** the narration from Step 1 to the user. The JSON writes and
`render_save.py` call happen before the reply; the user sees prose, not
state. On request, the user can ask `python tools/inspect_save.py --save <id>`
to inspect.

## Failure handling

- If the user's input is out-of-character (meta, tool-use, debugging),
  handle it as a tooling request — do not treat it as in-world action and
  do not advance the turn counter.
- If state validation fails catastrophically (e.g. the on-disk JSON is
  malformed), stop and tell the user. Never overwrite a malformed state
  with a guess.
