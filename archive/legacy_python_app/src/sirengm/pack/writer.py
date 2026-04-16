"""Write a Pack object out to a directory as Markdown+frontmatter files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter

from sirengm.pack.models import MetaPage, Pack, PageBase
from sirengm.pack.paths import ENTITY_DIRS, PackPaths


def write_pack(pack: Pack, pack_dir: Path) -> None:
    pack_dir.mkdir(parents=True, exist_ok=True)
    paths = PackPaths(pack_dir)

    # index.md carries the pack-level kind + inherits_genre in frontmatter.
    _write_index(paths.index, pack)
    _write_meta(paths.overview, pack.overview)
    _write_meta(paths.style_guide, pack.style_guide)
    _write_meta(paths.canon_guardrails, pack.canon_guardrails)
    _write_meta(paths.timeline, pack.timeline)
    _write_meta(paths.relationships, pack.relationships)
    _write_meta(paths.ambiguities, pack.ambiguities)

    _write_entity_dir(paths.entity_dir("characters"), pack.characters)
    _write_entity_dir(paths.entity_dir("factions"), pack.factions)
    _write_entity_dir(paths.entity_dir("locations"), pack.locations)
    _write_entity_dir(paths.entity_dir("systems"), pack.systems)
    _write_entity_dir(paths.entity_dir("arcs"), pack.arcs)
    _write_entity_dir(paths.entity_dir("events"), pack.events)


def _write_index(path: Path, pack: Pack) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    base = pack.index.model_dump(exclude={"body"}) if pack.index else {"name": pack.name}
    base = _dict_drop_empty(base)
    base["kind"] = pack.kind
    if pack.inherits_genre:
        base["inherits_genre"] = pack.inherits_genre
    body = pack.index.body if pack.index else f"# {pack.name}\n"
    _dump_page(path, base, body)


def _write_meta(path: Path, meta: MetaPage | None) -> None:
    if meta is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = _dict_drop_empty(meta.model_dump(exclude={"body"}))
    _dump_page(path, fm, meta.body)


def _write_entity_dir(dir_path: Path, pages: list[PageBase]) -> None:
    if not pages:
        return
    dir_path.mkdir(parents=True, exist_ok=True)
    for page in pages:
        payload = page.model_dump(exclude={"body"})
        body = page.body
        _dump_page(dir_path / f"{page.slug}.md", payload, body)


def _dump_page(path: Path, fm_data: dict[str, Any], body: str) -> None:
    post = frontmatter.Post(body, **fm_data)
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")


def _dict_drop_empty(d: dict[str, Any]) -> dict[str, Any]:
    """Drop None values so frontmatter stays tidy; empty strings/lists are kept."""
    return {k: v for k, v in d.items() if v is not None}


def scaffold_empty_pack(pack_dir: Path, name: str | None = None) -> None:
    """Create an empty pack directory with all expected subdirs and placeholder meta files."""
    pack_dir.mkdir(parents=True, exist_ok=True)
    for sub in ENTITY_DIRS:
        (pack_dir / sub).mkdir(exist_ok=True)
    (pack_dir / "relationships").mkdir(exist_ok=True)
    (pack_dir / "contradictions").mkdir(exist_ok=True)
    _write_meta(pack_dir / "index.md", MetaPage(name=name or pack_dir.name, body="# Index\n\nEmpty pack.\n"))
