"""Verify Pack objects round-trip through write/load without information loss."""

from __future__ import annotations

from pathlib import Path

from sirengm.pack.loader import load_pack
from sirengm.pack.models import (
    ArcPage,
    CharacterPage,
    EventPage,
    FactionPage,
    LocationPage,
    MetaPage,
    Pack,
    SystemPage,
)
from sirengm.pack.writer import write_pack


def _example_pack() -> Pack:
    return Pack(
        name="xianxia_test",
        kind="user",
        inherits_genre="xianxia",
        index=MetaPage(name="xianxia_test", body="# Index\n\n- [Protagonist](characters/protagonist.md)\n"),
        overview=MetaPage(name="overview", body="Cold mountains, rising dao.\n"),
        style_guide=MetaPage(name="style", body="Terse, cinematic prose.\n"),
        canon_guardrails=MetaPage(name="guardrails", body="Never break the system of the Jade Qing Sect.\n"),
        timeline=MetaPage(name="timeline", body="Year 0: protagonist enters the sect.\n"),
        relationships=MetaPage(
            name="rel_matrix",
            body="| from | to | kind |\n|---|---|---|\n| protagonist | master | disciple |\n",
        ),
        ambiguities=MetaPage(name="ambiguities", body="- Is the Rival truly dead?\n"),
        characters=[
            CharacterPage(
                slug="protagonist",
                name="Ye Han",
                aliases=["the boy from the village"],
                role="protagonist",
                sect="jade_qing_sect",
                cultivation_stage="Qi Condensation 3",
                status="alive",
                location="outer_gate",
                body="Taciturn, stubborn, shaped by loss.\n",
            ),
            CharacterPage(
                slug="master",
                name="Elder Yin",
                role="master",
                sect="jade_qing_sect",
                cultivation_stage="Nascent Soul 1",
                body="Elder of the Jade Qing Sect; cold but fair.\n",
            ),
        ],
        factions=[
            FactionPage(
                slug="jade_qing_sect",
                name="Jade Qing Sect",
                alignment="orthodox",
                seat="spirit_mountain",
                leaders=["master"],
                body="A mid-sized orthodox sect on Spirit Mountain.\n",
            )
        ],
        locations=[
            LocationPage(
                slug="outer_gate",
                name="Outer Gate",
                region="Spirit Mountain",
                controlled_by="jade_qing_sect",
                danger="guarded",
                body="The outer disciples' courtyard.\n",
            ),
            LocationPage(
                slug="spirit_mountain",
                name="Spirit Mountain",
                region="Eastern Range",
                controlled_by="jade_qing_sect",
                danger="guarded",
                body="A towering peak veiled in cloud.\n",
            ),
        ],
        systems=[
            SystemPage(
                slug="cultivation",
                name="Cultivation",
                kind="cultivation",
                body="Qi Condensation -> Foundation Establishment -> Core Formation ...\n",
            )
        ],
        arcs=[
            ArcPage(
                slug="opening_arc",
                name="Opening Arc",
                summary="Protagonist enters the sect and survives the outer trial.",
                status="opening",
                driving_entities=["protagonist", "master"],
                body="The opening arc focuses on survival and first lessons.\n",
            )
        ],
        events=[
            EventPage(
                slug="sect_trial",
                name="Sect Trial",
                kind="triggerable",
                preconditions=["in:outer_gate"],
                body="A test administered by Elder Yin.\n",
            )
        ],
    )


def test_pack_write_then_load_round_trip(tmp_path: Path) -> None:
    original = _example_pack()
    pack_dir = tmp_path / "packs" / original.name
    write_pack(original, pack_dir)

    loaded = load_pack(pack_dir)

    assert loaded.name == original.name
    assert loaded.kind == "user"
    assert loaded.inherits_genre == "xianxia"
    assert loaded.overview and loaded.overview.body.rstrip() == original.overview.body.rstrip()  # type: ignore[union-attr]
    assert loaded.canon_guardrails and "Jade Qing Sect" in (loaded.canon_guardrails.body or "")
    assert {c.slug for c in loaded.characters} == {"protagonist", "master"}

    protagonist = next(c for c in loaded.characters if c.slug == "protagonist")
    assert protagonist.name == "Ye Han"
    assert protagonist.aliases == ["the boy from the village"]
    assert protagonist.cultivation_stage == "Qi Condensation 3"
    assert protagonist.location == "outer_gate"
    assert "Taciturn" in protagonist.body

    sect = next(f for f in loaded.factions if f.slug == "jade_qing_sect")
    assert sect.leaders == ["master"]

    assert {loc.slug for loc in loaded.locations} == {"outer_gate", "spirit_mountain"}
    assert loaded.arcs[0].driving_entities == ["protagonist", "master"]
    assert loaded.events[0].kind == "triggerable"


def test_find_entity_and_all_slugs() -> None:
    pack = _example_pack()
    assert pack.find_entity("protagonist") is not None
    assert pack.find_entity("unknown") is None
    slugs = pack.all_entity_slugs()
    assert "protagonist" in slugs
    assert "jade_qing_sect" in slugs
    assert "outer_gate" in slugs
    assert "opening_arc" in slugs
    assert "sect_trial" in slugs
