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
   If `world_state.current_conflict` is non-null, the scene is
   inside an active conflict frame — stakes, sides, and momentum in
   that frame constrain the next turn's narration and options. See
   *Conflict frame lifecycle* in this playbook and the
   `genre_packs/universal/prompts/gm_system_fragment.md` section
   on conflict frames.
2. Last 6 entries of `saves/<pack>/<save_id>/session_log.jsonl`
   (`tail -n 6`).
3. `meta.json::hidden_truths` (the rendered `hidden_truths.md` is a
   display surface; do not read it for canonical state).
4. `packs/<pack>/index.md` — note the pack's `language` field; every
   subsequent narration and rendered label follows it.
5. `packs/<pack>/novel_rules.md` — the novel-specific power system,
   social order, tech level, tone, hard canon. This file is
   load-bearing; read it in full on every turn.
6. `packs/<pack>/progression_rules.md` — novel-themed stage labels,
   per-stage breakthrough triggers, artifact/innate/destiny
   instances, health-ladder wording. Load-bearing; read it in full
   on every turn (same rhythm as `novel_rules.md`).
7. `packs/<pack>/canon_guardrails.md` — any novel-specific overrides
   on top of the universal guardrails.
8. `saves/<pack>/meta_progress.json` (if present) — lets the turn
   output know the light meta counters for the compact HUD and
   informs unseen-first draft bias at breakthrough time.
9. For each slug in `world_state.present_entities` and
   `current_location`, read its entity page.
10. For each `active_threads[*].id` that maps to an arc slug, read
    that arc page (including its `flexibility` field).
11. `genre_packs/universal/style_guide.md`,
    `genre_packs/universal/canon_guardrails.md`, and
    `genre_packs/universal/prompts/gm_system_fragment.md` (which
    covers the progression layer rules).
12. `genre_packs/universal/systems/*.md` as needed — the mechanic
    seeds for stages, artifacts, traits, health, and meta.
13. For a breakthrough turn, also read
    `genre_packs/universal/prompts/breakthrough_pick.md`. For a
    death/completion turn, also read
    `genre_packs/universal/prompts/death_coda.md`.

**Never** scrape `current_scene.md` or `session_log.md` for scene state.
Those are display surfaces; they can drift. The JSON files are canonical.

## Step 1 · Narrate + offer 3+D options

Using the loaded context, produce the turn output **in the pack's
declared `language`** (from `packs/<name>/index.md`). Every turn
has two parts:

1. **Narration** — 300–700 characters (zh) / 200–500 words (en)
   of prose responding to the user's input. The budget is the
   narration prose **only**; the options block is counted separately
   and does not eat into it. Style follows
   `genre_packs/universal/style_guide.md` plus any novel-level
   overrides. Density matters: play the current beat through to its
   pivot (action → each NPC's distinct reaction → complication);
   a static tableau is a failure unless the player's input was
   itself observational. See *Beat density* in
   `prompts/gm_system_fragment.md`.
2. **Options block** — exactly three GM-proposed options
   (`选项A/B/C` in zh, `Option A/B/C` in en), each with a short
   tactic label in parentheses and a 60–150 character diegetic
   action description, followed by the fixed free-form slot
   (`选项D/Option D`). See `prompts/gm_system_fragment.md` for the
   required template and rules.

### Step 1a · Pre-options build scan (load-bearing)

**Before** drafting A/B/C, decide whether this turn warrants a
labeled special option. Default answer is **no** — most turns
emit zero labeled options.

1. Read `world_state.player.artifact` (name, archetype, `used`),
   `world_state.player.innate_traits` (3 archetypes), and
   `world_state.player.destiny_traits` (filter out
   `exhausted: true`).
2. Read the situation: `current_conflict` (live or null;
   endgame?), `health_state`, `risk_level`, `present_entities`,
   `active_threads`. The compact HUD's `Triggerable` row is a
   hint about which hooks are primed; it is **not** a mandate
   to surface a labeled option.
3. **Is this turn a key beat?** A turn qualifies only when one
   or more of:
   - the conflict frame opens, escalates with a real
     `paid_add` and momentum shift, or enters endgame
     (`beats_remaining(turn) <= 1`);
   - `health_state` ∈ {`badly_hurt`, `critical`} and the turn's
     prose centers on the danger;
   - `risk_level == "lethal"`;
   - the player is making a major branching decision with
     lasting consequence (back X or Y, reveal or conceal, where
     to commit);
   - investigation breakthrough — a key piece of information
     lands and changes how the player should act;
   - significant social pivot — an NPC's stance is about to
     flip (alliance, betrayal, first-trust, breaking point).

   Quiet exposition, recap, planning, travel, shopping, small
   talk, and mid-investigation "thinking it through" turns are
   **not** key beats, even when `risk_level == "tense"` or a
   conflict frame is technically active. The full list and
   negative cases are in `prompts/gm_system_fragment.md`
   § *Key beats*.

4. If the turn is **not** a key beat, emit **zero** labeled
   options and skip the rest of this step.

5. If it *is* a key beat, ask which single item on the player
   opens the most distinct approach for *this specific pivot*:
   the artifact (when its mechanic seed fires here), one of the
   three innate traits (when its archetype genuinely applies),
   or one unexhausted destiny trait (when its mechanic seed is
   primed). Pick the **strongest one**; leave the others
   unlabeled.

6. Emit **at most one labeled option per turn, total** — across
   artifact, innate, and destiny combined. The labeled option
   replaces one of A/B/C; it does not add a fifth slot. The
   fixed D free-form slot is unaffected.

Picking a labeled option does not consume the artifact or exhaust
the trait. Survival-trigger firings (`bond_rescue` `used: true`,
destiny `exhausted: true`) and ledger costs still go through the
normal patch keys. Full label format and rules are in
`prompts/gm_system_fragment.md` § *Pre-options scan*,
§ *Key beats*, and § *Labeled special options*.

Persist the narration and the four option strings separately in
Step 3; `session_log.jsonl` keeps `narration` (prose only) and
`options` (list of 4 full strings A/B/C/D) as distinct fields.

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
- `conflict_open` — a full `ConflictFrame` object to install into
  `world_state.current_conflict`. Rejected with a divergence if a
  frame is already active; to replace a stale frame, resolve the
  old one first.
- `conflict_update` — merge patch for the active frame:
  `{momentum?, escalation_note?, side_updates?: {label: {want?,
  paid_add?, members_add?, members_remove?}}}`. Dropped with a
  divergence if no frame is active, or if a `side_updates` label
  does not match any existing side.
- `conflict_resolve` — `{outcome, momentum_final, world_change}`.
  Clears `current_conflict`, writes `world_change` into
  `meta.json::hidden_truths` via the normal `hidden_truths_append`
  path, AND writes a `ConflictSummary` into
  `world_state.last_conflict_summary` (fields `id, kind, stake,
  outcome, momentum_final, resolved_turn` populated from the
  resolving frame plus the resolve payload — the renderer needs
  this block to keep the scene from feeling empty after resolve).
  The resolve patch MUST also be combined in the same turn with
  whichever of `relationship_updates`, `open_loops_close`,
  `open_loops_add`, `inventory_*` the outcome implies. A resolve
  that writes no world-state writeback is a bug: the conflict did
  not change the world and should not have been opened.
- `player_artifact_set` — `PlayerArtifact` dict. Accepted **only**
  when `turn == 0` or when `player.artifact is None` (i.e. during
  new-game Step 1.5). Rejected with a divergence otherwise.
- `player_innate_traits_set` — list of exactly 3 `Trait` dicts
  (each `kind: "innate"`, 3 distinct archetype keys). Accepted
  only when `turn == 0` (new-game Step 1.6). Rejected otherwise.
- `player_stage_advance` — `{new_index, new_label}`. Must advance
  `world_state.player.stage_index` by exactly 1, up to 5. Triggers
  the breakthrough flow (see § Breakthrough turn below). Rejected
  with a divergence if `new_index != stage_index + 1` or
  `new_index > 5`.
- `player_destiny_trait_add` — single `Trait` dict with `kind:
  "destiny"` and `source_stage == stage_index`. Rejected if a
  destiny with that `source_stage` already exists, if the
  archetype is already present on the player, or if the archetype
  key is not one of the 12 universal destiny seeds.
- `player_trait_exhaust` — `{slug}`. Flips `exhausted: true` on the
  named destiny trait. Idempotent. Used when a once-per-run
  ability (`not_meant_to_die`, `last_barrier`, `last_stand`, etc.)
  fires.
- `player_health_state` — `HealthState` (`healthy`/`hurt`/
  `badly_hurt`/`critical`/`dead`). Setting `"dead"` routes
  through **survival-trigger precedence** before becoming
  terminal. See § Health ladder + death below.
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

### Conflict frame lifecycle

A conflict frame is a scene of real tension with two or more named
parties, opposing wants, and an outcome that would change the state
of the world. The engine is cross-genre: `kind` is whatever the scene
actually is (辩论, 围城, 走私交接, 丹药失控, debate, duel, chase,
courtroom, …), picked fresh per frame.

- **Open (`conflict_open`)** — emit the turn the stakes become
  real, not earlier. Do not open a frame for small talk, logistics,
  or idle exploration. `sides` needs at least two entries; each
  side's `want` is one line; include the PC's side (`members`
  contains the PC's character slug or the literal `player`).
  `momentum` on opening is almost always `setup`.
  Additionally set `beat_budget` on open based on the conflict's
  scope (3–6, default 4). See *Beat budget* in
  `genre_packs/universal/prompts/gm_system_fragment.md` for the
  per-kind guidance table.
- **Update (`conflict_update`)** — every turn the frame is live,
  emit at least `momentum` (even if it stayed the same) and, when a
  pivotal beat landed, an `escalation_note`. Track costs with
  `side_updates[label].paid_add`. Keep each entry short — a bullet,
  not a paragraph.
  Do NOT patch `beat_budget` here — it is set once at open and
  thereafter derived (`beat_budget - (turn - opened_turn)`).
  Patches that include `beat_budget` inside `conflict_update` drop
  that field and log a divergence.
- **Resolve (`conflict_resolve`)** — emit the turn the stakes are
  answered or the player walks away. Always combine with the
  writebacks the outcome implies: `hidden_truths_append` for
  private GM knowledge, `relationship_updates` for stance changes,
  `open_loops_close` / `open_loops_add` for hooks created or shut,
  `inventory_*` for gear won or lost. If the player abandons the
  conflict mid-scene, resolve with `momentum_final: "even"` (or
  whichever label fits) and `world_change` stating the abandonment
  — do not leave the frame open.

When `remaining == 1` (i.e. `turn - opened_turn == beat_budget - 1`),
one A/B/C option must be a decisive (收束型) move and the HUD shows
`收束在即 / Endgame`. When `remaining == 0`, the turn SHOULD resolve
the frame. One-turn overshoot is allowed when a reveal needs to
play out. `tools/lint_save.py` warns when `remaining <= -2`.

### Breakthrough turn (stage advance)

When the current climactic beat matches one of the per-stage
triggers in `progression_rules.md` §2, emit `player_stage_advance`
in the turn's patch. Rules:

- Max 5 advances per run. Never more than one per turn. No
  regression.
- Only on a climactic beat. Not during small talk, travel, or
  routine logistics.
- The turn's output replaces A/B/C/D with the **Breakthrough
  block** (`genre_packs/universal/prompts/breakthrough_pick.md`):
  short narration (1–3 paragraphs) of the breakthrough, then the
  Unicode-boxed pick block with 3 destiny options + fixed D
  fallback.
- The player's next turn patches `player_destiny_trait_add` (or
  no-op on the D fallback). Resume normal A/B/C/D play after that.

Destiny options are drawn via `destiny_draw_order(meta,
already_picked_in_run)` in `tools/_progression.py` — unseen-first
bias against `meta.seen_destiny_archetypes`, filtered to exclude
archetypes already on the player.

### Health ladder + death

`world_state.player.health_state` is the 5-state narrative health
ladder (`healthy → hurt → badly_hurt → critical → dead`). Set it
via `player_health_state: <state>` whenever the narration implies
a move.

- Adjacent moves are the common case. Skips are allowed only when
  the prose clearly stages them.
- `critical` requires **mandatory priority handling on the next
  turn**: the prose centers on the danger, and A/B/C/D center on
  the crisis. It is **not** a 1-turn "recover or die" timer —
  genre-appropriate consequence timing (2–3 beats for a poison, a
  contested scene for a bleed-out) is allowed as long as the
  danger stays visible in every intervening turn.

**Survival-trigger precedence** (load-bearing). Before committing
a `player_health_state: "dead"` patch as terminal, check these in
order. Any one firing replaces the fatal patch with `health_state
→ critical`, marks the artifact/trait used/exhausted, and the
prose shows the trigger firing. The turn is **not** terminal.

1. **Artifact `bond_rescue`**, not yet used.
2. **Destiny `not_meant_to_die`**, not exhausted.
3. **Destiny `last_barrier`**, not exhausted, and only on the
   specific transition `critical → dead`. Grants one extra
   buffer turn at `critical`.

No other MVP trigger prevents death. Implementation is in
`tools/_progression.py :: resolve_survival_trigger`; the GM must
narrate in the same order.

If none applies → **terminal death flow**. The turn's output
replaces A/B/C/D with the **Run-end block**
(`genre_packs/universal/prompts/death_coda.md`): short coda
narration + the Unicode-boxed block. The turn also writes
`saves/<pack>/<save_id>/run_summary.md` and updates
`saves/<pack>/meta_progress.json` via
`tools/_progression.py :: merge_run_into_meta(outcome="death")`.
Full procedure in `playbooks/death-and-restart.md`.

### Clean completion turn

When `stage_index == 5` AND the final climactic beat has landed,
the agent emits the Run-end block with `outcome="completion"`.
`runs_finished` bumps; no `DeathRecord`. The save is retired but
not terminal-via-death. See `playbooks/death-and-restart.md`.

## Step 3 · Persist

Write the updated:
- `world_state.json` (with `turn += 1`),
- `relationship_state.json`,
- `open_loops.json`,
- `player.json` (mirror of `world_state.player`),
- append one entry to `session_log.jsonl`:
  `{turn, at, player_input, narration, options, summary}` where
  `options` is the list of four strings (A/B/C/D) shown to the
  player this turn, verbatim.

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

Output to the user exactly what Step 1 produced, with the compact
HUD line at the top. Step 4's `render_save.py` call has already
written the canonical compact HUD into
`saves/<pack>/<save_id>/current_scene.md` as a single bare line
between the frontmatter and the `# 当前场景 / # Current Scene`
heading — the chat reply **reproduces that exact line** verbatim.

The shape depends on whether a conflict frame is active after
this turn's patch has been applied:

- **No conflict frame (default)** — compact HUD line, one blank
  line, the prose narration, one blank line, the four option
  strings (A/B/C/D). Nothing else.
- **Conflict frame is active** — compact HUD line, one blank
  line, a single-line conflict HUD (format per
  `genre_packs/universal/prompts/gm_system_fragment.md` §
  *Conflict HUD line*), one blank line, the prose narration, one
  blank line, the four option strings. Both HUD elements are
  required and must never be abbreviated or folded into the
  prose.
- **Breakthrough or death turn** — compact HUD line, one blank
  line, the short narration coda, one blank line, the
  Unicode-boxed pick / Run-end block (per
  `prompts/breakthrough_pick.md` or `prompts/death_coda.md`).
  The breakthrough/death blocks **replace** A/B/C/D for that
  turn; the compact HUD line at the top is still required.

To produce the compact HUD line in the chat reply, copy the
single bare line from `current_scene.md` (the line immediately
after the closing `---` of the frontmatter, before the
`# 当前场景 / # Current Scene` heading). Format example:

```
第 12 回 / 〔悟性过人〕〔以诚动人〕〔奇缘不断〕 / 〔法宝・观机古镜〕 / 〔体况・健康〕
```

Do not wrap it in a code block, do not bold or italicize it, do
not reorder or rename segments. The text is authoritative and
matches `_hud.py :: render_compact_turn_hud` for the post-patch
state. Do not invent a more verbose form on conflict turns or
when health is critical — the segment list (turn / innate /
artifact / health / optional destiny / optional triggerable) is
the full vocabulary.

The JSON writes and `render_save.py` call happen **before** the
reply, so both HUD elements read the updated `current_conflict`
and `player` state (including any `conflict_open`,
`conflict_update`, `conflict_resolve`, or progression patches
this turn just wrote). If this turn resolved the frame, there is
no conflict HUD line next turn — but the player still sees the
"上一场冲突 / Last Conflict" block in `current_scene.md` on
request until the next conflict opens.

On request, the user can run
`python tools/inspect_save.py --save <pack>/<save_id>` to inspect.

## Failure handling

- If the user's input is out-of-character (meta, tool-use, debugging),
  handle it as a tooling request — do not treat it as in-world action and
  do not advance the turn counter.
- If state validation fails catastrophically (e.g. the on-disk JSON is
  malformed), stop and tell the user. Never overwrite a malformed state
  with a guess.
