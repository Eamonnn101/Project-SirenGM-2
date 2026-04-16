"""Split a novel text file into chunks the extract pass can handle.

Heuristic: find chapter markers like `第一章`, `第 1 章`, `Chapter 1`, or `# ...`
and split there. If no markers are found (or too few), fall back to fixed-size
chunks of ~3000 chars on paragraph boundaries.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

_CHAPTER_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十百千\d]{1,6}[章节回][\s　].*", re.MULTILINE),
    re.compile(r"^Chapter\s+\d+.*", re.MULTILINE),
    re.compile(r"^#\s+.+", re.MULTILINE),
]

DEFAULT_TARGET_CHARS = 3000
# Chapter-marker chunks can be small in short novels; only reject essentially empty ones.
MIN_CHUNK_CHARS = 40


@dataclass
class Chunk:
    id: int
    title: str
    text: str
    start: int  # char offset in original text


def chunk_novel(text: str, *, target_chars: int = DEFAULT_TARGET_CHARS) -> list[Chunk]:
    text = text.replace("\r\n", "\n").strip()
    markers = _find_markers(text)
    if len(markers) >= 2:
        chunks = _split_by_markers(text, markers)
    else:
        chunks = _split_by_size(text, target_chars=target_chars)
    return chunks


def write_chunks(pack_dir: Path, chunks: list[Chunk]) -> Path:
    ingest_dir = pack_dir / ".ingest"
    ingest_dir.mkdir(parents=True, exist_ok=True)
    out = ingest_dir / "chunks.jsonl"
    out.write_text(
        "\n".join(json.dumps(asdict(c), ensure_ascii=False) for c in chunks) + "\n",
        encoding="utf-8",
    )
    return out


def read_chunks(pack_dir: Path) -> list[Chunk]:
    path = pack_dir / ".ingest" / "chunks.jsonl"
    if not path.is_file():
        return []
    return [Chunk(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _find_markers(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for pat in _CHAPTER_PATTERNS:
        for m in pat.finditer(text):
            found.append((m.start(), m.group(0).strip()))
    found.sort()
    # Deduplicate positions that are within 5 chars of each other.
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
            chunks.append(Chunk(id=len(chunks), title=f"chunk-{len(chunks)+1}", text="\n\n".join(buf), start=start_offset))
            buf = []
            buf_len = 0
            start_offset = running_offset
        buf.append(para)
        buf_len += para_len
        running_offset += para_len
    if buf:
        chunks.append(Chunk(id=len(chunks), title=f"chunk-{len(chunks)+1}", text="\n\n".join(buf), start=start_offset))
    return chunks
