# Project SirenGM 2

**AI compiles a novel into a playable world.**

SirenGM 2 is a file-driven, agent-native story game framework. Drop a
Chinese or English novel into `raw/novel/`, ask the agent to ingest it,
and the project compiles the source into a playable Story Pack. You then
play 20-50 turns against that pack while the agent maintains structured
save state, rendered markdown, conflict frames, progression, health, and
run history.

The product path is:

```text
novel text -> generated pack -> checkpointed save -> playable run
```

There is no app server, daemon, web UI, or custom game CLI. Claude Code
or Codex is the runtime; the repo supplies prompts, playbooks, schemas,
and deterministic helper tools.

## Current Version

**v0.6.0 - Core Play Kernel + checkpoint runtime**

This release focuses on performance and weak-model compatibility. The
full gameplay surface remains intact, but ordinary turns no longer ask
the model to reread and rewrite the whole project state every time.

- **Core Play Kernel:** every turn follows five stable rules: understand
  intent, check danger/conflict, check relevant artifact/trait hooks,
  resolve with consequence, then decide whether to checkpoint.
- **Checkpoint runtime:** ordinary turns use conversation context, a
  compact active-state summary, and a pending buffer. Full JSON writes,
  markdown render, and save lint happen at checkpoints.
- **Checkpoint cadence:** default every 3 turns; maximum 5 turns.
- **Immediate checkpoints:** death, critical/dead health, breakthrough,
  destiny gain/exhaustion, artifact use/exhaustion, conflict resolution,
  major scene/world/faction change, important NPC death or betrayal,
  restart, explicit save request, or major source-novel divergence.
- **Active summary support:** `tools/inspect_save.py --active-summary`
  prints the compact state seed used between checkpoints, including the
  canonical HUD line.

The goal is simple: preserve SirenGM's core experience while reducing
per-turn cognitive load and file I/O.

## Quickstart

1. Open this repo in Claude Code or Codex.

2. Add a plain-text novel:

   ```bash
   cp my_novel.txt raw/novel/
   ```

   Supported inputs are `.txt` and `.md`. Convert PDF, EPUB, images, or
   other formats to text first.

3. Ask the agent to ingest:

   ```text
   导入小说
   ```

   or:

   ```text
   Ingest novels
   ```

   The agent follows `playbooks/ingest.md`, scans `raw/novel/`, derives
   pack slugs from filenames, and writes each compiled pack under
   `packs/<pack>/`.

4. Start a run:

   ```text
   开始游戏
   ```

   or:

   ```text
   Start a new game
   ```

   The agent follows `playbooks/new-game.md`, creates
   `saves/<pack>/<save_id>/`, and initializes the player build.

5. Play in character. The agent follows `playbooks/play-turn.md`.

During play, you can ask for a save/checkpoint at any time. The agent
will flush pending state to canonical JSON, render markdown, lint the
save, and refresh the active summary.

## Repository Layout

```text
Project SirenGM 2/
  AGENTS.md                  Codex entry point
  CLAUDE.md                  Agent operating schema
  README.md                  Project overview
  pyproject.toml             Optional Python tooling package

  raw/novel/                 Immutable source novels
  genre_packs/universal/     Shipped universal genre layer
  packs/<pack>/              Generated user packs
  saves/<pack>/<save_id>/    Per-pack run saves

  playbooks/                 Agent workflows
  tools/                     Deterministic helper scripts
```

Generated packs and saves are local working artifacts. The shipped core
is the universal genre layer, playbooks, schemas, prompts, and helper
tools.

## Architecture

SirenGM uses three layers:

```text
raw/novel/
  immutable source text

genre_packs/universal/
  genre-agnostic schemas, prompts, guardrails, systems

packs/<pack>/
  generated wiki for one source novel:
  novel_rules, canon guardrails, characters, factions, locations,
  arcs, events, relationships, progression rules

saves/<pack>/<save_id>/
  canonical JSON + rendered markdown for one run
```

### Source Of Truth

Structured JSON is authoritative at checkpoints:

- `world_state.json`
- `relationship_state.json`
- `open_loops.json`
- `player.json`
- `meta.json`
- `session_log.jsonl`
- `divergences.jsonl`

Rendered markdown files such as `current_scene.md`, `player.md`,
`session_log.md`, and `hidden_truths.md` are display surfaces. They are
regenerated from JSON and should never be scraped for canonical state.

Between checkpoints, ordinary turns may carry a compact pending buffer
inside the conversation. Any immediate-trigger fact must be flushed to
JSON before it is treated as durable.

## Runtime Loop

### Ordinary Turn

The agent uses:

- recent conversation;
- active state summary from `inspect_save.py --active-summary`;
- pending state buffer;
- narrow triggered references only when needed.

No full save render/lint is required unless the turn reaches the
checkpoint interval or fires an immediate trigger.

### Checkpoint Turn

The agent applies buffered turns in chronological order:

1. apply one buffered turn patch;
2. validate it against `tools/_models.py`;
3. update canonical state;
4. append that turn's session-log entry;
5. move to the next buffered turn.

After every buffered turn has been applied, the agent renders and lints
once:

```bash
python tools/render_save.py --save <pack>/<save_id>
python tools/lint_save.py --save <pack>/<save_id>
python tools/inspect_save.py --save <pack>/<save_id> --active-summary
```

This preserves ordered effects such as conflict ledgers, survival-trigger
precedence, stage breakthrough into destiny pick, and session-log turn
numbers without paying full I/O cost every ordinary turn.

## Core Gameplay Systems

- **Universal genre pack:** one shipped universal layer supports wuxia,
  sci-fi, political drama, romance, mystery, and other prose genres.
- **Per-novel rules:** each generated pack owns its `novel_rules.md`,
  canon guardrails, progression labels, and world entities.
- **Conflict frames:** any high-tension scene can become a structured
  `ConflictFrame` with sides, stakes, momentum, paid costs, escalation,
  and resolution writeback.
- **Pacing budget:** conflicts carry a 3-6 beat budget. The GM pushes
  toward decisive endgame beats instead of letting scenes drift.
- **Player build:** each run has one artifact, three innate traits, and
  breakthrough-earned destiny traits.
- **Progression:** six narrative stages, with GM-judged breakthroughs
  against each pack's source-novel trigger patterns.
- **Health and death:** five-state narrative health ladder:
  `healthy -> hurt -> badly_hurt -> critical -> dead`.
- **Survival precedence:** before terminal death, the runtime checks
  `bond_rescue`, then `not_meant_to_die`, then `last_barrier`.
- **Meta progression:** per-pack run history tracks completions, deaths,
  best stage, and seen archetypes for draft variety.
- **Compact HUD:** each player-facing turn begins with a single line
  summarizing turn, innate traits, artifact, health, destiny, and
  triggerable hooks.

All mechanics stay narrative. There is no XP, HP bar, damage formula, or
numeric combat stat layer.

## Tools

The scripts in `tools/` are deterministic helpers. They do not call an
LLM.

| script | use |
|---|---|
| `python tools/chunker.py <novel> --pack <pack>` | Split source text into ingest chunks. |
| `python tools/lint_pack.py --pack <pack>` | Validate a generated user pack. |
| `python tools/lint_pack.py --genre universal` | Validate the shipped universal genre pack. |
| `python tools/render_save.py --save <pack>/<save_id>` | Render markdown surfaces from canonical JSON. |
| `python tools/lint_save.py --save <pack>/<save_id>` | Validate a checkpointed save. |
| `python tools/inspect_save.py --save <pack>/<save_id>` | Print a compact save summary. |
| `python tools/inspect_save.py --save <pack>/<save_id> --active-summary` | Print the active-state seed for checkpoint runtime. |

Optional local setup:

```bash
uv venv --python 3.10 .venv
uv pip install -e .
```

If your shell has no global `python`, use `.venv/bin/python`.

Smoke check:

```bash
python tools/lint_pack.py --genre universal
```

## Agent Workflow

The agent reads the relevant playbook before acting:

- `playbooks/ingest.md` - compile novels into packs.
- `playbooks/new-game.md` - create a save and initial build.
- `playbooks/play-turn.md` - run ordinary and checkpoint turns.
- `playbooks/death-and-restart.md` - handle death, completion, and restart.
- `playbooks/lint.md` - inspect pack/save health.

Important rules:

- Do not modify `raw/novel/`; source text is immutable.
- Do not scrape rendered markdown for state; JSON wins.
- Do not force the player back to preset arcs; active threads are soft
  suggestions.
- Do not invent durable facts that cannot be patched into structured
  state; log a divergence instead.
- Do not add a new product CLI, web UI, daemon, or network runtime.

## Changelog

### v0.6.0

- Added the Core Play Kernel prompt.
- Reworked `playbooks/play-turn.md` around ordinary turns, scheduled
  checkpoints, and immediate checkpoints.
- Added the pending state buffer contract.
- Added `inspect_save.py --active-summary`.
- Changed runtime guidance so full save render/lint happens at
  checkpoints instead of every turn.

### v0.5.x

- Added the progression layer: artifact, innate traits, destiny traits,
  six narrative stages, breakthroughs, health/death, completion, and
  meta progression.
- Simplified the compact HUD into a single player-facing line.
- Tightened labeled special options so build hooks surface only on key
  beats and at most once per turn.

### v0.4

- Added conflict pacing budget, endgame HUD, denser beats, and time
  compression outside active conflicts.

### v0.3

- Added the cross-genre conflict engine, conflict HUD, session-log
  options, piped wiki-links, and language-locked packs.

### v0.2

- Added batch ingest, pack-scoped saves, save linting, and rendered
  session-log surfaces.

### v0.1

- Initial file-driven ingest -> pack -> save MVP.

## Out Of Scope

- Web UI, TUI, accounts, multiplayer, or hosted services.
- Per-genre shipped genre packs.
- Numeric combat systems.
- Images, voice, avatars, or asset generation.
- Vector DB or embeddings.
- A "perfect" one-shot ingest. The target is a runnable pack with minor
  room for manual polish.

## License

Proprietary. Contact the author before redistributing.
