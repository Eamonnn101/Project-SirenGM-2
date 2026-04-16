"""Mocked end-to-end ingest test: tiny novel -> valid user pack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sirengm.config import AppConfig
from sirengm.ingest.pipeline import run_ingest
from sirengm.llm.mock_client import MockProvider
from sirengm.pack.loader import load_user_pack

REPO_ROOT = Path(__file__).parent.parent
GENRE_ROOT = REPO_ROOT / "genre_packs"


TINY_NOVEL = """第一章  外门清晨

青衡一早醒来，身在玄霜宗外门东厢最末一间。山风冷，霜气未散。
他起身整好粗麻袍，拎起那把家传旧柴刀，走向演武场。

外门是山腰的一处聚落，归玄霜宗管辖，禁令严厉：外门弟子不得擅入灵峰主脉。
他是去年入门的杂役弟子，气感期三层，身份牌号"杂七"。

第二章  灵峰山风

演武场上霜白，青衡沿石径向山腰上方看——灵峰耸立在云里。
他不敢走远。一个执事在远处看他，他低头继续练刀。
"""


@pytest.fixture
def ingest_cfg(tmp_path: Path) -> AppConfig:
    (tmp_path / "packs").mkdir()
    (tmp_path / "saves").mkdir()
    (tmp_path / "raw" / "novel").mkdir(parents=True)
    (tmp_path / "genre_packs").symlink_to(GENRE_ROOT, target_is_directory=True)
    (tmp_path / "raw" / "novel" / "tiny.txt").write_text(TINY_NOVEL, encoding="utf-8")
    return AppConfig(
        root=tmp_path,
        provider="mock",
        anthropic_api_key=None,
        anthropic_model="claude-sonnet-4-6",
    )


def _extract_chunk0() -> str:
    return json.dumps({
        "chunk_id": 0,
        "mentions": [
            {"kind": "character", "slug": "ye_han", "name": "青衡", "source_chunk": 0, "evidence": "青衡一早醒来，身在玄霜宗外门东厢最末一间。", "role": "protagonist", "sect": "jade_frost_sect", "cultivation_stage": "气感期三层"},
            {"kind": "faction", "slug": "jade_frost_sect", "name": "玄霜宗", "source_chunk": 0, "evidence": "玄霜宗外门", "alignment": "orthodox"},
            {"kind": "location", "slug": "outer_gate", "name": "外门", "source_chunk": 0, "evidence": "外门是山腰的一处聚落", "controlled_by": "jade_frost_sect", "danger": "guarded"},
        ],
    })


def _extract_chunk1() -> str:
    return json.dumps({
        "chunk_id": 1,
        "mentions": [
            {"kind": "character", "slug": "ye_han", "name": "青衡", "source_chunk": 1, "evidence": "青衡沿石径向山腰上方看", "role": "protagonist"},
            {"kind": "location", "slug": "spirit_mountain", "name": "灵峰", "source_chunk": 1, "evidence": "灵峰耸立在云里", "controlled_by": "jade_frost_sect", "danger": "hostile"},
        ],
    })


def _draft_character() -> str:
    return json.dumps({
        "slug": "ye_han",
        "name": "青衡",
        "role": "protagonist",
        "sect": "jade_frost_sect",
        "cultivation_stage": "气感期三层",
        "status": "alive",
        "location": "outer_gate",
        "body": "十七岁。玄霜宗外门杂役弟子，身份牌号杂七。沉默倔强。",
    })


def _draft_faction() -> str:
    return json.dumps({
        "slug": "jade_frost_sect",
        "name": "玄霜宗",
        "alignment": "orthodox",
        "leaders": [],
        "body": "北陲灵霜山上的正道宗门。外门禁令：不得擅入灵峰主脉。",
    })


def _draft_location_outer() -> str:
    return json.dumps({
        "slug": "outer_gate",
        "name": "外门",
        "controlled_by": "jade_frost_sect",
        "danger": "guarded",
        "region": "灵霜山脉 · 山腰",
        "body": "玄霜宗外门，弟子聚居之处。演武场、执事房、东厢。",
    })


def _draft_location_mountain() -> str:
    return json.dumps({
        "slug": "spirit_mountain",
        "name": "灵峰",
        "controlled_by": "jade_frost_sect",
        "danger": "hostile",
        "region": "灵霜山脉 · 主峰",
        "body": "玄霜宗主脉。外门擅入死罪。",
    })


def test_ingest_produces_valid_user_pack(ingest_cfg: AppConfig) -> None:
    mock = MockProvider()
    mock.set("ingest.extract.0", _extract_chunk0())
    mock.set("ingest.extract.1", _extract_chunk1())
    mock.set("ingest.draft.character.ye_han", _draft_character())
    mock.set("ingest.draft.faction.jade_frost_sect", _draft_faction())
    mock.set("ingest.draft.location.outer_gate", _draft_location_outer())
    mock.set("ingest.draft.location.spirit_mountain", _draft_location_mountain())

    issues = run_ingest(
        ingest_cfg,
        novel_path=ingest_cfg.raw_dir / "novel" / "tiny.txt",
        pack_name="testpack",
        genre="xianxia",
        llm=mock,
    )
    assert issues == [], f"unexpected lint issues: {issues}"

    pack_dir = ingest_cfg.packs_dir / "testpack"
    pack = load_user_pack(pack_dir)
    assert pack.kind == "user"
    assert pack.inherits_genre == "xianxia"
    slugs = pack.all_entity_slugs()
    assert slugs == {"ye_han", "jade_frost_sect", "outer_gate", "spirit_mountain"}

    # Protagonist discovered.
    assert any(c.role == "protagonist" for c in pack.characters)

    # index.md lists the entities.
    index_md = (pack_dir / "index.md").read_text(encoding="utf-8")
    assert "ye_han" in index_md
    assert "jade_frost_sect" in index_md
    assert "outer_gate" in index_md
    assert "spirit_mountain" in index_md

    # Checkpoints exist.
    assert (pack_dir / ".ingest" / "chunks.jsonl").is_file()
    assert (pack_dir / ".ingest" / "mentions.jsonl").is_file()


def test_ingest_resume_from_draft_skips_extract(ingest_cfg: AppConfig, tmp_path: Path) -> None:
    mock = MockProvider()
    mock.set("ingest.extract.0", _extract_chunk0())
    mock.set("ingest.extract.1", _extract_chunk1())
    mock.set("ingest.draft.character.ye_han", _draft_character())
    mock.set("ingest.draft.faction.jade_frost_sect", _draft_faction())
    mock.set("ingest.draft.location.outer_gate", _draft_location_outer())
    mock.set("ingest.draft.location.spirit_mountain", _draft_location_mountain())

    # Full run first.
    run_ingest(
        ingest_cfg,
        novel_path=ingest_cfg.raw_dir / "novel" / "tiny.txt",
        pack_name="testpack",
        genre="xianxia",
        llm=mock,
    )
    first_calls = len([c for c in mock.calls if c[0] and c[0].startswith("ingest.extract.")])

    # Resume from draft — should NOT call extract tags.
    mock.calls.clear()
    run_ingest(
        ingest_cfg,
        novel_path=ingest_cfg.raw_dir / "novel" / "tiny.txt",
        pack_name="testpack",
        genre="xianxia",
        from_stage="draft",
        llm=mock,
    )
    second_extract_calls = [c for c in mock.calls if c[0] and c[0].startswith("ingest.extract.")]
    assert second_extract_calls == [], "draft-resume should not re-run extract"
    assert first_calls > 0
