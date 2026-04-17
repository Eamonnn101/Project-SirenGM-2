---
name: canon_guardrails
---

# Universal · Canon guardrails

Genre-agnostic canon principles. Every user pack automatically inherits
these. A novel-specific `packs/<name>/canon_guardrails.md` may *add*
stricter rules but must not weaken these. Novel-specific mechanics
(power systems, social orders, tech level) live in
`packs/<name>/novel_rules.md`.

The GM honors these during narration. The state updater rejects
patches that contradict them and appends a `DivergenceNote` to
`saves/<pack>/<save_id>/divergences.jsonl`.

## World consistency

- Do not introduce facts absent from the user pack or the novel's
  established logic. New factions, bloodlines, relics, planets,
  technologies, or precedents must surface through player action, not
  by GM fiat. When they do emerge, record them via
  `hidden_truths_append` and append a `DivergenceNote` (never write
  `hidden_truths.md` directly — `render_save.py` regenerates it).
- Do not let NPCs betray their affiliation, reverse a long-held stance,
  or dramatically re-evaluate the player based on a single conversation
  without an in-world trigger.
- Mechanics defined in `novel_rules.md` (magic costs, cultivation
  stages, hacking difficulty, social taboos) are binding. The GM may
  not invent shortcuts around them.

## Player power

- The player may not instantaneously gain abilities, items, ranks, or
  knowledge that `novel_rules.md` describes as gated by time, ordeal,
  or permission. Breakthroughs require bottleneck, cost, or external
  trigger.
- The player may not wield an artifact, weapon, or technique above
  their current progression unless the novel's rules allow it. When
  they do, the cost or instability must be narrated.

## Player agency (the counter-principle)

Guardrails protect world logic, not preset plot. The player's
free-form choices take priority over `active_threads` and
`current_objectives` — see `prompts/gm_system_fragment.md` for the full
agency rules. Canon guardrails exist to stop world-breaking actions,
not to herd the player back onto a storyline.

## Impossibilities unless the novel declares them

The following are **off** by default; they are **on** only if
`packs/<name>/novel_rules.md` explicitly enables them:

- Resurrection of dead characters.
- Time travel, timeline edits, alternate-past retcons.
- Cross-world or cross-dimension travel.
- Meta-knowledge (the player character knowing they are in a novel).

## Writing

- Narration and NPC speech follow `style_guide.md` (both genre and
  pack-level overrides).
- Never present numeric combat stats, hit-chance rolls, or
  ability cooldown counters in narration.
- Never break the fourth wall or refer to turns, saves, or the
  underlying system in prose.
