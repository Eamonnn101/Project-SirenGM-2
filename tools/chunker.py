"""Heuristic chapter-splitter for a raw novel text file.

Usage:
    python tools/chunker.py raw/novel/<file>.txt --pack <pack_name>

Writes packs/<pack_name>/.ingest/chunks.jsonl with one JSON object per chunk:
{"id": int, "title": str, "text": str, "start": int}.

The agent reads chunks.jsonl and processes entries one by one during the
extract pass described in playbooks/ingest.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_CHAPTER_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十百千\d]{1,6}[章节回][\s\u3000].*", re.MULTILINE),
    re.compile(r"^Chapter\s+\d+.*", re.MULTILINE),
    re.compile(r"^#\s+.+", re.MULTILINE),
]

DEFAULT_TARGET_CHARS = 3000
MIN_CHUNK_CHARS = 40


@dataclass
class Chunk:
    id: int
    title: str
    text: str
    start: int


def chunk_novel(text: str, *, target_chars: int = DEFAULT_TARGET_CHARS) -> list[Chunk]:
    text = text.replace("\r\n", "\n").strip()
    markers = _find_markers(text)
    if len(markers) >= 2:
        return _split_by_markers(text, markers)
    return _split_by_size(text, target_chars=target_chars)


def write_chunks(pack_dir: Path, chunks: list[Chunk]) -> Path:
    ingest_dir = pack_dir / ".ingest"
    ingest_dir.mkdir(parents=True, exist_ok=True)
    out = ingest_dir / "chunks.jsonl"
    out.write_text(
        "\n".join(json.dumps(asdict(c), ensure_ascii=False) for c in chunks) + "\n",
        encoding="utf-8",
    )
    return out


def _find_markers(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for pat in _CHAPTER_PATTERNS:
        for m in pat.finditer(text):
            found.append((m.start(), m.group(0).strip()))
    found.sort()
    deduped: list[tuple[int, str]] = []
    for pos, title in found:
        if deduped and pos - deduped[-1][0] < 5:
            continue
        deduped.append((pos, title))
    return deduped


def _split_by_markers(text: str, markers: list[tuple[int, str]]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i, (start, title) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        body = text[start:end].strip()
        if len(body) >= MIN_CHUNK_CHARS:
            chunks.append(Chunk(id=len(chunks), title=title, text=body, start=start))
    return chunks


def _split_by_size(text: str, *, target_chars: int) -> list[Chunk]:
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_len = 0
    start_offset = 0
    running_offset = 0
    for para in paragraphs:
        para_len = len(para) + 2
        if buf_len + para_len > target_chars and buf:
            chunks.append(
                Chunk(id=len(chunks), title=f"chunk-{len(chunks)+1}",
                      text="\n\n".join(buf), start=start_offset)
            )
            buf = []
            buf_len = 0
            start_offset = running_offset
        buf.append(para)
        buf_len += para_len
        running_offset += para_len
    if buf:
        chunks.append(
            Chunk(id=len(chunks), title=f"chunk-{len(chunks)+1}",
                  text="\n\n".join(buf), start=start_offset)
        )
    return chunks


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("novel", type=Path, help="path to the raw novel text file (utf-8)")
    p.add_argument("--pack", required=True, help="target pack name under packs/")
    p.add_argument("--target-chars", type=int, default=DEFAULT_TARGET_CHARS)
    p.add_argument("--packs-root", type=Path, default=Path("packs"))
    args = p.parse_args(argv)

    if not args.novel.is_file():
        print(f"error: novel file not found: {args.novel}", file=sys.stderr)
        return 2
    text = args.novel.read_text(encoding="utf-8")
    chunks = chunk_novel(text, target_chars=args.target_chars)
    pack_dir = args.packs_root / args.pack
    out = write_chunks(pack_dir, chunks)
    print(f"wrote {len(chunks)} chunks to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
