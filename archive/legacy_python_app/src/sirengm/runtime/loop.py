"""Play REPL: read player input, run narrator + state updater, persist, repeat.

The loop is kept deliberately small so the two-call turn pattern is obvious.
Each iteration:

    1. Build TurnContext from the current stacked pack + save.
    2. Call narrator -> narration text (shown to player).
    3. Call state updater -> validated StatePatch.
    4. apply_patch (soft-fails log divergences).
    5. Persist structured state + render markdown surfaces.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown

from sirengm.config import AppConfig
from sirengm.llm.base import LLMClient
from sirengm.llm.factory import build_client
from sirengm.pack.stacked import StackedPack, load_stacked
from sirengm.runtime.context import build_context
from sirengm.runtime.narrator import run_narrator
from sirengm.runtime.state_updater import run_state_updater
from sirengm.save import render as render_save
from sirengm.save.models import Save
from sirengm.save.patch import StatePatch, apply_patch
from sirengm.save.store import append_divergence, load_save, persist

console = Console()


def run_play_loop(
    cfg: AppConfig,
    *,
    save_id: str,
    llm: LLMClient | None = None,
    input_fn=None,
    max_turns: int | None = None,
) -> Save:
    """Drive the REPL. Returns the final Save.

    `input_fn` is an injectable prompt hook; defaults to builtin `input`.
    `max_turns` caps the loop for tests; None means loop until /quit or EOF.
    """
    save = load_save(cfg.saves_dir, save_id)
    stacked = load_stacked(cfg.packs_dir / save.pack_name, genre_packs_root=cfg.root / "genre_packs")
    llm = llm or build_client(cfg)
    input_fn = input_fn or _default_input

    _print_welcome(stacked, save)

    turns_run = 0
    while True:
        if max_turns is not None and turns_run >= max_turns:
            break

        line = input_fn("> ")
        if line is None:
            break
        line = line.strip()
        if not line:
            continue
        if line in {"/quit", "/q", "/exit"}:
            break
        if line == "/save":
            persist(cfg.saves_dir, save)
            render_save.render_all(cfg.saves_dir, save)
            console.print("[green]✓ saved[/]")
            continue
        if line == "/inspect":
            from sirengm.runtime.inspect import print_summary

            print_summary(stacked, save)
            continue

        _run_one_turn(cfg, stacked, save, player_input=line, llm=llm)
        turns_run += 1

    # Final persist on exit.
    persist(cfg.saves_dir, save)
    render_save.render_all(cfg.saves_dir, save)
    return save


def _run_one_turn(
    cfg: AppConfig,
    stacked: StackedPack,
    save: Save,
    *,
    player_input: str,
    llm: LLMClient,
) -> None:
    ctx = build_context(stacked, save)
    narration = run_narrator(ctx, player_input, llm=llm)
    console.print()
    console.print(Markdown(narration))
    console.print()

    try:
        patch: StatePatch = run_state_updater(ctx, player_input=player_input, narration=narration, llm=llm)
    except Exception as e:  # broad: Pydantic / provider / parse errors all come here
        from sirengm.save.models import DivergenceNote

        note = DivergenceNote(
            turn=save.world.turn,
            reason="state_updater call failed",
            detail=f"{type(e).__name__}: {e}",
        )
        save.divergences.append(note)
        append_divergence(cfg.saves_dir, save.save_id, note)
        console.print(f"[yellow]⚠ state updater failed: {e}[/]")
        # We still advance the turn with a synthetic session log so the loop can continue.
        from sirengm.save.models import SessionLogEntry

        save.session_log.append(SessionLogEntry(
            turn=save.world.turn,
            player_input=player_input,
            narration=narration,
            summary="[state_updater failure — see divergence_log.md]",
        ))
        save.world.turn += 1
    else:
        divergences = apply_patch(save, patch, stacked)
        for d in divergences:
            append_divergence(cfg.saves_dir, save.save_id, d)

    persist(cfg.saves_dir, save)
    render_save.render_all(cfg.saves_dir, save)


def _default_input(prompt: str) -> str | None:
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        console.print()
        return None


def _print_welcome(stacked: StackedPack, save: Save) -> None:
    console.rule(f"[bold]{stacked.name}[/] · save [cyan]{save.save_id}[/]")
    w = save.world
    console.print(f"turn {w.turn} · {w.time_of_day} · location [cyan]{w.current_location}[/] · risk {w.risk_level}")
    console.print(f"主角: {w.player.name} · {w.player.cultivation_stage}")
    console.print("[dim]输入 /quit 退出，/save 存档，/inspect 查看状态。[/]\n")
