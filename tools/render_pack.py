"""Render a user pack's wiki-link cross-references into plain Markdown.

Usage:
    python tools/render_pack.py --pack <name>

Canonical pack pages use a wiki-link dialect for cross-references:

    [[slug]]          — bare reference (ASCII-named entity only)
    [[slug|Display]]  — reference with an explicit display label

The slug is the canonical ASCII snake_case id; `Display` is the label a
human reads (typically the entity's native-language `name`). The lint
accepts both forms but **requires** the piped form whenever the target
entity's `name` contains non-ASCII characters — otherwise a bare
`[[xiao_yan]]` in a Chinese pack shows up as unreadable pinyin.

This renderer walks every `*.md` under `packs/<pack>/` (except
`.ingest/` and the renderer's own output directory), expands wiki
links to standard Markdown links, and writes the expanded copies into
`packs/<pack>/_rendered/` mirroring the source layout. The canonical
sources are left untouched so that ingest, lint, and this renderer can
all be re-run idempotently.

Expansion rules:

- `[[slug]]`          → `[<entity.name>](<relative path to slug page>)`
- `[[slug|Display]]`  → `[Display](<relative path to slug page>)`
- Unknown slugs are left verbatim (lint flags them separately).

Exits 0 on success, 2 on usage error.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import frontmatter

_LINK_PATTERN = re.compile(r"\[\[([a-zA-Z0-9_]+)(?:\|([^\]|]+))?\]\]")

_ENTITY_DIRS: tuple[str, ...] = (
    "characters",
    "factions",
    "locations",
    "systems",
    "arcs",
    "events",
)

_SKIP_DIR_PARTS: frozenset[str] = frozenset({".ingest", "_rendered"})


def _collect_entity_index(pack_dir: Path) -> dict[str, tuple[Path, str]]:
    """Return slug → (pack-relative path to the entity page, display name).

    The path is stored relative to `pack_dir`, so rendering can remap
    it into the mirror directory without reasoning about absolute paths.
    Display name is the page's frontmatter `name`, falling back to the
    slug itself if unset.
    """
    index: dict[str, tuple[Path, str]] = {}
    for subdir in _ENTITY_DIRS:
        d = pack_dir / subdir
        if not d.is_dir():
            continue
        for md in sorted(d.glob("*.md")):
            post = frontmatter.load(md)
            slug = str(post.metadata.get("slug") or md.stem)
            name = str(post.metadata.get("name") or slug.replace("_", " ").title())
            index[slug] = (md.relative_to(pack_dir), name)
    return index


def _relative_link(from_file: Path, to_file: Path) -> str:
    """POSIX relative link from `from_file` to `to_file` (both absolute)."""
    rel = os.path.relpath(to_file, from_file.parent)
    return rel.replace(os.sep, "/")


def _render_text(
    text: str,
    source_rel: Path,
    out_root: Path,
    entity_index: dict[str, tuple[Path, str]],
) -> str:
    """Expand wiki-links in `text`. Paths link into the mirror at `out_root`."""
    from_file = out_root / source_rel

    def _replace(m: re.Match) -> str:
        slug = m.group(1)
        display = m.group(2)
        entry = entity_index.get(slug)
        if entry is None:
            return m.group(0)  # unknown slug — leave for lint to flag
        target_rel, name = entry
        label = display if display is not None else name
        target_file = out_root / target_rel
        return f"[{label}]({_relative_link(from_file, target_file)})"

    return _LINK_PATTERN.sub(_replace, text)


def _iter_pack_markdown(pack_dir: Path):
    for md in pack_dir.rglob("*.md"):
        if any(part in _SKIP_DIR_PARTS for part in md.parts):
            continue
        yield md


def render_pack(pack_dir: Path, *, out_dir: Path | None = None) -> int:
    """Render the pack's wiki-link dialect into a _rendered/ mirror.

    Returns the number of files written.
    """
    if not pack_dir.is_dir():
        raise FileNotFoundError(f"pack dir not found: {pack_dir}")
    out_root = (out_dir or (pack_dir / "_rendered")).resolve()
    entity_index = _collect_entity_index(pack_dir)
    written = 0
    for md in _iter_pack_markdown(pack_dir):
        rel = md.relative_to(pack_dir)
        text = md.read_text(encoding="utf-8")
        rendered = _render_text(text, rel, out_root, entity_index)
        dst = out_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(rendered, encoding="utf-8")
        written += 1
    return written


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Render a user pack's wiki-link cross-references into plain Markdown.",
    )
    p.add_argument("--pack", required=True, help="user pack name under packs/")
    p.add_argument("--packs-root", type=Path, default=Path("packs"))
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: packs/<pack>/_rendered).",
    )
    args = p.parse_args(argv)

    pack_dir = args.packs_root / args.pack
    if not pack_dir.is_dir():
        print(f"error: pack dir not found: {pack_dir}", file=sys.stderr)
        return 2
    written = render_pack(pack_dir, out_dir=args.out)
    out_root = (args.out or (pack_dir / "_rendered")).resolve()
    print(f"rendered {written} file(s) from {pack_dir} → {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
