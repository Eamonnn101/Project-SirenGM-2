"""Build the per-turn context bundle passed to narrator and state updater.

The context is derived **from structured state**, not by scraping markdown.
Scene contents come from `WorldState.present_entities` / `current_location` /
`active_threads`. Relevant pack pages are fetched by direct slug lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sirengm.pack.models import PageBase
from sirengm.pack.stacked import StackedPack
from sirengm.save.models import Save, SessionLogEntry

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


@dataclass(frozen=True)
class TurnContext:
    stacked: StackedPack
    save: Save
    # Pre-resolved entity pages for present + location + arcs
    present_pages: list[PageBase]
    location_page: PageBase | None
    arc_pages: list[PageBase]
    # Stitched prompt fragments
    gm_system_prompt: str
    state_updater_system_prompt: str
    style_guide_body: str
    canon_guardrails_body: str
    overview_body: str
    # Recent session log (last N turns, already rendered short form)
    recent_log: list[SessionLogEntry]


def build_context(stacked: StackedPack, save: Save, *, recent_n: int = 6) -> TurnContext:
    world = save.world
    present_pages = [p for slug in world.present_entities if (p := stacked.find_entity(slug)) is not None]
    location_page = stacked.find_entity(world.current_location)
    arc_pages = [p for t in world.active_threads if (p := stacked.find_entity(t.id)) is not None]

    gm_system = _stitched_gm_system(stacked)
    updater_system = _stitched_state_updater_system(stacked)

    recent = save.session_log[-recent_n:]
    return TurnContext(
        stacked=stacked,
        save=save,
        present_pages=present_pages,
        location_page=location_page,
        arc_pages=arc_pages,
        gm_system_prompt=gm_system,
        state_updater_system_prompt=updater_system,
        style_guide_body=stacked.style_guide_body(),
        canon_guardrails_body=stacked.canon_guardrails_body(),
        overview_body=stacked.overview_body(),
        recent_log=list(recent),
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _stitched_gm_system(stacked: StackedPack) -> str:
    base = _read(_PROMPT_DIR / "system_gm.md")
    genre_fragment = _read(_genre_prompt(stacked, "gm_system_fragment.md"))
    return _concat(base, genre_fragment)


def _stitched_state_updater_system(stacked: StackedPack) -> str:
    base = _read(_PROMPT_DIR / "system_state_updater.md")
    # State updater benefits from the genre's guardrails so it knows what to refuse.
    return _concat(base, stacked.canon_guardrails_body())


def _genre_prompt(stacked: StackedPack, filename: str) -> Path:
    return stacked.genre_dir / "prompts" / filename


def _concat(*parts: str) -> str:
    return "\n\n---\n\n".join(p.strip() for p in parts if p and p.strip())
