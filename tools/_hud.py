"""HUD rendering helpers for the v0.4 progression layer.

Produces the two-layer text HUD described in the v0.4 plan:

- `render_compact_turn_hud`  — Layer A, written at the top of
  `current_scene.md` every turn.
- `render_full_build_hud`    — Layer B, written into `player.md` and
  mirrored by `inspect_save.py`.

All HUDs render in the pack's declared language (`zh` or `en`) with a
consistent Unicode box grammar. Warning markers surface the 5-state
health ladder + risk level. Alignment uses east-asian visual width so
labels line up in both Chinese and Latin monospace fonts.
"""

from __future__ import annotations

import unicodedata
from typing import Iterable

if __package__ is None or __package__ == "":
    from _models import (  # type: ignore[no-redef]
        PackMetaProgress,
        Save,
        STAGE_INDEX_MAX,
        UNIVERSAL_ARTIFACT_ARCHETYPES,
        UNIVERSAL_DESTINY_ARCHETYPES,
        UNIVERSAL_INNATE_ARCHETYPES,
    )
else:
    from ._models import (
        PackMetaProgress,
        Save,
        STAGE_INDEX_MAX,
        UNIVERSAL_ARTIFACT_ARCHETYPES,
        UNIVERSAL_DESTINY_ARCHETYPES,
        UNIVERSAL_INNATE_ARCHETYPES,
    )


# ---------------------------------------------------------------------------
# Visual-width helpers (CJK-aware)
# ---------------------------------------------------------------------------


def visual_width(s: str) -> int:
    """Return the monospace visual width of `s`, counting CJK glyphs as 2."""
    w = 0
    for ch in s:
        if unicodedata.category(ch).startswith("M"):
            continue
        eaw = unicodedata.east_asian_width(ch)
        w += 2 if eaw in ("W", "F") else 1
    return w


def pad_right(s: str, width: int) -> str:
    gap = width - visual_width(s)
    return s + (" " * gap if gap > 0 else "")


# ---------------------------------------------------------------------------
# Localized labels specific to the HUD layer.
# Extends the render_save.py label table without replacing its keys.
# ---------------------------------------------------------------------------


HUD_LABELS: dict[str, dict[str, str]] = {
    "zh": {
        # Block headers / special lines
        "compact_header": "状态",
        "compact_turn": "第 {turn} 回",
        "compact_time_sep": " · ",
        "build_header": "角色小传",
        "build_artifact_header": "法宝",
        "build_innate_header": "天赋",
        "build_destiny_header": "命格",
        "build_meta_header": "档案",
        "build_meta_coverage": "图鉴",
        "meta_artifact_coverage": "法宝",
        "meta_innate_coverage": "天赋",
        "meta_destiny_coverage": "命格",
        # Field labels
        "hud_stage": "境界",
        "hud_health": "体况",
        "hud_artifact": "法宝",
        "hud_innate": "天赋",
        "hud_destiny": "命格",
        "hud_conflict": "对局",
        "hud_goals": "主目标",
        "hud_threads": "悬念",
        "build_slug": "标识",
        "build_archetype": "类属",
        "build_activation": "效用",
        "build_source_stage": "得于",
        "build_available": "可用",
        "build_exhausted": "已用",
        "build_name": "名号",
        "build_status": "状态",
        "build_affiliation": "所属",
        "build_progression": "修为",
        "build_titles": "称号",
        "build_inventory": "物品",
        "build_stats": "属性",
        # Meta counters
        "meta_runs_started": "开局次数",
        "meta_runs_finished": "完局次数",
        "meta_deaths_count": "陨落次数",
        "meta_best_stage": "最高境界",
        "meta_recent_deaths": "近期陨落",
        # Warning / marker glyphs
        "risk_warn_calm": "",
        "risk_warn_tense": " · ⚠",
        "risk_warn_dangerous": " · ⚠⚠",
        "risk_warn_lethal": " · ☠",
        "health_warn_healthy": "",
        "health_warn_hurt": "",
        "health_warn_badly_hurt": " · ⚠",
        "health_warn_critical": " · ⚠⚠",
        "health_warn_dead": " · ☠",
        "used_marker": " · 已用",
        "exhausted_mark": "*",
        "destiny_sep": "、",
        "innate_sep": " · ",
        "dash": "—",
        "stage_fmt": "〔第 {index}/{max} 境〕",
        # 5-state health ladder — zh voice
        "health_healthy": "健康",
        "health_hurt": "负伤",
        "health_badly_hurt": "重伤",
        "health_critical": "濒死",
        "health_dead": "殒命",
        # Artifact archetype labels
        "artifact_insight": "洞见",
        "artifact_bond_rescue": "援护",
        "artifact_companion": "随行",
        # Innate archetype labels
        "innate_talent": "才华",
        "innate_survival": "坚韧",
        "innate_social": "人情",
        "innate_resource": "缘分",
        "innate_temperament": "性情",
        # Destiny archetype labels (generic zh readings of the universal seeds)
        "destiny_not_meant_to_die": "不该死",
        "destiny_golden_cicada_escape": "金蝉脱壳",
        "destiny_last_barrier": "最后一障",
        "destiny_heaven_piercing_eye": "洞天眼",
        "destiny_learn_from_enemy": "学敌之术",
        "destiny_breakthrough_instinct": "破局之觉",
        "destiny_martial_remnant_resolve": "残躯余勇",
        "destiny_last_stand": "背水一战",
        "destiny_blood_debt": "血债",
        "destiny_little_shadow": "小影",
        "destiny_timely_ally": "及时援",
        "destiny_read_the_room": "观势",
        # Conflict HUD row helpers (reuses existing momentum labels)
        "conflict_momentum_endgame": "收束在即",
        "momentum_setup": "开局",
        "momentum_player_pressing": "你方紧逼",
        "momentum_even": "僵持",
        "momentum_opposition_pressing": "对立方紧逼",
        "momentum_reversal_imminent": "逆转在即",
        "conflict_row_sep": " │ ",
        "stage_unset": "（未定）",
        "artifact_unset": "（未择）",
        "death_entry_fmt": "第 {turn} 回 · 落于 {cause} · {stage}",
    },
    "en": {
        "compact_header": "State",
        "compact_turn": "Turn {turn}",
        "compact_time_sep": " · ",
        "build_header": "Character",
        "build_artifact_header": "Artifact",
        "build_innate_header": "Innate",
        "build_destiny_header": "Destiny",
        "build_meta_header": "Pack Archive",
        "build_meta_coverage": "Coverage",
        "meta_artifact_coverage": "Artifacts",
        "meta_innate_coverage": "Innate",
        "meta_destiny_coverage": "Destiny",
        "hud_stage": "Stage",
        "hud_health": "Health",
        "hud_artifact": "Artifact",
        "hud_innate": "Innate",
        "hud_destiny": "Destiny",
        "hud_conflict": "Conflict",
        "hud_goals": "Goals",
        "hud_threads": "Threads",
        "build_slug": "Slug",
        "build_archetype": "Archetype",
        "build_activation": "Effect",
        "build_source_stage": "Gained at",
        "build_available": "available",
        "build_exhausted": "used",
        "build_name": "Name",
        "build_status": "Status",
        "build_affiliation": "Affiliation",
        "build_progression": "Progression",
        "build_titles": "Titles",
        "build_inventory": "Inventory",
        "build_stats": "Attributes",
        "meta_runs_started": "Runs started",
        "meta_runs_finished": "Runs finished",
        "meta_deaths_count": "Deaths",
        "meta_best_stage": "Best stage",
        "meta_recent_deaths": "Recent deaths",
        "risk_warn_calm": "",
        "risk_warn_tense": " · !",
        "risk_warn_dangerous": " · !!",
        "risk_warn_lethal": " · X",
        "health_warn_healthy": "",
        "health_warn_hurt": "",
        "health_warn_badly_hurt": " · !",
        "health_warn_critical": " · !!",
        "health_warn_dead": " · X",
        "used_marker": " · used",
        "exhausted_mark": "*",
        "destiny_sep": ", ",
        "innate_sep": " · ",
        "dash": "—",
        "stage_fmt": " [Stage {index}/{max}]",
        "health_healthy": "healthy",
        "health_hurt": "hurt",
        "health_badly_hurt": "badly hurt",
        "health_critical": "critical",
        "health_dead": "dead",
        "artifact_insight": "Insight",
        "artifact_bond_rescue": "Bond-Rescue",
        "artifact_companion": "Companion",
        "innate_talent": "Talent",
        "innate_survival": "Survival",
        "innate_social": "Social",
        "innate_resource": "Resource",
        "innate_temperament": "Temperament",
        "destiny_not_meant_to_die": "Not Meant to Die",
        "destiny_golden_cicada_escape": "Cicada Escape",
        "destiny_last_barrier": "Last Barrier",
        "destiny_heaven_piercing_eye": "Piercing Eye",
        "destiny_learn_from_enemy": "Learn from Enemy",
        "destiny_breakthrough_instinct": "Breakthrough Instinct",
        "destiny_martial_remnant_resolve": "Remnant Resolve",
        "destiny_last_stand": "Last Stand",
        "destiny_blood_debt": "Blood Debt",
        "destiny_little_shadow": "Little Shadow",
        "destiny_timely_ally": "Timely Ally",
        "destiny_read_the_room": "Read the Room",
        "conflict_momentum_endgame": "Endgame",
        "momentum_setup": "Setup",
        "momentum_player_pressing": "You pressing",
        "momentum_even": "Even",
        "momentum_opposition_pressing": "Opposition pressing",
        "momentum_reversal_imminent": "Reversal imminent",
        "conflict_row_sep": " | ",
        "stage_unset": "(unset)",
        "artifact_unset": "(unchosen)",
        "death_entry_fmt": "Turn {turn} · fell to {cause} · {stage}",
    },
}


def hud_labels(language: str | None) -> dict[str, str]:
    return HUD_LABELS.get(language or "zh", HUD_LABELS["zh"])


# ---------------------------------------------------------------------------
# Box-drawing primitives
# ---------------------------------------------------------------------------


def _box(rows: list[str], header: str) -> str:
    """Wrap a list of already-laid-out inner rows with a Unicode box.

    Each input row is a string without its own left/right walls; this
    helper adds `║ ` prefix and ` ║` suffix padded to a common width,
    plus `╔═ header ═…═╗` top and `╚═…═╝` bottom rules.
    """
    inner_widths = [visual_width(r) for r in rows]
    # Leave room for 1 leading space + row + trailing spaces.
    content_width = max([*inner_widths, visual_width(header) + 4])
    inner_width = content_width + 2  # ║ {row} ║
    top_dashes = "═" * (inner_width - visual_width(header) - 4)
    top = f"╔═ {header} ═{top_dashes}╗"
    bottom = "╚" + "═" * inner_width + "╝"
    body = [f"║ {pad_right(r, content_width)} ║" for r in rows]
    return "\n".join([top] + body + [bottom])


def _rule(header: str, width: int = 46) -> str:
    """Light-rule section header for the full build HUD."""
    pad = max(4, width - visual_width(header) - 4)
    return f"━ {header} " + "─" * pad


# ---------------------------------------------------------------------------
# Layer A · Compact turn HUD
# ---------------------------------------------------------------------------


def _format_label_value_rows(
    items: Iterable[tuple[str, str]],
) -> list[str]:
    """Format (label, value) pairs into `<label>  │  <value>` strings with
    a shared label-column width."""
    pairs = list(items)
    if not pairs:
        return []
    label_w = max(visual_width(lbl) for lbl, _ in pairs)
    return [f"{pad_right(lbl, label_w)}  │  {val}" for lbl, val in pairs]


def _artifact_row_value(save: Save, L: dict[str, str]) -> str:
    art = save.world.player.artifact
    if art is None:
        return L["artifact_unset"]
    archetype = L.get(f"artifact_{art.archetype}", art.archetype)
    used = L["used_marker"] if art.used else ""
    return f"{art.name}〔{archetype}〕{used}"


def _innate_row_value(save: Save, L: dict[str, str]) -> str:
    traits = save.world.player.innate_traits
    if not traits:
        return L["dash"]
    return L["innate_sep"].join(t.name for t in traits)


def _destiny_row_value(save: Save, L: dict[str, str]) -> str:
    traits = save.world.player.destiny_traits
    if not traits:
        return L["dash"]
    parts = []
    for t in traits:
        mark = L["exhausted_mark"] if t.exhausted else ""
        parts.append(f"{t.name}{mark}")
    return L["destiny_sep"].join(parts)


def _conflict_row_value(save: Save, L: dict[str, str]) -> str:
    w = save.world
    c = w.current_conflict
    if c is None:
        return L["dash"]
    if c.is_endgame(w.turn):
        momentum = L["conflict_momentum_endgame"]
    else:
        momentum = L.get(f"momentum_{c.momentum}", c.momentum)
    return L["conflict_row_sep"].join([c.kind, momentum, c.stake])


def _goals_row_value(save: Save, L: dict[str, str]) -> str:
    objs = save.world.current_objectives
    return "; ".join(objs) if objs else L["dash"]


def _threads_row_value(save: Save, L: dict[str, str]) -> str:
    threads = save.world.active_threads
    return "; ".join(t.title for t in threads) if threads else L["dash"]


def render_compact_turn_hud(save: Save, L: dict[str, str]) -> str:
    """Layer A · compact turn HUD box. Returns a string without trailing newline."""
    w = save.world
    p = w.player

    stage_label = p.stage_label or L["stage_unset"]
    stage_value = stage_label + L["stage_fmt"].format(
        index=p.stage_index, max=STAGE_INDEX_MAX
    )
    health_value = L.get(f"health_{p.health_state}", p.health_state) + L.get(
        f"health_warn_{p.health_state}", ""
    )
    risk_warn = L.get(f"risk_warn_{w.risk_level}", "")
    header = (
        f"{L['compact_header']}"
        f"{L['compact_time_sep']}"
        f"{L['compact_turn'].format(turn=w.turn)}"
        f"{L['compact_time_sep']}{w.time_of_day}"
        f"{risk_warn}"
    )

    pairs: list[tuple[str, str]] = [
        (L["hud_stage"], stage_value),
        (L["hud_health"], health_value),
        (L["hud_artifact"], _artifact_row_value(save, L)),
        (L["hud_innate"], _innate_row_value(save, L)),
        (L["hud_destiny"], _destiny_row_value(save, L)),
        (L["hud_conflict"], _conflict_row_value(save, L)),
        (L["hud_goals"], _goals_row_value(save, L)),
        (L["hud_threads"], _threads_row_value(save, L)),
    ]
    rows = _format_label_value_rows(pairs)
    return _box(rows, header)


# ---------------------------------------------------------------------------
# Layer B · Full build HUD
# ---------------------------------------------------------------------------


def _format_archetype_label(L: dict[str, str], kind: str, archetype: str) -> str:
    """Look up a localized label for an archetype; fall back to the raw key."""
    return L.get(f"{kind}_{archetype}", archetype)


def _render_full_artifact(save: Save, L: dict[str, str]) -> list[str]:
    art = save.world.player.artifact
    lines = [_rule(L["build_artifact_header"])]
    if art is None:
        lines.append(f"  {L['artifact_unset']}")
        return lines
    archetype = _format_archetype_label(L, "artifact", art.archetype)
    availability = L["build_exhausted"] if art.used else L["build_available"]
    lines.append(f"  {art.name}〔{archetype}〕  ·  {availability}")
    lines.append(f"    {L['build_slug']}: `{art.slug}`")
    if art.notes:
        lines.append(f"    {L['build_activation']}: {art.notes}")
    return lines


def _render_full_innate(save: Save, L: dict[str, str]) -> list[str]:
    traits = save.world.player.innate_traits
    lines = [_rule(L["build_innate_header"])]
    if not traits:
        lines.append(f"  {L['dash']}")
        return lines
    for t in traits:
        archetype = _format_archetype_label(L, "innate", t.archetype)
        lines.append(f"  · {t.name}〔{archetype}〕")
        if t.notes:
            lines.append(f"      {t.notes}")
    return lines


def _render_full_destiny(save: Save, L: dict[str, str]) -> list[str]:
    traits = save.world.player.destiny_traits
    lines = [_rule(L["build_destiny_header"])]
    if not traits:
        lines.append(f"  {L['dash']}")
        return lines
    for t in sorted(traits, key=lambda x: (x.source_stage or 0, x.slug)):
        archetype = _format_archetype_label(L, "destiny", t.archetype)
        availability = L["build_exhausted"] if t.exhausted else L["build_available"]
        stage_note = (
            f"{L['build_source_stage']} Stage {t.source_stage}"
            if t.source_stage is not None
            else ""
        )
        head = f"  · {t.name}〔{archetype}〕  ·  {availability}"
        if stage_note:
            head += f"  ·  {stage_note}"
        lines.append(head)
        if t.notes:
            lines.append(f"      {t.notes}")
    return lines


def _render_full_meta(
    meta: PackMetaProgress | None, L: dict[str, str]
) -> list[str]:
    if meta is None:
        return []
    lines = [_rule(L["build_meta_header"])]
    lines.append(
        f"  {L['meta_runs_started']}: {meta.runs_started}   "
        f"{L['meta_runs_finished']}: {meta.runs_finished}   "
        f"{L['meta_deaths_count']}: {meta.deaths_count}"
    )
    lines.append(
        f"  {L['meta_best_stage']}: {meta.best_stage_index}/{STAGE_INDEX_MAX}"
    )
    art_cov = len(set(meta.seen_artifact_archetypes))
    inn_cov = len(set(meta.seen_innate_archetypes))
    dest_cov = len(set(meta.seen_destiny_archetypes))
    lines.append(
        f"  {L['build_meta_coverage']}: "
        f"{L['meta_artifact_coverage']} {art_cov}/{len(UNIVERSAL_ARTIFACT_ARCHETYPES)}  ·  "
        f"{L['meta_innate_coverage']} {inn_cov}/{len(UNIVERSAL_INNATE_ARCHETYPES)}  ·  "
        f"{L['meta_destiny_coverage']} {dest_cov}/{len(UNIVERSAL_DESTINY_ARCHETYPES)}"
    )
    if meta.deaths:
        lines.append(f"  {L['meta_recent_deaths']}:")
        for record in meta.deaths[-3:]:
            stage_label = record.stage_label or f"Stage {record.stage_index}"
            lines.append(
                "    - "
                + L["death_entry_fmt"].format(
                    turn=record.turn,
                    cause=record.cause or L["dash"],
                    stage=stage_label,
                )
            )
    return lines


def render_full_build_hud(
    save: Save,
    L: dict[str, str],
    *,
    meta: PackMetaProgress | None = None,
) -> str:
    """Layer B · full build HUD, suitable for `player.md` and terminal inspection."""
    p = save.world.player
    health_label = L.get(f"health_{p.health_state}", p.health_state) + L.get(
        f"health_warn_{p.health_state}", ""
    )
    stage_label = p.stage_label or L["stage_unset"]
    header_rows = [
        f"{L['build_name']}: {p.name}  (`{p.slug}`)",
        f"{L['hud_stage']}: {stage_label}  [Stage {p.stage_index}/{STAGE_INDEX_MAX}]",
        f"{L['hud_health']}: {health_label}   ·   {L['build_status']}: {p.status}",
    ]
    if p.affiliation:
        header_rows.append(f"{L['build_affiliation']}: {p.affiliation}")
    if p.progression:
        header_rows.append(f"{L['build_progression']}: {p.progression}")
    if p.titles:
        header_rows.append(f"{L['build_titles']}: {', '.join(p.titles)}")
    header_block = _box(header_rows, L["build_header"])

    sections: list[str] = [header_block, ""]
    sections.extend(_render_full_artifact(save, L))
    sections.append("")
    sections.extend(_render_full_innate(save, L))
    sections.append("")
    sections.extend(_render_full_destiny(save, L))

    if p.stats:
        sections.append("")
        sections.append(_rule(L["build_stats"]))
        for key, value in p.stats.items():
            sections.append(f"  {key}: {value}")

    if p.inventory:
        sections.append("")
        sections.append(_rule(L["build_inventory"]))
        for item in p.inventory:
            note = f" — {item.notes}" if item.notes else ""
            sections.append(f"  · {item.name} (`{item.slug}`){note}")

    if meta is not None:
        sections.append("")
        sections.extend(_render_full_meta(meta, L))

    return "\n".join(sections)
