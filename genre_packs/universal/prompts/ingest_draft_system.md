---
name: ingest_draft_system
stage: ingest.draft
---

# Ingest Draft · Universal instructions

Genre-agnostic instructions for the **draft** step of
`playbooks/ingest.md`. Consolidate extracted mentions into
schema-valid entity pages.

## Before drafting any entity — synthesize novel_rules.md

If `packs/<pack>/novel_rules.md` does not already exist (or exists
only as a stub from Stage 0), synthesize it first from the mentions
and chunk evidence gathered so far. It captures **everything the GM
needs to know about this novel that the universal genre pack does
not specify**. Write it in the pack's declared `language`.

Required sections in `novel_rules.md`:

- **Power system** — the novel's magic/cultivation/tech/skill ladder.
  Names of stages or tiers, how advancement works, what it costs,
  what it gates. If the novel has no such system, state that
  explicitly ("mundane historical; no supernatural mechanics").
- **Social order** — how authority and affiliation work: noble
  houses, sects, guilds, ranks, titles, honorifics, courtesies,
  taboos.
- **Technology and era** — the novel's baseline (ancient, medieval,
  modern, near-future, far-future, post-apocalyptic, fantasy
  composite). Note what the novel treats as commonplace vs.
  anachronistic.
- **Tone and register** — formal/informal, archaic/contemporary, the
  novel's attitude toward death, magic, sex, violence.
- **Hard canon** — things the novel establishes as inviolable (no
  resurrection, no time travel, no cross-world travel — or the
  opposite, if the novel uses them).
- **Naming conventions** — how the novel names people, places, and
  artifacts. What sounds right vs. what would break immersion.

`novel_rules.md` is read at play start/resume, after backup writes, and
when hard canon is triggered, so keep it to the load-bearing rules only
— the things the GM needs to stay in character for *this* novel without
re-scanning the source.

## After novel_rules.md — synthesize progression_rules.md

Before drafting any entity pages, synthesize
`packs/<pack>/progression_rules.md` as well. This file re-themes
the **universal progression-layer seeds** (shipped in
`genre_packs/universal/systems/`) into novel-flavored instances.
The GM reads `progression_rules.md` at new-game (artifact + innate
pick) and at every breakthrough (destiny pick), so each section
must be complete before play begins.

Write it in the pack's declared `language`. Seven required
sections, in any order:

1. **Stages (6)** — for each `stage_index` 0..5:
   - novel-themed label (one line)
   - 1-paragraph description of what the stage feels like, what
     kinds of situations it contains, what the PC typically
     has/lacks
2. **Breakthrough triggers per stage (6 × 2–4 patterns)** — for
   each stage, list 2–4 novel-themed trigger patterns that would
   qualify as the climactic beat cueing a breakthrough. The GM
   still judges when to advance, but these give the engine
   grounded patterns rather than free judgment.
3. **Artifact archetypes (3)** — one novel-flavored instance per
   universal key (`insight`, `bond_rescue`, `companion`) with:
   - ASCII snake_case slug, novel-themed display name
   - 1-paragraph lore fit
   - one-line activation rule (when does it fire; is it
     repeatable?)
4. **Innate trait archetypes (5)** — one instance per universal
   key (`talent`, `survival`, `social`, `resource`,
   `temperament`) with slug, display name, and 1–2 sentence
   flavor.
5. **Destiny trait seeds (12)** — one instance per universal
   seed. Keep the universal archetype key in the entry's
   frontmatter so lint can validate. Each entry: slug, display
   name, 1–2 sentence effect in novel terms.
6. **Health ladder wording** — the five states (`healthy`,
   `hurt`, `badly_hurt`, `critical`, `dead`) named in novel
   voice. 1:1 mapping to the universal enum.
7. **Breakthrough voice** — a one-paragraph style guide for how
   breakthroughs feel in this novel (spiritual? political?
   combat? romantic? sci-fi?), informing the prose of both the
   breakthrough narration and the run-end coda.

`progression_rules.md` is load-bearing — `playbooks/play-turn.md`
loads it at start/resume, after backup writes, and when a progression
system is triggered. `tools/lint_pack.py` rejects user packs that are
missing any of the 7 sections.

## Per-entity drafting

Inputs:
- `entity_slug`, `entity_kind`, a list of extracted `mentions` (each
  with `chunk_id`, `evidence`, partial fields).
- The corresponding entity schema at
  `genre_packs/universal/schemas/<entity_kind>.schema.md`.
- `packs/<pack>/novel_rules.md` (read-only reference).

Output: a single markdown file at
`packs/<pack>/<entity_kind_plural>/<slug>.md` with schema-conformant
YAML frontmatter and a markdown body **in the pack's declared
language**.

### Required-field handling

- Fill every required field per the schema.
- Optional fields: include them only when the mentions support a
  concrete value. Do not invent.
- Pass-through novel-specific fields (e.g. `bloodline`, `house`,
  `augmentation`) go into frontmatter verbatim; they are preserved
  thanks to the models' `extra="allow"` setting.

### Body content

- Characters: a line or two of physical impression, then personality,
  core motive, relationship to the protagonist, salient abilities, and
  any hard character invariants.
- Factions: origin, doctrine, internal structure, alliances and
  rivalries, taboos, current direction.
- Locations: layout, who's usually there, environmental cues,
  hazards, entry conditions.
- Arcs: pacing, key beats, success/failure exits, links to other
  arcs. Default new arcs to `flexibility: soft` unless the novel
  establishes the beat as genuinely inviolable (`hard`).
- Events: follow `event.schema.md`. The mention's `event_kind` field
  becomes the page's frontmatter `kind`. Omit `can_skip` unless
  overriding the kind's default (`intended`/`triggerable` default to
  skippable; `player_boundary` defaults to non-skippable).

### Conflict resolution

If mentions disagree (e.g. two chunks give different
`progression` values for the same character), prefer the **latest**
chunk and append the older claim to
`packs/<pack>/contradictions/ambiguous_points.md` with the chunk id
and a short note.

### Cross-references

Canonical ids and display labels are separate concerns. Slugs are
always ASCII snake_case (romanized for non-Latin novels); display
labels are the native-language name the player reads.

Use the piped wiki-link dialect:

- `[[slug|Display]]` — explicit display label. **Required** in every
  Chinese pack (the target entity's `name` is Chinese, so the slug
  alone would surface as unreadable pinyin). Pick `Display` from the
  target's `name` or one of its `aliases` — whichever reads most
  naturally in the current sentence.
- `[[slug]]` — bare form. **Only** acceptable when the target
  entity's `name` is ASCII (typical in English packs). Never emit
  bare `[[xiao_yan]]`.

The slug is what the lint resolves; the display label is what the
player reads. `tools/lint_pack.py` rejects bare slugs that point at
non-ASCII-named entities. Wiki-link readers (Obsidian, etc.) follow
`[[slug|Display]]` natively. Do not hyperlink to URLs or external docs.

## Anti-patterns

- Granting abilities beyond what the mentions support.
- Introducing factions, artifacts, or places the novel does not
  mention.
- "Once the player arrives, they will ..." — entity pages describe
  the world, not the player's path. That belongs in arc/event pages.
- Mixing languages in a single body. Stay in the pack's declared
  language (names may remain in their native script).
- Authoring a fresh `novel_rules.md` on every entity draft — it is
  written **once** at the start of the draft stage and only amended
  if new chunks force a rewrite (in which case record the change in
  `ambiguous_points.md`).
