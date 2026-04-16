# Playbook · ingest

Compile a novel into a user pack. Invoked when the user says something like
"ingest `raw/novel/<file>.txt` as pack `<name>` with genre xianxia."

**Preconditions:**
- `raw/novel/<file>.txt` exists and is utf-8.
- `genre_packs/<genre>/` exists and lints clean.
- `packs/<name>/` does not exist yet, or the user has explicitly agreed to
  overwrite / resume.

**Layers touched:** creates `packs/<name>/`; reads `raw/novel/<file>.txt`
and `genre_packs/<genre>/**`; never writes `raw/`.

---

## Stage 1 · chunk

Split the novel into chapter-sized chunks. Prefer the deterministic helper:

```bash
python tools/chunker.py raw/novel/<file>.txt --pack <name>
```

This writes `packs/<name>/.ingest/chunks.jsonl`. Verify line count is sane
(a 200k-char novel should yield roughly 20–80 chunks). If the novel is
short (<5 chapters) or has no chapter markers, the chunker falls back to
~3000-char paragraph-boundary chunks.

## Stage 2 · extract

Read `genre_packs/<genre>/prompts/ingest_extract_system.md` once. Then
iterate `chunks.jsonl` chunk by chunk.

For each chunk, produce zero or more JSON objects describing mentions of
`character`, `faction`, `location`, `system_item`, `event`, `relationship`
found in the chunk. Append each as one JSON line to
`packs/<name>/.ingest/mentions.jsonl`. Include `source_chunk: <id>` and a
short `evidence` quote (≤60 chars) on every mention.

Guardrails: never fabricate entities that do not appear in the chunk; keep
slugs stable across chunks (same entity → same slug). If you're uncertain
whether two mentions refer to the same entity, emit them as separate slugs
and let Stage 4 (index) record the ambiguity.

Resumability: Stage 2 is append-only per chunk. If interrupted, inspect the
highest `source_chunk` in `mentions.jsonl` and resume from the next chunk.

## Stage 3 · draft

Read `genre_packs/<genre>/prompts/ingest_draft_system.md` once. Read the
per-kind schemas under `genre_packs/<genre>/schemas/*.schema.md`.

Group `mentions.jsonl` by `(kind, slug)`. For each group, draft a single
schema-valid page at `packs/<name>/<kind_plural>/<slug>.md`. Kinds and
their directories:

| kind | dir |
|---|---|
| character | `packs/<name>/characters/` |
| faction | `packs/<name>/factions/` |
| location | `packs/<name>/locations/` |
| arc | `packs/<name>/arcs/` |
| event | `packs/<name>/events/` |
| system_item | `packs/<name>/systems/` (optional) — create a page **only** if other pack pages reference the item as `[[slug]]` (e.g. a named artifact or signature herb); otherwise the mention is absorbed into the referring page's body and discarded. Genre-level mechanics (境界阶梯、社交礼仪) stay under `genre_packs/<genre>/systems/` and must not be duplicated into the user pack. |

Every page has YAML frontmatter matching its schema and a short markdown
body synthesized from the mentions.

Guardrails:
- No numeric combat stats. Use qualitative language.
- Cross-references to other entities must use `[[slug]]` syntax.
- If mentions conflict, prefer the latest chunk and record the older claim
  under `packs/<name>/contradictions/ambiguous_points.md` (append-only).

## Stage 4 · index

Write (or regenerate) three files:

- `packs/<name>/index.md` — frontmatter `name: <name>`, `kind: user`,
  `inherits_genre: <genre>`; body links every page by category.
- `packs/<name>/relationships/relationship_matrix.md` — bullet list of
  relationship mentions grouped by `from` slug.
- `packs/<name>/contradictions/ambiguous_points.md` — any ambiguities you
  logged during draft.
- `packs/<name>/timeline.md` — chronological list of events with their
  chunk provenance.
- `packs/<name>/canon_guardrails.md` — novel-specific overrides on top of
  the genre guardrails (may be empty but must exist with a heading).
- `packs/<name>/overview.md` — 200–400 word synopsis.

## Stage 5 · lint

```bash
python tools/lint_pack.py --pack <name>
```

If issues are reported, loop back to Stage 3 for the affected pages. Do
NOT proceed to `playbooks/new-game.md` until lint is clean.

## What to tell the user at the end

Report: chunk count, mention count, page counts per kind, lint status,
and one-paragraph summary of the overall synopsis. Do NOT start a game
yet — wait for the user to invoke `playbooks/new-game.md`.
