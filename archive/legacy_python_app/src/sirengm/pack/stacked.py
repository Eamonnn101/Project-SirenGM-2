"""Stacked pack view: a user pack layered on top of its genre pack.

The runtime always queries a StackedPack, never a raw Pack. Genre-level fields
(style_guide, canon_guardrails) become the union/concat of the two layers.
User-pack entities win; genre entities are only for systems and only
consulted if the user pack doesn't override them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sirengm.pack.loader import load_genre_pack, load_user_pack
from sirengm.pack.models import MetaPage, Pack, PageBase, SystemPage


@dataclass(frozen=True)
class StackedPack:
    genre: Pack
    user: Pack
    genre_root: Path

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def genre_name(self) -> str:
        return self.genre.name

    @property
    def genre_dir(self) -> Path:
        return self.genre_root / self.genre.name

    # --- Text surfaces ---

    def style_guide_body(self) -> str:
        return _concat_bodies(self.genre.style_guide, self.user.style_guide)

    def canon_guardrails_body(self) -> str:
        return _concat_bodies(self.genre.canon_guardrails, self.user.canon_guardrails)

    def overview_body(self) -> str:
        # Overview is user-pack only; genre overview (if any) is not narrative-worthy.
        return self.user.overview.body if self.user.overview else ""

    # --- Entity access ---

    def find_entity(self, slug: str) -> PageBase | None:
        # User pack is authoritative for novel-specific entities.
        found = self.user.find_entity(slug)
        if found is not None:
            return found
        # Fall back to genre for systems (cultivation, social_rules).
        for page in self.genre.systems:
            if page.slug == slug:
                return page
        return None

    def all_entity_slugs(self) -> set[str]:
        slugs = self.user.all_entity_slugs()
        slugs.update(s.slug for s in self.genre.systems)
        return slugs

    def systems(self) -> list[SystemPage]:
        # Genre systems first, user overrides later (if any share a slug).
        by_slug: dict[str, SystemPage] = {}
        for s in self.genre.systems:
            by_slug[s.slug] = s
        for s in self.user.systems:
            by_slug[s.slug] = s
        return list(by_slug.values())


def load_stacked(
    user_pack_dir: Path,
    *,
    genre_packs_root: Path,
) -> StackedPack:
    user = load_user_pack(user_pack_dir)
    if not user.inherits_genre:
        raise ValueError(f"User pack {user_pack_dir} does not declare inherits_genre.")
    genre_dir = genre_packs_root / user.inherits_genre
    genre = load_genre_pack(genre_dir)
    return StackedPack(genre=genre, user=user, genre_root=genre_packs_root)


def _concat_bodies(a: MetaPage | None, b: MetaPage | None) -> str:
    parts = [p.body for p in (a, b) if p is not None and p.body.strip()]
    return "\n\n---\n\n".join(parts)
