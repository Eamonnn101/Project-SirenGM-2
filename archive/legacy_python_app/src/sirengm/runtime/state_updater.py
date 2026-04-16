"""State updater call: derives a validated StatePatch from the turn's events."""

from __future__ import annotations

from sirengm.llm.base import LLMClient, LLMMessage
from sirengm.runtime.context import TurnContext
from sirengm.save.patch import StatePatch


def run_state_updater(
    ctx: TurnContext,
    *,
    player_input: str,
    narration: str,
    llm: LLMClient,
) -> StatePatch:
    messages = [
        LLMMessage(role="system", content=ctx.state_updater_system_prompt),
        LLMMessage(role="user", content=_user_payload(ctx, player_input, narration)),
    ]
    return llm.complete_structured(messages, StatePatch, tag="state_updater")


def _user_payload(ctx: TurnContext, player_input: str, narration: str) -> str:
    w = ctx.save.world
    known = sorted(ctx.stacked.all_entity_slugs())
    parts = [
        "# 已知实体 slug 列表",
        "以下是 stacked pack 中的合法 slug。任何 `present_entities` / `current_location` / `relationships` 的 key 若不在此列且不以 `emergent:` 开头，请 drop 并写入 `divergences`。",
        ", ".join(known),
        "",
        "# 当前结构化状态",
        f"- turn (即将更新的回合号): {w.turn}",
        f"- current_location: {w.current_location}",
        f"- present_entities: {w.present_entities}",
        f"- active_threads: {[t.id for t in w.active_threads]}",
        f"- current_objectives: {w.current_objectives}",
        f"- risk_level: {w.risk_level}",
        f"- player.cultivation_stage: {w.player.cultivation_stage}",
        f"- player.status: {w.player.status}",
        "",
        "# 本回合玩家输入",
        player_input.strip(),
        "",
        "# 本回合 GM 叙事",
        narration.strip(),
        "",
        "请产出 StatePatch JSON。必填：`session_log_entry`。其余字段按需填写；不变则省略。",
    ]
    return "\n".join(parts)
