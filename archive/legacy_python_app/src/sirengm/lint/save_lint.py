"""Rule-based save lint. Verifies structured state agrees with the stacked pack."""

from __future__ import annotations

from sirengm.config import AppConfig
from sirengm.pack.stacked import load_stacked
from sirengm.save.store import load_save


def lint_save(cfg: AppConfig, *, save_id: str) -> list[str]:
    issues: list[str] = []
    try:
        save = load_save(cfg.saves_dir, save_id)
    except Exception as e:
        return [f"failed to load save: {type(e).__name__}: {e}"]
    try:
        stacked = load_stacked(cfg.packs_dir / save.pack_name, genre_packs_root=cfg.root / "genre_packs")
    except Exception as e:
        return [f"failed to load stacked pack {save.pack_name!r}: {type(e).__name__}: {e}"]

    known = stacked.all_entity_slugs()
    w = save.world

    def _check_slug(slug: str, where: str) -> None:
        if slug in known:
            return
        if slug.startswith("emergent:"):
            return
        if f"emergent slug={slug}" in save.hidden_truths:
            return
        issues.append(f"{where} references unknown slug {slug!r}")

    _check_slug(w.current_location, "world_state.current_location")
    for slug in w.present_entities:
        _check_slug(slug, "world_state.present_entities")
    for thread in w.active_threads:
        _check_slug(thread.id, "world_state.active_threads")
    for slug in save.relationships.by_slug:
        _check_slug(slug, "relationship_state")

    # Player slug must match a protagonist character in the pack (unless emergent).
    if w.player.slug not in known and not w.player.slug.startswith("emergent:"):
        issues.append(f"player.slug {w.player.slug!r} not in user pack")

    # Open loops: closed loops must have closed_turn; turn counter consistent.
    for loop in save.open_loops.items:
        if loop.status == "closed" and loop.closed_turn is None:
            issues.append(f"open_loop {loop.id!r} marked closed but closed_turn is null")
    if save.session_log:
        last_turn = save.session_log[-1].turn
        expected_next = last_turn + 1
        if w.turn not in (last_turn, expected_next):
            issues.append(
                f"world.turn={w.turn} out of sync with last session_log turn={last_turn}"
            )
    return issues
