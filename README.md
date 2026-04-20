# Project SirenGM 2

**AI compiles a novel into a playable world.**

A file-driven, agent-native MVP. Drop a novel (any genre; Chinese or
English text) into `raw/novel/`, ask the agent to ingest it, and the
agent compiles it into a runnable Story Pack. Then play 20–50 turns
against that pack with persistent state — using only file I/O and
the agent's own LLM calls, no custom runtime.

The thesis is **"compile novel → playable world,"** not "play inside a
prebuilt world." There is no ready-made sample pack; the product path
is ingest.

The pattern is adapted from [llm-wiki](./llm-wiki.md): raw sources are
immutable, the pack is an LLM-maintained persistent middle layer, and
runtime reads from the compiled pack + structured save instead of
re-deriving from raw text on every turn.

**Version: v0.3** — headline feature is a cross-genre
[conflict engine](#the-conflict-engine-v03) that gives any scene of
tension (combat, debate, chase, trial, negotiation) a structured
frame with stakes, momentum, and a cost ledger. See
[Changelog](#changelog) for the full list.

## Quickstart

1. **Clone** this repo and open it in Claude Code (or Codex).
2. **Drop a novel** into `raw/novel/` as `.txt` or `.md` — one file
   becomes one pack. Non-text formats (PDF, EPUB, images) must be
   converted to plain text first; subdirectories aren't recursed.
   ```bash
   cp my_novel.txt raw/novel/
   ```
3. **Ingest.** Tell the agent:
   > "导入小说" / "Ingest novels"

   The agent scans `raw/novel/`, derives slugs from filenames
   (`My Cool Book.txt` → `my_cool_book`), prints a pre-scan
   (source → slug → action), and after you confirm, compiles each
   novel into `packs/<slug>/` with a Stage-0 checkpoint per book so
   you can catch setting misreads early. Expect 10–60 minutes per
   novel. Already-ingested packs are skipped unless you say
   "re-ingest".

   To name a single pack yourself:
   > "将 `raw/novel/my_novel.txt` 导入为 pack `mypack`" /
   > "Ingest `raw/novel/my_novel.txt` as pack `mypack`"

4. **New game.** Tell the agent:
   > "开始游戏" / "Start a new game"

   It picks the pack (asking if more than one exists), auto-numbers
   the save as `save_001` / `save_002` / …, and writes under
   `saves/<pack>/<save_id>/`. Each pack owns its own save namespace.

5. **Play.** Send in-character text. The agent follows
   [`playbooks/play-turn.md`](./playbooks/play-turn.md).

There is no CLI. The agent is the CLI.

## Architecture

```
  raw/novel/              ←  your novel text (immutable)
        │
        │  agent reads playbooks/ingest.md
        ▼
  genre_packs/universal/  ←  shipped genre-agnostic template
        │ +                   (style, guardrails, schemas, prompts)
        ▼
  packs/<user_pack>/      ←  generated user pack: language, novel_rules,
                              characters, factions, locations, arcs, events
        │ +
        ▼
  saves/<pack>/<save_id>/ ←  per-run state, one namespace per pack
                              •  world_state.json          (CANONICAL)
                              •  relationship_state.json   (CANONICAL)
                              •  open_loops.json           (CANONICAL)
                              •  player.json               (CANONICAL)
                              •  session_log.jsonl         (CANONICAL, append-only)
                              •  current_scene.md / session_log.md / …  (rendered only)
```

**Rule of the architecture.** Structured JSON is the single source of
truth. Markdown surfaces are re-rendered from JSON after every patch.
If narrator prose and structured state disagree, structured state wins.

**Scene context derives from structured state.** The GM reads
`world_state.present_entities`, `current_location`, and
`active_threads` directly; markdown is never scraped for scene facts.
`active_threads` and `current_objectives` are explicit **soft
suggestions** — player input wins when it diverges.

## The conflict engine (v0.3)

A cross-genre bookkeeping layer for scenes of tension — combat,
debate, chase, negotiation, trial, cultivation-ordeal. The GM opens
a `ConflictFrame` in `world_state.current_conflict` whenever the
scene has ≥2 identifiable parties with opposing wants and the
outcome would change the state of the world. Nothing combat-specific
about it; the `kind` field is free-form ("辩论", "追逐", "debate",
"hostage-trade", …) and the GM picks it per scene.

Each frame tracks five things — the same five questions regardless
of genre:

| field                 | what it answers                                                        |
| --------------------- | ---------------------------------------------------------------------- |
| `stake`               | what both sides are fighting over                                      |
| `sides`               | named parties with their members, `want`, and a running `paid` ledger  |
| `momentum`            | `setup` / `player_pressing` / `even` / `opposition_pressing` / `reversal_imminent` |
| `escalation_notes`    | pivotal beats that shifted the scene                                   |
| `world_change` (at resolve) | what the resolution changed in canonical state                   |

**Player visibility.** When a frame is active, every GM reply
prepends a single-line HUD above the prose:

```
〔冲突・追逐｜势头：对立方紧逼｜你方已付：虎口受伤、退路被封｜对立方已付：—〕
```

The English-pack equivalent is `[Conflict · chase | Momentum:
Opposition pressing | You paid: bruised hand, escape cut off |
Opposition paid: —]`. At least one of the four options every conflict
turn must push momentum — escalate, de-escalate, pay a cost, attempt
a reversal. Tactic tags tie to the conflict's `kind` ("辩锋",
"剑势", "截击", "press-advantage"), not generic labels.

**Lifecycle.** Three patch keys drive the frame:

- `conflict_open` — install a new frame. Rejected with a divergence
  if one is already active.
- `conflict_update` — per-turn delta: `momentum`, optional
  `escalation_note`, `side_updates.<label>.paid_add`. Every update
  turn must record at least one concrete `paid_add` on the side that
  absorbed a cost — the paid ledger is what the HUD reads.
- `conflict_resolve` — `{outcome, momentum_final, world_change}`
  plus the matching `relationship_updates`, `open_loops_close`,
  `open_loops_add`, `inventory_*`. Writes a `ConflictSummary` into
  `world_state.last_conflict_summary` so `current_scene.md` retains
  a "上一场冲突 / Last Conflict" block until the next frame opens.

**Post-resolution trace.** After resolve, the scene doesn't snap
back to "nothing happened" — `last_conflict_summary` preserves
`kind`, `stake`, `outcome`, `momentum_final`, `resolved_turn` and is
rendered into `current_scene.md` until a new `conflict_open` takes
over.

**Staleness check.** `tools/lint_save.py` warns (not errors) when a
frame has been open for more than 10 turns — usually a cue the GM
forgot to resolve or should narrow the frame.

Momentum is a discrete label, never a number. Keeps the engine off
the numeric-combat-stat slope and keeps narration literary.

See
[`genre_packs/universal/prompts/gm_system_fragment.md`](./genre_packs/universal/prompts/gm_system_fragment.md)
for the GM-side rules, [`playbooks/play-turn.md`](./playbooks/play-turn.md)
for the lifecycle in context, and
[`tools/_models.py`](./tools/_models.py) for the Pydantic schemas.

## Tools

A thin `tools/` layer helps the agent with chores. None are required
for gameplay; the agent invokes them where the playbook calls for
deterministic checks or re-rendering.

| script | purpose |
|---|---|
| `python tools/chunker.py <novel> --pack <pack>` | Split a raw novel into chapter chunks under `packs/<pack>/.ingest/chunks.jsonl`. |
| `python tools/lint_pack.py --pack <pack>` / `--genre <name>` | Validate a user or genre pack (required files, schemas, cross-refs, orphan wiki-links, bare slugs on non-ASCII-named entities). |
| `python tools/lint_save.py --save <pack>/<save_id>` | Validate a save: JSON legality, `turn ≡ len(session_log)`, `player.json ≡ world_state.player`, rendered-surface drift, slug existence, stale conflict frames. |
| `python tools/render_save.py --save <pack>/<save_id>` | Re-render markdown surfaces (including the current- and last-conflict blocks) from JSON. Load-bearing: run after every turn. |
| `python tools/render_pack.py --pack <pack>` | Expand the pack's `[[slug\|Display]]` wiki-links into plain Markdown links under `packs/<pack>/_rendered/` for non-wikilink readers. |
| `python tools/inspect_save.py --save <pack>/<save_id>` | One-screen plain-text state summary. |

### Setup

Only needed if you want to run the tools yourself:

```bash
uv venv --python 3.10 .venv
uv pip install -e .
# macOS-in-Documents quirk: unhide .pth files so editable imports work
chflags -R nohidden .venv
```

If your shell has no global `python`, use `.venv/bin/python` (or
activate the venv first). See [`tools/README.md`](./tools/README.md).

### Smoke check

```bash
python tools/lint_pack.py --genre universal   # exits 0 when clean
```

Once you've ingested a novel and started a save, the per-turn chain
is `render_save.py → lint_save.py → inspect_save.py`. The playbooks
call these at the appropriate points.

## Changelog

### v0.3

- **Cross-genre conflict engine.** `ConflictFrame` on `world_state`
  with named sides, momentum labels, per-side cost ledger,
  escalation notes. Three lifecycle patch keys
  (`conflict_open` / `conflict_update` / `conflict_resolve`).
  In-turn HUD line, post-resolve "Last Conflict" block,
  stale-frame lint warning. Full details
  [above](#the-conflict-engine-v03).
- **Beat density narration rule.** Each turn plays the current beat
  through its pivot (action lands → NPC reactions → complication),
  not a static tableau. The 300–700-char (zh) / 200–500-word (en)
  narration budget measures prose only; the options block is
  counted separately.
- **Per-turn 3+D options.** Every turn ends with four bullets:
  `选项A/B/C` (short tactic label + diegetic action) plus the fixed
  free-form `选项D（自创脑洞）`. Options are persisted on
  `SessionLogEntry.options`.
- **Piped wiki-link dialect.** Entity cross-refs use
  `[[slug|Display]]` — slug stays ASCII snake_case (stable for
  tools and lint); the display label is the native-language name
  the reader sees (`[[xiao_yan|萧炎]]`). Bare `[[slug]]` is
  rejected when the target has a non-ASCII `name`;
  `tools/render_pack.py` expands the dialect into plain Markdown.
- **Language-locked packs.** User packs declare `language: zh` or
  `language: en` in `index.md`; rendering picks localized labels
  from a two-language dictionary. `zh` is the default when the
  field is missing.

### v0.2

- **Batch ingest.** `导入小说` / `Ingest novels` scans
  `raw/novel/`, derives slugs from filenames, and ingests each
  `.txt` / `.md` source in sequence with a per-novel Stage-0
  checkpoint. Already-ingested packs (matched by `source_file`)
  are skipped; silent slug-collapse across sources is refused.
- **Start a game with no id.** `Start a new game` / "开始游戏" is
  enough; the agent picks the lone pack or asks, and auto-numbers
  saves (`save_001`, `save_002`, …) per pack.
- **One universal genre pack.** `genre_packs/xianxia/` is gone;
  `genre_packs/universal/` is the only shipped template. All
  novel-specific judgment moves into each user pack's
  `novel_rules.md` (load-bearing, synthesized at ingest time).
- **Pack-scoped save directories.** `saves/<pack>/<save_id>/` —
  each pack owns its save namespace, so two packs can both hold a
  `save_001` without colliding.
- **`tools/lint_save.py`.** New save linter: JSON validity,
  `turn ≡ len(session_log)`, `player.json ≡ world_state.player`,
  rendered-surface drift against the pack's localized labels, slug
  existence when a pack is resolvable.
- **`session_log.md` is display-only.** Canonical record lives in
  `session_log.jsonl`; the markdown is re-rendered after every
  turn.
- **Event skippability defaults by kind.** `EventPage.can_skip`
  defaults to `False` for `player_boundary` events and `True` for
  `intended` / `triggerable`; explicit values still override.

### v0.1

- Initial ingest → pack → save pipeline, shipped as the
  file-driven agent-native MVP of the llm-wiki pattern.

## What's out of scope for MVP

- Per-genre genre packs. One universal genre pack ships;
  novel-specific rules live in each user pack's `novel_rules.md`.
- Multiplayer, accounts, network services.
- Web UI, TUI.
- Numeric combat systems, damage formulas, HP bars. The conflict
  engine deliberately uses discrete momentum labels, not numbers.
- Images, voice, avatars.
- Vector DB / embeddings — index-scan over the pack is enough at
  MVP scale.
- Any novel producing a "perfect" pack. The thesis is that ingest
  produces a *runnable* pack with minor manual polish, not a
  flawless one.

## Directory layout

```
Project SirenGM 2/
  CLAUDE.md                — operating schema for the agent
  AGENTS.md                — Codex entry point (points at CLAUDE.md)
  README.md                — this file
  llm-wiki.md              — design inspiration
  pyproject.toml           — tools-only Python package (optional)

  genre_packs/universal/   — shipped genre-agnostic template
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
