---
name: stages
kind: progression
---

# Universal · Stages

Every run moves the protagonist through **6 narrative stages**.
Stages are not XP or levels — they are soft milestones describing
the shape of the run at a given moment. They are indexed 0..5 and
stored on the save as `PlayerState.stage_index` (structured) and
`PlayerState.stage_label` (novel-themed display).

## The 6 stages

| index | universal seed label          | what the run feels like                                           |
| ----- | ----------------------------- | ----------------------------------------------------------------- |
| 0     | establish footing             | Arriving. Learning the rules. Gathering allies, places, gear.     |
| 1     | enter the main conflict       | The central opposition becomes real and personal.                 |
| 2     | build influence / resources   | The PC starts to *matter* — a name, a base, obligations.          |
| 3     | break a key stalemate         | A long-standing equilibrium is forced to shift.                   |
| 4     | become a major variable       | The PC's choices now reshape the world around them.               |
| 5     | rewrite fate                  | The climactic resolution that ends the run cleanly.               |

Each user pack renames and re-flavors these stages inside its
`progression_rules.md` §1 ("Stages"). The universal index stays
stable so lint, meta, and draft-bias can reason across packs.

## Stage advance guidance (soft)

Breakthroughs are the GM's call. The rules below are loadbearing
discipline — not hard lints — and live here so the agent can read
them on every turn.

- **Max 5 advances per run.** From 0 → 5, never more.
- **Never on a non-climactic turn.** A breakthrough landing during
  small talk or routine logistics is always wrong. The trigger
  should be a resolved major conflict, a closed hard-arc, a
  decisive reveal, a bound oath, a geographic/factional threshold
  crossed, or equivalent. User packs list 2–4 novel-specific
  patterns per stage in `progression_rules.md` §2.
- **Never two stages in one turn.** Even if the narration could
  justify it, compress into a single stage advance. The next stage
  advance must wait.
- **Never skip a destiny pick** (other than via the explicit D
  fallback in the breakthrough block). If the player picks D, the
  stage still advances but no destiny trait is added.
- **No regression.** Stages only move forward. Loss/defeat is
  handled in the health ladder and death flow, not by rolling back
  `stage_index`.

## Breakthrough turn — engine contract

When the GM judges a breakthrough fits the beat, the turn's patch
emits `player_stage_advance: {new_index, new_label}`. The turn
output replaces the usual A/B/C/D options with the
**Breakthrough block** (see `prompts/breakthrough_pick.md`),
offering 3 destiny traits + the fixed D fallback. The player's
choice on the next turn patches `player_destiny_trait_add`.

Reached `stage_index == 5`? The run can now end cleanly. The next
climactic resolve is the run-end beat — see
`systems/health_and_death.md` § Clean completion.
