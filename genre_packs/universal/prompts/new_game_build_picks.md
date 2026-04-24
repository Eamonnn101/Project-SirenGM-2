---
name: new_game_build_picks
stage: runtime.new_game
---

# New-game · Build picks (artifact + 3 innate traits)

Genre-agnostic prompt fragment for the two pick steps inserted
between `playbooks/new-game.md` Step 1 (protagonist) and Step 2
(opening scene). Read the pack's `progression_rules.md` before
running these steps; it supplies the novel-themed names, flavor,
and activation rules for all 8 options (3 artifact + 5 innate).

All options must be rendered in the pack's declared `language`
(`zh` or `en`, from `packs/<name>/index.md`).

## Context to load before picking

- `packs/<pack>/progression_rules.md` — the authoritative source
  for artifact + innate + destiny novel-themed instances.
- `saves/<pack>/meta_progress.json` (if exists) — drives the
  **unseen-first draft bias**. While pool coverage is below ~70%,
  prefer archetype keys that have not yet been seen.
- The protagonist's character page — the pick blocks can weave
  light flavor that fits who the PC is, but the mechanical
  archetype must not shift based on the PC.

## Step 1.5 · Artifact pick block

Pick one novel-themed instance per archetype (`insight`,
`bond_rescue`, `companion`) from `progression_rules.md` §3.
Order the 3 options per `artifact_draw_order(meta)` — the draft
bias influences prominence, not composition; all 3 archetypes
always appear.

Layout (zh reference; `en` uses English labels with `| …` rule
characters). The box is rendered verbatim, Unicode box glyphs
included. Do **not** add a prose paragraph before or after the
block; the GM's job here is a clean pick prompt, not a scene.

```
╔══ 开局抉择 · 法宝 ══╗
A. <artifact_insight_name>〔洞见〕
   <one-line flavor from progression_rules.md>
   效用：<one-line activation rule>
B. <artifact_bond_rescue_name>〔援护〕
   <flavor>
   效用：<activation rule>
C. <artifact_companion_name>〔随行〕
   <flavor>
   效用：<activation rule>
D. 让我自己描述想要的法宝（自由脑洞）
╚═════════════════════╝
```

If the player picks A/B/C, emit `player_artifact_set` with that
archetype's data from `progression_rules.md`. If the player picks
D (free-form), the GM translates the player's description into the
closest of the three archetypes, names it in pack-language voice,
and emits `player_artifact_set` with `archetype` set to the
matched universal key (one of `insight`, `bond_rescue`,
`companion`). Tell the player briefly how you classified their
description so they can correct you.

## Step 1.6 · Innate pick block

Show all 5 archetype options (`talent`, `survival`, `social`,
`resource`, `temperament`) from `progression_rules.md` §4.
Order per `innate_draw_order(meta)`. The player picks **3 distinct
archetypes**; duplicates are rejected.

```
╔══ 开局抉择 · 天赋（任选三种不同档） ══╗
1. <talent_name>〔才华〕
   <one-line flavor>
2. <survival_name>〔坚韧〕
   <flavor>
3. <social_name>〔人情〕
   <flavor>
4. <resource_name>〔缘分〕
   <flavor>
5. <temperament_name>〔性情〕
   <flavor>

请选三项（如 1、3、4）。不同档位之间互不重复。
╚══════════════════════════════════════╝
```

Accept `1, 3, 4` / `A, C, D` / `才华 + 人情 + 缘分` — any
comma/space separated list of three distinct picks. If the player
picks fewer than 3, fewer distinct archetypes, or an unknown
option, restate the block and ask for exactly 3 distinct picks.
The `en` variant uses `A–E` letter labels and English archetype
names.

On valid picks, emit `player_innate_traits_set` with exactly 3
`Trait` dicts (each `kind: "innate"`, `archetype` set to the
universal key, `name`/`slug`/`notes` from progression_rules.md).

## After both picks

- Set `player.stage_index = 0` and `player.stage_label` to the
  stage-0 label from `progression_rules.md` §1.
- Set `player.health_state = "healthy"`.
- Proceed to `playbooks/new-game.md` Step 2 (opening scene).
- On the first turn, the compact turn HUD (see
  `gm_system_fragment.md`) must show all four rows — stage,
  health, artifact, innate traits — populated.

## Common failure modes to avoid

- Rendering the block as narrative prose instead of the literal
  Unicode box. The box is a chat-reply block, not in-world text.
- Inventing a 4th artifact archetype to better fit the novel.
  Three is the MVP. Flavor within the three seeds.
- Letting the PC's novel-themed "cultivation root" or similar
  bypass the 3-distinct-archetypes rule.
- Forgetting to patch `player_artifact_set` and
  `player_innate_traits_set` — the HUD will show "(未择) /
  (unchosen)" and `lint_save.py` will flag it.
