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

## What innate traits are NOT

- Not numeric buffs. No "+2 Perception". The archetypes are
  dispositional flavors, enacted by the GM's narration.
- Not class selections. A `talent`-heavy build is not a "scholar
  class"; it is a direction in which events lean when the dice
  would otherwise be flat.
- Not destiny traits. Destiny traits fire at specific moments;
  innate traits are the background hum of the PC's personality and
  competence.
