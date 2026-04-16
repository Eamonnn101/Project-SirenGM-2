"""Final ingest pass: build index.md, relationship_matrix, ambiguities, and run basic lint.

This stage is **rule-based**. It reads what draft_pages wrote, composes a
listing index, a relationship matrix derived from mention `kind=relationship`,
and an ambiguities stub that records any conflicting mentions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import frontmatter

from sirengm.ingest.passes.extract import Mention, MentionKind
from sirengm.pack.loader import load_user_pack
from sirengm.pack.models import Pack
from sirengm.pack.paths import ENTITY_DIRS, PackPaths


def run_index_and_lint_pass(
    *,
    pack_dir: Path,
    pack_name: str,
    genre_name: str,
    mentions: list[Mention],
) -> list[str]:
    """Write index.md, relationship_matrix.md, ambiguous_points.md, timeline.md.

    Returns a list of rule-based lint issues (empty means "clean").
    """
    paths = PackPaths(pack_dir)
    _write_index_md(paths.index, pack_name=pack_name, genre_name=genre_name, pack_dir=pack_dir)
    _write_relationship_matrix(paths.relationships, mentions)
    _write_ambiguities(paths.ambiguities, mentions)
    _write_timeline_stub(paths.timeline, pack_name)

    # Reload and basic-lint the fresh pack.
    pack = load_user_pack(pack_dir)
    return _basic_lint(pack)


# --- Writers --------------------------------------------------------------


def _write_index_md(path: Path, *, pack_name: str, genre_name: str, pack_dir: Path) -> None:
    lines: list[str] = [
        "---",
        f"name: {pack_name}",
        "kind: user",
        f"inherits_genre: {genre_name}",
        "---",
        "",
        f"# Pack · {pack_name}",
        "",
        f"由 `sirengm ingest` 自动生成，继承 genre 模板 `{genre_name}`。",
        "",
    ]
    for subdir in ENTITY_DIRS:
        md_files = sorted((pack_dir / subdir).glob("*.md"))
        if not md_files:
            continue
        lines.append(f"## {subdir}")
        lines.append("")
        for md in md_files:
            slug, name = _slug_and_name(md)
            lines.append(f"- [{name}]({subdir}/{md.name}) · `{slug}`")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_relationship_matrix(path: Path, mentions: list[Mention]) -> None:
    rels = [m for m in mentions if m.kind == "relationship"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rels:
        path.write_text(
            "---\nname: relationship_matrix\n---\n\n# 关系矩阵\n\n_(ingest 未抽取到关系；可稍后手工补充)_\n",
            encoding="utf-8",
        )
        return

    lines = ["---", "name: relationship_matrix", "---", "", "# 关系矩阵", "", "| from | to | kind | notes |", "|---|---|---|---|"]
    for m in rels:
        extras = m.model_dump()
        lines.append(
            f"| {extras.get('from', '?')} | {extras.get('to', '?')} | {extras.get('relation', '?')} | chunk {m.source_chunk}: {m.evidence} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_ambiguities(path: Path, mentions: list[Mention]) -> None:
    # Group by (kind, slug) and record conflicting fields.
    by_key: dict[tuple[str, str], list[Mention]] = {}
    for m in mentions:
        by_key.setdefault((m.kind, m.slug), []).append(m)
    conflicts: list[str] = []
    for (kind, slug), group in by_key.items():
        if len(group) < 2:
            continue
        for field in ("cultivation_stage", "status", "alignment", "danger", "role", "sect"):
            values = {str(getattr(m, field, None)) for m in group if getattr(m, field, None) is not None}
            if len(values) > 1:
                conflicts.append(f"- `{kind}:{slug}` — 字段 `{field}` 值矛盾：{', '.join(sorted(values))}")

    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", "name: ambiguous_points", "---", "", "# 模糊点与矛盾点", ""]
    if conflicts:
        lines.append("## 从 ingest 抽取中检测到的矛盾")
        lines.append("")
        lines.extend(conflicts)
    else:
        lines.append("_(ingest 未检测到显著矛盾)_")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_timeline_stub(path: Path, pack_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: timeline\n---\n\n# 时间线\n\n_(ingest 尚未提取细粒度时间线。{pack_name} 的关键事件待玩家推进。)_\n",
        encoding="utf-8",
    )


# --- Basic lint -----------------------------------------------------------


def _basic_lint(pack: Pack) -> list[str]:
    issues: list[str] = []
    if pack.kind != "user":
        issues.append(f"pack.kind should be 'user', got {pack.kind!r}")
    if not pack.inherits_genre:
        issues.append("pack.inherits_genre is required for user packs")
    if not any(c.role == "protagonist" for c in pack.characters):
        issues.append("no character has role=protagonist")
    # Every sect referenced by a character must exist among factions.
    faction_slugs = {f.slug for f in pack.factions}
    for c in pack.characters:
        if c.sect and c.sect not in faction_slugs:
            issues.append(f"character {c.slug!r} references unknown sect {c.sect!r}")
    # Every location controlled_by must exist among factions.
    for loc in pack.locations:
        if loc.controlled_by and loc.controlled_by not in faction_slugs:
            issues.append(f"location {loc.slug!r} references unknown controlled_by {loc.controlled_by!r}")
    return issues


def _slug_and_name(md: Path) -> tuple[str, str]:
    post = frontmatter.load(md)
    fm = dict(post.metadata)
    slug = fm.get("slug") or md.stem
    name = fm.get("name") or slug
    return slug, name
