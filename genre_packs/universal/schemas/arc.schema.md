---
name: arc_schema
entity: arc
---

# Arc Frontmatter Schema

User-pack `arcs/<slug>.md` frontmatter.

## Required

- `slug` (string).
- `name` (string): arc title in the pack's language.
- `status` (enum): `opening`, `active`, `suspended`, `closed`.
- `summary` (string): a sentence describing the arc's central goal or
  conflict.

## Optional

- `driving_entities` (list[string]): slugs of characters or factions
  whose actions drive the arc.
- `flexibility` (enum, default `soft`): how tightly the GM must honor
  this arc when the player moves off it.
  - `soft` (default): a *suggestion* the GM may follow when the player
    shows interest, but the GM **must not** herd the player toward it.
    If the player's action diverges, mark the arc `suspended` or emit
    `active_threads_remove`. Off-rails play on a `soft` arc is fine
    and does not require a divergence log.
  - `hard`: the arc is canon — its core facts must hold. The GM may
    still delay or reroute it, but narration must not contradict its
    established beats (e.g. "the empire falls in the tenth year" is
    world-fixed even if the player ignores it).

## Body

Cover: pacing (rough turn intervals if meaningful), key beats,
success and failure exits, links to other arcs. Keep this short —
arcs are scaffolding, not scripts.

Cross-references use the piped wiki-link dialect `[[slug|Display]]`;
see `prompts/ingest_draft_system.md`. Bare `[[slug]]` is only valid
when the target entity's `name` is ASCII.
