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


if __name__ == "__main__":
    unittest.main()
