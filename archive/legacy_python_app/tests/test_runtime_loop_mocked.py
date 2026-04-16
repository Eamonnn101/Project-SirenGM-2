"""End-to-end runtime loop test using MockProvider.

Copies the mini_user_pack fixture into a tmp `packs/` directory, symlinks
the repo's `genre_packs/`, creates a save via the wizard, and runs 5 turns
with scripted LLM responses. Asserts structured state evolves coherently
and markdown surfaces are re-rendered.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterator

import pytest

from sirengm.config import AppConfig
from sirengm.llm.mock_client import MockProvider
from sirengm.runtime.loop import run_play_loop
from sirengm.runtime.new_game import build_initial_save
from sirengm.save.store import load_save

REPO_ROOT = Path(__file__).parent.parent
FIXTURE_PACK = Path(__file__).parent / "fixtures" / "mini_user_pack"
GENRE_ROOT = REPO_ROOT / "genre_packs"


@pytest.fixture
def tmp_cfg(tmp_path: Path) -> AppConfig:
    (tmp_path / "packs").mkdir()
    (tmp_path / "saves").mkdir()
    (tmp_path / "raw" / "novel").mkdir(parents=True)
    # Copy the user fixture pack into tmp packs/.
    shutil.copytree(FIXTURE_PACK, tmp_path / "packs" / "mini")
    # Link genre_packs/ so the StackedPack loader finds it.
    (tmp_path / "genre_packs").symlink_to(GENRE_ROOT, target_is_directory=True)
    return AppConfig(
        root=tmp_path,
        provider="mock",
        anthropic_api_key=None,
        anthropic_model="claude-sonnet-4-6",
    )


def _state_patch_json(turn: int, player_input: str, narration: str, location: str = "outer_gate") -> str:
    return json.dumps({
        "world": {
            "advance_turn": True,
            "current_location": location,
            "present_entities": ["protagonist", "master"] if turn >= 2 else ["protagonist"],
            "risk_level": "tense" if turn >= 3 else "calm",
        },
        "relationships": {
            "master": {"affinity_delta": 1, "status": "acquainted"}
        } if turn >= 2 else {},
        "session_log_entry": {
            "turn": turn,
            "player_input": player_input,
            "narration": narration,
            "summary": f"turn {turn} 推进。",
        },
    })


def test_five_turn_mocked_run_evolves_state(tmp_cfg: AppConfig) -> None:
    build_initial_save(tmp_cfg, pack_name="mini", save_id="save_t")

    mock = MockProvider()
    call_count = {"narrator": 0, "state_updater": 0}
    inputs = iter(["打扫院子", "走到演武场", "看到元隐", "向元隐行礼", "继续练习"])

    def narrator_resp(_messages):
        call_count["narrator"] += 1
        return f"GM 叙事（第 {call_count['narrator']} 回合）：山风掠过，霜气未散。"

    def updater_resp(_messages):
        call_count["state_updater"] += 1
        # The current save.world.turn at the moment updater is called.
        # The mock doesn't know it, but we stored player input in narrator_resp sequence.
        # Use call_count to index since narrator is called first each turn.
        turn = call_count["state_updater"] - 1
        # Find last player input from messages — simplest: encode it into narration.
        # For the test, simply produce a patch that references the current loop iteration.
        return _state_patch_json(
            turn=turn,
            player_input=f"(input turn {turn})",
            narration=f"(narration turn {turn})",
        )

    mock.set("narrator", narrator_resp)
    mock.set("state_updater", updater_resp)

    def input_fn(_prompt: str) -> str | None:
        try:
            return next(inputs)
        except StopIteration:
            return None

    save = run_play_loop(tmp_cfg, save_id="save_t", llm=mock, input_fn=input_fn, max_turns=5)

    assert save.world.turn == 5, f"expected 5 advances, got {save.world.turn}"
    assert len(save.session_log) == 5
    # Relationship with master updated from turn 2 onwards (3 of 5 turns).
    assert save.relationships.by_slug["master"].affinity == 3
    # Risk level escalated by turn 3.
    assert save.world.risk_level == "tense"

    # Reload from disk: state persists across the process boundary.
    reloaded = load_save(tmp_cfg.saves_dir, "save_t")
    assert reloaded.world.turn == 5
    assert len(reloaded.session_log) == 5
    assert reloaded.relationships.by_slug["master"].affinity == 3

    # Markdown surfaces were re-rendered.
    scene = (tmp_cfg.saves_dir / "save_t" / "current_scene.md").read_text(encoding="utf-8")
    assert "turn: 5" in scene
    assert "outer_gate" in scene


def test_state_updater_failure_is_soft(tmp_cfg: AppConfig) -> None:
    build_initial_save(tmp_cfg, pack_name="mini", save_id="save_bad")

    mock = MockProvider()
    mock.set("narrator", lambda _m: "山风。")
    # Return garbage that fails Pydantic validation.
    mock.set("state_updater", lambda _m: json.dumps({"world": {}, "not_a_field": 1}))

    inputs = iter(["试试"])

    def input_fn(_p: str):
        try:
            return next(inputs)
        except StopIteration:
            return None

    save = run_play_loop(tmp_cfg, save_id="save_bad", llm=mock, input_fn=input_fn, max_turns=1)

    # Turn still advanced; state not corrupted; divergence recorded.
    assert save.world.turn == 1
    assert len(save.session_log) == 1
    assert any("state_updater call failed" in d.reason for d in save.divergences)
    divergence_md = (tmp_cfg.saves_dir / "save_bad" / "divergence_log.md").read_text(encoding="utf-8")
    assert "state_updater call failed" in divergence_md
