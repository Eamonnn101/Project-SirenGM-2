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
