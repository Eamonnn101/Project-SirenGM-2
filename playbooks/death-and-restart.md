# Playbook · death-and-restart

Handle end-of-run: terminal death (survival-trigger precedence
failed to fire) or clean completion (stage 5 reached, final beat
landed). Both paths emit the **Run-end block** from
`genre_packs/universal/prompts/death_coda.md` and update
`saves/<pack>/meta_progress.json`. The difference between the two
paths is narrative (outcome label, cause field) and counter
(`deaths_count` vs `runs_finished`).

## When this playbook fires

- **Terminal death** — during `playbooks/play-turn.md` Step 2, a
  patch set `player_health_state: "dead"` and the survival-trigger
  precedence check (see `systems/health_and_death.md`) did not
  fire. The fatal patch becomes terminal.
- **Clean completion** — during play-turn Step 1, the GM judges
  the final climactic beat at `stage_index == 5` has fully landed
  (the novel-themed "rewrite fate" equivalent has resolved). No
  fatal patch is involved.

Both paths replace the usual A/B/C/D options on the triggering
turn with the boxed Run-end block. No further turns run after
either.

## Survival-trigger precedence (must check before death is terminal)

The death path **must not** run until `resolve_survival_trigger(
player, prior_health_state)` (from `tools/_progression.py`) has
been consulted. If it returns a non-None trigger, narrate the
trigger firing, patch the exhaust/used flag, transition
`health_state → critical`, and do **not** run this playbook.

The three triggers, in fixed order:

1. `PlayerArtifact` with `archetype == "bond_rescue"` and `used
   == False` → fires first. Flip `artifact.used = True`.
2. Destiny trait `archetype == "not_meant_to_die"` and `exhausted
   == False` → fires second. Emit `player_trait_exhaust`.
3. Destiny trait `archetype == "last_barrier"` and `exhausted ==
   False`, and the transition is specifically `critical → dead`
   (not a skip-to-dead) → fires third. Emit `player_trait_exhaust`.

Full rules in `genre_packs/universal/systems/health_and_death.md`.
Narration discipline is in
`genre_packs/universal/prompts/gm_system_fragment.md` § "Survival
trigger precedence".

## Turn output (terminal death)

1. **Final narration** — one coda beat, pack-language, shorter
   than a normal turn (150–350 zh chars / 100–200 en words).
   Voice per `progression_rules.md` §7 ("Breakthrough voice",
   reused for the funeral coda).
2. **Run-end block** — Unicode-boxed, verbatim per
   `genre_packs/universal/prompts/death_coda.md`. `结局类别：陨落`
   / `Outcome: Fallen`. All fields populated from the current
   `world_state.player`, `saves/<pack>/meta_progress.json`, and
   the death narration's cause phrase.
3. **No options block.** The run is over.

## Turn output (clean completion)

1. **Final narration** — one triumphal / settling beat, same
   length budget as the death coda. Voice per
   `progression_rules.md` §7.
2. **Run-end block** — same layout as the death path, but
   `结局类别：功成` / `Outcome: Completed`. The `死因 / Cause`
   row is omitted.
3. **No options block.** The save is retired.

## Patch + file writes (terminal death)

Bundled into the same terminal turn:

1. **Patch (play-turn.md Step 2):**
   - `player_health_state: "dead"` (unchanged — the fatal patch
     that triggered this playbook)
   - `world_state: {player: {status: "dead"}}`
   - If a conflict is live: `conflict_resolve` with an outcome
     naming the PC's death and `world_change` describing the
     terminal event.
   - Any `relationship_updates`, `open_loops_close`,
     `inventory_*` the death plausibly implies.
2. **File writes (play-turn.md Step 3/4 plus this playbook):**
   - Normal persist: `world_state.json`, `player.json`,
     `session_log.jsonl`.
   - Write `saves/<pack>/<save_id>/run_summary.md` — 200–400
     chars, pack language, one-paragraph run summary covering
     stages reached, key arcs, cause of death.
   - Update `saves/<pack>/meta_progress.json` via:
     ```python
     merge_run_into_meta(
         meta, player=<final player>, save_id=<this save>,
         turn=<this turn>, outcome="death",
         cause=<one-line cause phrase from the narration>,
     )
     ```
     This folds archetypes/slugs into seen lists, appends a
     `DeathRecord`, bumps `deaths_count`, updates
     `best_stage_index`. Does NOT touch `runs_finished`.
   - Run `tools/render_save.py` and `tools/lint_save.py` per the
     usual play-turn Step 4. Lint requires `run_summary.md` on a
     `health_state == "dead"` save; the file is written above, so
     lint should pass.

## Patch + file writes (clean completion)

Bundled into the same completion turn:

1. **Patch:** normal resolve of whatever conflict or arc was live
   (with `conflict_resolve` if a frame was active), plus any
   `open_loops_close` the ending implies. **No** `status = "dead"`
   or `health_state = "dead"` patch on this path — the PC is
   alive.
2. **File writes:**
   - `run_summary.md` — same length budget, in victory voice.
   - Update `meta_progress.json` via
     ```python
     merge_run_into_meta(
         meta, player=<final player>, save_id=<this save>,
         turn=<this turn>, outcome="completion",
     )
     ```
     Bumps `runs_finished`, merges seen pools. No `DeathRecord`.
   - Normal render + lint.

## Restart prompt

After emitting the Run-end block, ask the user which restart path
they want. Both zh and en templates are fixed (see `death_coda.md`);
the agent routes the reply:

- **"Replay this pack from scratch" / "沿用此 pack，从零再来"** →
  delegate to `playbooks/new-game.md` against the same pack. The
  new save's `runs_started` bump will see the freshly-merged
  seen-pools from this run, driving unseen-first bias on the next
  artifact/innate menus.
- **"Pick a different pack" / "选择其他 pack"** → ask the user
  which pack, then delegate to `playbooks/new-game.md` against
  that pack.
- **"Load an older save" / "载入旧档"** → ask the user for a save
  id under `saves/<pack>/`; resume normal play-turn against it.
- **"Pause" / "暂停"** → stop. The user can resume later with any
  of the above.

No further turns are accepted against the terminated / completed
save.

## What this playbook is NOT

- Not a general "how to end a save" utility. It fires only on
  terminal death (after survival-trigger precedence) or clean
  completion at stage 5. A session the player abandons mid-run
  is neither — it just stops.
- Not the owner of the survival-trigger logic. That lives in
  `tools/_progression.py :: resolve_survival_trigger`,
  `systems/health_and_death.md`, and the GM prompt fragment.
  This playbook runs only when the trigger logic has already
  returned None.
- Not the place to patch stats or unlock future content. The
  meta-progression is intentionally light — counters + seen
  archetypes only; no unlock tree.
