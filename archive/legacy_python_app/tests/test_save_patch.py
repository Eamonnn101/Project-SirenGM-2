"""Tests for save layer: models, store, patch apply, render, roundtrip."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from sirengm.pack.stacked import load_stacked
from sirengm.save import render as render_save
from sirengm.save.models import (
    ActiveThread,
    OpenLoop,
    PlayerState,
    Relationship,
    SessionLogEntry,
)
from sirengm.save.patch import (
    ActiveThreadChange,
    PlayerStatePatch,
    RelationshipDelta,
    StatePatch,
    WorldStatePatch,
    apply_patch,
)
from sirengm.save.store import load_save, new_save, persist

REPO_ROOT = Path(__file__).parent.parent
GENRE_ROOT = REPO_ROOT / "genre_packs"
MINI = Path(__file__).parent / "fixtures" / "mini_user_pack"


@pytest.fixture
def stacked():
    return load_stacked(MINI, genre_packs_root=GENRE_ROOT)


@pytest.fixture
def fresh_save(tmp_path, stacked):
    saves = tmp_path / "saves"
    save = new_save(
        saves,
        save_id="save_t",
        pack_name=stacked.name,
        player=PlayerState(
            slug="protagonist",
            name="青衡",
            sect="jade_frost_sect",
            cultivation_stage="气感期三层",
        ),
        starting_location="outer_gate",
        starting_entities=["protagonist"],
        starting_objective="熟悉外门",
    )
    render_save.render_all(saves, save)
    return saves, save


def test_fresh_save_has_required_structured_fields(fresh_save):
    _, save = fresh_save
    w = save.world
    # The five fields required by project memory.
    assert w.current_location == "outer_gate"
    assert w.present_entities == ["protagonist"]
    assert w.active_threads == []
    assert w.current_objectives == ["熟悉外门"]
    assert w.risk_level == "calm"
    # Player mirror.
    assert w.player.slug == "protagonist"
    assert w.player.cultivation_stage == "气感期三层"


def test_save_roundtrips_through_disk(fresh_save):
    saves_root, save = fresh_save
    persist(saves_root, save)
    reloaded = load_save(saves_root, save.save_id)
    assert reloaded.save_id == save.save_id
    assert reloaded.world.current_location == save.world.current_location
    assert reloaded.world.player.name == save.world.player.name
    assert reloaded.world.turn == 0


def test_apply_valid_patch_updates_state(fresh_save, stacked):
    saves_root, save = fresh_save
    patch = StatePatch(
        world=WorldStatePatch(
            current_location="spirit_mountain",
            present_entities=["protagonist", "master"],
            current_objectives=["与元隐擦肩", "记住他说过的话"],
            risk_level="tense",
            time_of_day="dusk",
            flags_set={"first_night_done": True},
        ),
        player=PlayerStatePatch(cultivation_stage="气感期四层"),
        relationships={
            "master": RelationshipDelta(affinity_delta=1, status="acquainted", notes="元隐停了三息"),
        },
        open_loops_add=[
            OpenLoop(id="find_mother", title="查母亲下落", opened_turn=0),
        ],
        active_thread_changes=[
            ActiveThreadChange(op="add", thread=ActiveThread(id="opening_arc", title="入门", priority="active")),
        ],
        session_log_entry=SessionLogEntry(turn=0, player_input="上山", narration="山风很冷。"),
        hidden_truths_append="- 元隐注意到你眉末的疤。",
    )
    divergences = apply_patch(save, patch, stacked)
    assert divergences == []
    assert save.world.current_location == "spirit_mountain"
    assert save.world.present_entities == ["protagonist", "master"]
    assert save.world.risk_level == "tense"
    assert save.world.time_of_day == "dusk"
    assert save.world.flags == {"first_night_done": True}
    assert save.world.player.cultivation_stage == "气感期四层"
    assert save.relationships.by_slug["master"].affinity == 1
    assert save.relationships.by_slug["master"].status == "acquainted"
    assert save.relationships.by_slug["master"].last_interaction_turn == 0
    assert [l.id for l in save.open_loops.items] == ["find_mother"]
    assert [t.id for t in save.world.active_threads] == ["opening_arc"]
    # Turn advanced once.
    assert save.world.turn == 1
    assert "元隐注意到" in save.hidden_truths


def test_unknown_slug_logs_divergence_and_skips(fresh_save, stacked):
    saves_root, save = fresh_save
    patch = StatePatch(
        world=WorldStatePatch(
            current_location="ghost_palace",  # not in pack, not emergent
            present_entities=["protagonist", "nobody"],  # nobody invalid
        ),
        relationships={"stranger": RelationshipDelta(affinity_delta=5)},  # stranger invalid
        session_log_entry=SessionLogEntry(turn=0, player_input="?", narration="..."),
    )
    divergences = apply_patch(save, patch, stacked)
    # current_location unchanged; present_entities sanitized; relationship not added.
    assert save.world.current_location == "outer_gate"
    assert save.world.present_entities == ["protagonist"]
    assert "stranger" not in save.relationships.by_slug
    reasons = {d.reason for d in divergences}
    assert "current_location references unknown slug" in reasons
    assert "present_entities contains unknown slug" in reasons
    assert "relationship update on unknown slug" in reasons
    # Session log still recorded; turn still advanced.
    assert len(save.session_log) == 1
    assert save.world.turn == 1


def test_close_loop_and_duplicate_handling(fresh_save, stacked):
    saves_root, save = fresh_save
    # Open a loop first.
    open_patch = StatePatch(
        world=WorldStatePatch(advance_turn=False),
        open_loops_add=[OpenLoop(id="trial_signup", title="报名试炼", opened_turn=0)],
        session_log_entry=SessionLogEntry(turn=0, player_input="报名", narration="..."),
    )
    apply_patch(save, open_patch, stacked)
    assert save.open_loops.items[0].status == "open"

    # Duplicate add + legitimate close.
    close_patch = StatePatch(
        open_loops_add=[OpenLoop(id="trial_signup", title="重复", opened_turn=0)],
        open_loops_close=["trial_signup", "nonexistent"],
        session_log_entry=SessionLogEntry(turn=0, player_input="x", narration="y"),
    )
    divergences = apply_patch(save, close_patch, stacked)
    reasons = {d.reason for d in divergences}
    assert "duplicate open_loop id" in reasons
    assert "close on unknown open_loop id" in reasons
    assert save.open_loops.items[0].status == "closed"
    # Closure is recorded at the current turn (0), THEN the turn advances to 1.
    assert save.open_loops.items[0].closed_turn == 0


def test_emergent_prefix_bypasses_slug_check(fresh_save, stacked):
    saves_root, save = fresh_save
    patch = StatePatch(
        world=WorldStatePatch(present_entities=["protagonist", "emergent:wandering_monk"]),
        relationships={"emergent:wandering_monk": RelationshipDelta(affinity_delta=1)},
        session_log_entry=SessionLogEntry(turn=0, player_input="搭话", narration="陌生僧人停下脚步。"),
    )
    divergences = apply_patch(save, patch, stacked)
    assert divergences == []
    assert "emergent:wandering_monk" in save.world.present_entities
    assert save.relationships.by_slug["emergent:wandering_monk"].affinity == 1


def test_render_produces_markdown_surfaces(fresh_save, stacked):
    saves_root, save = fresh_save
    patch = StatePatch(
        world=WorldStatePatch(advance_turn=False),
        session_log_entry=SessionLogEntry(
            turn=0,
            player_input="起床。",
            narration="天还没亮。",
            summary="玩家醒来。",
        ),
    )
    apply_patch(save, patch, stacked)
    render_save.render_all(saves_root, save)

    d = saves_root / save.save_id
    cs = (d / "current_scene.md").read_text(encoding="utf-8")
    pm = (d / "player.md").read_text(encoding="utf-8")
    sl_md = (d / "session_log.md").read_text(encoding="utf-8")
    sl_jsonl = (d / "session_log.jsonl").read_text(encoding="utf-8")

    assert "outer_gate" in cs
    assert "protagonist" in cs
    assert "青衡" in pm
    assert "气感期三层" in pm
    assert "起床" in sl_md
    assert sl_jsonl.strip().startswith("{")


def test_state_updater_schema_rejects_missing_session_log():
    with pytest.raises(ValidationError):
        StatePatch.model_validate({})


def test_save_reload_includes_session_log_and_divergences(fresh_save, stacked):
    saves_root, save = fresh_save
    patch = StatePatch(
        world=WorldStatePatch(current_location="nowhere_town"),  # unknown -> divergence
        session_log_entry=SessionLogEntry(turn=0, player_input="??", narration="雾。"),
    )
    apply_patch(save, patch, stacked)
    persist(saves_root, save)
    render_save.render_all(saves_root, save)
    # Also append a divergence to disk.
    from sirengm.save.store import append_divergence

    append_divergence(saves_root, save.save_id, save.divergences[0])

    reloaded = load_save(saves_root, save.save_id)
    assert len(reloaded.session_log) == 1
    assert reloaded.world.turn == 1
