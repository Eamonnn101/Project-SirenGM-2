# Playbook · play-turn

One turn of gameplay against an active save. The agent is still the
runtime; there is no separate game daemon. This playbook optimizes the
runtime loop for weaker models by separating **ordinary turns** from
**checkpoint turns**.

The active save lives at `saves/<pack>/<save_id>/`. Canonical JSON is
the source of truth at checkpoints. Between checkpoints, the agent uses
conversation context, the compact active-state summary, and the pending
buffer below.

## Core Play Kernel

Read `genre_packs/universal/prompts/core_play_kernel.md` as the stable
per-turn kernel:

1. Understand player intent.
2. Check current danger/conflict.
3. Check whether artifact / innate traits / destiny traits are relevant.
4. Resolve the turn with consequence and forward motion.
5. Decide whether this turn requires a checkpoint.

Everything else in the universal GM prompt, system docs, pack rules, and
save files is conditional support for this kernel. Load it when starting
or resuming play, at checkpoint time, or when a triggered system needs
the full rule text.

## Runtime State Stack

Use three layers during play:

- **Checkpoint state** — canonical files under
  `saves/<pack>/<save_id>/`. JSON wins over prose whenever they differ.
- **Active State Summary** — compact in-conversation snapshot seeded
  by `python tools/inspect_save.py --save <pack>/<save_id>
  --active-summary` when play starts/resumes or after each checkpoint.
- **Pending State Since Last Checkpoint** — compact in-conversation
  delta block maintained on ordinary turns. It is not shown to the
  player and is not written to disk until checkpoint.

Pending buffer template:

```text
Pending State Since Last Checkpoint:
- turn_delta:
- health_delta:
- relationship_delta:
- artifact/trait triggers:
- conflict_delta:
- location_delta:
- open consequences:
- checkpoint_due:
- immediate_trigger:
```

The buffer must stay short. It records only facts needed to safely
persist the next checkpoint. Keep the per-turn narration/options and
one-line session-log summaries in conversation as well so the checkpoint
can append one `SessionLogEntry` per buffered turn.

## Checkpoint Policy

Default checkpoint interval: every 3 turns.

Maximum checkpoint interval: 5 turns.

Ordinary turns may proceed without file writes when no immediate trigger
fires and the checkpoint interval has not been reached. A checkpoint
turn applies the pending buffer to canonical JSON, appends session-log
entries, re-renders markdown, and lints the save before the user-facing
reply is considered safe.

The user can force a checkpoint/save at any time. Treat explicit
"save", "checkpoint", "存档", and equivalent requests as tooling input,
not in-world action, unless they also include an in-world move.

### Immediate Checkpoint Triggers

Do not leave these events only in chat memory. Flush them before
replying, even if the ordinary checkpoint interval has not elapsed:

- player death
- health becomes `critical` or `dead`
- stage breakthrough
- destiny trait gained
- artifact used or exhausted
- destiny trait exhausted
- conflict frame resolves
- major scene/location transition
- major relationship/faction/world-state change
- important NPC death/betrayal
- run restart
- user explicitly asks to save
- major divergence from the source novel

If a turn includes one of these triggers, switch to checkpoint mode for
that turn. If unsure whether an event is "major", checkpoint.

## Loading Context

### Start / Resume / After Checkpoint

Load enough canonical context to seed the active summary:

1. `world_state.json`, `relationship_state.json`, `open_loops.json`,
   `meta.json`, and the last 6 entries of `session_log.jsonl`.
2. `packs/<pack>/index.md` for `language`.
3. `packs/<pack>/novel_rules.md` and `packs/<pack>/progression_rules.md`
   as compact reference for hard novel rules, stages, artifacts,
   innate traits, destiny traits, and health wording.
4. `packs/<pack>/canon_guardrails.md` plus universal
   `genre_packs/universal/canon_guardrails.md`.
5. Entity pages for `current_location`, `present_entities`, and any
   active thread whose id maps to an arc slug.
6. `genre_packs/universal/prompts/core_play_kernel.md` and
   `gm_system_fragment.md` for output format and conditional systems.

Then run:

```bash
python tools/inspect_save.py --save <pack>/<save_id> --active-summary
```

Copy the resulting active-state summary into the conversation. This
summary is the default context for ordinary turns.

### Ordinary Turn

Do not re-scan the full pack or save by default. Use:

- the active-state summary;
- the pending buffer;
- recent conversation;
- any narrow rule/page that the current turn actually triggers.

Load conditional references only when needed:

- `gm_system_fragment.md` sections for conflict HUD, options, labeled
  options, health/death, breakthrough, or player-agency edge cases;
- `systems/*.md` for artifact/trait/health semantics when a relevant
  hook is primed;
- `breakthrough_pick.md` on breakthrough turns;
- `death_coda.md` and `playbooks/death-and-restart.md` on terminal
  death or clean completion.

Never scrape `current_scene.md` or `session_log.md` for state.
Rendered markdown is display-only.

## Turn Modes

### Mode A · Ordinary Turn

Use this path when no immediate checkpoint trigger fires and the
checkpoint interval has not been reached.

1. Run the Core Play Kernel.
2. Produce the player-facing reply in the pack's language:
   - compact HUD line derived from active summary + pending buffer;
   - conflict HUD line if an active conflict remains live;
   - narration;
   - exactly three A/B/C options plus the fixed free-form D slot, unless
     a breakthrough/death block replaces options.
3. Update the pending buffer in conversation.
4. Record the turn's player input, narration, options, and summary in
   conversation for the next checkpoint.
5. Decide whether the next turn is scheduled checkpoint due.

The compact HUD on an ordinary turn is provisional because it has not
been rendered from JSON yet. Keep it consistent with the active summary
and pending buffer, and do not invent new HUD vocabulary.

### Mode B · Scheduled Checkpoint Turn

Use this path when `turn_delta` reaches 3 by default, or before it would
exceed 5.

1. Resolve the current player input with the Core Play Kernel.
2. Apply buffered turns in chronological order. Do not collapse the
   buffer into a final-state patch. Instead, apply one buffered turn at a time:
   take that turn's patch, validate it against the current
   in-memory state, update the state, append that turn's
   `SessionLogEntry`, then move to the next buffered turn. This preserves
   conflict costs, survival-trigger `prior_health_state`, stage →
   destiny sequencing, and session-log turn numbers.
3. Use the existing patch vocabulary for each buffered turn:
   `world_state`, `present_entities_*`, `active_threads_*`,
   `objectives_*`, `relationship_updates`, `open_loops_*`,
   `inventory_*`, `hidden_truths_append`, `conflict_open`,
   `conflict_update`, `conflict_resolve`, `player_health_state`,
   `player_stage_advance`, `player_destiny_trait_add`,
   `player_trait_exhaust`, and `divergence`.
4. Validate each turn patch against `tools/_models.py` before applying
   the next one. Drop invalid sub-patches and append `DivergenceNote`
   entries rather than overwriting broken state with guesses.
5. Persist after every buffered turn has been applied:
   - `world_state.json` with `turn` advanced once per buffered turn;
   - `relationship_state.json`;
   - `open_loops.json`;
   - `player.json` mirrored from `world_state.player`;
   - one `session_log.jsonl` entry per buffered turn;
   - `meta.json::hidden_truths` and `divergences.jsonl` as needed.
6. After that, render/lint only once after every buffered turn has been applied:

   ```bash
   python tools/render_save.py --save <pack>/<save_id>
   python tools/lint_save.py --save <pack>/<save_id>
   ```

7. If lint exits 1, fix before replying. If lint exits 0, refresh the
   active summary with `inspect_save.py --active-summary`, clear the
   pending buffer, and reply to the user.

### Mode C · Immediate Checkpoint Turn

Use this path whenever an immediate trigger fires. Same as scheduled
checkpoint mode, except the current trigger must be persisted before the
reply. Examples:

- a `player_health_state: "dead"` patch must run survival-trigger
  precedence and either persist the trigger firing or the terminal death
  flow immediately;
- `conflict_resolve` must write `last_conflict_summary` plus the
  implied relationship/open-loop/world-state changes immediately;
- a major location jump must update `current_location` and
  `present_entities` immediately;
- a major source-novel divergence must either be encoded in state or
  logged to `divergences.jsonl` immediately.

Do not postpone an immediate trigger to the next scheduled checkpoint.

## Output Format

The chat reply keeps the existing player-facing shape:

- **No active conflict** — compact HUD line, blank line, prose
  narration, blank line, four option strings.
- **Active conflict** — compact HUD line, blank line, conflict HUD
  line, blank line, prose narration, blank line, four option strings.
- **Breakthrough / death / completion** — compact HUD line, blank line,
  short coda/breakthrough narration, blank line, the required boxed
  block from `breakthrough_pick.md` or `death_coda.md`.

On checkpoint turns, copy the compact HUD line from freshly rendered
`current_scene.md` after `render_save.py` succeeds. On ordinary turns,
derive the same line from the active summary + pending buffer and keep
it provisional until the next checkpoint.

## Conditional System Reminders

These systems remain fully functional. They are not scanned in full on
every ordinary turn.

- **Player agency:** player input outranks active threads and
  objectives. If the player abandons a thread, follow the player and
  remove or downgrade the thread at checkpoint.
- **Canon / source-novel divergence:** protect hard novel rules from
  `novel_rules.md` and `canon_guardrails.md`. Major divergence is an
  immediate checkpoint trigger.
- **Conflict frames:** open only for real tension with opposing wants;
  update momentum and paid costs while live; resolve when stakes are
  answered or the player walks away.
- **Build hooks:** artifact, innate, and destiny labeled options appear
  only when the current pivot makes them relevant. Default is zero
  labeled options; at most one labeled option per turn.
- **Health/death:** `critical` takes priority on the next turn.
  Before terminal death, check survival-trigger precedence in order:
  `bond_rescue`, `not_meant_to_die`, then `last_barrier`.
- **Breakthrough:** stage advance happens only on climactic beats,
  never more than once per turn, and immediately checkpoints.

## Failure Handling

- If the user's input is meta/tooling/debugging, do not advance the
  turn unless they also include an in-world action.
- If canonical JSON is malformed, stop and tell the user. Never replace
  malformed state from memory.
- If the active summary and canonical files disagree at resume, canonical
  JSON wins. Rebuild the active summary from disk and discard stale
  pending memory.
