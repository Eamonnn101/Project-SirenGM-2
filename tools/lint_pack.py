"""Rule-based lint for a genre or user pack.

Usage:
    python tools/lint_pack.py --genre universal
    python tools/lint_pack.py --pack my_novel_pack

Exits 0 when clean, 1 when issues are found, 2 on usage error.

Genre-pack checks enforce purity: no novel-specific entity pages allowed.
User-pack checks validate genre inheritance and cross-reference integrity.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import cast

import frontmatter

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _models import (
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
else:
    from ._models import (
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


_LINK_PATTERN = re.compile(r"\[\[([a-zA-Z0-9_]+)(?:\|([^\]|]+))?\]\]")


def _has_non_ascii(s: str) -> bool:
    return any(ord(ch) > 127 for ch in s)

# Entity subdirectories.
_ENTITY_MODEL: dict[str, type[PageBase]] = {
    "characters": CharacterPage,
    "factions": FactionPage,
    "locations": LocationPage,
    "systems": SystemPage,
    "arcs": ArcPage,
    "events": EventPage,
}


# ---------------------------------------------------------------------------
# Pack loader (ported from sirengm/pack/loader.py + sirengm/pack/paths.py)
# ---------------------------------------------------------------------------

def load_pack(pack_dir: Path) -> Pack:
    if not pack_dir.is_dir():
        raise FileNotFoundError(f"Pack directory not found: {pack_dir}")

    index_meta, index_fm = _load_meta_and_fm(pack_dir / "index.md")
    kind = cast(PackKind, index_fm.get("kind", "user"))
    inherits_genre = index_fm.get("inherits_genre") if kind == "user" else None
    language = index_fm.get("language")

    return Pack(
        name=pack_dir.name,
        kind=kind,
        inherits_genre=inherits_genre,
        language=language,
        index=index_meta,
        overview=_load_meta(pack_dir / "overview.md"),
        style_guide=_load_meta(pack_dir / "style_guide.md"),
        canon_guardrails=_load_meta(pack_dir / "canon_guardrails.md"),
        timeline=_load_meta(pack_dir / "timeline.md"),
        relationships=_load_meta(pack_dir / "relationships" / "relationship_matrix.md"),
        ambiguities=_load_meta(pack_dir / "contradictions" / "ambiguous_points.md"),
        characters=_load_entity_dir(pack_dir / "characters", CharacterPage),
        factions=_load_entity_dir(pack_dir / "factions", FactionPage),
        locations=_load_entity_dir(pack_dir / "locations", LocationPage),
        systems=_load_entity_dir(pack_dir / "systems", SystemPage),
        arcs=_load_entity_dir(pack_dir / "arcs", ArcPage),
        events=_load_entity_dir(pack_dir / "events", EventPage),
    )


def _load_meta(path: Path) -> MetaPage | None:
    meta, _ = _load_meta_and_fm(path)
    return meta


def _load_meta_and_fm(path: Path) -> tuple[MetaPage | None, dict]:
    if not path.is_file():
        return None, {}
    post = frontmatter.load(path)
    fm = dict(post.metadata)
    meta_fields = {k: v for k, v in fm.items() if k not in {"kind", "inherits_genre", "language"}}
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


# ---------------------------------------------------------------------------
# Lint (ported verbatim from sirengm/lint/pack_lint.py)
# ---------------------------------------------------------------------------

def lint_pack(pack_dir: Path, *, genre_packs_root: Path | None = None) -> list[str]:
    """Returns a list of issue strings. Empty means clean.

    If the pack is a user pack, `genre_packs_root` is used to verify the
    declared genre exists and loads. When omitted, genre existence is only
    checked via the declared field.
    """
    if not pack_dir.is_dir():
        return [f"pack dir not found: {pack_dir}"]
    try:
        pack = load_pack(pack_dir)
    except Exception as e:
        return [f"failed to load pack: {type(e).__name__}: {e}"]

    issues: list[str] = []
    if pack.kind == "genre":
        issues.extend(_lint_genre(pack, pack_dir))
    else:
        issues.extend(_lint_user(pack, pack_dir, genre_packs_root=genre_packs_root))
    return issues


_REQUIRED_GENRE_PROMPTS = (
    "ingest_extract_system.md",
    "ingest_draft_system.md",
    "gm_system_fragment.md",
)


def _lint_genre(pack, pack_dir: Path) -> list[str]:
    issues: list[str] = []
    # Pydantic already rejects genre packs with entity pages; re-check at rule level too.
    for bucket_name, bucket in (
        ("characters", pack.characters),
        ("factions", pack.factions),
        ("locations", pack.locations),
        ("arcs", pack.arcs),
        ("events", pack.events),
    ):
        if bucket:
            issues.append(f"genre pack must not contain {bucket_name}; found {len(bucket)}")
    # Required top-level files.
    for required in ("index.md", "style_guide.md", "canon_guardrails.md"):
        if not (pack_dir / required).is_file():
            issues.append(f"genre pack missing required file: {required}")
    # At least one systems/*.md.
    systems_dir = pack_dir / "systems"
    if not systems_dir.is_dir() or not any(systems_dir.glob("*.md")):
        issues.append("genre pack must provide at least one systems/*.md")
    # At least one schemas/*.schema.md — the schema contracts drive ingest draft.
    schemas_dir = pack_dir / "schemas"
    if not schemas_dir.is_dir() or not any(schemas_dir.glob("*.schema.md")):
        issues.append("genre pack must provide at least one schemas/*.schema.md")
    # Required prompts/ files — the three the playbooks read during ingest + play.
    prompts_dir = pack_dir / "prompts"
    for required in _REQUIRED_GENRE_PROMPTS:
        if not (prompts_dir / required).is_file():
            issues.append(f"genre pack missing required prompt: prompts/{required}")
    return issues


_REQUIRED_USER_PACK_FILES = (
    "index.md",
    "novel_rules.md",
    "overview.md",
    "canon_guardrails.md",
    "timeline.md",
    "progression_rules.md",
    "relationships/relationship_matrix.md",
    "contradictions/ambiguous_points.md",
)

# Sections required in progression_rules.md. Matched by an H2 line
# `## <title>`; subsection order is flexible, but all 7 must appear.
_REQUIRED_PROGRESSION_SECTIONS = (
    ("stages", ("Stages", "境界", "阶段")),
    ("breakthrough_triggers", ("Breakthrough triggers", "Breakthrough Triggers", "破境触机", "破境触发")),
    ("artifacts", ("Artifacts", "Artifact archetypes", "法宝", "法宝类型")),
    ("innate", ("Innate", "Innate traits", "天赋", "天赋类型")),
    ("destiny", ("Destiny", "Destiny traits", "命格", "命格类型")),
    ("health_ladder", ("Health ladder", "Health", "体况", "体况梯度")),
    ("breakthrough_voice", ("Breakthrough voice", "破境笔触", "破境风格")),
)


def _lint_user(pack, pack_dir: Path, *, genre_packs_root: Path | None) -> list[str]:
    issues: list[str] = []
    # Required top-level files — the playbooks assume these exist.
    for relative in _REQUIRED_USER_PACK_FILES:
        if not (pack_dir / relative).is_file():
            issues.append(f"user pack missing required file: {relative}")

    if not pack.inherits_genre:
        issues.append("user pack missing inherits_genre in index.md")
    elif genre_packs_root is not None:
        genre_dir = genre_packs_root / pack.inherits_genre
        if not genre_dir.is_dir():
            issues.append(f"declared genre {pack.inherits_genre!r} not found under {genre_packs_root}/")

    # Must have at least one protagonist.
    if not any(c.role == "protagonist" for c in pack.characters):
        issues.append("no character has role=protagonist")

    # Cross-refs: affiliation, controlled_by, seat, leaders.
    faction_slugs = {f.slug for f in pack.factions}
    character_slugs = {c.slug for c in pack.characters}
    location_slugs = {l.slug for l in pack.locations}

    for c in pack.characters:
        if c.affiliation and c.affiliation not in faction_slugs:
            issues.append(f"character {c.slug!r} references unknown affiliation {c.affiliation!r}")
        if c.location and c.location not in location_slugs:
            issues.append(f"character {c.slug!r} references unknown location {c.location!r}")
    for loc in pack.locations:
        if loc.controlled_by and loc.controlled_by not in faction_slugs:
            issues.append(f"location {loc.slug!r} references unknown controlled_by {loc.controlled_by!r}")
    for f in pack.factions:
        if f.seat and f.seat not in location_slugs:
            issues.append(f"faction {f.slug!r} references unknown seat {f.seat!r}")
        for leader in f.leaders:
            if leader not in character_slugs:
                issues.append(f"faction {f.slug!r} lists unknown leader {leader!r}")
    for arc in pack.arcs:
        for ent in arc.driving_entities:
            if ent not in character_slugs and ent not in faction_slugs:
                issues.append(f"arc {arc.slug!r} lists unknown driving_entity {ent!r}")

    # progression_rules.md section checks (7 required sections).
    issues.extend(_lint_progression_rules(pack_dir))

    # [[wiki-links]] resolution: every link in any body should match an entity slug.
    # We also build a slug → display-name map so we can require a |Display label
    # on references to entities whose canonical name contains non-ASCII characters
    # (otherwise a bare [[xiao_yan]] shows up as unreadable pinyin in prose).
    slug_to_name: dict[str, str] = {}
    for bucket in (pack.characters, pack.factions, pack.locations, pack.systems, pack.arcs, pack.events):
        for page in bucket:
            slug_to_name[page.slug] = page.name
    issues.extend(_scan_wiki_links(pack_dir, slug_to_name))
    return issues


def _lint_progression_rules(pack_dir: Path) -> list[str]:
    """Confirm packs/<pack>/progression_rules.md carries all 7 required
    sections (matching H2 headings or their known zh/en synonyms).

    The file itself is required by _REQUIRED_USER_PACK_FILES. This check
    adds structural validation — a progression_rules.md that parses but
    is missing sections will not serve the turn loop or new-game flow.

    Heading matching is case-insensitive: ingested packs may legitimately
    use natural title case (`## Artifact Archetypes`) and we should not
    reject a compliant file based only on capitalization.
    """
    path = pack_dir / "progression_rules.md"
    if not path.is_file():
        # The required-files check will have flagged the missing file.
        return []
    text = path.read_text(encoding="utf-8")
    # Extract all H2 lines (`## ...`), normalized for case-insensitive
    # substring matching. Lowercasing is a no-op on CJK characters, so
    # zh synonyms like "境界" / "破境触机" still match exactly.
    headings_lower: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            headings_lower.append(line[3:].strip().lower())

    issues: list[str] = []
    for section_key, synonyms in _REQUIRED_PROGRESSION_SECTIONS:
        syns_lower = [syn.lower() for syn in synonyms]
        if not any(any(syn in h for syn in syns_lower) for h in headings_lower):
            issues.append(
                f"progression_rules.md missing required section {section_key!r} "
                f"(expected an H2 heading containing one of: {list(synonyms)})"
            )
    return issues


def _scan_wiki_links(pack_dir: Path, slug_to_name: dict[str, str]) -> list[str]:
    issues: list[str] = []
    known_slugs = set(slug_to_name)
    for md in pack_dir.rglob("*.md"):
        if ".ingest" in md.parts or "_rendered" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        rel = md.relative_to(pack_dir)
        for m in _LINK_PATTERN.finditer(text):
            slug = m.group(1)
            display = m.group(2)
            if slug not in known_slugs:
                raw = m.group(0)
                issues.append(f"{rel}: {raw} does not resolve to any entity slug")
                continue
            name = slug_to_name[slug]
            # If the canonical entity name is non-ASCII (e.g. 萧炎), a bare
            # [[slug]] is unreadable in plain Markdown — require the piped
            # [[slug|Display]] form.
            if display is None and _has_non_ascii(name):
                issues.append(
                    f"{rel}: [[{slug}]] references entity with non-ASCII name "
                    f"{name!r}; use [[{slug}|{name}]] so the pack reads in its "
                    "declared language"
                )
    return issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rule-based lint for a genre or user pack.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--pack", help="user pack name under packs/")
    g.add_argument("--genre", help="genre pack name under genre_packs/")
    p.add_argument("--packs-root", type=Path, default=Path("packs"))
    p.add_argument("--genre-packs-root", type=Path, default=Path("genre_packs"))
    args = p.parse_args(argv)

    if args.pack:
        pack_dir = args.packs_root / args.pack
        issues = lint_pack(pack_dir, genre_packs_root=args.genre_packs_root)
    else:
        pack_dir = args.genre_packs_root / args.genre
        issues = lint_pack(pack_dir)

    if not issues:
        print(f"ok: {pack_dir} has no lint issues")
        return 0
    print(f"{len(issues)} issue(s) in {pack_dir}:")
    for i in issues:
        print(f"  - {i}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
