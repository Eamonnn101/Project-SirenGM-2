# Faster Pacing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `ConflictFrame` a `beat_budget` (3–6, default 4) so conflicts resolve in 3–5 turns, tighten the GM prompt to pack two pivots per turn, and allow time compression outside conflicts.

**Architecture:** `beat_budget` is the *initial* budget set at `conflict_open`. Remaining beats are derived on the fly as `beat_budget - (world.turn - opened_turn)` via a helper method — no auto-decrement engine, no GM-patch contract, no desync risk. Lint warns when overshoot exceeds 1 turn. `render_save.py` and the GM system fragment both show `收束在即 / Endgame` in the momentum field when ≤ 1 beat remains. Parallel prompt edits (`gm_system_fragment.md`, `style_guide.md`, `play-turn.md`) carry the soft guidance and time-compression permission.

**Tech Stack:** Python 3.10+, Pydantic 2, stdlib `unittest` for tests (no new deps).

**Reference spec:** `docs/superpowers/specs/2026-04-20-faster-pacing-design.md`

---

## File map

**Create:**
- `tests/__init__.py` — empty package init so `python -m unittest tests.<module>` works
- `tests/test_conflict_budget.py` — schema/helper/lint/render tests

**Modify:**
- `tools/_models.py` — add `beat_budget` field + `beats_remaining` helper on `ConflictFrame`
- `tools/lint_save.py` — replace `STALE_CONFLICT_THRESHOLD` rule with budget-aware rule
- `tools/render_save.py` — override momentum display with `收束在即 / Endgame` when beats_remaining ≤ 1
- `genre_packs/universal/prompts/gm_system_fragment.md` — beat-budget subsection, beat-density rewrite, options constraint addendum, HUD rule
- `genre_packs/universal/style_guide.md` — add *Time compression* section
- `playbooks/play-turn.md` — add `beat_budget` lifecycle paragraph
- `docs/superpowers/specs/2026-04-20-faster-pacing-design.md` — refine the decrement paragraph to reflect derived design

---

## Task 1: Add `beat_budget` field and `beats_remaining` helper to `ConflictFrame`

**Files:**
- Modify: `tools/_models.py:87-111` (the `ConflictFrame` class)
- Create: `tests/__init__.py`
- Create: `tests/test_conflict_budget.py`

- [ ] **Step 1: Create empty tests package init**

```bash
: > tests/__init__.py
```

- [ ] **Step 2: Write failing tests for `beat_budget` field**

Create `tests/test_conflict_budget.py`:

```python
"""Tests for ConflictFrame beat_budget + derived remaining beats."""
from __future__ import annotations

import unittest

from pydantic import ValidationError

from tools._models import ConflictFrame, ConflictSide


def _make_frame(**overrides):
    defaults = dict(
        id="c_test_01",
        kind="combat",
        stake="who reaches the relic first",
        sides=[
            ConflictSide(label="player", want="escape"),
            ConflictSide(label="opposition", want="capture"),
        ],
        opened_turn=5,
    )
    defaults.update(overrides)
    return ConflictFrame(**defaults)


class TestBeatBudget(unittest.TestCase):
    def test_default_beat_budget_is_4(self):
        frame = _make_frame()
        self.assertEqual(frame.beat_budget, 4)

    def test_beat_budget_accepts_3_through_6(self):
        for n in (3, 4, 5, 6):
            frame = _make_frame(beat_budget=n)
            self.assertEqual(frame.beat_budget, n)

    def test_beat_budget_rejects_below_3(self):
        with self.assertRaises(ValidationError):
            _make_frame(beat_budget=2)

    def test_beat_budget_rejects_above_6(self):
        with self.assertRaises(ValidationError):
            _make_frame(beat_budget=7)

    def test_legacy_save_without_beat_budget_defaults_to_4(self):
        raw = {
            "id": "c_legacy_01",
            "kind": "chase",
            "stake": "escape",
            "sides": [
                {"label": "player", "want": "escape", "members": [], "paid": []},
                {"label": "pursuers", "want": "capture", "members": [], "paid": []},
            ],
            "momentum": "setup",
            "escalation_notes": [],
            "opened_turn": 3,
        }
        frame = ConflictFrame.model_validate(raw)
        self.assertEqual(frame.beat_budget, 4)


class TestBeatsRemaining(unittest.TestCase):
    def test_remaining_equals_budget_on_open_turn(self):
        frame = _make_frame(opened_turn=5, beat_budget=4)
        self.assertEqual(frame.beats_remaining(current_turn=5), 4)

    def test_remaining_decreases_with_age(self):
        frame = _make_frame(opened_turn=5, beat_budget=4)
        self.assertEqual(frame.beats_remaining(current_turn=6), 3)
        self.assertEqual(frame.beats_remaining(current_turn=8), 1)
        self.assertEqual(frame.beats_remaining(current_turn=9), 0)

    def test_remaining_goes_negative_on_overshoot(self):
        frame = _make_frame(opened_turn=5, beat_budget=4)
        self.assertEqual(frame.beats_remaining(current_turn=10), -1)
        self.assertEqual(frame.beats_remaining(current_turn=11), -2)

    def test_endgame_threshold_is_budget_minus_1(self):
        frame = _make_frame(opened_turn=5, beat_budget=4)
        self.assertFalse(frame.is_endgame(current_turn=7))  # remaining=2
        self.assertTrue(frame.is_endgame(current_turn=8))   # remaining=1
        self.assertTrue(frame.is_endgame(current_turn=9))   # remaining=0


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
.venv/bin/python -m unittest tests.test_conflict_budget -v
```

Expected: errors like `AttributeError: 'ConflictFrame' object has no attribute 'beat_budget'` or `beats_remaining`.

- [ ] **Step 4: Add `beat_budget` field + helpers to `ConflictFrame`**

In `tools/_models.py`, modify the `ConflictFrame` class (currently at lines 87–111). The final class should read:

```python
class ConflictFrame(BaseModel):
    """A scene of tension tracked by the conflict engine.

    Cross-genre: `kind` is free-form (combat, debate, chase, trial, ...).
    Momentum is a discrete label, never a number — consistent with the
    no-numeric-combat-stats guardrail.

    `beat_budget` is the initial pacing budget set at conflict_open and
    never changes thereafter. Remaining beats are derived from the
    current world turn via `beats_remaining`.
    """

    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., description="Free-form id, e.g. 'c_bianlun_01'.")
    kind: str = Field(..., description="Free-form conflict kind the GM chose for this scene.")
    stake: str = Field(..., description="One-line 'what both sides are fighting over'.")
    sides: list[ConflictSide] = Field(..., description="Two or more parties with opposing wants.")
    momentum: ConflictMomentum = "setup"
    escalation_notes: list[str] = Field(default_factory=list)
    opened_turn: int
    beat_budget: int = Field(
        default=4,
        ge=3,
        le=6,
        description=(
            "Initial pacing budget set at conflict_open. "
            "Remaining beats = beat_budget - (current_turn - opened_turn). "
            "Lint warns when remaining drops below -1."
        ),
    )

    @model_validator(mode="after")
    def _validate_sides(self) -> "ConflictFrame":
        if len(self.sides) < 2:
            raise ValueError("ConflictFrame.sides must have at least 2 entries")
        labels = [s.label for s in self.sides]
        if len(set(labels)) != len(labels):
            raise ValueError(f"ConflictFrame.sides has duplicate labels: {labels}")
        return self

    def beats_remaining(self, current_turn: int) -> int:
        """Beats left before budget is exhausted. Can go negative on overshoot."""
        return self.beat_budget - (current_turn - self.opened_turn)

    def is_endgame(self, current_turn: int) -> bool:
        """True when the HUD should display endgame; i.e. remaining <= 1."""
        return self.beats_remaining(current_turn) <= 1
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/python -m unittest tests.test_conflict_budget -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add tools/_models.py tests/__init__.py tests/test_conflict_budget.py
git commit -m "$(cat <<'EOF'
feat(models): add ConflictFrame.beat_budget + beats_remaining helper

Sets up the pacing mechanism: initial budget 3-6 (default 4) at
conflict_open, remaining beats derived from opened_turn + current
world turn. No auto-decrement — the engine-less design keeps GM
patch contract simple.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Update `lint_save.py` to use budget-aware threshold

**Files:**
- Modify: `tools/lint_save.py:212-227`
- Modify: `tests/test_conflict_budget.py` (add lint tests)

- [ ] **Step 1: Write failing lint tests**

Append to `tests/test_conflict_budget.py` (before the `if __name__` block):

```python
class TestLintConflictFrame(unittest.TestCase):
    """Lint should warn only when the conflict overshoots beat_budget by 2+."""

    def _make_save_with_frame(self, *, opened_turn: int, current_turn: int, budget: int):
        from tools._models import PlayerState, WorldState, Save, RelationshipState, OpenLoops

        frame = _make_frame(
            opened_turn=opened_turn,
            beat_budget=budget,
        )
        world = WorldState(
            turn=current_turn,
            current_location="emergent:test_room",
            present_entities=[],
            player=PlayerState(name="Test", slug="player"),
            current_conflict=frame,
        )
        return Save(
            save_id="save_test",
            pack_name="test_pack",
            world=world,
            relationships=RelationshipState(),
            open_loops=OpenLoops(),
        )

    def test_no_warning_when_within_budget(self):
        from tools.lint_save import _lint_conflict_frame
        save = self._make_save_with_frame(opened_turn=5, current_turn=8, budget=4)  # age=3, remaining=1
        self.assertEqual(_lint_conflict_frame(save), [])

    def test_no_warning_at_budget_exhausted(self):
        from tools.lint_save import _lint_conflict_frame
        save = self._make_save_with_frame(opened_turn=5, current_turn=9, budget=4)  # age=4, remaining=0
        self.assertEqual(_lint_conflict_frame(save), [])

    def test_no_warning_at_one_turn_overshoot(self):
        from tools.lint_save import _lint_conflict_frame
        save = self._make_save_with_frame(opened_turn=5, current_turn=10, budget=4)  # age=5, remaining=-1
        self.assertEqual(_lint_conflict_frame(save), [])

    def test_warning_at_two_turn_overshoot(self):
        from tools.lint_save import _lint_conflict_frame
        save = self._make_save_with_frame(opened_turn=5, current_turn=11, budget=4)  # age=6, remaining=-2
        issues = _lint_conflict_frame(save)
        self.assertEqual(len(issues), 1)
        self.assertIn("overshoot", issues[0].lower())
```

Verified against `tools/_models.py`: `Save` (fields: `save_id`, `pack_name`, `world`, `relationships`, `open_loops`, `session_log`, `divergences`, `hidden_truths`), `OpenLoops`, `RelationshipState`, `PlayerState`, `WorldState`. There is no `Meta` class — `save_id` and `pack_name` are direct fields on `Save`.

- [ ] **Step 2: Run lint tests to verify they fail**

```bash
.venv/bin/python -m unittest tests.test_conflict_budget.TestLintConflictFrame -v
```

Expected: the "warning at 2-turn overshoot" test fails because current rule warns at age > 10, not at overshoot. The "no warning at X" tests may pass incidentally.

- [ ] **Step 3: Replace the lint rule**

In `tools/lint_save.py`, replace lines 212–227 with:

```python
def _lint_conflict_frame(save) -> list[str]:
    conflict = save.world.current_conflict
    if conflict is None:
        return []
    issues: list[str] = []
    remaining = conflict.beats_remaining(save.world.turn)
    if remaining <= -2:
        overshoot = -remaining
        issues.append(
            f"current_conflict {conflict.id!r} has overshot beat_budget "
            f"by {overshoot} turns (budget {conflict.beat_budget}, "
            f"opened turn {conflict.opened_turn}, now {save.world.turn}); "
            f"resolve or revise the frame"
        )
    return issues
```

Also remove the now-unused `STALE_CONFLICT_THRESHOLD = 10` constant at line 212 (above the function).

- [ ] **Step 4: Run lint tests to verify they pass**

```bash
.venv/bin/python -m unittest tests.test_conflict_budget.TestLintConflictFrame -v
```

Expected: all 4 lint tests pass.

- [ ] **Step 5: Run full test module to make sure nothing regressed**

```bash
.venv/bin/python -m unittest tests.test_conflict_budget -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add tools/lint_save.py tests/test_conflict_budget.py
git commit -m "$(cat <<'EOF'
feat(lint): warn when conflict overshoots beat_budget by 2+ turns

Replaces the old fixed STALE_CONFLICT_THRESHOLD=10 with a
budget-aware rule: warn only when beats_remaining <= -2 (i.e. the
GM has already used the 1-turn overshoot grace and still hasn't
resolved). The wording surfaces the overshoot count so the
operator sees how overdue the frame is.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Update `render_save.py` to show endgame in current_scene.md

**Files:**
- Modify: `tools/render_save.py:58-130` (the module-level `LABELS` dict, zh and en entries) — add `conflict_momentum_endgame` key to both
- Modify: `tools/render_save.py:246-277` (caller + `_render_conflict_block`) — pass `current_turn`, override momentum display when endgame
- Modify: `tests/test_conflict_budget.py` — add render tests

The repo already has `_labels_for(language)` at line 133 and a module-level `LABELS` dict at lines 58–130; no refactor needed, just add one key per language and extend the function signature.

- [ ] **Step 1: Write failing render tests**

Append to `tests/test_conflict_budget.py` (before the `if __name__` block):

```python
class TestRenderConflictEndgame(unittest.TestCase):
    """render_save should show 收束在即 / Endgame in the momentum field when beats_remaining <= 1."""

    def _render(self, conflict, current_turn: int, lang: str):
        from tools.render_save import _render_conflict_block, _labels_for
        L = _labels_for(lang)
        return "\n".join(_render_conflict_block(conflict, L, current_turn))

    def test_zh_normal_momentum_when_not_endgame(self):
        frame = _make_frame(opened_turn=0, beat_budget=4, momentum="even")
        out = self._render(frame, current_turn=2, lang="zh")  # remaining=2
        self.assertIn("势头", out)
        self.assertIn("even", out)
        self.assertNotIn("收束在即", out)

    def test_zh_endgame_overrides_at_remaining_1(self):
        frame = _make_frame(opened_turn=0, beat_budget=4, momentum="even")
        out = self._render(frame, current_turn=3, lang="zh")  # remaining=1
        self.assertIn("收束在即", out)
        self.assertNotIn("- **势头**: even", out)

    def test_zh_endgame_at_remaining_0(self):
        frame = _make_frame(opened_turn=0, beat_budget=4, momentum="reversal_imminent")
        out = self._render(frame, current_turn=4, lang="zh")  # remaining=0
        self.assertIn("收束在即", out)

    def test_en_endgame_label(self):
        frame = _make_frame(opened_turn=0, beat_budget=4, momentum="even")
        out = self._render(frame, current_turn=3, lang="en")  # remaining=1
        self.assertIn("Endgame", out)
        self.assertNotIn("Momentum**: even", out)
```

- [ ] **Step 2: Run render tests to verify they fail**

```bash
.venv/bin/python -m unittest tests.test_conflict_budget.TestRenderConflictEndgame -v
```

Expected: tests fail — either with a `TypeError` because `_render_conflict_block` takes 2 args, not 3, OR the endgame tests fail because the override isn't in place.

- [ ] **Step 3: Add the endgame label to both language dicts**

In `tools/render_save.py`, inside the `LABELS` dict:

Under the `"zh"` sub-dict (currently ending at line 93 with `"last_conflict_resolved_at": "结束于回合",`), add:

```python
        "conflict_momentum_endgame": "收束在即",
```

Under the `"en"` sub-dict (currently ending at line 128 with `"last_conflict_resolved_at": "Resolved on turn",`), add:

```python
        "conflict_momentum_endgame": "Endgame",
```

- [ ] **Step 4: Modify `_render_conflict_block` to honor endgame**

In `tools/render_save.py` at line 258, change the function signature and the momentum line:

```python
def _render_conflict_block(conflict, L: dict[str, str], current_turn: int) -> list[str]:
    lines: list[str] = ["", f"## {L['current_conflict']}", ""]
    lines.append(f"- **{L['conflict_stake']}**: {conflict.stake}")
    lines.append(f"- **{L['conflict_kind']}**: {conflict.kind}")
    if conflict.is_endgame(current_turn):
        momentum_display = L["conflict_momentum_endgame"]
    else:
        momentum_display = conflict.momentum
    lines.append(f"- **{L['conflict_momentum']}**: {momentum_display}")
    lines.append(f"- **{L['conflict_sides']}**:")
    for side in conflict.sides:
        paid = "、".join(side.paid) if side.paid else "—"
        members = "、".join(side.members) if side.members else "—"
        lines.append(
            f"  - `{side.label}` · {L['conflict_side_want']}: {side.want} · "
            f"{L['conflict_side_paid']}: {paid}"
        )
        lines.append(f"    {L['conflict_side_members']}: {members}")
    if conflict.escalation_notes:
        lines.append(f"- **{L['conflict_escalation']}**:")
        for note in conflict.escalation_notes:
            lines.append(f"  - {note}")
    return lines
```

(The `"、"` / `"—"` literals in the paid/members join were present in the original code; preserve them exactly. If the original uses different separators in the en path, match whatever was there — this task is not reformatting.)

- [ ] **Step 5: Update the caller to pass `current_turn`**

At line 246–247 of `tools/render_save.py`:

```python
    if w.current_conflict is not None:
        lines += _render_conflict_block(w.current_conflict, L)
```

Change the second line to:

```python
        lines += _render_conflict_block(w.current_conflict, L, w.turn)
```

- [ ] **Step 6: Run render tests to verify they pass**

```bash
.venv/bin/python -m unittest tests.test_conflict_budget.TestRenderConflictEndgame -v
```

Expected: all 4 render tests pass.

- [ ] **Step 7: Run full test module to verify no regression**

```bash
.venv/bin/python -m unittest tests.test_conflict_budget -v
```

Expected: all tests pass.

- [ ] **Step 8: Smoke test on an existing save (if one exists)**

```bash
ls saves/ 2>/dev/null && .venv/bin/python tools/render_save.py --save $(ls saves | head -1)/$(ls saves/$(ls saves | head -1) | head -1) 2>&1 | tail -20
```

Expected: no crash, `current_scene.md` still renders. If no saves exist, skip.

- [ ] **Step 9: Commit**

```bash
git add tools/render_save.py tests/test_conflict_budget.py
git commit -m "$(cat <<'EOF'
feat(render): show 收束在即 / Endgame when conflict enters last beat

current_scene.md's conflict block now swaps the momentum label for
'收束在即' (zh) / 'Endgame' (en) when ConflictFrame.beats_remaining
drops to 1 or below. Keeps the player aware they're in the closing
beat without exposing a raw countdown.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Update `gm_system_fragment.md` — beat-budget, beat-density, options, HUD

**Files:**
- Modify: `genre_packs/universal/prompts/gm_system_fragment.md`

Four prompt edits in one commit (they're tightly coupled).

- [ ] **Step 1: Read the current file to locate edit anchors**

```bash
grep -n "^### Beat density\|^### Conflict frame\|^### Conflict HUD line\|Coupling to the A/B/C options" genre_packs/universal/prompts/gm_system_fragment.md
```

- [ ] **Step 2: Rewrite the "Beat density" subsection**

Find the block starting `### Beat density (load-bearing)` and replace its body with:

```markdown
### Beat density (load-bearing)

One turn = one player decision, **not** one sentence or one frozen
tableau. Inside that turn, play the beat through **two pivots**
before handing back to the player:

1. The player's action lands in the world — show what it actually
   does, including the immediate counter or response.
2. **First pivot**: an in-scene NPC reaction that materially changes
   the situation (a wound, a disarm, a reveal, a bystander stepping
   in). Every NPC who plausibly reacts still gets a distinct
   reaction; silent NPCs are fine when silence is in-character.
3. **Second pivot**: a complication on top of the first — momentum
   shifts, a new arrival, a cost crystallizes, a closed door, a
   fresh question. The A/B/C options are a choice on the state
   **after both pivots**, not after the first.

Previously this rule called for a single pivot per turn; combat
turns drifted into micro-exchanges (抢腕 → 藏针 → 拂尘 → 毒掌, one
per turn). One turn should now compress what used to be two
turns' beats. A turn that stops at "you open the door, here is
what you see" is still a failure unless the player's input was
itself observational (waiting, looking, listening). Density comes
from showing the beat resolve twice, not from padding word count.
Do **not** compress multiple player *decisions* into one turn —
escalate *within* the current beat.
```

- [ ] **Step 3: Add the "Beat budget" subsection after "Conflict frame (load-bearing)"**

Locate the end of the `### Conflict frame (load-bearing)` section (the paragraph ending with "A resolve that clears the frame without writing the summary and without any world-state writeback is a bug — the conflict did not change the world, so it should not have been opened.").

Immediately after that paragraph (before the next `###` header), insert:

```markdown
### Beat budget (load-bearing)

Every active `ConflictFrame` carries `beat_budget` (integer 3–6, set
at `conflict_open`). The engine derives remaining beats as
`beat_budget - (world.turn - opened_turn)` on every read; you do
not patch it yourself after open.

Pick the budget at open time based on scope:

| Conflict kind (examples)                             | `beat_budget` |
| ---------------------------------------------------- | ------------- |
| Brawl, short chase, assassination attempt            | 3             |
| General combat, ambush, flight (default)             | 4             |
| Debate, negotiation, interrogation, alchemy crisis   | 5             |
| Siege, large courtroom, multi-party standoff         | 6             |

Larger than 6 means the scene is really two conflicts back-to-back;
resolve the first, then `conflict_open` the second.

**Countdown behavior** (check remaining each turn before writing
narration):

- `remaining >= 2` — standard pacing. A/B/C span the usual tactic
  vectors; each turn still emits a `paid_add` on the side that
  absorbed a cost.
- `remaining == 1` — last beat imminent. At least one of A/B/C
  MUST be a **decisive** move that would resolve the frame if it
  lands ("一击定音"). Generic "press the advantage" is not enough;
  name the specific decisive action. The HUD momentum column
  displays `收束在即 / Endgame` regardless of the underlying
  `momentum` value.
- `remaining == 0` — this turn SHOULD emit `conflict_resolve`.
  Acceptable outcomes: player wins, opposition wins, even +
  `world_change`, player disengages. Disengagement still counts as
  resolve — do not leave the frame open because the scene feels
  unfinished.
- `remaining == -1` — one-turn overshoot allowed only when a
  just-landed reveal genuinely needs one more beat to play out;
  resolve on that turn.
- `remaining <= -2` — lint warns; you should have resolved.
```

- [ ] **Step 4: Add the options constraint addendum**

Inside the existing `### Conflict frame (load-bearing)` section, find the paragraph starting "Coupling to the A/B/C options (load-bearing): while a frame is active, **at least one** of A/B/C must be a concrete move that pushes momentum...". Append this sentence at the end of that paragraph:

```markdown
Additionally, when `beat_budget - (turn - opened_turn) <= 1`, one of A/B/C MUST be a 收束型 (decisive) move that could end the frame this turn if it lands — not merely a momentum push.
```

- [ ] **Step 5: Update the Conflict HUD line section**

Find the `### Conflict HUD line` section. After the existing "Momentum label table" (the table ending with `| reversal_imminent | 逆转在即 | Reversal imminent |`), add:

```markdown

**Endgame override:** When `current_conflict.beats_remaining(world.turn) <= 1`, the momentum column in the HUD displays `收束在即` (zh) / `Endgame` (en) regardless of the underlying `momentum` value. This is the only time the HUD's momentum field deviates from the table above; it signals that the frame is on its last beat and one of A/B/C must be a decisive move.
```

- [ ] **Step 6: Verify all four edits landed**

```bash
grep -n "Beat budget (load-bearing)\|two pivots\|Endgame override\|收束型" genre_packs/universal/prompts/gm_system_fragment.md
```

Expected: four matches, one per edit.

- [ ] **Step 7: Commit**

```bash
git add genre_packs/universal/prompts/gm_system_fragment.md
git commit -m "$(cat <<'EOF'
feat(prompt): beat budget + two-pivot density + endgame HUD

gm_system_fragment.md changes:
- New "Beat budget" subsection: 3-6 range per conflict scope,
  decisive-option requirement at remaining==1, resolve expected
  at remaining==0, 1-turn overshoot grace, lint at <=-2.
- "Beat density" rewritten from one pivot per turn to two;
  explicit that this compresses what used to be two turns into
  one.
- Options constraint addendum: when remaining<=1, one of A/B/C
  must be a 收束型 (decisive) move.
- Conflict HUD line: momentum column shows 收束在即 / Endgame
  when remaining<=1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Add time-compression section to `style_guide.md`

**Files:**
- Modify: `genre_packs/universal/style_guide.md`

- [ ] **Step 1: Add a new section after "Paragraph rhythm"**

After the `## Paragraph rhythm` section (ends with "no 'with this, the journey begins'."), insert a new `## Time compression` section before `## Sensory grounding`:

```markdown
## Time compression

When the player's input is routine — travel, rest, shopping, waiting
for a scheduled event, training montage, long study, an uneventful
journey — one turn MAY fast-forward hours or days to the next point
of tension, rather than narrating every intervening step.

Signals that a turn should compress time:

- The player wrote a **goal** ("I ride to 嘉兴", "I sleep at the inn
  and leave at dawn"), not a **step** ("I tighten the saddle", "I
  ask the innkeeper about rates").
- Nothing in `world_state.present_entities`, `active_threads`, or
  `novel_rules.md` would make the routine itself fraught — no one
  is actively watching, the route is safe, the inn is not a trap.
- `world_state.current_conflict` is null. **Inside an active
  conflict frame, never compress time** — every turn is one beat
  inside the frame.

When compressing, land the turn at the next in-world beat that
requires a player decision: arrival at the destination, the first
new encounter, a changed circumstance. Do not end a compression turn
on a non-decision tableau — the A/B/C options must still be a real
choice.
```

- [ ] **Step 2: Verify the insertion**

```bash
grep -n "^## " genre_packs/universal/style_guide.md
```

Expected order includes: `## Point of view and tense`, `## Paragraph rhythm`, `## Time compression`, `## Sensory grounding`, `## Language and register`, `## Options and hints`, `## What the GM does NOT produce`.

- [ ] **Step 3: Commit**

```bash
git add genre_packs/universal/style_guide.md
git commit -m "$(cat <<'EOF'
feat(prompt): allow time compression on routine-action turns

style_guide.md grows a "Time compression" section: when the player
writes a goal (not a step), nothing makes the routine fraught, and
no conflict frame is active, the GM may fast-forward hours or days
to the next point of tension. Explicitly forbidden inside an active
conflict frame.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Update `playbooks/play-turn.md` with beat_budget lifecycle

**Files:**
- Modify: `playbooks/play-turn.md`

- [ ] **Step 1: Locate the conflict lifecycle section**

```bash
grep -n "^### Conflict frame lifecycle\|conflict_open\|conflict_update\|conflict_resolve" playbooks/play-turn.md | head
```

- [ ] **Step 2: Add a beat_budget paragraph to the lifecycle section**

Inside the `### Conflict frame lifecycle` section (in Step 2), find the bullet for **Open (`conflict_open`)**. Append to that bullet's body (after "`momentum` on opening is almost always `setup`."):

```markdown
  Additionally set `beat_budget` on open based on the conflict's
  scope (3–6, default 4). See *Beat budget* in
  `genre_packs/universal/prompts/gm_system_fragment.md` for the
  per-kind guidance table.
```

Then find the **Update (`conflict_update`)** bullet and append:

```markdown
  Do NOT patch `beat_budget` here — it is set once at open and
  thereafter derived (`beat_budget - (turn - opened_turn)`).
  Patches that include `beat_budget` inside `conflict_update` drop
  that field and log a divergence.
```

Finally, replace the paragraph at the very end of the lifecycle section (currently: "If the frame sits open for more than ~10 turns, `tools/lint_save.py` will warn. That is a cue to resolve or narrow the frame, not a hard error.") with:

```markdown
When `remaining == 1` (i.e. `turn - opened_turn == beat_budget - 1`),
one A/B/C option must be a decisive (收束型) move and the HUD shows
`收束在即 / Endgame`. When `remaining == 0`, the turn SHOULD resolve
the frame. One-turn overshoot is allowed when a reveal needs to
play out. `tools/lint_save.py` warns when `remaining <= -2`.
```

- [ ] **Step 3: Verify the edits**

```bash
grep -n "beat_budget\|收束在即\|decisive" playbooks/play-turn.md
```

Expected: at least three matches.

- [ ] **Step 4: Commit**

```bash
git add playbooks/play-turn.md
git commit -m "$(cat <<'EOF'
docs(playbook): wire beat_budget into the conflict-frame lifecycle

play-turn.md's conflict-frame lifecycle section now explains:
- conflict_open must set beat_budget (3-6, default 4)
- conflict_update must NOT patch beat_budget (derived, not stored)
- remaining==1 -> decisive option + endgame HUD
- remaining==0 -> resolve expected
- remaining<=-2 -> lint warns
Replaces the old "10 turns" lint reference.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Refine the spec to match the derived-budget implementation

**Files:**
- Modify: `docs/superpowers/specs/2026-04-20-faster-pacing-design.md`

The spec described auto-decrement on `conflict_update`; the implementation derives remaining beats on the fly. Update the spec so it reflects what actually shipped.

- [ ] **Step 1: Edit the "Countdown behavior" and "`conflict_update` auto-decrement logic" sections**

In `docs/superpowers/specs/2026-04-20-faster-pacing-design.md`:

Replace the bullet under *Semantics* that reads:

> - Decremented by 1 **automatically** each time a `conflict_update` patch
>   is accepted. The GM does NOT patch `beat_budget` directly inside
>   `conflict_update`; if they do, drop the field and log a divergence.

with:

> - Remaining beats are **derived** on every read:
>   `remaining = beat_budget - (world.turn - opened_turn)`.
>   No auto-decrement engine; no stored counter. The field is set
>   once at `conflict_open` and never patched thereafter. If the GM
>   supplies `beat_budget` inside `conflict_update`, the field is
>   dropped and a divergence is logged.

Replace the `### 4.2 · conflict_update auto-decrement logic` subsection (in the Schema/lint/render section) with:

> ### 4.2 · `conflict_update` handling
>
> `conflict_update` does NOT mutate `beat_budget`. The field is set
> once at `conflict_open` and the lifecycle is purely age-based
> (`world.turn - opened_turn`). If a patch includes `beat_budget`
> inside `conflict_update`, drop that field and log a divergence.

Leave every other section of the spec intact — the user-facing behavior is unchanged.

- [ ] **Step 2: Verify the spec still reads coherently**

```bash
grep -n "auto-decrement\|Decremented\|derived\|beats_remaining" docs/superpowers/specs/2026-04-20-faster-pacing-design.md
```

Expected: no "auto-decrement" / "Decremented" matches left in the spec; "derived" / "beats_remaining" referenced.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-20-faster-pacing-design.md
git commit -m "$(cat <<'EOF'
docs(spec): refine beat_budget design to derived-remaining model

The implementation computes remaining beats on the fly from
beat_budget and opened_turn rather than decrementing a stored
counter on each conflict_update. Observable behavior is identical;
the design note is updated so the spec and the shipped code agree.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: End-to-end sanity run

**Files:** none modified.

- [ ] **Step 1: Run the full test suite**

```bash
.venv/bin/python -m unittest tests.test_conflict_budget -v
```

Expected: every test passes.

- [ ] **Step 2: Run lint_pack on the universal pack**

```bash
.venv/bin/python tools/lint_pack.py --genre universal
```

Expected: no new lint issues from the prompt-file edits.

- [ ] **Step 3: Run lint_save + render_save on any existing save**

```bash
EXISTING_SAVE=$(find saves -maxdepth 2 -type d | grep -E "saves/[^/]+/save_" | head -1 | sed 's|^saves/||')
if [ -n "$EXISTING_SAVE" ]; then
  .venv/bin/python tools/render_save.py --save "$EXISTING_SAVE"
  .venv/bin/python tools/lint_save.py --save "$EXISTING_SAVE"
else
  echo "no existing save to smoke-test; skipping"
fi
```

Expected: render runs cleanly. Lint either prints "ok" or — if the save has a legacy in-flight frame that was older than 10 turns — the new overshoot message.

- [ ] **Step 4: Verify git log**

```bash
git log --oneline -20
```

Expected: seven new commits on top of `c1ea40d` (the spec commit), in this order:

```
<hash> docs(spec): refine beat_budget design to derived-remaining model
<hash> docs(playbook): wire beat_budget into the conflict-frame lifecycle
<hash> feat(prompt): allow time compression on routine-action turns
<hash> feat(prompt): beat budget + two-pivot density + endgame HUD
<hash> feat(render): show 收束在即 / Endgame when conflict enters last beat
<hash> feat(lint): warn when conflict overshoots beat_budget by 2+ turns
<hash> feat(models): add ConflictFrame.beat_budget + beats_remaining helper
c1ea40d docs: spec for faster pacing — conflict beat budget + denser turns + time compression
```

- [ ] **Step 5: Report back to the user**

Summarize:
- 3 code files modified (`_models.py`, `lint_save.py`, `render_save.py`)
- 3 prompt files modified (`gm_system_fragment.md`, `style_guide.md`, `play-turn.md`)
- 1 test file added (`tests/test_conflict_budget.py`)
- 1 spec file refined
- Target pacing: conflicts resolve in 3–5 turns; non-conflict turns denser (two pivots); routine actions may compress time.
