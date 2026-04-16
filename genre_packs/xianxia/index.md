---
name: xianxia
kind: genre
version: 0.1.0
---

# Genre · 修仙 (xianxia)

Genre-level template for xianxia (cultivation) novels. This pack contains **only reusable genre assets** — style conventions, generic guardrails, shared cultivation/social mechanics, entity frontmatter schemas, and ingest/GM prompt fragments.

It MUST NOT contain novel-specific characters, factions, locations, timelines, or pre-written arcs. Those live in user packs the agent generates from a specific novel per `playbooks/ingest.md`.

## Index

### Conventions
- [style_guide.md](style_guide.md) — how GM narrates in this genre
- [canon_guardrails.md](canon_guardrails.md) — generic xianxia rules that no novel should break

### Shared systems
- [systems/cultivation.md](systems/cultivation.md) — realm progression + qi mechanics
- [systems/social_rules.md](systems/social_rules.md) — sect etiquette, honorifics, forbidden acts

### Schemas (for ingest + runtime validation)
- [schemas/character.schema.md](schemas/character.schema.md)
- [schemas/faction.schema.md](schemas/faction.schema.md)
- [schemas/location.schema.md](schemas/location.schema.md)
- [schemas/arc.schema.md](schemas/arc.schema.md)
- [schemas/event.schema.md](schemas/event.schema.md)

### Prompt fragments
- [prompts/ingest_extract_system.md](prompts/ingest_extract_system.md) — spliced into the extract LLM call
- [prompts/ingest_draft_system.md](prompts/ingest_draft_system.md) — spliced into the draft-pages LLM call
- [prompts/gm_system_fragment.md](prompts/gm_system_fragment.md) — spliced into the GM narrator prompt
