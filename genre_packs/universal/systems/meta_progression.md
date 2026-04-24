---
name: meta_progression
kind: progression
---

# Universal · Light meta progression

Each pack carries a single, small meta file at
`saves/<pack>/meta_progress.json`. It persists across every save
in that pack, survives ingest regeneration, and is the minimum
structure needed to make repeat runs feel different without
becoming a permanent power tree.

Schema: `tools/_models.py :: PackMetaProgress`.

## What it stores

- **Coverage by universal archetype** — the stable-key lists
  `seen_artifact_archetypes`, `seen_innate_archetypes`,
  `seen_destiny_archetypes`. These drive the unseen-first draft
  bias.
- **Coverage by novel-themed slug** — the flavor lists
  `seen_artifact_slugs`, `seen_innate_slugs`,
  `seen_destiny_slugs`. These let the LLM vary names across runs
  when the archetype repeats.
- **Lightweight counters** — `runs_started`, `runs_finished`
  (reached stage 5 without dying), `deaths_count`,
  `best_stage_index`.
- **Death history** — a list of compact `DeathRecord` entries
  (save_id, turn, cause, stage_index, stage_label).

That is everything. No achievements, no trait trees, no pack-spanning
compendium, no unlock thresholds.

## When it's written

- **New-game start.** `runs_started += 1`, no other fields.
- **Terminal death** (see `systems/health_and_death.md`). Merge
  seen-pools, append `DeathRecord`, `deaths_count += 1`, update
  `best_stage_index`.
- **Clean completion** (stage 5 reached without dying). Merge
  seen-pools, `runs_finished += 1`, update `best_stage_index`. No
  `DeathRecord`.

## Draft bias contract (load-bearing)

When generating:

- the new-game artifact menu (3 options, one per archetype),
- the new-game innate menu (one option per archetype, 5 options),
- a breakthrough destiny draw (3 of 12),

the LLM **must** prefer universal archetype keys whose coverage
count in the relevant `seen_*_archetypes` list is **lowest**, until
the coverage ratio reaches ~70% of the pool:

- ≥ 3 of 3 artifact archetypes
- ≥ 4 of 5 innate archetypes
- ≥ 9 of 12 destiny archetypes

Above the threshold, fall back to free draw (universal order).

Within each archetype, vary the novel-themed **slug and name** from
those already in `seen_*_slugs` so runs feel flavor-new even when
the archetype repeats.

The artifact menu always shows one per archetype (all 3), so the
bias there drives visual prominence and naming variation — not
menu composition.

Implementation lives in `tools/_progression.py`:
- `draft_bias_order(seen, universal_pool)`
- `destiny_draw_order(meta, already_picked_in_run)`
- `innate_draw_order(meta)`
- `artifact_draw_order(meta)`

## What meta progression is NOT

- **Not an unlock tree.** Every archetype is available on every
  run, regardless of coverage. The bias only changes *which
  options surface first*.
- **Not an achievement system.** Counters are surfaced in the HUD
  and run-end block for feel, not as gating thresholds.
- **Not a cross-pack compendium.** Each pack owns its own
  meta_progress.json. No sharing of seen-pools across packs.
- **Not a difficulty modifier.** Replaying a pack is not harder or
  easier than a first run. The bias affects variety, not challenge.

## Engine contract

- `PackMetaProgress.pack_name` must match the save's `pack_name`.
  Lint enforces.
- The file is optional; its absence is equivalent to an empty
  meta (all counters at 0, all `seen_*` empty). New-game's first
  action in a pack is to create it with `runs_started = 1`.
- Model-level validation: `seen_*_archetypes` entries must be
  keys from the universal pool. Unknown keys are rejected.
