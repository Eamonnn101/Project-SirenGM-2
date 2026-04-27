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
novel text -> generated pack -> backed-up save -> playable run
```

There is no app server, daemon, web UI, or custom game CLI. Claude Code
or Codex is the runtime; the repo supplies prompts, playbooks, schemas,
and deterministic helper tools.

## Inspiration

SirenGM 2 is inspired by Andrej Karpathy's
[`LLM Wiki`](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
pattern: an LLM incrementally compiles raw source material into a
persistent, structured middle layer instead of re-deriving everything
from raw text on every interaction. SirenGM adapts that idea from
personal knowledge bases to playable fiction: raw novel -> generated
story pack -> backed-up game state.

## Current Version

**v0.7.0 — Slimmed prompts + leaner runtime**

This release extends v0.6's token-efficiency focus by removing duplicate
text from the GM system prompt, condensing playbooks, and deleting two
helper tools whose output was already covered by `render_save.py` plus
a wiki-link-aware editor (Obsidian). Core gameplay is unchanged.

- **Lighter GM prompt.** `gm_system_fragment.md` — spliced into the GM
  prompt once per session — trimmed by ~1,100 words (~270 tokens). The
  compact-HUD spec is delegated to `tools/_hud.py`; the key-beat list,
  role description, and pre-options scan are condensed. Redundant
  sections (`Role` ↔ `style_guide`, `What the GM does not do` ↔
  `Player agency`, multi-section HUD format) merged.
- **Incremental `context_summary.md`.** Session-log detail window grew
  from 5 to 10 turns. `context_summary.md` is now built up by appending
  a new segment every 10 turns that slide out of the window — existing
  segments are never edited. A per-save cursor in
  `meta.json::context_summary_through_turn` tracks coverage.
- **Hard backup-policy whitelist.** `playbooks/play-turn.md` replaced
  its soft "feels save-worthy" trigger with a whitelist of structured
  state changes: `risk_level`, `current_location`,
  `player.{stage_index, health_state, destiny_traits, artifact.used}`,
  `hidden_truths`, conflict open/resolve, and any
  `Relationship.status` enum flip.
- **Removed duplicate tools.** `tools/inspect_save.py` (output already
  written to `player.md`) and `tools/render_pack.py` (this repo is read
  in Obsidian, which renders wiki-links natively) deleted.
- **Single-source survival precedence.** The full spec lives only in
  `gm_system_fragment.md`; `systems/health_and_death.md` and
  `prompts/death_coda.md` now reference it. `tools/_progression.py` is
  reframed as a spec-only module (no Python ever imports it).

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

During play, you can ask for a save at any time. The agent
will write a backup to canonical JSON, render markdown, and lint the
save. It should continue ordinary play from conversation context, not by
reloading the save.

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

### Backup Files

Structured JSON is authoritative when a backup is read or written:

- `world_state.json`
- `relationship_state.json`
- `open_loops.json`
- `player.json`
- `meta.json`
- `session_log.jsonl`
- `divergences.jsonl`

`context_summary.md` is compressed recovery memory. It is not ordinary
prompt context while the conversation window still contains the run.

Rendered markdown files such as `current_scene.md`, `player.md`,
`session_log.md`, and `hidden_truths.md` are display surfaces. They are
regenerated from JSON and should never be scraped for canonical state.
`session_log.md` renders the latest ten detailed turns for recovery;
the full archive remains in `session_log.jsonl`.

Ordinary turns should not refresh themselves from save files. Continue
from conversation context and pack rules; write backups only when useful
or mandatory.

When switching LLMs, after losing conversation context, or on explicit
load/recovery, read `context_summary.md` and the rendered
`session_log.md`. Do not read `session_log.jsonl` into the prompt; it is
for archive, lint, audit, and replay tooling.

## Runtime Loop

### Ordinary Turn

The agent uses:

- recent conversation;
- the relevant pack files, especially `novel_rules.md`,
  `progression_rules.md`, and current entity pages;
- narrow triggered references only when needed.

No save read/write/render/lint is required unless the agent judges the
state should be backed up, the user asks to save, or the turn fires an
immediate backup trigger.

### Backup Turn

The agent applies noted turns in chronological order:

1. apply one noted turn patch;
2. validate it against `tools/_models.py`;
3. update canonical state;
4. append that turn's session-log entry;
5. move to the next noted turn.

After backup entries have been prepared, the agent should prefer the
backup helper and render/lint once:

```bash
python tools/checkpoint_save.py --save <pack>/<save_id> --patch /tmp/<patch>.json --render --lint
```

This preserves ordered effects such as conflict ledgers, survival-trigger
precedence, stage breakthrough into destiny pick, and session-log turn
numbers without paying full I/O cost every ordinary turn.

Once 10 or more turns have slid out of the latest 10-turn detail window
without summary, the next backup must include one
`context_summary_rewrite` covering the indicated turn range; the helper
appends it as a new segment to `context_summary.md`. Below the
threshold, omit the field — segments are added incrementally, never
rewritten.

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
| `python tools/checkpoint_save.py --save <pack>/<save_id> --patch <patch.json> --render --lint` | Apply a compact backup patch, append detailed logs, append a new `context_summary.md` segment when 10+ turns have slid out without summary, render, and lint. |
| `python tools/render_save.py --save <pack>/<save_id>` | Render markdown surfaces from canonical JSON; `session_log.md` is the latest ten-turn recovery window. |
| `python tools/lint_save.py --save <pack>/<save_id>` | Validate a backed-up save. |

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
- `playbooks/play-turn.md` - run ordinary turns and backup turns.
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

### v0.7.0

- Aggressive subtractive refactor of the GM prompt
  (`gm_system_fragment.md` 679 → 553 lines, ~1,100 words /
  ~270 tokens cut per session start). Compact-HUD format delegated to
  `tools/_hud.py`; sections collapsed into runtime constraints +
  references.
- `context_summary.md` is now built up by appending one new segment
  every 10 turns that slide out of the detail window, instead of being
  rewritten on every backup. Window grew from 5 to 10 turns. New
  cursor field `meta.json::context_summary_through_turn`.
- Backup policy in `playbooks/play-turn.md` replaced its soft
  "feels save-worthy" judgment with a hard whitelist of structured
  state changes.
- Removed `tools/inspect_save.py` (duplicated `player.md`) and
  `tools/render_pack.py` (Obsidian renders wiki-links natively).
- Survival-trigger precedence canonicalized to one full spec in
  `gm_system_fragment.md`; `systems/health_and_death.md` and
  `prompts/death_coda.md` reference it instead of duplicating.
- `tools/_progression.py` reframed as a spec-only module — never
  imported by Python; the LLM mentally executes its functions per
  prompt references.

Net: 15 files changed, +126 / -712 lines.

### v0.6.0

- Added the Core Play Kernel prompt.
- Reworked `playbooks/play-turn.md` so ordinary turns use conversation
  and pack context; saves are backups, not the default information
  source.
- Added a hard player-facing output ban for kernel/mode/private-note
  leakage.
- Added recovery-memory backups: `session_log.md` keeps the latest ten
  detailed turns, `session_log.jsonl` keeps the archive, and
  `context_summary.md` stores readable key-node memory for recovery,
  appended in segments after every 10 turns slide out of the window.
- Added `checkpoint_save.py` for compact backup patches.

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
