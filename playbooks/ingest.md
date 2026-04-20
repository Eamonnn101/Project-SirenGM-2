# Playbook · ingest

Compile one or more novels into user packs.

## Invocation forms

Batch is the main path — each eligible file in `raw/novel/` becomes
its own pack, auto-named from the filename. The single-file explicit
form is still supported when the user wants to name the pack
themselves or pin a language.

All forms below are recognized in either English or Chinese. The
agent is lenient about exact wording; these are the canonical
shapes.

### Batch — preferred

Any of these are equivalent:

> "Ingest novels" / "导入小说"
>
> "Ingest `raw/novel/`" / "导入 `raw/novel/`"

The agent scans `raw/novel/` and compiles **every eligible source**
into its own pack, auto-naming each from the filename.

### Eligibility filter

Include only top-level files in `raw/novel/` that all of:

- have a case-insensitive extension of `.txt` or `.md`,
- are UTF-8 decodable (spot-check the first few KB; skip on
  `UnicodeDecodeError`),
- are not `README.md`, and
- do not start with `.`.

Subdirectories are not recursed — combine multi-file novels into a
single text file first.

Any file skipped by this filter is reported in the pre-scan summary
(see "Pre-scan" below) with a short reason, e.g. `skipped: unsupported
extension .pdf — convert to .txt/.md first`. Unsupported sources are
never passed to Stage 0.

### Pack-slug derivation

From the filename stem:

- Lowercase; replace spaces, punctuation, and separators with `_`;
  keep only ASCII `[a-z0-9_]`; collapse runs of `_`; strip leading /
  trailing `_`.
- Example: `My Cool Book.txt` → `my_cool_book`.
- Example: `Book-II (final).md` → `book_ii_final`.
- If the stem is **entirely non-ASCII** (e.g. `凡人修仙传.txt`), the
  agent proposes an ASCII slug (transliterated if possible) and asks
  the user to confirm or override before proceeding.

### Pre-scan (before any ingest starts)

In batch mode, compute the slug for every eligible source first and
build a `source → slug` map. Then:

1. **In-batch collisions.** If two distinct sources map to the same
   slug (e.g. `My Book.txt` and `my-book.md` both → `my_book`, or two
   non-ASCII titles transliterate to the same ASCII slug), **stop
   before Stage 0** and report the collision. Ask the user to rename
   one of the files or supply an explicit alternate slug for one of
   them. Do not auto-resolve by suffixing `_2`, `_3`, … — silent
   disambiguation hides a user decision.
2. **Existing-pack skips.** If `packs/<slug>/` already exists,
   **do not assume it came from the same source**. If the pack's
   `index.md` records a `source_file` that equals the current
   filename, treat it as a legitimate skip and report `already
   ingested from <source_file>`. If `source_file` is missing or
   differs, stop and ask the user whether this is the same novel
   (skip), a collision (rename / alternate slug), or a re-ingest.

Print the pre-scan summary (one line per source: filename → slug →
action) and wait for the user to confirm before Stage 0 runs on
anything.

### Re-ingest

Invoked only when the user explicitly says so (e.g. "re-ingest
`<slug>`"). Re-ingest wipes `packs/<slug>/` first, except any
`novel_rules.md` the user has hand-edited; if that file has mtime
newer than `index.md`, the agent asks before overwriting.

### Stage-0 bookkeeping

When Stage 0 writes `packs/<slug>/index.md`, include
`source_file: <relative path under raw/novel/>` in the frontmatter so
later batches can tell real collisions from legitimate skips.

### Explicit — single-file with named pack

> "Ingest `raw/novel/<file>.txt` as pack `<name>`" /
> "将 `raw/novel/<file>.txt` 导入为 pack `<name>`"

Compile a single novel into a named pack. The user may optionally
pin the language by appending " in English" / " in Chinese" in
English, or "，用英文" / "，用中文" in Chinese; otherwise the
agent auto-detects it during Stage 0.

---

## Per-novel pipeline

For each eligible novel (one in explicit mode; each file in batch
mode), run Stages 0–5 in order. In batch mode, process novels one
at a time; do **not** parallelize. Stage 0's stop-and-summarize
happens per novel so the user can course-correct before committing
to the rest of the pipeline on that file.

**Preconditions per novel:**
- The source file exists and is UTF-8.
- `genre_packs/universal/` exists and lints clean.
- `packs/<slug>/` does not exist (or the user authorized re-ingest).

**Layers touched:** creates `packs/<slug>/`; reads `raw/novel/<file>`
and `genre_packs/universal/**`; never writes `raw/`.

### Stage 0 · Sample and synthesize

Read the first ~20–40 KB of the novel (roughly one to three chapters).
Then, in this order, write:

1. `packs/<slug>/index.md` with frontmatter:
   ```yaml
   name: <slug>
   kind: user
   inherits_genre: universal
   language: zh   # must be 'zh' or 'en' — the only two supported
   source_file: <relative path under raw/novel/>   # e.g. my_novel.txt
   ```
   If the user passed an explicit language override at invocation, use
   that instead of the detection. Only `zh` and `en` are accepted; if
   the novel is primarily in another language, stop and ask the user
   to supply a zh/en translation first. `source_file` lets later batch runs distinguish
   "same novel, already ingested" from "different novel, slug
   collision" (see Pre-scan).

2. `packs/<slug>/novel_rules.md` — the load-bearing novel-specific
   rulebook, **in the pack's declared language**. Sections:
   - Power / skill / cultivation system (or "none — mundane setting").
   - Social order (factions, ranks, honorifics, taboos).
   - Technology and era baseline.
   - Tone and register.
   - Hard canon (resurrection, time travel, cross-world — on/off).
   - Naming conventions.

   Keep it tight — the GM reads it on every turn.

3. `packs/<slug>/canon_guardrails.md` — may be a stub at this stage
   (a heading plus "no novel-specific overrides yet"); Stage 4 may
   refine it.

Stop after Stage 0 and summarize what you synthesized so the user can
correct any misread of the setting before committing to full ingest.
In batch mode, summarize and confirm per novel; do not proceed to
Stage 1 for any pack until the user green-lights that pack's Stage 0.

### Stage 1 · chunk

Split the novel into chapter-sized chunks with the deterministic helper:

```bash
python tools/chunker.py raw/novel/<file> --pack <slug>
```

This writes `packs/<slug>/.ingest/chunks.jsonl`. Verify line count is
sane (a 200k-char novel should yield roughly 20–80 chunks). If the
novel is short (<5 chapters) or has no chapter markers, the chunker
falls back to ~3000-char paragraph-boundary chunks.

### Stage 2 · extract

Read `genre_packs/universal/prompts/ingest_extract_system.md` once.
Note the pack's `language` (from `packs/<slug>/index.md`) and the
synthesized `novel_rules.md` so extraction uses terminology the novel
actually uses. Then iterate `chunks.jsonl` chunk by chunk.

For each chunk, produce zero or more JSON objects describing mentions
of `character`, `faction`, `location`, `system_item`, `event`,
`relationship` found in the chunk. Append each as one JSON line to
`packs/<slug>/.ingest/mentions.jsonl`. Include `source_chunk: <id>` and
a short `evidence` quote (≤60 chars, verbatim from the source) on
every mention.

Guardrails: never fabricate entities that do not appear in the chunk;
keep slugs stable across chunks (same entity → same slug); slugs are
always ASCII snake_case (for Chinese sources, romanize via pinyin).
If you're uncertain whether two mentions refer to the same entity,
emit them as separate slugs and let Stage 4 (index) record the
ambiguity.

Resumability: Stage 2 is append-only per chunk. If interrupted,
inspect the highest `source_chunk` in `mentions.jsonl` and resume from
the next chunk.

### Stage 3 · draft

Read `genre_packs/universal/prompts/ingest_draft_system.md` once. Read
the per-kind schemas under `genre_packs/universal/schemas/*.schema.md`.
Re-read `packs/<slug>/novel_rules.md` — every drafted page must be
consistent with it.

If Stage 0's `novel_rules.md` turned out to be incomplete or wrong
based on later chunks, revise it here and note the change in
`packs/<slug>/contradictions/ambiguous_points.md`.

Group `mentions.jsonl` by `(kind, slug)`. For each group, draft a
single schema-valid page at `packs/<slug>/<kind_plural>/<slug>.md`,
with body content **in the pack's declared language**. Kinds and their
directories:

| kind | dir |
|---|---|
| character | `packs/<slug>/characters/` |
| faction | `packs/<slug>/factions/` |
| location | `packs/<slug>/locations/` |
| arc | `packs/<slug>/arcs/` (default new arcs to `flexibility: soft`) |
| event | `packs/<slug>/events/` (omit `can_skip` unless overriding the kind's default — `intended`/`triggerable` → `true`, `player_boundary` → `false`) |
| system_item | `packs/<slug>/systems/` (optional) — create a page **only** if other pack pages reference the item as `[[slug]]` (e.g. a named artifact or signature herb); otherwise the mention is absorbed into the referring page's body and discarded. Novel-level mechanical rules stay in `packs/<slug>/novel_rules.md` — do not duplicate them into per-entity pages. |

Every page has YAML frontmatter matching its schema and a short
markdown body synthesized from the mentions.

Guardrails:
- No numeric combat stats. Use qualitative language.
- Cross-references to other entities use the piped wiki-link dialect
  `[[slug|Display]]`, where `slug` is the canonical ASCII snake_case
  id and `Display` is the native-language label the reader sees.
  Bare `[[slug]]` is only valid when the target entity's `name` is
  already ASCII; packs whose entities have non-ASCII names **must**
  always carry a display label (the lint rejects bare slugs pointing
  at non-ASCII-named entities). See
  `genre_packs/universal/prompts/ingest_draft_system.md` for the
  full rule; `python tools/render_pack.py --pack <slug>` rewrites
  these into plain Markdown links under `packs/<slug>/_rendered/`.
- If mentions conflict, prefer the latest chunk and record the older
  claim under `packs/<slug>/contradictions/ambiguous_points.md`
  (append-only).

### Stage 4 · index

Ensure the following files exist and are coherent (overwrite if
rerunning):

- `packs/<slug>/index.md` — frontmatter `name`, `kind: user`,
  `inherits_genre: universal`, `language: <code>`; body links every
  page by category.
- `packs/<slug>/relationships/relationship_matrix.md` — bullet list of
  relationship mentions grouped by `from` slug.
- `packs/<slug>/contradictions/ambiguous_points.md` — any ambiguities
  you logged during draft.
- `packs/<slug>/timeline.md` — chronological list of events with their
  chunk provenance.
- `packs/<slug>/canon_guardrails.md` — novel-specific overrides on top
  of the universal guardrails (may be empty but must exist with a
  heading).
- `packs/<slug>/novel_rules.md` — finalized per-novel ruleset (written
  in Stage 0, refined here if late chunks forced changes).
- `packs/<slug>/overview.md` — 200–400 word synopsis in the pack's
  language.

### Stage 5 · lint

```bash
python tools/lint_pack.py --pack <slug>
```

If issues are reported, loop back to Stage 3 for the affected pages.
Do NOT proceed to `playbooks/new-game.md` until lint is clean.

Optionally, render the pack's wiki-link cross-references into plain
Markdown for reading in a non-wikilink editor:

```bash
python tools/render_pack.py --pack <slug>
```

This writes expanded copies under `packs/<slug>/_rendered/` (the
canonical sources keep the `[[slug|Display]]` form).

## What to tell the user at the end

Per pack, report: detected/declared language, chunk count, mention
count, page counts per kind, lint status, and a one-paragraph overall
synopsis.

In batch mode, also report a summary table at the end listing each
source file, its derived slug, and the outcome (`ingested`, `skipped
(exists)`, `failed lint`, etc.). Do NOT start a game yet — wait for
the user to invoke `playbooks/new-game.md`.
