"""Per-chunk extract pass: produces structured mentions of entities/events/relationships."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from sirengm.ingest.chunker import Chunk, read_chunks
from sirengm.llm.base import LLMClient, LLMMessage

MentionKind = Literal["character", "faction", "location", "event", "relationship", "system_item"]


class Mention(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: MentionKind
    slug: str
    name: str | None = None
    source_chunk: int
    evidence: str = Field(default="", description="Short quote or paraphrase from the chunk that supports this mention.")
    # kind-specific fields (role, alignment, relation, etc.) go in extras via extra='allow'


class ChunkMentions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: int
    mentions: list[Mention] = Field(default_factory=list)


def run_extract_pass(
    *,
    pack_dir: Path,
    genre_dir: Path,
    llm: LLMClient,
    force: bool = False,
) -> list[Mention]:
    """Run extract for every chunk. Writes `.ingest/mentions.jsonl`."""
    ingest_dir = pack_dir / ".ingest"
    ingest_dir.mkdir(parents=True, exist_ok=True)
    out = ingest_dir / "mentions.jsonl"
    if out.is_file() and not force:
        return _read_mentions(out)

    chunks = read_chunks(pack_dir)
    if not chunks:
        raise RuntimeError(f"No chunks under {pack_dir}/.ingest/ — run the chunk stage first.")

    system_prompt = _build_system_prompt(genre_dir)
    all_mentions: list[Mention] = []
    for chunk in chunks:
        cm = _extract_chunk(chunk, system_prompt=system_prompt, llm=llm)
        all_mentions.extend(cm.mentions)

    out.write_text(
        "\n".join(m.model_dump_json() for m in all_mentions) + "\n",
        encoding="utf-8",
    )
    return all_mentions


def _extract_chunk(chunk: Chunk, *, system_prompt: str, llm: LLMClient) -> ChunkMentions:
    user = (
        f"# Chunk {chunk.id} · {chunk.title}\n\n"
        f"{chunk.text}\n\n"
        f"请按 system prompt 的要求抽取此 chunk 中的 mention。"
        f" `chunk_id` 必须设为 {chunk.id}。"
    )
    return llm.complete_structured(
        [LLMMessage(role="system", content=system_prompt), LLMMessage(role="user", content=user)],
        ChunkMentions,
        tag=f"ingest.extract.{chunk.id}",
    )


def _build_system_prompt(genre_dir: Path) -> str:
    fragment = genre_dir / "prompts" / "ingest_extract_system.md"
    extra = fragment.read_text(encoding="utf-8") if fragment.is_file() else ""
    base = (
        "你是一个从中文小说章节中抽取结构化 mention 的助手。"
        "严格按照下面的 genre-level 指导产出 JSON，遵循输出 schema。"
    )
    return base + ("\n\n---\n\n" + extra if extra else "")


def _read_mentions(path: Path) -> list[Mention]:
    return [Mention.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def group_mentions(mentions: list[Mention]) -> dict[tuple[MentionKind, str], list[Mention]]:
    grouped: dict[tuple[MentionKind, str], list[Mention]] = {}
    for m in mentions:
        grouped.setdefault((m.kind, m.slug), []).append(m)
    return grouped
