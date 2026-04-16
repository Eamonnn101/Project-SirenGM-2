"""Read a Story Pack directory from disk into a Pack object.

`load_pack` auto-detects whether the directory is a genre or user pack by
reading `kind` from `index.md` frontmatter. Convenience wrappers
`load_genre_pack` and `load_user_pack` assert the expected kind.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import frontmatter

from sirengm.pack.models import (
    ArcPage,
    CharacterPage,
    EventPage,
    FactionPage,
    LocationPage,
    MetaPage,
    Pack,
    PackKind,
    PageBase,
    SystemPage,
)
from sirengm.pack.paths import ENTITY_DIRS, PackPaths

# Map subdirectory name -> Pydantic model class.
_ENTITY_MODEL: dict[str, type[PageBase]] = {
    "characters": CharacterPage,
    "factions": FactionPage,
    "locations": LocationPage,
    "systems": SystemPage,
    "arcs": ArcPage,
    "events": EventPage,
}


def load_pack(pack_dir: Path) -> Pack:
    if not pack_dir.is_dir():
        raise FileNotFoundError(f"Pack directory not found: {pack_dir}")
    paths = PackPaths(pack_dir)

    index_meta, index_fm = _load_meta_and_fm(paths.index)
    kind = cast(PackKind, index_fm.get("kind", "user"))
    inherits_genre = index_fm.get("inherits_genre") if kind == "user" else None

    return Pack(
        name=pack_dir.name,
        kind=kind,
        inherits_genre=inherits_genre,
        index=index_meta,
        overview=_load_meta(paths.overview),
        style_guide=_load_meta(paths.style_guide),
        canon_guardrails=_load_meta(paths.canon_guardrails),
        timeline=_load_meta(paths.timeline),
        relationships=_load_meta(paths.relationships),
        ambiguities=_load_meta(paths.ambiguities),
        characters=_load_entity_dir(paths.entity_dir("characters"), CharacterPage),
        factions=_load_entity_dir(paths.entity_dir("factions"), FactionPage),
        locations=_load_entity_dir(paths.entity_dir("locations"), LocationPage),
        systems=_load_entity_dir(paths.entity_dir("systems"), SystemPage),
        arcs=_load_entity_dir(paths.entity_dir("arcs"), ArcPage),
        events=_load_entity_dir(paths.entity_dir("events"), EventPage),
    )


def load_genre_pack(pack_dir: Path) -> Pack:
    pack = load_pack(pack_dir)
    if pack.kind != "genre":
        raise ValueError(f"{pack_dir} is not a genre pack (kind={pack.kind!r})")
    return pack


def load_user_pack(pack_dir: Path) -> Pack:
    pack = load_pack(pack_dir)
    if pack.kind != "user":
        raise ValueError(f"{pack_dir} is not a user pack (kind={pack.kind!r})")
    return pack


def _load_meta(path: Path) -> MetaPage | None:
    meta, _ = _load_meta_and_fm(path)
    return meta


def _load_meta_and_fm(path: Path) -> tuple[MetaPage | None, dict]:
    if not path.is_file():
        return None, {}
    post = frontmatter.load(path)
    fm = dict(post.metadata)
    # Consumed-by-Pack fields live in frontmatter but don't belong on MetaPage.
    for reserved in ("kind", "inherits_genre"):
        fm.pop(reserved, None) if False else None  # keep in fm for Pack-level reading
    meta_fields = {k: v for k, v in fm.items() if k not in {"kind", "inherits_genre"}}
    name = meta_fields.pop("name", None) or path.stem
    return MetaPage(name=name, body=post.content, **meta_fields), fm


def _load_entity_dir(dir_path: Path, model: type[PageBase]) -> list[PageBase]:
    if not dir_path.is_dir():
        return []
    pages: list[PageBase] = []
    for md in sorted(dir_path.glob("*.md")):
        post = frontmatter.load(md)
        meta = dict(post.metadata)
        slug = meta.pop("slug", None) or md.stem
        name = meta.pop("name", None) or slug.replace("_", " ").title()
        meta.pop("category", None)  # derived from model, not input
        pages.append(model(slug=slug, name=name, body=post.content, **meta))
    return pages


def ensure_entity_dirs_exist() -> tuple[str, ...]:
    return tuple(ENTITY_DIRS.keys())
