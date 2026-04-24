"""Tests for the v0.5 progression layer: artifacts, innate/destiny traits,
stage index, health ladder, death flow, and per-pack meta progression."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from tools._models import (
    DeathRecord,
    PackMetaProgress,
    PlayerArtifact,
    PlayerState,
    STAGE_INDEX_MAX,
    Trait,
    UNIVERSAL_ARTIFACT_ARCHETYPES,
    UNIVERSAL_DESTINY_ARCHETYPES,
    UNIVERSAL_INNATE_ARCHETYPES,
)
from tools._progression import (
    DRAFT_BIAS_COVERAGE_THRESHOLD,
    artifact_draw_order,
    destiny_draw_order,
    draft_bias_order,
    innate_draw_order,
    merge_run_into_meta,
    resolve_survival_trigger,
)


def _player(**overrides) -> PlayerState:
    base = dict(slug="hero", name="Hero")
    base.update(overrides)
    return PlayerState(**base)


def _innate(archetype: str, slug: str | None = None) -> Trait:
    return Trait(
        slug=slug or f"innate_{archetype}",
        name=archetype.title(),
        kind="innate",
        archetype=archetype,
    )


def _destiny(archetype: str, source_stage: int, slug: str | None = None, exhausted: bool = False) -> Trait:
    return Trait(
        slug=slug or f"destiny_{archetype}",
        name=archetype.title(),
        kind="destiny",
        archetype=archetype,
        source_stage=source_stage,
        exhausted=exhausted,
    )


def _artifact(archetype: str = "insight", used: bool = False) -> PlayerArtifact:
    return PlayerArtifact(
        slug=f"art_{archetype}",
        name=archetype.title(),
        archetype=archetype,
        used=used,
    )


# ---------------------------------------------------------------------------
# PlayerArtifact / Trait models
# ---------------------------------------------------------------------------


class TestPlayerArtifact(unittest.TestCase):
    def test_accepts_all_three_archetypes(self):
        for a in UNIVERSAL_ARTIFACT_ARCHETYPES:
            art = _artifact(a)
            self.assertEqual(art.archetype, a)
            self.assertFalse(art.used)

    def test_rejects_unknown_archetype(self):
        with self.assertRaises(ValidationError):
            PlayerArtifact(slug="x", name="X", archetype="weapon")  # type: ignore[arg-type]


class TestTrait(unittest.TestCase):
    def test_innate_accepts_all_five_keys(self):
        for k in UNIVERSAL_INNATE_ARCHETYPES:
            t = _innate(k)
            self.assertEqual(t.archetype, k)
            self.assertIsNone(t.source_stage)

    def test_destiny_accepts_all_twelve_keys(self):
        for k in UNIVERSAL_DESTINY_ARCHETYPES:
            t = _destiny(k, source_stage=1)
            self.assertEqual(t.archetype, k)

    def test_innate_rejects_destiny_key(self):
        with self.assertRaises(ValidationError):
            _innate("not_meant_to_die")

    def test_destiny_rejects_innate_key(self):
        with self.assertRaises(ValidationError):
            _destiny("talent", source_stage=1)

    def test_innate_cannot_carry_source_stage(self):
        with self.assertRaises(ValidationError):
            Trait(
                slug="x",
                name="X",
                kind="innate",
                archetype="talent",
                source_stage=1,
            )

    def test_rejects_unknown_archetype_string(self):
        with self.assertRaises(ValidationError):
            Trait(slug="x", name="X", kind="destiny", archetype="made_up", source_stage=1)


# ---------------------------------------------------------------------------
# PlayerState progression fields
# ---------------------------------------------------------------------------


class TestPlayerStateProgression(unittest.TestCase):
    def test_defaults(self):
        p = _player()
        self.assertEqual(p.stage_index, 0)
        self.assertIsNone(p.stage_label)
        self.assertEqual(p.health_state, "healthy")
        self.assertIsNone(p.artifact)
        self.assertEqual(p.innate_traits, [])
        self.assertEqual(p.destiny_traits, [])

    def test_stage_index_upper_bound(self):
        _player(stage_index=STAGE_INDEX_MAX)  # 5 ok
        with self.assertRaises(ValidationError):
            _player(stage_index=STAGE_INDEX_MAX + 1)

    def test_stage_index_lower_bound(self):
        with self.assertRaises(ValidationError):
            _player(stage_index=-1)

    def test_three_innate_distinct_archetypes_ok(self):
        p = _player(
            innate_traits=[
                _innate("talent"),
                _innate("survival"),
                _innate("social"),
            ],
        )
        self.assertEqual(len(p.innate_traits), 3)

    def test_duplicate_innate_archetypes_rejected(self):
        with self.assertRaises(ValidationError):
            _player(
                innate_traits=[
                    _innate("talent", slug="a"),
                    _innate("talent", slug="b"),
                    _innate("social"),
                ],
            )

    def test_more_than_three_innates_rejected(self):
        with self.assertRaises(ValidationError):
            _player(
                innate_traits=[
                    _innate("talent"),
                    _innate("survival"),
                    _innate("social"),
                    _innate("resource"),
                ],
            )

    def test_destiny_source_stage_must_be_within_current_stage(self):
        # stage_index=2, destiny source_stage=1 ok
        _player(
            stage_index=2,
            stage_label="stage 2",
            destiny_traits=[_destiny("not_meant_to_die", source_stage=1)],
        )
        # source_stage=3 while stage_index=2 → invalid
        with self.assertRaises(ValidationError):
            _player(
                stage_index=2,
                destiny_traits=[_destiny("not_meant_to_die", source_stage=3)],
            )

    def test_destiny_source_stage_zero_rejected(self):
        # Stage 0 is the run's starting stage; no destiny at stage 0.
        with self.assertRaises(ValidationError):
            _player(
                stage_index=1,
                destiny_traits=[_destiny("not_meant_to_die", source_stage=0)],
            )

    def test_destiny_archetypes_must_be_distinct(self):
        with self.assertRaises(ValidationError):
            _player(
                stage_index=3,
                destiny_traits=[
                    _destiny("not_meant_to_die", source_stage=1, slug="a"),
                    _destiny("not_meant_to_die", source_stage=2, slug="b"),
                ],
            )

    def test_destiny_source_stages_must_be_distinct(self):
        # Two different archetypes both claiming source_stage=1 violates the
        # "one destiny per breakthrough" contract even though their archetype
        # keys differ.
        with self.assertRaises(ValidationError):
            _player(
                stage_index=2,
                destiny_traits=[
                    _destiny("not_meant_to_die", source_stage=1, slug="a"),
                    _destiny("learn_from_enemy", source_stage=1, slug="b"),
                ],
            )

    def test_destiny_missing_source_stage_rejected(self):
        with self.assertRaises(ValidationError):
            _player(
                stage_index=1,
                destiny_traits=[
                    Trait(
                        slug="d",
                        name="D",
                        kind="destiny",
                        archetype="not_meant_to_die",
                    )
                ],
            )

    def test_more_than_five_destinies_rejected(self):
        with self.assertRaises(ValidationError):
            _player(
                stage_index=STAGE_INDEX_MAX,
                destiny_traits=[
                    _destiny("not_meant_to_die", 1, slug="a"),
                    _destiny("golden_cicada_escape", 2, slug="b"),
                    _destiny("last_barrier", 3, slug="c"),
                    _destiny("heaven_piercing_eye", 4, slug="d"),
                    _destiny("learn_from_enemy", 5, slug="e"),
                    _destiny("breakthrough_instinct", 5, slug="f"),
                ],
            )

    def test_health_dead_requires_status_dead(self):
        with self.assertRaises(ValidationError):
            _player(health_state="dead", status="alive")

    def test_status_dead_requires_health_dead_or_critical(self):
        # dead+dead ok
        _player(health_state="dead", status="dead")
        # dead+critical ok (mid-death turn)
        _player(health_state="critical", status="dead")
        # dead+healthy not ok
        with self.assertRaises(ValidationError):
            _player(health_state="healthy", status="dead")

    def test_all_five_health_states_accepted(self):
        for h in ("healthy", "hurt", "badly_hurt", "critical"):
            p = _player(health_state=h)
            self.assertEqual(p.health_state, h)


# ---------------------------------------------------------------------------
# PackMetaProgress
# ---------------------------------------------------------------------------


class TestPackMetaProgress(unittest.TestCase):
    def test_defaults(self):
        meta = PackMetaProgress(pack_name="demo")
        self.assertEqual(meta.runs_started, 0)
        self.assertEqual(meta.runs_finished, 0)
        self.assertEqual(meta.deaths_count, 0)
        self.assertEqual(meta.best_stage_index, 0)
        self.assertEqual(meta.deaths, [])

    def test_rejects_unknown_archetype_in_seen(self):
        with self.assertRaises(ValidationError):
            PackMetaProgress(
                pack_name="demo",
                seen_destiny_archetypes=["not_a_real_destiny"],
            )

    def test_coverage_helpers(self):
        meta = PackMetaProgress(
            pack_name="demo",
            seen_artifact_archetypes=["insight"],
            seen_innate_archetypes=["talent", "survival"],
            seen_destiny_archetypes=["not_meant_to_die", "last_barrier", "read_the_room"],
        )
        self.assertAlmostEqual(meta.coverage_artifact(), 1 / 3)
        self.assertAlmostEqual(meta.coverage_innate(), 2 / 5)
        self.assertAlmostEqual(meta.coverage_destiny(), 3 / 12)

    def test_unseen_helpers_preserve_universal_order(self):
        meta = PackMetaProgress(
            pack_name="demo",
            seen_destiny_archetypes=[
                "not_meant_to_die",
                "heaven_piercing_eye",
            ],
        )
        unseen = meta.unseen_destiny_archetypes()
        # Order should match UNIVERSAL_DESTINY_ARCHETYPES with the two seen
        # filtered out.
        expected = [k for k in UNIVERSAL_DESTINY_ARCHETYPES if k not in ("not_meant_to_die", "heaven_piercing_eye")]
        self.assertEqual(unseen, expected)


# ---------------------------------------------------------------------------
# Survival-trigger precedence
# ---------------------------------------------------------------------------


class TestSurvivalPrecedence(unittest.TestCase):
    def test_no_trigger_when_nothing_applies(self):
        p = _player(
            stage_index=2,
            stage_label="s",
            destiny_traits=[_destiny("read_the_room", 1)],
        )
        self.assertIsNone(resolve_survival_trigger(p, prior_health_state="badly_hurt"))

    def test_bond_rescue_artifact_fires_first(self):
        p = _player(
            artifact=_artifact("bond_rescue"),
            stage_index=1,
            destiny_traits=[_destiny("not_meant_to_die", 1)],
        )
        trigger = resolve_survival_trigger(p, prior_health_state="hurt")
        self.assertIsNotNone(trigger)
        assert trigger is not None
        self.assertEqual(trigger.kind, "artifact")
        self.assertEqual(trigger.archetype, "bond_rescue")
        self.assertEqual(trigger.new_health_state, "critical")

    def test_not_meant_to_die_fires_when_no_bond_rescue(self):
        p = _player(
            stage_index=1,
            destiny_traits=[_destiny("not_meant_to_die", 1)],
        )
        trigger = resolve_survival_trigger(p, prior_health_state="hurt")
        self.assertIsNotNone(trigger)
        assert trigger is not None
        self.assertEqual(trigger.archetype, "not_meant_to_die")

    def test_not_meant_to_die_skipped_when_exhausted(self):
        p = _player(
            stage_index=1,
            destiny_traits=[_destiny("not_meant_to_die", 1, exhausted=True)],
        )
        self.assertIsNone(resolve_survival_trigger(p, prior_health_state="hurt"))

    def test_last_barrier_only_fires_from_critical(self):
        p = _player(
            stage_index=1,
            destiny_traits=[_destiny("last_barrier", 1)],
        )
        # From badly_hurt → dead, last_barrier does NOT fire (needs critical).
        self.assertIsNone(resolve_survival_trigger(p, prior_health_state="badly_hurt"))
        # From critical → dead, last_barrier DOES fire.
        trigger = resolve_survival_trigger(p, prior_health_state="critical")
        self.assertIsNotNone(trigger)
        assert trigger is not None
        self.assertEqual(trigger.archetype, "last_barrier")

    def test_bond_rescue_skipped_when_used(self):
        p = _player(
            artifact=_artifact("bond_rescue", used=True),
            stage_index=1,
            destiny_traits=[_destiny("not_meant_to_die", 1)],
        )
        trigger = resolve_survival_trigger(p, prior_health_state="hurt")
        # Falls through to destiny precedence.
        self.assertIsNotNone(trigger)
        assert trigger is not None
        self.assertEqual(trigger.archetype, "not_meant_to_die")

    def test_non_death_preventing_destinies_ignored(self):
        # read_the_room / timely_ally etc. must not prevent death.
        p = _player(
            stage_index=2,
            destiny_traits=[
                _destiny("read_the_room", 1),
                _destiny("timely_ally", 2),
            ],
        )
        self.assertIsNone(resolve_survival_trigger(p, prior_health_state="critical"))


# ---------------------------------------------------------------------------
# Draft bias
# ---------------------------------------------------------------------------


class TestDraftBias(unittest.TestCase):
    def test_empty_pool_returns_empty_list(self):
        self.assertEqual(draft_bias_order([], ()), [])

    def test_unseen_first_when_below_threshold(self):
        # 2 of 12 destinies seen (~17%), well below 70% threshold.
        order = draft_bias_order(
            ["not_meant_to_die", "read_the_room"],
            UNIVERSAL_DESTINY_ARCHETYPES,
        )
        # First 10 should all be unseen; last 2 should be the seen ones.
        self.assertEqual(len(order), 12)
        self.assertNotIn("not_meant_to_die", order[:10])
        self.assertNotIn("read_the_room", order[:10])
        self.assertEqual(sorted(order[10:]), sorted(["not_meant_to_die", "read_the_room"]))

    def test_free_draw_above_threshold(self):
        # 9 of 12 = 75% ≥ 70% threshold → free draw, universal order.
        seen = list(UNIVERSAL_DESTINY_ARCHETYPES[:9])
        order = draft_bias_order(seen, UNIVERSAL_DESTINY_ARCHETYPES)
        self.assertEqual(order, list(UNIVERSAL_DESTINY_ARCHETYPES))

    def test_threshold_is_inclusive(self):
        # Exactly 70% of 10 items == 7 seen → should be free draw.
        pool = tuple(f"k{i}" for i in range(10))
        seen = list(pool[:7])
        order = draft_bias_order(seen, pool, coverage_threshold=0.70)
        self.assertEqual(order, list(pool))

    def test_destiny_draw_order_filters_in_run_picks(self):
        meta = PackMetaProgress(
            pack_name="demo",
            seen_destiny_archetypes=["not_meant_to_die"],
        )
        picked = ["read_the_room"]
        order = destiny_draw_order(meta, already_picked_in_run=picked)
        # 11 candidates (12 - 1 picked); not_meant_to_die is seen so it goes last.
        self.assertEqual(len(order), 11)
        self.assertNotIn("read_the_room", order)
        self.assertEqual(order[-1], "not_meant_to_die")

    def test_destiny_draw_order_coverage_uses_full_pool(self):
        # Pack has seen 6 of 12 destinies (50%, well below 70% threshold).
        # 4 archetypes already picked this run — none of which were
        # previously seen. Without the coverage_against fix, the candidate
        # pool would shrink to 8 with 6 of those seen → 6/8 = 75% which
        # would trip the free-draw branch and surface seen archetypes
        # before the 2 remaining unseen ones. The fix keeps coverage
        # against the full 12-pool so unseen-first still holds.
        seen = list(UNIVERSAL_DESTINY_ARCHETYPES[:6])  # archetypes 0..5
        picked = list(UNIVERSAL_DESTINY_ARCHETYPES[6:10])  # archetypes 6..9
        meta = PackMetaProgress(pack_name="demo", seen_destiny_archetypes=seen)
        order = destiny_draw_order(meta, already_picked_in_run=picked)
        self.assertEqual(len(order), 8)
        # The 2 unseen archetypes (indices 10, 11) must come first.
        unseen_in_candidates = [
            k for k in UNIVERSAL_DESTINY_ARCHETYPES
            if k not in seen and k not in picked
        ]
        self.assertEqual(len(unseen_in_candidates), 2)
        self.assertEqual(order[: len(unseen_in_candidates)], unseen_in_candidates)
        # The 6 seen archetypes follow the unseen ones.
        self.assertEqual(set(order[len(unseen_in_candidates):]), set(seen))

    def test_draft_bias_coverage_against_decouples_pool(self):
        # 9 of 12 keys seen → 75% in the full pool, above 70% threshold:
        # if coverage is computed against the filtered candidates (8) we'd
        # get 6/8 = 75% — same answer here, but the contract is "use the
        # full pool". Verify by passing a smaller candidate tuple where
        # only filtered-pool coverage would trip the threshold.
        full = tuple(f"k{i}" for i in range(10))
        seen = list(full[:5])  # 50% of full
        candidates = tuple(full[:6])  # filter that includes 5 of 6 seen
        # Without coverage_against: 5/6 = 0.83 → free draw → seen first.
        order_filtered = draft_bias_order(seen, candidates)
        self.assertEqual(order_filtered, list(candidates))
        # With coverage_against=full: 5/10 = 0.50 → unseen-first → "k5" leads.
        order_against_full = draft_bias_order(
            seen, candidates, coverage_against=full,
        )
        self.assertEqual(order_against_full[0], "k5")

    def test_innate_draw_order(self):
        meta = PackMetaProgress(
            pack_name="demo",
            seen_innate_archetypes=["talent"],
        )
        order = innate_draw_order(meta)
        self.assertEqual(len(order), 5)
        # Below threshold (1/5 = 20% < 70%) → unseen first.
        self.assertEqual(order[-1], "talent")

    def test_artifact_draw_order_always_all_three(self):
        meta = PackMetaProgress(
            pack_name="demo",
            seen_artifact_archetypes=["insight"],
        )
        order = artifact_draw_order(meta)
        self.assertEqual(set(order), set(UNIVERSAL_ARTIFACT_ARCHETYPES))
        self.assertEqual(len(order), 3)


# ---------------------------------------------------------------------------
# Meta-progress merge on run end
# ---------------------------------------------------------------------------


class TestMergeRunIntoMeta(unittest.TestCase):
    def _final_player(self) -> PlayerState:
        return _player(
            stage_index=3,
            stage_label="break stalemate",
            artifact=_artifact("bond_rescue", used=True),
            innate_traits=[
                _innate("talent"),
                _innate("survival"),
                _innate("social"),
            ],
            destiny_traits=[
                _destiny("not_meant_to_die", 1, exhausted=True),
                _destiny("learn_from_enemy", 2),
                _destiny("read_the_room", 3),
            ],
            health_state="dead",
            status="dead",
        )

    def test_death_merge_bumps_deaths_count(self):
        meta = PackMetaProgress(pack_name="demo")
        updated = merge_run_into_meta(
            meta,
            player=self._final_player(),
            save_id="save_001",
            turn=42,
            outcome="death",
            cause="struck down by rival",
        )
        self.assertEqual(updated.deaths_count, 1)
        self.assertEqual(updated.runs_finished, 0)
        self.assertEqual(updated.best_stage_index, 3)
        self.assertEqual(len(updated.deaths), 1)
        record = updated.deaths[0]
        self.assertEqual(record.save_id, "save_001")
        self.assertEqual(record.turn, 42)
        self.assertEqual(record.stage_index, 3)
        self.assertEqual(record.cause, "struck down by rival")

    def test_death_merge_folds_archetypes_and_slugs(self):
        meta = PackMetaProgress(pack_name="demo")
        updated = merge_run_into_meta(
            meta,
            player=self._final_player(),
            save_id="save_001",
            turn=42,
            outcome="death",
        )
        self.assertEqual(updated.seen_artifact_archetypes, ["bond_rescue"])
        self.assertEqual(
            set(updated.seen_innate_archetypes),
            {"talent", "survival", "social"},
        )
        self.assertEqual(
            set(updated.seen_destiny_archetypes),
            {"not_meant_to_die", "learn_from_enemy", "read_the_room"},
        )
        self.assertIn("art_bond_rescue", updated.seen_artifact_slugs)

    def test_merge_dedups_across_runs(self):
        meta = PackMetaProgress(
            pack_name="demo",
            seen_innate_archetypes=["talent"],
            seen_innate_slugs=["innate_talent"],
        )
        updated = merge_run_into_meta(
            meta,
            player=self._final_player(),
            save_id="save_002",
            turn=10,
            outcome="death",
        )
        # 'talent' should not appear twice.
        self.assertEqual(updated.seen_innate_archetypes.count("talent"), 1)
        self.assertEqual(updated.seen_innate_slugs.count("innate_talent"), 1)

    def test_completion_merge_bumps_runs_finished_not_deaths(self):
        meta = PackMetaProgress(pack_name="demo")
        finisher = _player(
            stage_index=STAGE_INDEX_MAX,
            stage_label="rewrite fate",
            artifact=_artifact("insight"),
            innate_traits=[
                _innate("talent"),
                _innate("survival"),
                _innate("social"),
            ],
            destiny_traits=[
                _destiny("not_meant_to_die", 1),
                _destiny("learn_from_enemy", 2),
                _destiny("read_the_room", 3),
                _destiny("breakthrough_instinct", 4),
                _destiny("timely_ally", 5),
            ],
        )
        updated = merge_run_into_meta(
            meta,
            player=finisher,
            save_id="save_003",
            turn=100,
            outcome="completion",
        )
        self.assertEqual(updated.runs_finished, 1)
        self.assertEqual(updated.deaths_count, 0)
        self.assertEqual(updated.deaths, [])
        self.assertEqual(updated.best_stage_index, STAGE_INDEX_MAX)

    def test_best_stage_index_never_regresses(self):
        meta = PackMetaProgress(pack_name="demo", best_stage_index=4)
        early_death = _player(
            stage_index=1,
            artifact=_artifact("insight"),
            innate_traits=[
                _innate("talent"),
                _innate("survival"),
                _innate("social"),
            ],
            health_state="dead",
            status="dead",
        )
        updated = merge_run_into_meta(
            meta,
            player=early_death,
            save_id="save_004",
            turn=3,
            outcome="death",
        )
        self.assertEqual(updated.best_stage_index, 4)


# ---------------------------------------------------------------------------
# lint_save progression-invariant gates (turn-zero saves)
# ---------------------------------------------------------------------------


class TestLintSaveProgressionGates(unittest.TestCase):
    """Bootstrap saves (turn 0) must already carry artifact + 3 innate traits.

    new-game.md writes the save to disk only after Steps 1.5 and 1.6, so
    the lint gate cannot exempt turn 0 — a missing artifact / innates on a
    persisted turn-0 save means the bootstrap was skipped.
    """

    def _save_with(self, **player_overrides):
        from tools._models import Save, WorldState

        player = _player(**player_overrides)
        # Use an emergent location to avoid pack-slug existence checks; the
        # lint helper under test (_lint_progression) does not consult slugs.
        world = WorldState(
            current_location="emergent:somewhere",
            player=player,
        )
        return Save(save_id="save_001", pack_name="demo", world=world)

    def test_turn_zero_save_without_artifact_is_flagged(self):
        from pathlib import Path
        from tools.lint_save import _lint_progression

        save = self._save_with(
            innate_traits=[
                _innate("talent"), _innate("survival"), _innate("social"),
            ],
        )
        issues = _lint_progression(save, Path("/nonexistent"))
        self.assertTrue(
            any("artifact is null" in i for i in issues),
            f"expected artifact issue, got: {issues}",
        )

    def test_turn_zero_save_without_innates_is_flagged(self):
        from pathlib import Path
        from tools.lint_save import _lint_progression

        save = self._save_with(artifact=_artifact("insight"))
        issues = _lint_progression(save, Path("/nonexistent"))
        self.assertTrue(
            any("innate_traits must be exactly 3" in i for i in issues),
            f"expected innate-count issue, got: {issues}",
        )

    def test_complete_turn_zero_save_passes(self):
        from pathlib import Path
        from tools.lint_save import _lint_progression

        save = self._save_with(
            artifact=_artifact("insight"),
            innate_traits=[
                _innate("talent"), _innate("survival"), _innate("social"),
            ],
            stage_label="入局起步",
        )
        issues = _lint_progression(save, Path("/nonexistent"))
        self.assertEqual(issues, [])


# ---------------------------------------------------------------------------
# lint_pack progression_rules.md heading matching (case-insensitive)
# ---------------------------------------------------------------------------


class TestLintPackProgressionHeadings(unittest.TestCase):
    """Heading matching must be case-insensitive so naturally title-cased
    sections (e.g. `## Artifact Archetypes`) are accepted."""

    def _write_pack(self, tmp_root, headings: list[str]):
        from pathlib import Path

        pack_dir = Path(tmp_root) / "demo_pack"
        pack_dir.mkdir(parents=True)
        body = "\n\n".join(f"## {h}\n\nbody.\n" for h in headings)
        (pack_dir / "progression_rules.md").write_text(body, encoding="utf-8")
        return pack_dir

    def test_title_case_headings_accepted(self):
        import tempfile

        from tools.lint_pack import _lint_progression_rules

        title_case_headings = [
            "Stages",
            "Breakthrough Triggers",
            "Artifact Archetypes",
            "Innate Traits",
            "Destiny Traits",
            "Health Ladder",
            "Breakthrough Voice",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            pack_dir = self._write_pack(tmp, title_case_headings)
            issues = _lint_progression_rules(pack_dir)
            self.assertEqual(
                issues,
                [],
                f"title-case headings should pass; got issues: {issues}",
            )

    def test_chinese_headings_accepted(self):
        import tempfile

        from tools.lint_pack import _lint_progression_rules

        zh_headings = [
            "境界",
            "破境触机",
            "法宝类型",
            "天赋类型",
            "命格类型",
            "体况梯度",
            "破境笔触",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            pack_dir = self._write_pack(tmp, zh_headings)
            issues = _lint_progression_rules(pack_dir)
            self.assertEqual(
                issues, [], f"zh headings should pass; got issues: {issues}"
            )

    def test_missing_section_still_flagged(self):
        import tempfile

        from tools.lint_pack import _lint_progression_rules

        # Drop "Breakthrough Voice" — should be flagged even with otherwise
        # title-case headings.
        partial = [
            "Stages",
            "Breakthrough Triggers",
            "Artifact Archetypes",
            "Innate Traits",
            "Destiny Traits",
            "Health Ladder",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            pack_dir = self._write_pack(tmp, partial)
            issues = _lint_progression_rules(pack_dir)
            self.assertTrue(
                any("breakthrough_voice" in i for i in issues),
                f"expected breakthrough_voice issue, got: {issues}",
            )


if __name__ == "__main__":
    unittest.main()
