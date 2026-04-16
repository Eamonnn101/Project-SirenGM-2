# Project SirenGM 2

**AI compiles a novel into a playable world.**

A file-driven, agent-native MVP that validates:

> An agent (Claude Code or Codex) can compile a user-supplied xianxia
> (修仙) novel into a runnable Story Pack, and then run a coherent
> 20–50-turn game against that pack with persistent state across
> save/load — using only file I/O and the agent's own LLM calls, no
> custom runtime.

The thesis is **"compile novel → playable world,"** not "play inside a
prebuilt world." There is no ready-made sample pack — the product path
is ingest.

Adapted from the [llm-wiki](./llm-wiki.md) pattern: raw sources are
immutable, the pack is an LLM-maintained persistent middle layer, and
runtime reads from the compiled pack + structured save instead of
re-deriving from raw text on every turn.

Version: **v0.1** — refactored from a Python CLI into the agent-native
file-driven architecture; the legacy implementation is preserved under
`archive/legacy_python_app/` for reference.

## Architecture

```
  raw/novel/             ←  your novel text (immutable)
        │
        │  agent reads playbooks/ingest.md
        ▼
  genre_packs/xianxia/   ←  reusable genre template (style, guardrails,
                            systems, schemas, agent-facing prompts)
        │ +
        ▼
  packs/<user_pack>/     ←  generated user pack (characters, factions,
                            locations, arcs, events) specific to your novel
        │ +
        ▼
  saves/<save_id>/       ←  per-run state
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
2. Drop a xianxia novel into `raw/novel/`:
   ```bash
   cp my_xianxia.txt raw/novel/my_xianxia.txt
   ```
3. Tell the agent:
   > "Ingest `raw/novel/my_xianxia.txt` as pack `mypack`, genre xianxia."

   The agent reads [`CLAUDE.md`](./CLAUDE.md) and
   [`playbooks/ingest.md`](./playbooks/ingest.md) and compiles the
   novel into `packs/mypack/`. Expect 10–60 minutes depending on novel
   length.
4. When ingest is done, tell the agent:
   > "Start a new game against pack `mypack`, save as `save_001`."

   It reads [`playbooks/new-game.md`](./playbooks/new-game.md) and
   writes `saves/save_001/`.
5. Play turns by sending in-character text. The agent follows
   [`playbooks/play-turn.md`](./playbooks/play-turn.md).

There is no CLI. The agent is the CLI.

## Optional deterministic tools

A thin `tools/` layer helps the agent with chores. None are required
for gameplay; the agent only invokes them where the plan calls for
deterministic checks or re-rendering.

| script | purpose |
|---|---|
| `python tools/chunker.py <novel> --pack <name>` | Split a raw novel into chapter chunks under `packs/<name>/.ingest/chunks.jsonl`. |
| `python tools/lint_pack.py --pack <name>` / `--genre <name>` | Validate a user or genre pack (required files, schemas, cross-refs, orphan wiki-links). |
| `python tools/lint_save.py --save <id>` | Validate a save: JSON legality, `turn ≡ len(session_log)`, `player.json ≡ world_state.player`, rendered-surface drift, slug existence. |
| `python tools/render_save.py --save <id>` | Re-render markdown surfaces from JSON. Load-bearing: run after every turn. |
| `python tools/inspect_save.py --save <id>` | One-screen plain-text state summary. |

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
python tools/lint_pack.py --genre xianxia   # exits 0 when clean
```

Once you've ingested your own novel and started a save, the per-turn
chain is `render_save.py → lint_save.py → inspect_save.py`. The
playbooks call these at the appropriate points.

## What's out of scope for MVP

- Multi-genre (only xianxia). Other genres land as future
  `genre_packs/<name>/` additions.
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

  genre_packs/xianxia/     — reusable xianxia template (not novel-specific)
  raw/novel/               — drop your novel text here (immutable)
  packs/                   — generated user packs (gitignored)
  saves/                   — per-run save states (gitignored)

  playbooks/               — workflow instructions for the agent
                              (ingest, new-game, play-turn, lint)
  tools/                   — optional deterministic helper scripts
  docs/                    — plans and design docs

  archive/legacy_python_app/  — prior Python-CLI implementation
                                (reference only; do not run)
```

## License

Proprietary — see `pyproject.toml`. Contact the author before
redistributing.
