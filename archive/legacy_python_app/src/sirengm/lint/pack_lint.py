"""Rule-based pack lint. Handles both genre and user packs.

Genre-pack checks enforce purity: no novel-specific entity pages allowed.
User-pack checks validate genre inheritance and cross-reference integrity.
"""

from __future__ import annotations

import re
from pathlib import Path

from sirengm.pack.loader import load_pack

_LINK_PATTERN = re.compile(r"\[\[([a-zA-Z0-9_]+)\]\]")


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
    # Required files present.
    for required in ("style_guide.md", "canon_guardrails.md"):
        if not (pack_dir / required).is_file():
            issues.append(f"genre pack missing required file: {required}")
    # At least one of systems/cultivation.md / social_rules.md should be present.
    systems_dir = pack_dir / "systems"
    if not systems_dir.is_dir() or not any(systems_dir.glob("*.md")):
        issues.append("genre pack should provide at least one systems/*.md")
    return issues


def _lint_user(pack, pack_dir: Path, *, genre_packs_root: Path | None) -> list[str]:
    issues: list[str] = []
    if not pack.inherits_genre:
        issues.append("user pack missing inherits_genre in index.md")
    elif genre_packs_root is not None:
        genre_dir = genre_packs_root / pack.inherits_genre
        if not genre_dir.is_dir():
            issues.append(f"declared genre {pack.inherits_genre!r} not found under {genre_packs_root}/")

    # Must have at least one protagonist.
    if not any(c.role == "protagonist" for c in pack.characters):
        issues.append("no character has role=protagonist")

    # Cross-refs: sect, controlled_by, seat, leaders.
    faction_slugs = {f.slug for f in pack.factions}
    character_slugs = {c.slug for c in pack.characters}
    location_slugs = {l.slug for l in pack.locations}

    for c in pack.characters:
        if c.sect and c.sect not in faction_slugs:
            issues.append(f"character {c.slug!r} references unknown sect {c.sect!r}")
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

    # [[wiki-links]] resolution: every link in any body should match an entity slug.
    all_slugs = character_slugs | faction_slugs | location_slugs | {s.slug for s in pack.systems} | {a.slug for a in pack.arcs} | {e.slug for e in pack.events}
    issues.extend(_scan_wiki_links(pack_dir, all_slugs))
    return issues


def _scan_wiki_links(pack_dir: Path, known_slugs: set[str]) -> list[str]:
    issues: list[str] = []
    for md in pack_dir.rglob("*.md"):
        if ".ingest" in md.parts:
            continue
        text = md.read_text(encoding="utf-8")
        for m in _LINK_PATTERN.finditer(text):
            slug = m.group(1)
            if slug not in known_slugs:
                rel = md.relative_to(pack_dir)
                issues.append(f"{rel}: [[{slug}]] does not resolve to any entity slug")
    return issues
