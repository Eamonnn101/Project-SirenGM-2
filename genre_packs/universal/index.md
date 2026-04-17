---
name: universal
kind: genre
version: 0.1.0
---

# Genre · Universal

Genre-agnostic scaffolding used by every user pack in this repo. It
contains no world-specific facts — no characters, factions, locations,
arcs, events — and no fiction-specific mechanics. All novel-specific
rules live in `packs/<name>/novel_rules.md`, synthesized during ingest.

Each user pack declares its own `language` in `index.md` frontmatter
(`zh` or `en` — the only two supported values; `zh` is the rendering
default). The agent writes narration, entity names, and novel rules
in that language. Slugs remain ASCII (`[a-z0-9_]+`) regardless.

## Index

### Conventions
- [style_guide.md](style_guide.md) — how the GM narrates, regardless of genre
- [canon_guardrails.md](canon_guardrails.md) — principles that apply to every novel

### Shared systems
- [systems/README.md](systems/README.md) — placeholder; novel-specific systems live in `packs/<name>/novel_rules.md`

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
