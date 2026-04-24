"""Progression-layer helpers: survival-trigger precedence, draft bias,
and meta-progress merging.

These functions are the deterministic, testable core of the v0.5
progression layer. The playbooks and GM prompts reference them, but
the agent does not need to call them on every turn — they exist so
lint/tests/inspection can reason about the same rules the agent
follows in prose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal, Optional

from ._models import (
    DeathRecord,
    HealthState,
    PackMetaProgress,
    PlayerState,
    UNIVERSAL_ARTIFACT_ARCHETYPES,
    UNIVERSAL_DESTINY_ARCHETYPES,
    UNIVERSAL_INNATE_ARCHETYPES,
)


# ---------------------------------------------------------------------------
# Survival-trigger precedence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SurvivalTrigger:
    """Which survival trigger (if any) fires before a fatal patch is terminal."""

    kind: Literal["artifact", "destiny"]
    slug: str
    archetype: str
    new_health_state: HealthState  # always "critical" in MVP
    note: str


def resolve_survival_trigger(
    player: PlayerState,
    prior_health_state: HealthState,
) -> Optional[SurvivalTrigger]:
    """Return the trigger that replaces a `player_health_state: 'dead'` patch,
    or None if the fatal patch should be committed as terminal.

    Precedence (locked per the v0.5 plan + gm_system_fragment.md):

      1. Artifact `bond_rescue` archetype, unused  → critical, artifact used.
      2. Destiny `not_meant_to_die`,     not exhausted → critical, exhausted.
      3. Destiny `last_barrier`, not exhausted, and
         `prior_health_state == 'critical'`           → critical, exhausted.

    `last_barrier` only fires on the transition `critical → dead`, not on a
    skip-to-dead from healthier states. No other MVP trigger prevents death.
    """
    artifact = player.artifact
    if (
        artifact is not None
        and artifact.archetype == "bond_rescue"
        and not artifact.used
    ):
        return SurvivalTrigger(
            kind="artifact",
            slug=artifact.slug,
            archetype="bond_rescue",
            new_health_state="critical",
            note="bond_rescue artifact fires; player drops to critical",
        )

    for t in player.destiny_traits:
        if t.archetype == "not_meant_to_die" and not t.exhausted:
            return SurvivalTrigger(
                kind="destiny",
                slug=t.slug,
                archetype="not_meant_to_die",
                new_health_state="critical",
                note="not_meant_to_die destiny fires; player drops to critical",
            )

    if prior_health_state == "critical":
        for t in player.destiny_traits:
            if t.archetype == "last_barrier" and not t.exhausted:
                return SurvivalTrigger(
                    kind="destiny",
                    slug=t.slug,
                    archetype="last_barrier",
                    new_health_state="critical",
                    note="last_barrier destiny fires; one-turn buffer at critical",
                )

    return None


# ---------------------------------------------------------------------------
# Draft bias (unseen-first menus)
# ---------------------------------------------------------------------------


# Coverage fraction above which the menu falls back to free draw.
DRAFT_BIAS_COVERAGE_THRESHOLD: float = 0.70


def draft_bias_order(
    seen_archetypes: Iterable[str],
    universal_pool: tuple[str, ...],
    *,
    coverage_threshold: float = DRAFT_BIAS_COVERAGE_THRESHOLD,
    coverage_against: tuple[str, ...] | None = None,
) -> list[str]:
    """Return universal archetype keys ordered for a fresh draw menu.

    While coverage < threshold: unseen keys first (stable order), then seen.
    While coverage >= threshold: universal_pool order as-is (free draw).

    The caller picks however many it needs from the front of the list.

    `coverage_against` lets the caller decouple the **ordering pool** from
    the **coverage pool**. For destiny draws, `universal_pool` is the
    candidates after filtering out archetypes already picked this run, but
    the coverage cutoff must stay against the full 12-archetype pool —
    otherwise a single picked-this-run archetype shrinks the denominator
    and the threshold trips early. When omitted, defaults to
    `universal_pool` (the right answer for unfiltered menus like artifact
    and innate).
    """
    if not universal_pool:
        return []
    pool_set = set(universal_pool)
    seen_set = set(seen_archetypes)
    coverage_pool = coverage_against if coverage_against is not None else universal_pool
    if coverage_pool:
        seen_in_coverage = set(coverage_pool) & seen_set
        coverage = len(seen_in_coverage) / len(coverage_pool)
    else:
        coverage = 0.0
    if coverage >= coverage_threshold:
        return list(universal_pool)
    seen_in_pool = pool_set & seen_set
    unseen = [k for k in universal_pool if k not in seen_in_pool]
    seen_tail = [k for k in universal_pool if k in seen_in_pool]
    return unseen + seen_tail


def destiny_draw_order(
    meta: PackMetaProgress,
    already_picked_in_run: Iterable[str],
) -> list[str]:
    """Order the 12 destiny archetypes for a breakthrough draw.

    Filters out archetypes already picked in the current run, then applies
    the unseen-first bias against `meta.seen_destiny_archetypes`. The
    coverage cutoff stays against the **full** 12-pool so picking 4-5
    destinies per run does not artificially trip the threshold.
    """
    picked = set(already_picked_in_run)
    candidates = tuple(k for k in UNIVERSAL_DESTINY_ARCHETYPES if k not in picked)
    return draft_bias_order(
        meta.seen_destiny_archetypes,
        candidates,
        coverage_against=UNIVERSAL_DESTINY_ARCHETYPES,
    )


def innate_draw_order(meta: PackMetaProgress) -> list[str]:
    """Order the 5 innate archetypes for the new-game pick menu."""
    return draft_bias_order(meta.seen_innate_archetypes, UNIVERSAL_INNATE_ARCHETYPES)


def artifact_draw_order(meta: PackMetaProgress) -> list[str]:
    """Order the 3 artifact archetypes for the new-game pick menu.

    The artifact menu always shows one per archetype, so the bias here
    drives which archetype is rendered first (visual prominence), not
    which archetypes appear.
    """
    return draft_bias_order(meta.seen_artifact_archetypes, UNIVERSAL_ARTIFACT_ARCHETYPES)


# ---------------------------------------------------------------------------
# Meta-progress merge on run end
# ---------------------------------------------------------------------------


RunOutcome = Literal["death", "completion"]


def _dedup_extend(dst: list[str], src: Iterable[str]) -> list[str]:
    seen = set(dst)
    out = list(dst)
    for k in src:
        if k not in seen:
            out.append(k)
            seen.add(k)
    return out


def merge_run_into_meta(
    meta: PackMetaProgress,
    *,
    player: PlayerState,
    save_id: str,
    turn: int,
    outcome: RunOutcome,
    cause: str = "",
) -> PackMetaProgress:
    """Return a new PackMetaProgress with this run folded in.

    - Merges the run's artifact, innate, destiny archetype keys + slugs into
      seen_* lists (dedup, order-preserving).
    - outcome='death'   → deaths_count += 1, appends DeathRecord, updates
                          best_stage_index.
    - outcome='completion' → runs_finished += 1, updates best_stage_index.
    - Does NOT modify runs_started (that increments at new-game init).
    """
    artifact_archetypes: list[str] = []
    artifact_slugs: list[str] = []
    if player.artifact is not None:
        artifact_archetypes.append(player.artifact.archetype)
        artifact_slugs.append(player.artifact.slug)

    innate_archetypes = [t.archetype for t in player.innate_traits]
    innate_slugs = [t.slug for t in player.innate_traits]

    destiny_archetypes = [t.archetype for t in player.destiny_traits]
    destiny_slugs = [t.slug for t in player.destiny_traits]

    updated = meta.model_copy(
        update={
            "seen_artifact_archetypes": _dedup_extend(
                meta.seen_artifact_archetypes, artifact_archetypes
            ),
            "seen_artifact_slugs": _dedup_extend(meta.seen_artifact_slugs, artifact_slugs),
            "seen_innate_archetypes": _dedup_extend(
                meta.seen_innate_archetypes, innate_archetypes
            ),
            "seen_innate_slugs": _dedup_extend(meta.seen_innate_slugs, innate_slugs),
            "seen_destiny_archetypes": _dedup_extend(
                meta.seen_destiny_archetypes, destiny_archetypes
            ),
            "seen_destiny_slugs": _dedup_extend(meta.seen_destiny_slugs, destiny_slugs),
            "best_stage_index": max(meta.best_stage_index, player.stage_index),
        }
    )

    if outcome == "death":
        updated = updated.model_copy(
            update={
                "deaths_count": updated.deaths_count + 1,
                "deaths": [
                    *updated.deaths,
                    DeathRecord(
                        save_id=save_id,
                        turn=turn,
                        cause=cause,
                        stage_index=player.stage_index,
                        stage_label=player.stage_label,
                    ),
                ],
            }
        )
    else:  # completion
        updated = updated.model_copy(
            update={"runs_finished": updated.runs_finished + 1}
        )

    return updated
