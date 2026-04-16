"""Verify genre/user split and stacked pack semantics."""

from __future__ import annotations

from pathlib import Path

import pytest

from sirengm.pack.loader import load_genre_pack, load_user_pack
from sirengm.pack.models import CharacterPage, MetaPage, Pack
from sirengm.pack.stacked import StackedPack, load_stacked

REPO_ROOT = Path(__file__).parent.parent
GENRE_ROOT = REPO_ROOT / "genre_packs"
MINI_USER_PACK = Path(__file__).parent / "fixtures" / "mini_user_pack"


def test_genre_xianxia_loads_and_is_genre_kind() -> None:
    pack = load_genre_pack(GENRE_ROOT / "xianxia")
    assert pack.kind == "genre"
    assert pack.inherits_genre is None
    assert pack.style_guide is not None
    assert pack.canon_guardrails is not None
    # Genre packs may only have systems among entity categories.
    assert pack.characters == []
    assert pack.factions == []
    assert pack.locations == []
    assert pack.arcs == []
    assert pack.events == []
    # systems/cultivation.md + systems/social_rules.md are present.
    slugs = {s.slug for s in pack.systems}
    assert "cultivation" in slugs
    assert "social_rules" in slugs


def test_genre_pack_rejects_entities_at_model_level() -> None:
    with pytest.raises(ValueError, match="genre packs must not contain"):
        Pack(
            name="bad_genre",
            kind="genre",
            characters=[CharacterPage(slug="x", name="X", role="protagonist")],
        )


def test_user_pack_requires_inherits_genre() -> None:
    with pytest.raises(ValueError, match="inherits_genre"):
        Pack(name="orphan", kind="user")


def test_mini_user_pack_loads_with_kind_user() -> None:
    pack = load_user_pack(MINI_USER_PACK)
    assert pack.kind == "user"
    assert pack.inherits_genre == "xianxia"
    slugs = pack.all_entity_slugs()
    assert "protagonist" in slugs
    assert "jade_frost_sect" in slugs
    assert "outer_gate" in slugs
    assert "opening_arc" in slugs


def test_stacked_pack_combines_genre_and_user() -> None:
    stacked = load_stacked(MINI_USER_PACK, genre_packs_root=GENRE_ROOT)
    assert isinstance(stacked, StackedPack)
    assert stacked.genre_name == "xianxia"
    assert stacked.name == "mini_user_pack"
    # Style guide is from the genre pack.
    assert "第二人称现在时" in stacked.style_guide_body()
    # Guardrails are concatenated genre + user.
    gr = stacked.canon_guardrails_body()
    assert "不可跳阶" in gr
    assert "开局 20 回合内" in gr
    # Entity lookup goes user pack first.
    protagonist = stacked.find_entity("protagonist")
    assert protagonist is not None
    assert protagonist.name == "青衡"
    # Genre systems surface through stacked.
    assert stacked.find_entity("cultivation") is not None
    assert stacked.find_entity("social_rules") is not None


def test_stacked_pack_entity_slug_set_includes_both_layers() -> None:
    stacked = load_stacked(MINI_USER_PACK, genre_packs_root=GENRE_ROOT)
    slugs = stacked.all_entity_slugs()
    assert "protagonist" in slugs  # user
    assert "cultivation" in slugs  # genre
    assert "outer_gate" in slugs  # user
