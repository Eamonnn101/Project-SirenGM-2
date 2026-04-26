# Playbook · play-turn

One turn of gameplay against an active save. The agent is still the
runtime; there is no separate game daemon.

The important shift: **the save is a backup, not the ordinary context
source.** During an ongoing play session, use the live conversation
window and the pack files. Backup files exist so the run can be restored
later and so the agent can persist durable state without hand-writing a
large amount of text every turn.

## Core Play Kernel

Read `genre_packs/universal/prompts/core_play_kernel.md` as a private
per-turn checklist:

1. Understand player intent.
2. Check current danger/conflict.
3. Check whether artifact / innate traits / destiny traits are relevant.
4. Resolve the turn with consequence and forward motion.
5. Decide whether this turn needs a backup write.

The kernel is never player-facing. Never print "Core Play Kernel",
"Mode A", "Mode B", "Mode C", backup reasoning, private notes,
pending state, JSON patches, or tool commands in the chat reply.

## Context Sources

Use this priority during ordinary play:

1. **Live conversation** — the current scene, unresolved consequences,
   provisional state, and the player's latest input.
2. **User pack** — `packs/<pack>/novel_rules.md`,
   `progression_rules.md`, `canon_guardrails.md`, and current entity
   pages. This is the main external information source.
3. **Universal rules** — the Core Play Kernel and triggered universal
   systems.
4. **Save backup** — JSON/markdown under `saves/<pack>/<save_id>/`,
   used for backup, restore, lint, or explicit save/load checks. Do not
   read save logs during ordinary turns when the conversation already
   contains the needed continuity.

`context_summary.md` and `session_log.md` are recovery surfaces. Read
them only when switching LLMs, after the model's conversation context is
lost, or when the user explicitly asks to load/recover from disk. In
that case, read `context_summary.md` plus the latest ten detailed turns
already rendered in `session_log.md`.

Never read `session_log.jsonl` for ordinary play or recovery prompting.
It is the complete archive for tooling, lint, audit, and replay only.

## Backup Policy

There is no fixed every-turn persistence requirement. Ordinary turns can
advance from conversation context. Write a backup only when one of the
following hard triggers fires:

- the user explicitly asks to save/存档;
- `world_state.json` changes in any of these fields this turn:
  `risk_level`, `current_location`, `player.stage_index`,
  `player.health_state`, `player.destiny_traits` (gain or exhausted
  flip), `player.artifact.used`, `hidden_truths`,
  `current_conflict` (open or resolve);
- a relationship's `status` enum changes (numeric `affinity` / `trust`
  drift alone is **not** a trigger);
- death, stage breakthrough, artifact use/exhaustion, important NPC
  death/betrayal, run restart, or major source-novel divergence.

Plain scene transitions, dialogue beats, exploration, and small
affinity/trust nudges do **not** trigger a backup. When in doubt, skip
the backup; the next durable event will fold the unsaved beats into one
write.

Backup writes are for durability only. Do not refresh the prompt from
the backup after every write.

## Recovery Memory

`session_log.md` is the detailed ten-turn recovery window. It should
render full recent turn details: player input, narration, options, and
summary.

`context_summary.md` is built up **incrementally**, not rewritten:

- If `len(session_log)` is at most 10, do nothing extra.
- Once at least 10 turns have slid out of the window without yet being
  summarized, the next backup must include a `context_summary_rewrite`
  whose body is a key-node compression of those specific turns.
  `checkpoint_save.py` reports the exact turn range; it prepends a
  `## 回合 N–M` (or `## Turns N–M`) header and a `---` separator and
  appends the new segment to the file. Existing segments are never
  edited.
- Keep each segment short readable prose. Do not duplicate tables, HUD
  mirrors, NPC rosters, or live-state lists already covered by JSON.
- A single backup that batches more than 10 turns triggers exactly one
  segment covering the full out-of-window range; many small backups
  that accumulate past 10 unsummarized turns also trigger one segment.

The LLM writes the compression text because it requires narrative
judgment. Tools only persist and render the backup surfaces.

## Ordinary Turn

Use this path when no backup write is needed.

1. Run the Core Play Kernel privately.
2. Produce only the player-facing reply:
   - compact HUD line;
   - conflict HUD line if a conflict is active;
   - narration;
   - exactly three A/B/C options plus the fixed free-form D slot, unless
     a breakthrough/death block replaces options.
3. Keep any working notes internal to the conversation. Do not show
   them.

## Backup Turn

Use this path when a backup write is needed.

1. Resolve the turn normally first.
2. Apply state changes in chronological order. Do not merge multiple
   turns into a final-state blob if intermediate costs/triggers matter.
3. Append one detailed `SessionLogEntry` per backed-up turn.
4. If 10 or more unsummarized turns will sit outside the latest 10-turn
   detail window after this patch, include exactly one
   `context_summary_rewrite`. Its body should be a short prose
   compression of the specific turn range the helper indicates; do not
   restate or edit older segments. Below the threshold, omit
   `context_summary_rewrite` entirely.
5. Run the backup helper when possible:

   ```bash
   python tools/checkpoint_save.py --save <pack>/<save_id> --patch /tmp/<patch>.json --render --lint
   ```

   The helper supports `world_state`, `flags_merge`,
   `relationship_updates`, `open_loops_add`, `open_loops_update`,
   `open_loops_close`, `hidden_truths_append`, `session_log_entries`,
   and `context_summary_rewrite`.
6. If lint fails, fix the backup before claiming it is saved. Do not
   paste tool output, JSON, or private notes into the player-facing turn.

## Output Format

The chat reply keeps this shape:

- **No active conflict** — compact HUD line, blank line, prose
  narration, blank line, four option strings.
- **Active conflict** — compact HUD line, blank line, conflict HUD
  line, blank line, prose narration, blank line, four option strings.
- **Breakthrough / death / completion** — compact HUD line, blank line,
  short coda/breakthrough narration, blank line, the required boxed
  block from `breakthrough_pick.md` or `death_coda.md`.

Hard ban: the player-facing reply must not contain internal headings,
kernel checklists, mode names, backup decisions, private notes,
pending buffers, JSON patches, or tool commands. If such text appears in
the draft, delete it before sending. The first visible line must be the
compact HUD.

## Conditional System Reminders

- **Player agency:** player input outranks active threads and
  objectives. Follow the player and let abandoned threads fall away.
- **Canon / source-novel divergence:** protect hard novel rules from
  `novel_rules.md` and `canon_guardrails.md`. Major divergence is a
  backup trigger.
- **Conflict frames:** open only for real tension with opposing wants;
  update momentum and paid costs while live; resolve when stakes are
  answered or the player walks away.
- **Build hooks:** artifact, innate, and destiny labeled options appear
  only when the current pivot makes them relevant. Default is zero
  labeled options; at most one labeled option per turn.
- **Health/death:** `critical` takes priority on the next turn. Before
  terminal death, check survival-trigger precedence in order:
  `bond_rescue`, `not_meant_to_die`, then `last_barrier`.
- **Breakthrough:** stage advance happens only on climactic beats, never
  more than once per turn, and triggers a backup write.

## Failure Handling

- If the user's input is meta/tooling/debugging, do not advance the turn
  unless they also include an in-world action.
- If backup JSON is malformed during a save/load operation, stop and
  tell the user. Never replace malformed state from memory without
  explicit confirmation.
- If the conversation context is available, do not read backup logs just
  to continue ordinary play.
