"""Typer entry point for `sirengm`.

Subcommand bodies live in their respective modules under sirengm.runtime / .ingest /
.lint / .save and are wired in as imports grow. The CLI itself stays thin.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from sirengm.config import load_config

app = typer.Typer(
    name="sirengm",
    help="llm-wiki-style xianxia text-game MVP.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.command()
def version() -> None:
    """Print version and resolved config."""
    from sirengm import __version__

    cfg = load_config()
    console.print(f"sirengm {__version__}")
    console.print(f"  root     = {cfg.root}")
    console.print(f"  provider = {cfg.provider}")


@app.command("new-game")
def new_game(
    pack: str = typer.Option(..., "--pack", help="Pack name under packs/."),
    save: str = typer.Option("save_001", "--save", help="Save id under saves/."),
) -> None:
    """Create a new save by running the player-creation wizard."""
    from sirengm.runtime.new_game import run_new_game_wizard

    cfg = load_config()
    run_new_game_wizard(cfg, pack_name=pack, save_id=save)


@app.command()
def play(
    save: str = typer.Option(..., "--save", help="Save id under saves/."),
) -> None:
    """Enter the play REPL against an existing save."""
    from sirengm.runtime.loop import run_play_loop

    cfg = load_config()
    run_play_loop(cfg, save_id=save)


@app.command()
def load(
    save: str = typer.Option(..., "--save", help="Save id under saves/."),
) -> None:
    """Alias for `play` — resume an existing save."""
    from sirengm.runtime.loop import run_play_loop

    cfg = load_config()
    run_play_loop(cfg, save_id=save)


@app.command()
def inspect(
    save: str = typer.Option(..., "--save", help="Save id under saves/."),
) -> None:
    """Print a compact summary of the save's structured state."""
    from sirengm.runtime.inspect import render_save_summary

    cfg = load_config()
    render_save_summary(cfg, save_id=save)


@app.command()
def ingest(
    novel_path: Path = typer.Argument(..., exists=True, readable=True, help="Raw novel text file."),
    pack: str = typer.Option(..., "--pack", help="Target pack name (created under packs/)."),
    from_stage: str = typer.Option(
        "chunk",
        "--from",
        help="Stage to start from: chunk | extract | draft | index.",
    ),
    force: bool = typer.Option(False, "--force", help="Re-run stages even if outputs exist."),
) -> None:
    """Compile a novel into a Story Pack (multi-pass, resumable)."""
    from sirengm.ingest.pipeline import run_ingest

    cfg = load_config()
    run_ingest(cfg, novel_path=novel_path, pack_name=pack, from_stage=from_stage, force=force)


@app.command("lint-pack")
def lint_pack_cmd(
    pack: str | None = typer.Option(None, "--pack", help="User pack name under packs/."),
    genre: str | None = typer.Option(None, "--genre", help="Genre pack name under genre_packs/."),
) -> None:
    """Run rule-based pack consistency checks on a user or genre pack."""
    from sirengm.lint.pack_lint import lint_pack

    cfg = load_config()
    if (pack is None) == (genre is None):
        raise typer.BadParameter("Specify exactly one of --pack or --genre.")
    if pack is not None:
        issues = lint_pack(cfg.packs_dir / pack, genre_packs_root=cfg.root / "genre_packs")
        label = f"pack:{pack}"
    else:
        issues = lint_pack(cfg.root / "genre_packs" / genre)
        label = f"genre:{genre}"
    _print_issues(issues, label=label)
    raise typer.Exit(code=1 if issues else 0)


@app.command("lint-save")
def lint_save_cmd(save: str = typer.Option(..., "--save", help="Save id under saves/.")) -> None:
    """Run rule-based save continuity checks."""
    from sirengm.lint.save_lint import lint_save

    cfg = load_config()
    issues = lint_save(cfg, save_id=save)
    _print_issues(issues, label=f"save:{save}")
    raise typer.Exit(code=1 if issues else 0)


def _print_issues(issues: list[str], *, label: str) -> None:
    if not issues:
        console.print(f"[green]✓ {label}: no issues[/]")
        return
    console.print(f"[red]✗ {label}: {len(issues)} issue(s)[/]")
    for msg in issues:
        console.print(f"  - {msg}")


if __name__ == "__main__":  # pragma: no cover
    app()
