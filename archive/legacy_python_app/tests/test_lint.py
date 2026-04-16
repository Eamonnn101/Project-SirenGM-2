"""Tests for rule-based lint on genre packs, user packs, and saves."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from sirengm.config import AppConfig
from sirengm.lint.pack_lint import lint_pack
from sirengm.lint.save_lint import lint_save
from sirengm.runtime.new_game import build_initial_save
from sirengm.save import render as render_save
from sirengm.save.store import load_save, persist

REPO_ROOT = Path(__file__).parent.parent
GENRE_ROOT = REPO_ROOT / "genre_packs"
MINI = Path(__file__).parent / "fixtures" / "mini_user_pack"


def test_genre_xianxia_pack_lints_clean() -> None:
    issues = lint_pack(GENRE_ROOT / "xianxia")
    assert issues == [], f"unexpected genre pack issues: {issues}"


def test_mini_user_pack_lints_clean() -> None:
    issues = lint_pack(MINI, genre_packs_root=GENRE_ROOT)
    assert issues == [], f"unexpected user pack issues: {issues}"


def test_user_pack_with_broken_refs(tmp_path: Path) -> None:
    # Start from the mini fixture; corrupt a reference.
    target = tmp_path / "broken"
    shutil.copytree(MINI, target)
    # Make the protagonist reference a non-existent sect.
    protag = target / "characters" / "protagonist.md"
    text = protag.read_text(encoding="utf-8")
    text = text.replace("sect: jade_frost_sect", "sect: ghost_sect")
    protag.write_text(text, encoding="utf-8")

    issues = lint_pack(target, genre_packs_root=GENRE_ROOT)
    assert any("unknown sect" in i for i in issues)


def test_user_pack_missing_protagonist(tmp_path: Path) -> None:
    target = tmp_path / "no_protag"
    shutil.copytree(MINI, target)
    # Swap protagonist role to something else.
    protag = target / "characters" / "protagonist.md"
    text = protag.read_text(encoding="utf-8").replace("role: protagonist", "role: ally")
    protag.write_text(text, encoding="utf-8")

    issues = lint_pack(target, genre_packs_root=GENRE_ROOT)
    assert any("protagonist" in i for i in issues)


def test_user_pack_unresolved_wiki_link(tmp_path: Path) -> None:
    target = tmp_path / "badlink"
    shutil.copytree(MINI, target)
    loc = target / "locations" / "outer_gate.md"
    loc.write_text(loc.read_text(encoding="utf-8") + "\n\n参见 [[nonexistent_slug]]。\n", encoding="utf-8")
    issues = lint_pack(target, genre_packs_root=GENRE_ROOT)
    assert any("does not resolve" in i for i in issues)


def test_genre_pack_rejects_entity_dir(tmp_path: Path) -> None:
    # Copy genre/xianxia and inject a characters/ file.
    target = tmp_path / "corrupt_genre"
    shutil.copytree(GENRE_ROOT / "xianxia", target)
    (target / "characters").mkdir()
    (target / "characters" / "protagonist.md").write_text(
        "---\nslug: protagonist\nname: X\nrole: protagonist\n---\n\nbody\n",
        encoding="utf-8",
    )
    issues = lint_pack(target)
    # The Pydantic model validator rejects genre packs with entity lists before lint runs;
    # the error surfaces as a load failure mentioning 'characters/factions/locations'.
    assert any("must not contain" in i and "characters" in i for i in issues)


# --- save lint -----------------------------------------------------------


@pytest.fixture
def cfg_with_copy(tmp_path: Path) -> AppConfig:
    (tmp_path / "packs").mkdir()
    (tmp_path / "saves").mkdir()
    (tmp_path / "raw" / "novel").mkdir(parents=True)
    (tmp_path / "genre_packs").symlink_to(GENRE_ROOT, target_is_directory=True)
    shutil.copytree(MINI, tmp_path / "packs" / "mini")
    return AppConfig(root=tmp_path, provider="mock", anthropic_api_key=None, anthropic_model="claude-sonnet-4-6")


def test_save_lint_clean_after_new_game(cfg_with_copy: AppConfig) -> None:
    build_initial_save(cfg_with_copy, pack_name="mini", save_id="save_t")
    issues = lint_save(cfg_with_copy, save_id="save_t")
    assert issues == [], f"unexpected save lint issues: {issues}"


def test_save_lint_flags_unknown_slug(cfg_with_copy: AppConfig) -> None:
    build_initial_save(cfg_with_copy, pack_name="mini", save_id="save_corrupt")
    save = load_save(cfg_with_copy.saves_dir, "save_corrupt")
    save.world.present_entities.append("nobody")
    persist(cfg_with_copy.saves_dir, save)
    render_save.render_all(cfg_with_copy.saves_dir, save)
    issues = lint_save(cfg_with_copy, save_id="save_corrupt")
    assert any("unknown slug 'nobody'" in i for i in issues)


def test_save_lint_accepts_emergent_slug(cfg_with_copy: AppConfig) -> None:
    build_initial_save(cfg_with_copy, pack_name="mini", save_id="save_emg")
    save = load_save(cfg_with_copy.saves_dir, "save_emg")
    save.world.present_entities.append("emergent:passing_monk")
    persist(cfg_with_copy.saves_dir, save)
    render_save.render_all(cfg_with_copy.saves_dir, save)
    issues = lint_save(cfg_with_copy, save_id="save_emg")
    assert issues == []
