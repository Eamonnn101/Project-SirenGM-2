"""New-game wizard: build the initial Save from a stacked pack + player inputs."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from sirengm.config import AppConfig
from sirengm.pack.models import CharacterPage
from sirengm.pack.stacked import StackedPack, load_stacked
from sirengm.save import render as render_save
from sirengm.save.models import PlayerState
from sirengm.save.store import new_save

console = Console()


def _find_protagonist(stacked: StackedPack) -> CharacterPage:
    for c in stacked.user.characters:
        if c.role == "protagonist":
            return c
    raise RuntimeError(
        f"User pack {stacked.name!r} has no character with role=protagonist. "
        f"Check packs/{stacked.name}/characters/."
    )


def build_initial_save(
    cfg: AppConfig,
    *,
    pack_name: str,
    save_id: str,
    player_name_override: str | None = None,
    starting_location_override: str | None = None,
) -> None:
    """Non-interactive save creation. Useful for tests and for the CLI wizard."""
    user_pack_dir = cfg.packs_dir / pack_name
    if not user_pack_dir.is_dir():
        raise FileNotFoundError(
            f"User pack not found: {user_pack_dir}. "
            f"Run `sirengm ingest ... --pack {pack_name}` first, or use an existing pack."
        )
    genre_root = _genre_packs_root(cfg.root)
    stacked = load_stacked(user_pack_dir, genre_packs_root=genre_root)

    protagonist = _find_protagonist(stacked)
    player = PlayerState(
        slug=protagonist.slug,
        name=player_name_override or protagonist.name,
        sect=protagonist.sect,
        cultivation_stage=protagonist.cultivation_stage or "气感期一层",
    )

    starting_location = (
        starting_location_override
        or protagonist.location
        or _first_location_slug(stacked)
        or protagonist.slug
    )
    save = new_save(
        cfg.saves_dir,
        save_id=save_id,
        pack_name=pack_name,
        player=player,
        starting_location=starting_location,
        starting_entities=[protagonist.slug],
        starting_objective="熟悉" + (stacked.user.overview.name if stacked.user.overview else "所处世界"),
    )
    render_save.render_all(cfg.saves_dir, save)


def run_new_game_wizard(cfg: AppConfig, *, pack_name: str, save_id: str) -> None:
    user_pack_dir = cfg.packs_dir / pack_name
    if not user_pack_dir.is_dir():
        raise typer.BadParameter(
            f"User pack not found at {user_pack_dir}. Run `sirengm ingest` first."
        )
    genre_root = _genre_packs_root(cfg.root)
    stacked = load_stacked(user_pack_dir, genre_packs_root=genre_root)
    protagonist = _find_protagonist(stacked)

    console.rule(f"[bold cyan]新建存档 · {pack_name} → {save_id}[/]")
    console.print(f"剧情包：[cyan]{stacked.name}[/] (genre: {stacked.genre_name})")
    console.print(f"主角：[green]{protagonist.name}[/] · {protagonist.cultivation_stage or '气感期一层'} · 宗门: {protagonist.sect or '无'}")

    player_name = typer.prompt("玩家名 (回车使用剧情包中的主角名)", default=protagonist.name, show_default=True)
    default_loc = protagonist.location or _first_location_slug(stacked) or protagonist.slug
    start_loc = typer.prompt("起始地点 slug", default=default_loc, show_default=True)

    build_initial_save(
        cfg,
        pack_name=pack_name,
        save_id=save_id,
        player_name_override=player_name,
        starting_location_override=start_loc,
    )
    console.print(f"[green]✓[/] 存档已创建于 saves/{save_id}/")
    console.print(f"[dim]运行 `sirengm play --save {save_id}` 开始游玩。[/]")


def _first_location_slug(stacked: StackedPack) -> str | None:
    for loc in stacked.user.locations:
        return loc.slug
    return None


def _genre_packs_root(project_root: Path) -> Path:
    return project_root / "genre_packs"
