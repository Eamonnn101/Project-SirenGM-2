# Project SirenGM 2

**AI compiles a novel into a playable world.**

A file-driven, agent-native MVP that validates:

> An agent (Claude Code or Codex) can compile a user-supplied novel
> (any genre, any language) into a runnable Story Pack, and then run
> a coherent 20–50-turn game against that pack with persistent state
> across save/load — using only file I/O and the agent's own LLM
> calls, no custom runtime.

The thesis is **"compile novel → playable world,"** not "play inside a
prebuilt world." There is no ready-made sample pack — the product path
is ingest.

Adapted from the [llm-wiki](./llm-wiki.md) pattern: raw sources are
immutable, the pack is an LLM-maintained persistent middle layer, and
runtime reads from the compiled pack + structured save instead of
re-deriving from raw text on every turn.

Version: **v0.2** — genre-agnostic ingest, pack-scoped saves, localized rendering.

## What's new in v0.2

### Invocation

- **Batch ingest.** `Ingest raw/novel/ as pack` compiles every
  eligible file under `raw/novel/` into its own pack in one pass. Pack
  slugs are derived from filenames (`My Cool Book.txt` →
  `my_cool_book`); packs that already exist are skipped unless you
  explicitly re-ingest. The single-novel form (`…as pack <name>`) is
  still accepted.
- **Start game, no id required.** `Start a new game` / "开始游戏" is
  enough: if exactly one pack exists, the agent picks it; otherwise it
  lists the packs and asks. The save id auto-increments
  (`save_001`, `save_002`, …) per pack. Fully explicit forms (pack
  and/or save id) are still accepted.

### Pack layer

- **One genre pack, any novel.** `genre_packs/xianxia/` is gone;
  `genre_packs/universal/` is the only shipped template. All
  novel-specific judgment (power system, social order, tone, hard
  canon) moves into each user pack's `novel_rules.md`.
- **Language is a first-class pack field.** User packs declare
  `language: <code>` in `index.md`. Rendering and lint pick localized
  labels from a per-language dictionary (English and Simplified
  Chinese ship; others fall back to English with a stderr warning).
- **`novel_rules.md` is load-bearing.** The ingest pipeline synthesizes
  it before drafting entities, and `lint_pack.py` now requires it on
  every user pack.

### Save layer

- **Pack-scoped save directories.** Saves now live at
  `saves/<pack>/<save_id>/`. Each pack owns its own save namespace, so
  two packs can both hold a `save_001` without colliding, and `ls
  saves/mypack/` cleanly lists one pack's run history. Tool calls use
  `--save <pack>/<save_id>` (e.g. `--save my_novel/save_001`);
  `meta.json::save_id` holds only the short id.
- **New save linter.** `tools/lint_save.py` verifies JSON legality,
  `turn ≡ len(session_log)`, `player.json ≡ world_state.player`,
  rendered-surface drift against the pack's localized labels, and slug
  existence (when a pack is resolvable).
- **`session_log.md` is display-only.** The canonical record lives in
  `session_log.jsonl`; the markdown is re-rendered after every turn.

### Correctness

- **Scene context derives from structured state.** The GM reads
  `world_state.present_entities`, `current_location`, and
  `active_threads` directly; markdown surfaces are never scraped for
  scene facts. `active_threads` and `current_objectives` are explicit
  **soft suggestions** — player input wins when it diverges.
- **Event skippability defaults by kind.** `EventPage.can_skip`
  defaults to `False` for `player_boundary` events and `True` for
  `intended` / `triggerable`. Explicit values still override.
- **Ingest prompt disambiguates event kinds.** Extract mentions use
  `event_kind` (`intended` / `triggerable` / `player_boundary`) so it
  no longer collides with the top-level mention `kind` enum.

## Architecture

```
  raw/novel/             ←  your novel text (immutable)
        │
        │  agent reads playbooks/ingest.md
        ▼
  genre_packs/universal/ ←  shipped genre-agnostic template (style,
                            guardrails, schemas, agent-facing prompts)
        │ +
        ▼
  packs/<user_pack>/     ←  generated user pack: language, novel_rules,
                            characters, factions, locations, arcs, events
        │ +
        ▼
  saves/<pack>/<save_id>/←  per-run state, one namespace per pack
                            •  world_state.json   (CANONICAL)
                            •  relationship_state.json   (CANONICAL)
                            •  open_loops.json   (CANONICAL)
                            •  player.json   (CANONICAL)
                            •  session_log.jsonl   (CANONICAL, append-only)
                            •  current_scene.md / session_log.md / ...   (rendered only)
```

**Rule of the architecture:** structured JSON is the single source of
truth. Markdown surfaces are re-rendered from JSON after every patch.
If narrator prose and structured state disagree, structured state wins.

## How to use it

1. Clone this repo and open the folder in Claude Code (or Codex).
2. Drop one or more novels (any genre, any language) into `raw/novel/`:
   ```bash
   cp my_novel.txt raw/novel/
   cp another_book.txt raw/novel/
   ```
   Each top-level file becomes one pack. Subdirectories aren't
   recursed — combine multi-file novels into a single text file first.
3. Tell the agent:
   > "Ingest `raw/novel/` as pack."

   The agent reads [`CLAUDE.md`](./CLAUDE.md) and
   [`playbooks/ingest.md`](./playbooks/ingest.md), scans `raw/novel/`,
   derives a pack slug from each filename (e.g. `My Cool Book.txt` →
   `my_cool_book`), auto-detects each novel's language, synthesizes
   its `novel_rules.md`, and compiles it into `packs/<slug>/`. Packs
   that already exist are skipped unless you say "re-ingest". Expect
   10–60 minutes per novel depending on length.

   (The single-novel form is still supported:
   > "Ingest `raw/novel/my_novel.txt` as pack `mypack`.")

4. When ingest is done, tell the agent:
   > "开始游戏" / "Start a new game"

   It reads [`playbooks/new-game.md`](./playbooks/new-game.md), picks
   the pack (asking if more than one is present), auto-numbers the
   save as `save_001` / `save_002` / …, and writes
   `saves/<pack>/<save_id>/`. Saves live under their pack, so every
   pack keeps its own independent save numbering. You can also be
   explicit:
   > "Start a new game against pack `mypack`" — or —
   > "Start a new game against pack `mypack`, save as `save_042`."

5. Play turns by sending in-character text. The agent follows
   [`playbooks/play-turn.md`](./playbooks/play-turn.md).

There is no CLI. The agent is the CLI.

## Optional deterministic tools

A thin `tools/` layer helps the agent with chores. None are required
for gameplay; the agent only invokes them where the plan calls for
deterministic checks or re-rendering.

| script | purpose |
|---|---|
| `python tools/chunker.py <novel> --pack <pack>` | Split a raw novel into chapter chunks under `packs/<pack>/.ingest/chunks.jsonl`. |
| `python tools/lint_pack.py --pack <pack>` / `--genre <name>` | Validate a user or genre pack (required files, schemas, cross-refs, orphan wiki-links). |
| `python tools/lint_save.py --save <pack>/<save_id>` | Validate a save: JSON legality, `turn ≡ len(session_log)`, `player.json ≡ world_state.player`, rendered-surface drift, slug existence. |
| `python tools/render_save.py --save <pack>/<save_id>` | Re-render markdown surfaces from JSON. Load-bearing: run after every turn. |
| `python tools/inspect_save.py --save <pack>/<save_id>` | One-screen plain-text state summary. |

### Setup

Optional — only needed if you want to run the tools yourself:

```bash
uv venv --python 3.10 .venv
uv pip install -e .
# macOS-in-Documents quirk:
chflags -R nohidden .venv
```

If your shell has no global `python`, use `.venv/bin/python` (or
activate the venv first). See [`tools/README.md`](./tools/README.md)
and the playbooks.

### Smoke check

With the genre pack alone you can verify the tools installed cleanly:

```bash
python tools/lint_pack.py --genre universal   # exits 0 when clean
```

Once you've ingested your own novel and started a save, the per-turn
chain is `render_save.py → lint_save.py → inspect_save.py`. The
playbooks call these at the appropriate points.

## What's out of scope for MVP

- Per-genre genre packs. One universal genre pack ships; novel-specific
  rules live in each user pack's `novel_rules.md`.
- Multiplayer, accounts, network services.
- Web UI, TUI.
- Numeric combat systems, damage formulas.
- Images, voice, avatars.
- Vector DB / embeddings — index-scan over the pack is enough at MVP
  scale.
- Any novel producing a "perfect" pack. The thesis is that ingest
  produces a *runnable* pack with minor manual polish, not a flawless
  one.

## Directory layout

```
Project SirenGM 2/
  CLAUDE.md                — operating schema for the agent
  AGENTS.md                — Codex entry point (points at CLAUDE.md)
  README.md                — this file
  llm-wiki.md              — design inspiration
  pyproject.toml           — tools-only Python package (optional)

  genre_packs/universal/   — shipped genre-agnostic template (not novel-specific)
  raw/novel/               — drop your novel text here (immutable)
  packs/<pack>/            — one generated pack per novel (gitignored)
  saves/<pack>/<save_id>/  — per-pack, per-run save states (gitignored)

  playbooks/               — workflow instructions for the agent
                              (ingest, new-game, play-turn, lint)
  tools/                   — optional deterministic helper scripts
```

## License

Proprietary — see `pyproject.toml`. Contact the author before
redistributing.
