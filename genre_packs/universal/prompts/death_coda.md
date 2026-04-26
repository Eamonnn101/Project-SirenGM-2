---
name: death_coda
stage: runtime.gm
---

# Runtime · Death coda + run-end block

Genre-agnostic prompt fragment for the terminal-death turn and the
clean-completion turn. Both paths emit the same **Run-end block**
shape, with the "结局类别 / Outcome" field naming the difference.

Triggered from `playbooks/death-and-restart.md`.

## Precondition: survival-trigger precedence

Before running this coda for a death, the engine **must** have
checked `resolve_survival_trigger(player, prior_health_state)`
from `tools/_progression.py`. If any trigger fires, this coda
does **not** run — the survival trigger narration runs instead.
See `systems/health_and_death.md` § Survival-trigger precedence
and `gm_system_fragment.md` § Survival trigger precedence.

The order is fixed (artifact `bond_rescue` → destiny
`not_meant_to_die` → destiny `last_barrier`). The coda below fires
only after all applicable triggers have been exhausted or none
applied.

## Terminal-death turn output

1. **Final narration** — a single coda beat in the pack's
   language. Length: shorter than a normal turn (150–350 zh chars
   / 100–200 en words). The voice follows
   `progression_rules.md` §7 ("Breakthrough voice" — reused as the
   novel's funeral voice). Close-weighted, consequence-grounded,
   no meta-commentary.
2. **Run-end block** (below), verbatim, replacing A/B/C/D.
3. **No options block**. The turn ends the run.

## Clean-completion turn output

1. **Final narration** — a single triumphal / settling beat,
   same length budget as the death coda. Voice per
   `progression_rules.md` §7.
2. **Run-end block** (below) with `结局类别：功成 / Outcome:
   Completed`.
3. **No options block**.

## Run-end block (zh reference)

```
╔══ 落幕 · 第 <turn> 回 · <stage_label> ══╗
结局类别 │ <陨落 / 功成>
<if death:>
死因    │ <cause>
<endif>
落笔之地│ <current_location_name>
身具法宝│ <artifact_name>〔<archetype_label>〕
已刻命格│ <destiny_list>  或 "—"
尘埃小记│ <run_summary snippet, ~80 chars>

━ 此 pack 档案 ━
开局次数 │ <runs_started>     陨落次数 │ <deaths_count>
完局次数 │ <runs_finished>    最高境界 │ <best_stage_label>
图鉴覆盖│ 法宝 <a/3>  天赋 <b/5>  命格 <c/12>
╚══════════════════════════════════════╝

此局已终。是否再起一局？
· 沿用此 pack，从零再来
· 选择其他 pack
· 载入旧档
· 暂停
```

`en` variant: replace `│` with `|`, replace every zh label with
its English counterpart (see `tools/_hud.py` HUD_LABELS[en]), and
replace the closing menu with:

```
This run is over. Start another?
- Replay this pack from scratch
- Pick a different pack
- Load an older save
- Pause
```

## Patch + file-write obligations (death path)

On the terminal-death turn, the engine's patch and filesystem
updates are bundled — the agent executes all of them in the same
turn:

1. **Patch (play-turn.md Step 2):**
   - `player_health_state: "dead"`
   - `world_state: {player: {status: "dead"}}` (updates coarser
     status to match)
   - `conflict_resolve` if a conflict is live, with the death as
     the outcome and `world_change` naming the terminal event
     (also appended to `hidden_truths` via the existing path).
2. **File writes (play-turn.md immediate backup + death flow):**
   - Normal persist to `world_state.json`, `player.json`, append
     to `session_log.jsonl`.
   - Write `saves/<pack>/<save_id>/run_summary.md` — 200-400
     chars, pack language, covering stages reached, key arcs,
     cause of death. One paragraph is enough.
   - Update `saves/<pack>/meta_progress.json` via
     `merge_run_into_meta(meta, player=..., save_id=..., turn=...,
     outcome="death", cause=...)` from `tools/_progression.py`.
   - Checkpoint `render_save.py` + `lint_save.py` exit 0 before the
     reply.

## Patch + file-write obligations (completion path)

On the clean-completion turn (stage_index == 5 and the final beat
lands cleanly):

1. **Patch:** normal resolve of whatever conflict/arc was live,
   plus any `open_loops_close` the ending implies.
2. **File writes:**
   - `run_summary.md` same as above, in victory voice.
   - `merge_run_into_meta(..., outcome="completion")` — bumps
     `runs_finished`, no `DeathRecord`.
3. **No `player.status = "dead"` patch** on this path — the PC is
   alive; the save is simply retired.

## Common failure modes

- Skipping the survival-trigger check. A `bond_rescue` artifact
  that should have fired must not be bypassed by narrative
  convenience.
- Treating `critical` like a 1-turn death timer. `critical` means
  priority handling, not mandatory death next turn. See
  `systems/health_and_death.md`.
- Leaving a conflict frame open on the death turn. Every
  terminal-death turn must include `conflict_resolve` if a frame
  was live.
- Forgetting `run_summary.md`. `lint_save.py` will flag this and
  block the session from moving on.
- Narrating the run-end block contents inside the prose as well
  (duplication). The block is the player's visible artifact; the
  narration is the coda beat.
