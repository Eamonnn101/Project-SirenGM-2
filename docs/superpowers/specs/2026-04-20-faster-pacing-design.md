# Faster Pacing Design — Conflict Beat Budget + Denser Turns + Time Compression

Date: 2026-04-20
Status: Approved, pending implementation plan

## Problem

Play-testing shows the game drags, particularly in combat. A single scene
(chase + combat against Li Mochou in 陆家庄) ran 12 turns in one session:
5 turns of chase/escape (turns 1–5) followed by 7 turns of combat
(turns 6–12), with the combat still unresolved by turn 12. Every turn
executed a tiny half-beat (抢腕 → 藏针被拍偏 → 毒掌提起 → …) without the
frame ever closing.

Root causes, from `genre_packs/universal/prompts/gm_system_fragment.md`:

1. **No target length on conflict frames.** Lint warns at 10 active turns,
   but nothing pushes the GM to resolve. 10 turns is already well past the
   player's patience.
2. **Beat density rule tops out at one pivot per turn.** The current rule
   asks for "action lands → NPC reactions → one complication." That
   invites micro-exchanges that each feel dense in isolation but
   collectively stall.
3. **No concept of narrative time compression.** Even routine actions
   (travel, rest) are narrated step by step at 300–700 zh chars per turn.

## Goal

- Conflict frames (combat, chase, debate, any `ConflictFrame`) resolve
  in 3–5 turns by default, up to 6 for genuinely large-scope conflicts.
- Each turn packs roughly two turns' worth of previous content (two
  pivots, not one) — narration length budget stays 300–700 zh chars /
  200–500 en words.
- Routine player actions (travel, rest, shopping, montage) compress
  into one turn regardless of in-world duration.

## Non-goals

- Changing the ingest pipeline, save format outside `ConflictFrame`, or
  the options/HUD-language layer.
- Tuning individual novels — this is a universal pack change.
- Shipping a separate "combat pack." Pacing is cross-genre; one
  mechanism covers combat, chase, debate, heist, courtroom, etc.

## Design

Three-layer enforcement, hard → soft:

### 1. Schema hard constraint — `ConflictFrame.beat_budget`

Add field to `tools/_models.py::ConflictFrame`:

```python
beat_budget: int = Field(default=4, ge=3, le=6)
```

Semantics:

- Set at `conflict_open` time by the GM based on scope (see table below).
  Defaults to 4 if not specified in the open patch.
- Legal range 3–6. Conflicts genuinely larger than 6 beats are split into
  sequential frames (resolve the first, open the next).
- Decremented by 1 **automatically** each time a `conflict_update` patch
  is accepted. The GM does NOT patch `beat_budget` directly inside
  `conflict_update`; if they do, drop the field and log a divergence.

Recommended budget table (GM guidance, not schema-enforced):

| Conflict kind (examples) | Recommended `beat_budget` |
| --- | --- |
| Brawl, short chase, assassination attempt | 3 |
| General combat, ambush, flight (default) | 4 |
| Debate, negotiation, interrogation, alchemy crisis | 5 |
| Siege, large courtroom, multi-party standoff | 6 |

Countdown behavior:

- `beat_budget == 1` — last beat imminent. GM MUST offer at least one
  decisive (收束型) A/B/C option. HUD momentum column switches to
  `收束在即 / Endgame`.
- `beat_budget == 0` — this turn SHOULD emit `conflict_resolve`.
  Acceptable outcomes: player wins, opposition wins, even +
  `world_change`, player disengages. A disengagement still counts as
  resolve.
- `beat_budget == -1` — one-turn overshoot allowed if a just-revealed
  development genuinely needs to play out; then resolve.
- `beat_budget <= -2` — lint warns.

### 2. GM prompt soft guidance — `gm_system_fragment.md`

Three edits inside the *Conflict frame* section:

**Edit A** · New subsection at the end of *Conflict frame (load-bearing)*:

> **Beat budget (load-bearing).** On `conflict_open`, set `beat_budget`
> to 3–6 based on the conflict's scope (see guidance table). Each
> `conflict_update` decrements it automatically.
>
> - `beat_budget == 1`: at least one of A/B/C must be a concrete
>   decisive move that would resolve the frame if it lands.
> - `beat_budget == 0`: this turn SHOULD emit `conflict_resolve`
>   (player wins / opposition wins / even + world_change / player
>   disengages — disengagement counts as resolve).
> - `beat_budget == -1` allowed only when a just-landed reveal truly
>   needs one more beat; then resolve. Lint warns at `<= -2`.

**Edit B** · Rewrite *Beat density* from one-pivot-per-turn to two:

> **Beat density (load-bearing).** One turn = one player decision.
> Inside that turn, play the beat through **two pivots** before handing
> back:
>
> 1. The player's action lands — show what it does, including the
>    immediate counter/response.
> 2. First pivot: an NPC reaction that materially changes the situation
>    (a wound, a disarm, a reveal, a bystander moving).
> 3. Second pivot: the complication on top of that — momentum shifts,
>    a new arrival, a cost crystallizes, a door closes. The A/B/C
>    options are a choice on the state *after* both pivots.
>
> Previously this rule called for a single pivot per turn; combat drifted
> into micro-exchanges (抢腕 → 藏针 → 拂尘 → 毒掌, one per turn). One
> turn should now compress what used to be two turns' beats.

**Edit C** · Options constraint addendum:

> While a frame is active AND `beat_budget <= 1`, one of A/B/C MUST be a
> 收束型 move (could resolve the frame this turn if it lands). Generic
> "press the advantage" is not enough; the option must describe the
> specific decisive action.

### 3. Style guide — time compression

New section in `genre_packs/universal/style_guide.md`:

> **Time compression.** When the player's input is routine — travel,
> rest, shopping, waiting for a scheduled event, training montage, long
> study — one turn MAY fast-forward hours or days to the next point of
> tension, rather than narrating the intervening steps.
>
> Signals that a turn should compress time: the player wrote a goal
> ("I ride to 嘉兴"), not a step ("I tighten the saddle"); nothing in
> `present_entities` or `active_threads` would make the routine itself
> fraught; no active conflict frame.
>
> Inside an active conflict frame, never compress time — every turn is
> one beat inside the frame.

### 4. HUD — `tools/render_save.py`

When rendering the conflict HUD line:

- Read `current_conflict.beat_budget`.
- If `beat_budget <= 1`, force the momentum column to
  `收束在即` (zh) / `Endgame` (en), overriding the underlying momentum
  label.
- Otherwise render normally per the existing momentum table.

No numeric budget is shown to the player. Budget lives in JSON; only its
endgame threshold leaks into the HUD.

### 5. Lint — `tools/lint_save.py`

- **Remove** the existing rule "conflict active > 10 turns → warn".
- **Add**: if `current_conflict` is present and
  `beat_budget <= -2` → warn ("conflict has overshot budget by 2+ beats,
  should resolve").
- **Add** (info only, not a warning): if the last resolved conflict
  summary shows resolve happened with `beat_budget > 2` remaining → info
  message ("conflict resolved early") for observability; no action.

### 6. Playbook update

`playbooks/play-turn.md` · *Conflict frame lifecycle* adds a short
paragraph on `beat_budget` flow (set at open, auto-decrement on update,
resolve expected at 0, 1-turn overshoot allowed, lint warns at -2).

`CLAUDE.md` is not changed — this schema detail lives below the top-level
operating schema.

## Backward compatibility

- Existing saves without `beat_budget`: Pydantic fills `default=4` on
  load. Next successful write persists it.
- A legacy in-flight frame (one that has already been active for N turns
  before this change): gets a fresh budget of 4 from the load point,
  regardless of how many turns it has already run. Worst case, a
  10-turns-old frame gets 4 more before lint warns — still a material
  improvement, and a one-time effect per save.
- Resolves that happen *before* the load-point of this change are
  untouched.
- No migration script needed.

## Testing

- Unit: `ConflictFrame` accepts `beat_budget` 3–6, rejects 2 and 7,
  defaults to 4 when absent.
- Unit: patch application decrements `beat_budget` on `conflict_update`;
  ignores GM-supplied `beat_budget` inside `conflict_update`.
- Unit: `lint_save.py` warns at `beat_budget <= -2` and not before;
  info-logs early resolve.
- Unit: `render_save.py` emits `收束在即 / Endgame` when
  `beat_budget <= 1`; normal momentum otherwise.
- Manual: replay a chase + combat scene similar to the Li Mochou log
  and confirm the chase resolves in ≤4 turns and the combat in ≤4 turns.

## Risks

- **Premature resolution.** The GM may hit budget 0 mid-beat and force
  an awkward resolve. Mitigation: the 1-turn overshoot permission + the
  GM's budget-selection guidance at `conflict_open`. If practice shows
  this is common, raise the default from 4 to 5 in a follow-up.
- **Player feels railroaded by early endgame HUD.** Mitigation: the
  HUD word is "收束在即 / Endgame", not a countdown; the prose still
  dictates the feel, and the options still include the free-form D
  slot.
- **Time compression gets abused inside conflicts.** Mitigation: the
  style guide rule explicitly forbids compression inside an active
  frame.

## Out of scope (deferred)

- Per-genre budget tables (e.g. a wuxia pack vs. a courtroom-drama pack
  wanting different defaults). If ever needed, add a
  `novel_rules.md` override hook.
- Multi-frame concurrency (two conflicts running in parallel). Current
  design assumes one active frame at a time; splitting large conflicts
  into sequential frames is the workaround.
- Player-visible budget number. Kept hidden per section 4; reconsider
  only if play-test feedback asks for it.
