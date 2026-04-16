"""Narrator call: produces GM narration for one turn.

Input:   TurnContext + player input.
Output:  free-form narration (Chinese markdown string).

The narrator does NOT modify state. The state updater is a separate call.
"""

from __future__ import annotations

from sirengm.llm.base import LLMClient, LLMMessage
from sirengm.pack.models import PageBase
from sirengm.runtime.context import TurnContext


def run_narrator(ctx: TurnContext, player_input: str, *, llm: LLMClient) -> str:
    messages = [
        LLMMessage(role="system", content=ctx.gm_system_prompt + "\n\n---\n\n" + ctx.style_guide_body + "\n\n" + ctx.canon_guardrails_body),
        LLMMessage(role="user", content=_user_payload(ctx, player_input)),
    ]
    resp = llm.complete(messages, tag="narrator")
    return resp.text.strip()


def _user_payload(ctx: TurnContext, player_input: str) -> str:
    w = ctx.save.world
    parts: list[str] = []
    if ctx.overview_body.strip():
        parts.append("# 剧情包概要\n\n" + ctx.overview_body)

    # Structured state snapshot (canonical)
    parts.append(
        "# 结构化状态\n\n"
        f"- turn: {w.turn}\n"
        f"- day: {w.day}\n"
        f"- time_of_day: {w.time_of_day}\n"
        f"- current_location: {w.current_location}\n"
        f"- present_entities: {', '.join(w.present_entities) if w.present_entities else '（空）'}\n"
        f"- active_threads: {', '.join(t.id for t in w.active_threads) if w.active_threads else '（空）'}\n"
        f"- current_objectives: {w.current_objectives or '（空）'}\n"
        f"- risk_level: {w.risk_level}\n"
        f"- player: {w.player.name} · {w.player.cultivation_stage} · 宗门: {w.player.sect or '无'} · 状态: {w.player.status}"
    )

    # Pack pages for everything in scene
    if ctx.location_page is not None:
        parts.append(f"# 当前地点: {ctx.location_page.name} (`{ctx.location_page.slug}`)\n\n" + ctx.location_page.body)
    for page in ctx.present_pages:
        parts.append(f"# 在场: {page.name} (`{page.slug}`)\n\n{page.body}")
    for page in ctx.arc_pages:
        parts.append(f"# Arc: {page.name} (`{page.slug}`)\n\n{page.body}")

    if ctx.recent_log:
        parts.append(
            "# 最近回合\n\n"
            + "\n\n".join(
                f"## turn {e.turn}\n玩家: {e.player_input}\n\nGM: {e.narration}"
                for e in ctx.recent_log
            )
        )

    parts.append(f"# 玩家本回合输入\n\n{player_input.strip()}\n\n请按风格指南输出本回合的叙事。")
    return "\n\n".join(parts)


def _page_brief(page: PageBase) -> str:
    body = page.body.strip().splitlines()
    preview = "\n".join(body[:10])
    return f"`{page.slug}` ({page.name})\n{preview}"
