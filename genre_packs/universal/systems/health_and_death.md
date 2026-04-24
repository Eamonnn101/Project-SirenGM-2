---
name: health_and_death
kind: progression
---

# Universal · Health ladder + death

Every run tracks the PC's health as a **5-state narrative ladder**,
stored as `PlayerState.health_state`. No HP, no damage numbers, no
rolls. The GM updates the ladder by emitting
`player_health_state: <state>` in the turn's patch whenever the
narration implies a move.

## The 5 states

| state         | feel                                                                |
| ------------- | ------------------------------------------------------------------- |
| `healthy`     | Uninjured, unstrained. Default starting state.                      |
| `hurt`        | A real wound or significant stress. Reduces stamina for the scene.  |
| `badly_hurt`  | Bleeding, burned, fractured, or shaken deeply. Visible to others.   |
| `critical`    | Immediate, acute danger. One wrong step away from `dead`.           |
| `dead`        | Terminal (after survival-trigger precedence — see below).           |

Moves between **adjacent** states are the common case. A skip
(`healthy → critical` from an assassin strike, or `badly_hurt →
healthy` from a rare restoration) is allowed **only** when the
prose clearly stages the skip — never a silent state change.

## `critical` is priority — not a strict 1-turn clock

When `health_state` becomes `critical`, the **next turn** must:

1. Treat the danger as the dominant beat. No shopping, no
   exposition detour, no thread-switching.
2. Center A/B/C/D on the crisis.
3. Show the danger in the prose — a slide toward recovery OR
   toward death, visible in every intervening turn.

It is **not** a hard "recover or die on the very next turn" timer.
Genre-appropriate consequence timing is allowed:

- a poison may linger 2–3 beats
- a bleed-out may play across a contested scene
- a spiritual corruption may need a specific counterritual

The only rule is: the danger stays visible, and the prose never
silently flattens back to "healthy" without the scene having done
the work.

## Survival-trigger precedence (load-bearing)

Before a `player_health_state: "dead"` patch becomes terminal, the
engine checks the following triggers in this fixed order. Any one
firing replaces the patch with the trigger's outcome: `health_state
→ critical`, the relevant artifact/trait is exhausted, and the
narration shows the trigger firing. The turn is **not** terminal.

**Precedence order:**

1. **Artifact `bond_rescue` archetype.** If `player.artifact.archetype
   == "bond_rescue"` and `player.artifact.used == False`, the
   artifact fires → critical, artifact `used: true`.
2. **Destiny `not_meant_to_die`.** If a destiny trait with this
   archetype exists and is not exhausted, it fires → critical,
   trait `exhausted: true`.
3. **Destiny `last_barrier`.** Only on the specific transition
   `critical → dead` (not a skip-to-dead from healthy/hurt/badly_hurt).
   Fires → the turn stays at `critical` (one extra buffer turn),
   trait `exhausted: true`. Next turn the danger returns full-force.

If none of the above applies, the terminal death flow runs.
Implementation lives in `tools/_progression.py ::
resolve_survival_trigger`; the agent must follow the same order
when narrating.

**No other MVP trigger prevents death.** Novel-themed destiny
traits with death-flavored prose still map to one of the 12
universal seeds, and only the two above (`not_meant_to_die`,
`last_barrier`, plus any `bond_rescue` artifact) carry
death-prevention semantics.

## Terminal death flow

When a fatal patch is committed without a survival trigger
firing, the run ends.

1. The turn's narration is the **final beat** — a pack-language
   coda, no options block. The run-end HUD block (see
   `prompts/death_coda.md`) replaces A/B/C/D.
2. The patch sets `player.health_state = "dead"` and
   `player.status = "dead"`. Any active conflict is resolved in
   the same patch with a `conflict_resolve` whose outcome names
   the protagonist's death.
3. The agent writes `saves/<pack>/<save_id>/run_summary.md`
   (200–400 chars, pack language, covering stages reached, key
   arcs, cause of death).
4. The agent updates `saves/<pack>/meta_progress.json`:
   - merges this run's artifact / innate / destiny archetype keys
     and novel-themed slugs into the respective `seen_*` lists
     (dedup);
   - `deaths_count += 1`; appends a `DeathRecord`;
   - `best_stage_index = max(best_stage_index,
     player.stage_index)`.
   - Does **not** increment `runs_finished` — that counter fires
     only on clean completion.
5. The agent asks whether to start a new game against the same
   pack, load a different save, or pause. See
   `playbooks/death-and-restart.md`.

No further turns are accepted on a terminal save.
`tools/lint_save.py` requires `run_summary.md` when
`health_state == "dead"`.

## Clean completion

When the run reaches `stage_index == 5` AND the GM judges the
final climactic beat has fully landed (the novel-themed "rewrite
fate" equivalent has resolved), the agent emits the **Run-end
block** with `结局类别：功成 / Outcome: Completed`, increments
`runs_finished`, and merges seen pools into meta_progress.json.
No `DeathRecord`. `deaths_count` unchanged. The save is retired
but not terminal-via-death.

## Engine contract

- `player_health_state` patch is valid at any turn. Setting
  `"dead"` routes through survival-trigger precedence before
  becoming terminal.
- `player.health_state == "dead"` ⇒ `player.status == "dead"`
  (model validator).
- `player.status == "dead"` ⇒ `player.health_state ∈ {"critical",
  "dead"}` (lets the narration land the death beat in the same
  turn before persistence transitions).
- On terminal death, the save's `run_summary.md` must exist.
  `lint_save.py` enforces this.
