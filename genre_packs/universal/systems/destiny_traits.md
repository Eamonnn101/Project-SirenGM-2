---
name: destiny_traits
kind: progression
---

# Universal · Destiny trait seeds

At each stage breakthrough (stages 1..5) the GM offers **3 destiny
traits drawn from the 12 universal seeds** below, plus a fixed D
fallback (the player declines; the stage still advances, no
destiny is added). Destiny traits feel stronger and more
build-defining than innate traits — they change playstyle, risk
handling, survival pattern, conflict resolution, or information
access.

Destiny traits are stored as `PlayerState.destiny_traits:
list[Trait]` with `kind == "destiny"`. Up to 5 over a full run
(one per stage advance). Each entry carries `source_stage` equal
to the `stage_index` at which it was picked. `exhausted: true`
marks once-per-run abilities that have already fired.

User packs flavor one novel-themed instance per seed in
`progression_rules.md` §5 — novel-themed name, slug, 1–2 sentence
effect described in the novel's own vocabulary.

## The 12 seeds (4 families)

### Survival / escape

- **`not_meant_to_die`** — **once/run**; before the next fatal
  patch is terminal, the trait fires and the player drops to
  `critical` instead. Trait is exhausted. Precedence **2** in the
  survival-trigger order (after the `bond_rescue` artifact).
- **`golden_cicada_escape`** — **once/run**; in a deadly lock
  (cornered, surrounded, about to be captured or killed), the
  player forcibly disengages. Does NOT prevent death from a patch
  already set to `dead` — this is an earlier-beat escape.
- **`last_barrier`** — **once/run**; fires only on the
  `critical → dead` transition. Grants one extra turn of buffer
  at `critical` with explicit reprieve framing. Precedence **3**
  in the survival-trigger order.

### Insight / learning

- **`heaven_piercing_eye`** — reveal a hidden weakness, truth, or
  pattern for a major edge. Repeatable; each use has a narrative
  cost (a gaze the enemy now knows, a headache, a glimpse of
  something you didn't want to see).
- **`learn_from_enemy`** — after a major conflict resolve, the
  player permanently learns one move / tactic archetype from the
  opposition. Can fire multiple times but only at conflict
  resolve.
- **`breakthrough_instinct`** — in a deadlock, the player detects
  the single line most likely to crack the situation open.
  Repeatable with narrative cost (it's not subtle; the opposition
  notices the PC is *looking*).

### Desperation / clutch

- **`martial_remnant_resolve`** — near collapse (typically
  `badly_hurt` or `critical`), the player gets one short window of
  extreme resistance or pressure. Flavor varies: martial, mental,
  rhetorical. Does NOT prevent death; it buys narrative space for
  a decisive move.
- **`last_stand`** — the player performs one over-limit action at
  major cost. The cost must be real (a wound, a secret, an ally
  turned, a resource burned) and the GM records it on the conflict
  frame's `paid` ledger.
- **`blood_debt`** — when badly hurt, the player gets one powerful
  retaliation or reversal opportunity. Different from `last_stand`
  in that the trigger is the *wound*, not the player's choice.

### Companion / social / information

- **`little_shadow`** — the player gains an odd but useful
  follower / helper pattern. Narrated as an actual entity (with
  `emergent:` prefix if not in the pack). Follows the companion
  from this point on until explicitly lost.
- **`timely_ally`** — **once/run**; at a key chapter, an
  unexpected ally or resource appears. The GM picks the form to
  fit the beat — it is not player-controlled beyond flavor.
- **`read_the_room`** — in high-stakes social scenes, the player
  detects what someone truly wants, fears, or is hiding.
  Repeatable; each use costs social surface (the target feels
  scrutinized).

## Draw rules

- **3 from the 12** per breakthrough.
- **Never offer an archetype already picked this run.** The
  `player.destiny_traits` list determines what's off the table.
- Apply the **draft bias contract** (see
  `systems/meta_progression.md`): while coverage is below ~70% of
  the 12 seeds across the pack's history, prefer unseen
  archetypes first.
- Prefer archetypes that are *not already* present in the player's
  innate traits so the destiny picks keep expanding the build.

## Engine contract

- `Trait.kind == "destiny"` and `Trait.archetype` ∈ the 12 seeds
  above. Lint rejects anything else.
- `source_stage` must equal the `stage_index` at the time the
  trait was added; out-of-range entries are rejected by the model
  validator.
- `exhausted` flips to `true` for once-per-run triggers after
  firing (engine uses `player_trait_exhaust` patch key).
- No two destiny traits share an archetype key within a run.

## Labeled destiny options (load-bearing)

Like artifacts and innate traits, the GM surfaces an unexhausted
destiny trait via a **labeled special option** when its mechanic
seed is *primed* and the turn is a **key beat** (see
`gm_system_fragment.md` § *Key beats*). Default cadence is
**zero per turn**. Format:

- `zh`: `选项A〔命格・<destiny_name>〕（…）：…`
- `en`: `Option A [Destiny · <destiny_name>] (…): …`

Per-family priming shapes (also drives the HUD's `Triggerable`
row):

| family       | primed when                                                              |
| ------------ | ------------------------------------------------------------------------ |
| Survival     | `health_state` ∈ {`badly_hurt`, `critical`} OR conflict in endgame       |
| Insight      | conflict frame active AND at a pivot beat (open / escalation / endgame)  |
| Desperation  | `health_state` ∈ {`badly_hurt`, `critical`}                              |
| Companion    | conflict frame active at a pivot beat AND a fitting NPC / asset is present |

Even when primed, the labeled option appears only if this turn
is a true pivot. Across artifact + innate + destiny combined,
**at most one labeled option appears per turn** — pick the
strongest match.

Picking a labeled destiny option does not on its own exhaust the
trait. Survival-trigger firings flip `exhausted: true` via the
explicit `player_trait_exhaust` patch (see *Survival-trigger
precedence* in `gm_system_fragment.md`); other once-per-run
destinies require an explicit narrative-cost patch when they
fire. Repeatable destinies (e.g., `heaven_piercing_eye`,
`learn_from_enemy`, `read_the_room`) never set `exhausted: true`.

## What destiny traits are NOT

- Not flat +%. A `read_the_room` trait is a reveal mechanic, not a
  stat.
- Not fixed xianxia lore. The mechanic seeds are named in a
  xianxia-shaped vocabulary for convenience; ingest re-themes them
  freely for any genre.
- Not death-prevention across the board. Only
  `not_meant_to_die` + `last_barrier` sit in the survival-trigger
  order. The other 10 seeds do not prevent a fatal patch from
  being terminal.
