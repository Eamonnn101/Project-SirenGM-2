---
name: ingest_extract_system
stage: ingest.extract
---

# Ingest Extract · Universal instructions

Genre-agnostic instructions the agent follows during the **extract**
step of `playbooks/ingest.md`. Read this once before processing any
chunk. Then, for each chunk in `packs/<pack>/.ingest/chunks.jsonl`,
produce zero or more JSON lines in `packs/<pack>/.ingest/mentions.jsonl`.

## Language

The user pack's `index.md` declares `language: zh` or `language: en`
(the only two supported values). Load that value before extracting.

- `name` fields hold the **native form** from the novel, in the
  pack's language.
- `slug` fields are always ASCII snake_case. For Chinese sources,
  romanize via pinyin and stay consistent throughout the pack.
- `evidence` quotes are verbatim from the novel, in the source
  language.
- Free-form `notes` are written in the pack's declared language.

## Task

For each chunk of text, identify mentions of these entity kinds:

- `character` — any named individual, deity, ancestor, or personified
  being the novel treats as an actor.
- `faction` — any collective the novel treats as a coherent actor
  (sect, guild, court, corporation, tribe, cult, bloodline, crew).
- `location` — any named place with scene-level specificity (city,
  realm, room, ship).
- `system_item` — any named artifact, weapon, technique, spell, drug,
  relic, or device that the novel treats as a distinct referent.
  **Only extract when other pack pages are likely to reference it by
  slug** (`[[slug]]`); otherwise let the mention be absorbed into the
  containing entity's body.
- `event` — a discrete happening the novel stages (a battle, a
  marriage, a betrayal, a breakthrough).
- `relationship` — a directional relationship between two entities.

**Do not fabricate.** If a character is only referenced by a title or
alias, record that alias and leave `name` unknown until later chunks
reveal the personal name. Use `aliases` to preserve both forms.

## Per-mention fields

- `kind`: one of the six kinds above. This is the **mention-level**
  kind, not a schema field. The event entity has its own enum — record
  that in `event_kind` (below), never in `kind`.
- `slug`: ASCII snake_case; the **same** entity keeps the **same**
  slug across chunks in the pack.
- `name`: the native-language name most commonly used in the novel.
- `role` / `alignment` / `danger`: populate per the corresponding
  schema in `genre_packs/universal/schemas/<kind>.schema.md`. If the
  value is novel-specific (e.g. a progression label not matching any
  generic enum), put it in `progression` or a pass-through field
  documented in the schema; do not force a translation.
- For `kind: event` mentions specifically:
  - `event_kind` (enum): `intended` | `triggerable` | `player_boundary`
    per `event.schema.md`. The draft step writes this into the page's
    frontmatter `kind` field.
  - `preconditions` (list[string]): free-form trigger tags, optional.
- `source_chunk`: the chunk id the mention was drawn from.
- `evidence`: a short verbatim quote (≤ 60 chars in the source
  language) proving the entity appears in this chunk.

Relationship mentions use `{kind: "relationship", from: <slug>,
to: <slug>, relation: <string>, source_chunk, evidence}`. The
`relation` string is free-form (e.g. `master_of`, `rival_of`,
`sworn_enemy`, `parent_of`, `client_of`).

## No genre assumptions

- Do **not** force any progression/stage/rank system onto entities
  that do not have one. Leave `progression` empty if the novel does
  not track it.
- Do not invent faction affiliations the novel does not state.
- Do not flag "modern" vocabulary as anachronistic unless the novel
  itself treats it that way. The novel's genre and era are defined
  by itself.

## Anti-patterns

- Numeric combat stats (HP, ATK, damage rolls).
- Entities the chunk does not actually mention.
- Subjective evaluations of the novel ("this character is poorly
  written") — those have no place in extraction.
- Translations of names into another language. Preserve the novel's
  form.
