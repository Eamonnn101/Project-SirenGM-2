"""`sirengm inspect` — print a compact summary of the save's structured state."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from sirengm.config import AppConfig
from sirengm.pack.stacked import StackedPack, load_stacked
from sirengm.save.models import Save
from sirengm.save.store import load_save

console = Console()


def render_save_summary(cfg: AppConfig, *, save_id: str) -> None:
    save = load_save(cfg.saves_dir, save_id)
    stacked = load_stacked(cfg.packs_dir / save.pack_name, genre_packs_root=cfg.root / "genre_packs")
    print_summary(stacked, save)


def print_summary(stacked: StackedPack, save: Save) -> None:
    w = save.world
    console.rule(f"[bold]{save.save_id}[/] · pack [cyan]{stacked.name}[/] (genre: {stacked.genre_name})")

    t = Table(show_header=False, box=None, pad_edge=False)
    t.add_column("k", style="dim")
    t.add_column("v")
    t.add_row("turn", f"{w.turn}  day {w.day}  {w.time_of_day}")
    t.add_row("location", w.current_location)
    t.add_row("risk", w.risk_level)
    t.add_row("present", ", ".join(w.present_entities) or "(空)")
    t.add_row("threads", ", ".join(t.id for t in w.active_threads) or "(空)")
    t.add_row("objectives", "; ".join(w.current_objectives) or "(空)")
    console.print(t)

    console.print()
    pt = Table(title="玩家", show_header=True, header_style="bold")
    pt.add_column("field")
    pt.add_column("value")
    pt.add_row("name", w.player.name)
    pt.add_row("cultivation", w.player.cultivation_stage)
    pt.add_row("sect", w.player.sect or "—")
    pt.add_row("status", w.player.status)
    pt.add_row("inventory", ", ".join(i.name for i in w.player.inventory) or "(空)")
    console.print(pt)

    if save.relationships.by_slug:
        rt = Table(title="关系", show_header=True, header_style="bold")
        rt.add_column("slug")
        rt.add_column("affinity")
        rt.add_column("trust")
        rt.add_column("status")
        rt.add_column("last turn")
        for slug, rel in save.relationships.by_slug.items():
            rt.add_row(slug, str(rel.affinity), str(rel.trust), rel.status, str(rel.last_interaction_turn or "—"))
        console.print(rt)

    if save.open_loops.items:
        lt = Table(title="Open loops", show_header=True, header_style="bold")
        lt.add_column("id")
        lt.add_column("title")
        lt.add_column("status")
        lt.add_column("opened")
        lt.add_column("closed")
        for l in save.open_loops.items:
            lt.add_row(l.id, l.title, l.status, str(l.opened_turn), str(l.closed_turn or "—"))
        console.print(lt)

    if save.session_log:
        console.print()
        last = save.session_log[-1]
        console.print(f"[dim]last narration (turn {last.turn}):[/]")
        console.print(last.narration)
