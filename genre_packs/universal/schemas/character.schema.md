---
name: character_schema
entity: character
---

# Character Frontmatter Schema

User-pack `characters/<slug>.md` frontmatter. The ingest draft stage
must produce these fields; lint rejects missing required fields.

## Required

- `slug` (string, snake_case, ASCII): unique id in this category.
- `name` (string): display name **in the pack's declared `language`**.
  For non-Latin names, put the native form here and romanize the slug.
- `role` (string): free-form role label, e.g. `protagonist`, `mentor`,
  `rival`, `antagonist`, `ally`, `informant`. One character per user
  pack must have `role: protagonist`.

## Optional but recommended

- `aliases` (list[string]): nicknames, former names, titles.
- `affiliation` (string): slug of a faction page. Empty means unaffiliated.
- `progression` (string): free-form label for the character's standing
  on whatever power/skill/social ladder the novel uses. Examples:
  `"筑基中期"`, `"Lieutenant"`, `"Level 12 Ranger"`, `"Arcanum Apprentice"`.
  The exact label space is defined in `packs/<name>/novel_rules.md`.
- `status` (enum): `alive` (default), `injured`, `unconscious`, `dead`,
  `missing`, `unknown`. Matches `PlayerState.status`.
- `location` (string): slug of a location page where the character is
  usually found (used to seed opening scenes).

## Novel-specific frontmatter

Any field not listed above passes through via the model's
`extra="allow"` config and is preserved verbatim in the pack. Use this
to record fields the novel actually exercises (e.g. `bloodline`,
`augmentation_level`, `spellbook`, `house`). Do **not** add xianxia,
d&d, or any other genre-specific field unless the novel in question
uses it.

## Body

The body is reference text the GM reads when the character is in
scene. Cover: physical impression (a line or two), personality,
core motive, relationship to the protagonist, salient abilities, and
any hard character invariants ("would never betray the guild",
"refuses to lie"). Do not describe "what happens when the player
does X" — that is the job of arc/event pages.

Cross-references to other entities use `[[slug]]` syntax.

## Anti-patterns

- Numeric combat stats (HP, ATK, DEF).
- Emoji.
- Cross-references to entities that do not exist in the pack (lint
  will reject them).
- "Player will ..." narration — character pages describe the world,
  not the player's path through it.
