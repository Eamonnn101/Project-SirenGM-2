---
name: faction_schema
entity: faction
---

# Faction Frontmatter Schema

User-pack `factions/<slug>.md` frontmatter. "Faction" here is a broad
umbrella — a sect, guild, court, corporation, tribe, cult, or any
collective the novel treats as a coherent actor.

## Required

- `slug` (string, snake_case, ASCII).
- `name` (string): display name in the pack's language.
- `alignment` (string): free-form label. Examples: `orthodox`,
  `demonic`, `neutral`, `lawful`, `chaotic`, `rebel`, `crown`,
  `corporate`, `underground`. Use the vocabulary the novel actually
  uses; the schema does not constrain it.

## Optional

- `seat` (string): slug of a location page where the faction is based.
- `leaders` (list[string]): slugs of character pages for the leadership
  (faction heads, council members, captains).

## Novel-specific frontmatter

Extra fields pass through. Use these for novel-specific attributes
(`tier`, `doctrine`, `tech_level`, `patron_deity`, etc.) that the
novel actually exercises.

## Body

Cover: origin or founding principle, core doctrine or signature craft,
internal structure, standing alliances and rivalries, hard taboos,
recent direction. Do not list individual members' histories — those
belong on their character pages.

Cross-references use the piped wiki-link dialect `[[slug|Display]]`;
see `prompts/ingest_draft_system.md`. Bare `[[slug]]` is only valid
when the target entity's `name` is ASCII.
