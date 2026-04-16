"""Draft user-pack entity pages from aggregated mentions.

For each unique (kind, slug) in the extracted mentions, the LLM is asked to
produce a schema-conforming frontmatter-and-body draft. The draft passes
through the same Pydantic entity model the runtime uses, guaranteeing the
page survives `load_pack` without surprises.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from sirengm.ingest.passes.extract import Mention, MentionKind, group_mentions
from sirengm.llm.base import LLMClient, LLMMessage
from sirengm.pack.models import (
    ArcPage,
    CharacterPage,
    EventPage,
    FactionPage,
    LocationPage,
    PageBase,
)
from sirengm.pack.paths import PackPaths

# Map mention kind -> (subdir_plural, page_model)
_KIND_TO_TARGET: dict[MentionKind, tuple[str, type[PageBase]]] = {
    "character": ("characters", CharacterPage),
    "faction": ("factions", FactionPage),
    "location": ("locations", LocationPage),
    "event": ("events", EventPage),
}


class DraftPageResponse(BaseModel):
    """What the LLM returns for one entity's page draft."""

    model_config = ConfigDict(extra="allow")

    slug: str
    name: str
    body: str = ""
    # extra fields go into the entity page's allowed extras / required frontmatter slots


def run_draft_pages_pass(
    *,
    pack_dir: Path,
    genre_dir: Path,
    mentions: list[Mention],
    llm: LLMClient,
) -> dict[str, list[PageBase]]:
    """Write pages into pack_dir and return them grouped by category for further processing.

    Skips any mention kinds that aren't in _KIND_TO_TARGET (e.g. 'relationship' and
    'system_item' are handled at the index+relationships pass, not as pages).
    """
    grouped = group_mentions(mentions)
    system_prompt = _build_system_prompt(genre_dir)
    paths = PackPaths(pack_dir)

    emitted: dict[str, list[PageBase]] = {}
    for (kind, slug), kind_mentions in grouped.items():
        if kind not in _KIND_TO_TARGET:
            continue
        subdir, model = _KIND_TO_TARGET[kind]
        draft = _draft_one(kind=kind, slug=slug, mentions=kind_mentions, system_prompt=system_prompt, llm=llm)
        page = _draft_to_page(draft, model=model, kind=kind)
        dir_path = paths.entity_dir(subdir)
        dir_path.mkdir(parents=True, exist_ok=True)
        _write_entity_page(dir_path / f"{page.slug}.md", page)
        emitted.setdefault(subdir, []).append(page)
    return emitted


def _draft_one(
    *,
    kind: MentionKind,
    slug: str,
    mentions: list[Mention],
    system_prompt: str,
    llm: LLMClient,
) -> DraftPageResponse:
    evidence_lines = "\n".join(
        f"- [chunk {m.source_chunk}] {m.evidence}"
        + _fmt_extra_fields(m)
        for m in mentions
    )
    user = (
        f"# 实体 {kind} · slug={slug}\n\n"
        f"下列是原文中关于此实体的所有 mentions。请综合产出一份 user-pack 的 frontmatter + body 草稿。\n\n"
        f"{evidence_lines}\n\n"
        f"要求：返回 JSON，字段至少包含 `slug`, `name`, `body`。其他可选字段按 genre schema 填入（role/alignment/danger/...）。"
    )
    return llm.complete_structured(
        [LLMMessage(role="system", content=system_prompt), LLMMessage(role="user", content=user)],
        DraftPageResponse,
        tag=f"ingest.draft.{kind}.{slug}",
    )


def _fmt_extra_fields(m: Mention) -> str:
    extras = {k: v for k, v in m.model_dump().items() if k not in {"kind", "slug", "name", "source_chunk", "evidence"}}
    if not extras:
        return ""
    return " " + ", ".join(f"{k}={v!r}" for k, v in extras.items())


def _draft_to_page(draft: DraftPageResponse, *, model: type[PageBase], kind: str) -> PageBase:
    data = draft.model_dump()
    # `kind` as a Pydantic field conflicts with the per-model category discriminator.
    data.pop("category", None)
    extras = {k: v for k, v in data.items() if k not in {"slug", "name", "body"}}
    return model(slug=data["slug"], name=data["name"], body=data.get("body", ""), **extras)


def _write_entity_page(path: Path, page: PageBase) -> None:
    import frontmatter

    payload = page.model_dump(exclude={"body"})
    # Drop None fields for tidy frontmatter.
    payload = {k: v for k, v in payload.items() if v is not None}
    post = frontmatter.Post(page.body, **payload)
    path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")


def _build_system_prompt(genre_dir: Path) -> str:
    fragment = genre_dir / "prompts" / "ingest_draft_system.md"
    extra = fragment.read_text(encoding="utf-8") if fragment.is_file() else ""
    base = (
        "你把一个实体的多个 mention 汇总为一份 user-pack 页面草稿。"
        "不臆造原文没有的信息。严格按 genre 的 schema 产出 JSON。"
    )
    return base + ("\n\n---\n\n" + extra if extra else "")
