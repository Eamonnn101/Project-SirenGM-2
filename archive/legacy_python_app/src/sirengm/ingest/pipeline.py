"""Top-level ingest orchestrator: chunk -> extract -> draft -> index+lint."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from rich.console import Console

from sirengm.config import AppConfig
from sirengm.ingest.chunker import chunk_novel, write_chunks
from sirengm.ingest.passes.draft_pages import run_draft_pages_pass
from sirengm.ingest.passes.extract import Mention, run_extract_pass
from sirengm.ingest.passes.index_and_lint import run_index_and_lint_pass
from sirengm.llm.base import LLMClient
from sirengm.llm.factory import build_client

Stage = Literal["chunk", "extract", "draft", "index"]
_ORDER: tuple[Stage, ...] = ("chunk", "extract", "draft", "index")

console = Console()


def run_ingest(
    cfg: AppConfig,
    *,
    novel_path: Path,
    pack_name: str,
    genre: str = "xianxia",
    from_stage: Stage = "chunk",
    force: bool = False,
    llm: LLMClient | None = None,
) -> list[str]:
    """Run the ingest pipeline for one novel. Returns any lint issues from the final stage.

    Pass an explicit `llm` to override the provider built from config (used by tests).
    """
    pack_dir = cfg.packs_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    genre_dir = cfg.root / "genre_packs" / genre
    if not genre_dir.is_dir():
        raise FileNotFoundError(f"Genre pack not found: {genre_dir}")

    stages = _ORDER[_ORDER.index(from_stage):]
    if llm is None:
        llm = build_client(cfg)
    mentions: list[Mention] = []

    if "chunk" in stages:
        console.print(f"[cyan]▶[/] chunk  ← {novel_path}")
        text = novel_path.read_text(encoding="utf-8")
        chunks = chunk_novel(text)
        write_chunks(pack_dir, chunks)
        console.print(f"  {len(chunks)} chunks -> {pack_dir / '.ingest' / 'chunks.jsonl'}")

    if "extract" in stages:
        console.print("[cyan]▶[/] extract")
        mentions = run_extract_pass(pack_dir=pack_dir, genre_dir=genre_dir, llm=llm, force=force)
        console.print(f"  {len(mentions)} mentions -> {pack_dir / '.ingest' / 'mentions.jsonl'}")
    elif "draft" in stages or "index" in stages:
        # Load cached mentions for later stages.
        mentions = _load_mentions(pack_dir)

    if "draft" in stages:
        console.print("[cyan]▶[/] draft pages")
        emitted = run_draft_pages_pass(pack_dir=pack_dir, genre_dir=genre_dir, mentions=mentions, llm=llm)
        total = sum(len(v) for v in emitted.values())
        console.print(f"  wrote {total} entity pages across {len(emitted)} categories")

    if "index" in stages:
        console.print("[cyan]▶[/] index + rule-based lint")
        issues = run_index_and_lint_pass(
            pack_dir=pack_dir,
            pack_name=pack_name,
            genre_name=genre,
            mentions=mentions,
        )
        if issues:
            console.print(f"[yellow]⚠ {len(issues)} lint issue(s):[/]")
            for msg in issues:
                console.print(f"  - {msg}")
        else:
            console.print("[green]✓ lint clean[/]")
        return issues

    return []


def _load_mentions(pack_dir: Path) -> list[Mention]:
    path = pack_dir / ".ingest" / "mentions.jsonl"
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found — run an earlier stage first (`--from extract` or `--from chunk`)."
        )
    return [Mention.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
