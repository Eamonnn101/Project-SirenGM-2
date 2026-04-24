---
name: breakthrough_pick
stage: runtime.gm
---

# Runtime · Breakthrough pick block

Genre-agnostic prompt fragment for the turn on which the GM judges
a breakthrough has landed. Replaces the usual A/B/C/D options with
a destiny-pick block. Triggered by the same turn's patch emitting
`player_stage_advance: {new_index, new_label}`.

## When to fire a breakthrough

Read `packs/<pack>/progression_rules.md` §2 ("Breakthrough triggers
per stage") — the user pack supplies 2–4 novel-themed trigger
patterns per stage. Match the current climactic beat against those
patterns. If no pattern clearly matches, **do not** advance the
stage yet. The breakthrough should feel earned by the narrative,
not scheduled.

Soft rules (also codified in `systems/stages.md`):

- Max 5 advances per run.
- Never on a non-climactic turn.
- Never two stages in one turn.
- No regression — stages only move forward.

## Turn output format

When a breakthrough fires, the turn has three parts in this order:

1. **Short narration** of the breakthrough beat (1–3 short
   paragraphs in pack language, honoring the normal narration
   length budget). Do NOT stretch into the full per-turn budget
   unless the beat genuinely needs it — the breakthrough block
   below is the player's focus.
2. **Breakthrough block** (Unicode box, rendered verbatim,
   replacing A/B/C/D).
3. **No additional options** beyond the block. The usual A/B/C/D
   does not appear on this turn.

Layout (zh reference; `en` uses English labels and `| ` rule
characters):

```
╔══ 破境 · <new_stage_label>〔第 <new_index>/5 境〕══╗
触机：<one-line echo of the narrative trigger that fired>

A. <destiny_1_name>〔<family_label>〕
   <1–2 sentence effect in novel terms>
B. <destiny_2_name>〔<family_label>〕
   <effect>
C. <destiny_3_name>〔<family_label>〕
   <effect>
D. 拒此劫命格，静守本心
   （境界照常进阶，但此次不取命格）
╚══════════════════════════════════════╝
```

The family labels are fixed strings per universal archetype group
(Survival / Insight / Desperation / Companion). Use the pack
language's family names (e.g. `生机 / 洞察 / 拼搏 / 羁绊` in zh,
`Survival / Insight / Desperation / Companion` in en).

## How to pick the 3 options

Apply `destiny_draw_order(meta, already_picked_in_run)` from
`tools/_progression.py`:

1. Filter out destiny archetypes the PC already has this run.
2. Apply unseen-first bias against
   `meta.seen_destiny_archetypes`.
3. Also prefer archetypes **not already present in the PC's
   innate traits** (soft bias — skip if it conflicts with rule 2).
4. Take the first 3 from the ordered list.

For each of the 3, pull the novel-themed instance from
`progression_rules.md` §5 for that archetype key. Never invent a
new archetype; all 12 are fixed in the universal pool.

## Player response

The player replies with `A`, `B`, `C`, or `D` (or a prose
restatement). Interpret the reply:

- **A / B / C** → emit `player_destiny_trait_add` with the chosen
  trait's novel-themed slug/name/notes from
  `progression_rules.md`, `archetype` set to the universal key,
  `kind: "destiny"`, `source_stage: <new_index>`.
- **D** → emit no destiny-add patch. The stage_index is already
  at `new_index` from the previous turn's `player_stage_advance`;
  the run continues without a destiny for this breakthrough.

After the response turn, resume normal A/B/C/D play per
`playbooks/play-turn.md`.

## Common failure modes

- Offering a destiny the player already has (violates the
  "not already picked this run" filter).
- Inventing a novel-themed destiny that does not map to one of
  the 12 universal seeds. The archetype key must match.
- Narrating the breakthrough across 4+ paragraphs. Keep the prose
  focused; the block is the player-facing milestone.
- Forgetting the D fallback. It is fixed verbatim per language.
- Emitting both a destiny-pick and an A/B/C/D options block on
  the same turn. Pick one — the breakthrough turn replaces the
  usual options.
