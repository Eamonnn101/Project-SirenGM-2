---
name: innate_traits
kind: progression
---

# Universal · Innate trait archetypes

At new-game (Step 1.6) the player picks **3 innate traits from 3
distinct archetypes** out of 5. Innate traits are immutable for the
rest of the run. They are stored on the save as
`PlayerState.innate_traits: list[Trait]` (length == 3, all
`kind == "innate"`).

User packs flavor one novel-themed instance per archetype in
`progression_rules.md` §4 — name, slug, 1–2 sentence flavor. The
universal archetype key stays stable so lint and meta can track
coverage and bias future runs.

## The 5 archetypes

| key           | build tendency (mechanic seed)                                                    |
| ------------- | --------------------------------------------------------------------------------- |
| `talent`      | Fast learning, pattern acquisition. Picks up a new move / skill / argument faster than peers. |
| `survival`    | Toughness, resilience, escape under pressure. Absorbs damage, endures, recovers.  |
| `social`      | Empathy, persuasion, influence in high-stakes social scenes.                      |
| `resource`    | Luck, opportunity, finding-what-you-need. The right NPC, item, or opening shows up. |
| `temperament` | Risk appetite, style, psychological steadiness. How the PC holds up under fear/anger. |

These are tendencies, not modifiers. The GM reads them as a lens on
how the PC responds when stakes spike — the narration should feel
consistent with the 3 chosen traits without reducing to "+X on a
roll".

## The 3-distinct-archetypes rule

Locked in MVP: the 3 innate picks must come from **3 different
archetypes**. Two `talent` traits in one run is rejected by the
model validator and by `lint_save.py`. The rule keeps builds broad
and prevents a run from collapsing into "I'm very good at one thing
and unmentioned at everything else".

User packs can still give two distinct novel-themed options per
archetype (e.g., both `talent` instances have different flavor
text), but only one can enter the player's innate list per run.

## Engine contract

- `Trait.kind == "innate"` and `Trait.archetype` ∈ the 5 keys
  above. Lint rejects anything else.
- `source_stage` **must** be None on innate traits (they are
  chosen at new-game, not earned at a breakthrough).
- `exhausted` is not typically used on innate traits — they are
  passive tendencies, not one-shot abilities.
- `player_innate_traits_set` is accepted only at `turn == 0`.
  Later patches that attempt to replace innate traits are rejected
  with a divergence.

## BG3-style labeled options (load-bearing)

The GM surfaces innate traits to the player primarily through
**labeled special options** — A/B/C entries prefixed with the
trait's archetype label so the player can see which choices are
build-driven. Format per language:

- `zh`: `选项A〔才华〕（…）：…` / `〔坚韧〕` / `〔人情〕` / `〔缘分〕` / `〔性情〕`
- `en`: `Option A [Talent] (…): …` / `[Survival]` / `[Social]` /
  `[Resource]` / `[Temperament]`

Example option bodies (English, abbreviated):

- `[Talent] analyze the opponent's pattern`
- `[Social] appeal with sincerity`
- `[Survival] identify the safest escape line`
- `[Resource] remember a useful contact / tool / place`
- `[Temperament] force the confrontation instead of backing down`

### When to expose `[Trait]` options

**Selective, on key beats only.** Default cadence is **zero
labeled options per turn**; surface a `[Trait]` option only on a
clear pivot. The full list of key beats is in
`genre_packs/universal/prompts/gm_system_fragment.md`
§ *Key beats* — conflict open / escalation / endgame, health
crisis, lethal risk, major branching decision, investigation
breakthrough, significant social pivot.

Per-archetype priming shapes (the renderer's `Triggerable` row
uses the same heuristic as a hint to the GM):

| archetype     | primed when                                                                |
| ------------- | -------------------------------------------------------------------------- |
| `talent`      | a conflict frame is active and is at a pivot beat (open / escalation / endgame) |
| `survival`    | `health_state` ∈ {`badly_hurt`, `critical`} OR `risk_level == "lethal"`    |
| `social`      | conflict active AND ≥1 NPC present AND the social stance is the lever     |
| `resource`    | conflict active AND active threads/objectives genuinely intersect          |
| `temperament` | conflict active AND momentum ∈ {`reversal_imminent`, endgame}              |

The renderer's `Triggerable` row only fires when the salience
gate (`conflict active OR health pressed OR risk lethal`) passes
**and** the per-archetype shape above matches. These are
*hints*, not mandates — the GM still applies narrative judgment
to decide whether the turn is a true pivot, and emits at most
one labeled option per turn even if multiple are primed.

**Default to zero.** Trivial turns — exposition, recap,
planning, travel, shopping, small talk, mid-investigation
thinking — get no labeled options, even when a conflict frame
is technically active or `risk_level == "tense"`.

### What labeled options do

- Open a *special approach*; they are **not** automatic wins.
- May reduce risk, reveal information, create alternate routes,
  shift a conflict's `kind` (e.g., debate → social negotiation),
  or improve positioning.
- Still consume one of A/B/C — labels *replace* an unlabeled
  tactic, they do not add a fifth option. The free-form D slot
  stays fixed.
- Picking a labeled innate option does not exhaust the trait —
  innate traits are passive tendencies and remain available.

Full label format and rules are in
`genre_packs/universal/prompts/gm_system_fragment.md`
§ *Pre-options scan* and § *Labeled special options*.

## What innate traits are NOT

- Not numeric buffs. No "+2 Perception". The archetypes are
  dispositional flavors, enacted by the GM's narration.
- Not class selections. A `talent`-heavy build is not a "scholar
  class"; it is a direction in which events lean when the dice
  would otherwise be flat.
- Not destiny traits. Destiny traits fire at specific moments;
  innate traits are the background hum of the PC's personality and
  competence.
