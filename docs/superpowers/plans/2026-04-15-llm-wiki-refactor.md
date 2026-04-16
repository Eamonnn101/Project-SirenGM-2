# llm-wiki Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor SirenGM 2 from a Python CLI app (`sirengm ingest/new-game/play`) into a pure file-driven, llm-wiki-style project where Claude Code / Codex are the runtime, `CLAUDE.md` is the operating schema, `genre_packs/xianxia/` is the reusable template, `raw/novel/` is immutable input, `packs/<user_pack>/` is the AI-compiled wiki, and `saves/<save_id>/` is the persistent game state. Retain only a thin `tools/` layer of optional deterministic helpers.

**Architecture:** The agent (Claude Code or Codex) drives ingest, new-game, and turn loops by reading `CLAUDE.md` + playbooks, reading raw novel text, writing pack files, and reading/writing structured save JSON + re-rendered markdown surfaces. The Python app is archived wholesale under `archive/legacy_python_app/`. Deterministic pure-Python helpers (chunker, lint, render, inspect) survive as standalone scripts callable via `python tools/<name>.py ...`. No more `typer`, `anthropic`, or LLM-client abstractions — the agent *is* the LLM client.

**Tech Stack:** Markdown + JSON as data; Python 3.10+ stdlib + small dependency set (`pydantic`, `pyyaml`, `python-frontmatter`) for the helper tools; no CLI framework, no provider SDKs, no test framework in the product path.

---

## File Structure

```
Project SirenGM 2/
  CLAUDE.md                     — rewritten: operating schema for the agent
  AGENTS.md                     — new: thin pointer to CLAUDE.md for Codex
  README.md                     — rewritten: file-driven workflow, no CLI
  llm-wiki.md                   — kept as-is (design inspiration)
  pyproject.toml                — slimmed: tools-only deps, no console scripts

  genre_packs/
    xianxia/                    — kept; prompts re-framed as agent-facing instructions

  raw/novel/                    — kept (immutable)

  packs/                        — empty dir; agent writes into packs/<user_pack>/
  saves/                        — empty dir; agent writes into saves/<save_id>/

  playbooks/
    ingest.md                   — new: step-by-step for compiling a novel into a pack
    new-game.md                 — new: step-by-step for bootstrapping a save from a pack
    play-turn.md                — new: the two-step agent turn loop (narrate → patch state)
    lint.md                     — new: how the agent invokes tools/ and interprets output

  tools/
    README.md                   — new: how to invoke each helper
    _models.py                  — new: Pydantic schemas for Save + Pack (ported)
    chunker.py                  — new: standalone port of ingest/chunker.py
    lint_pack.py                — new: standalone port of lint/pack_lint.py
    render_save.py              — new: standalone port of save/render.py
    inspect_save.py             — new: compact JSON→text summary of a save

  docs/superpowers/plans/
    2026-04-15-llm-wiki-refactor.md   — this document

  archive/legacy_python_app/
    src/                        — moved from src/
    tests/                      — moved from tests/
    README.md                   — new: one-paragraph explanation + removal policy
```

**Files removed (after archival):**
- top-level `src/` — moved into `archive/legacy_python_app/src/`
- top-level `tests/` — moved into `archive/legacy_python_app/tests/`
- `.pytest_cache/` — deleted
- `.venv/` — left in place; it's a dev artifact, not tracked

**Files untouched:** `genre_packs/xianxia/` (content edits are in Task 10 only), `raw/novel/`, `packs/`, `saves/`, `llm-wiki.md`, `.gitignore`, `.claude/`.

---

## Cross-cutting conventions for this plan

- **No git, no commits.** The repo is not a git repository (confirmed at plan-write time). Replace the usual "commit" step with "save point": verify the intended files exist with expected content via `ls` + spot-reads, then move on.
- **Style guardrails for new prose files (CLAUDE.md, playbooks, README):** direct, terse, no emojis, no marketing voice, no forward-looking promises, match the voice of the existing `CLAUDE.md`.
- **Never rewrite `llm-wiki.md`** — it is reference material.
- **Never rewrite `genre_packs/xianxia/` content** except where Task 10 explicitly prescribes it.
- **Tools must be standalone:** `python tools/<name>.py --help` works without `pip install -e .` and without any `sirengm` import. They may import `_models.py` from the same `tools/` dir.
- **Absolute paths in examples:** use `packs/<name>/` relative to repo root; never absolute disk paths in any written file.

---

## Task 1: Create archive directory and move the Python app

**Files:**
- Create: `archive/legacy_python_app/README.md`
- Move: `src/` → `archive/legacy_python_app/src/`
- Move: `tests/` → `archive/legacy_python_app/tests/`
- Delete: `.pytest_cache/`

- [ ] **Step 1: Confirm source locations exist**

Run: `ls -d src tests .pytest_cache`
Expected: all three print without error, from repo root.

- [ ] **Step 2: Create archive directory**

Run: `mkdir -p archive/legacy_python_app`
Expected: exits 0; `ls archive/legacy_python_app` prints nothing (empty).

- [ ] **Step 3: Move `src/` into archive**

Run: `mv src archive/legacy_python_app/src`
Expected: `ls src` now errors; `ls archive/legacy_python_app/src/sirengm` prints `cli.py config.py ingest/ ...`.

- [ ] **Step 4: Move `tests/` into archive**

Run: `mv tests archive/legacy_python_app/tests`
Expected: `ls tests` now errors; `ls archive/legacy_python_app/tests` prints the old test files.

- [ ] **Step 5: Delete the pytest cache**

Run: `rm -rf .pytest_cache`
Expected: `ls .pytest_cache` errors.

- [ ] **Step 6: Write the archive README**

Create `archive/legacy_python_app/README.md` with this exact content:

```markdown
# Archived: legacy Python app

This directory contains the prior implementation of SirenGM 2 as a `typer`-based
Python CLI (`sirengm ingest / new-game / play`). It was the main product path
up to the llm-wiki refactor on 2026-04-15.

It is kept for reference only. The new product path is the agent-driven,
file-driven workflow described in the repo-root `CLAUDE.md`. Small portions of
this code were ported into `tools/` as standalone helper scripts; the rest is
no longer executed.

This directory is a candidate for deletion after the new flow has been
exercised end-to-end on at least one real novel.
```

- [ ] **Step 7: Save point — verify structure**

Run: `ls archive/legacy_python_app && ls archive/legacy_python_app/src/sirengm && test ! -e src && test ! -e tests`
Expected: prints the archive contents and exits 0.

---

## Task 2: Slim `pyproject.toml` to tools-only dependencies

**Files:**
- Modify: `pyproject.toml` (complete rewrite)

- [ ] **Step 1: Read the current `pyproject.toml`**

Run: `cat pyproject.toml`
Expected: current content includes `[project.scripts] sirengm = ...` and deps on `typer`, `rich`, `anthropic`, etc. Confirm before rewriting so nothing important is lost.

- [ ] **Step 2: Overwrite with the slim tools-only version**

Write this exact content to `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sirengm-tools"
version = "0.2.0"
description = "Optional deterministic helper tools for the SirenGM 2 llm-wiki workflow. The main product path is agent-driven and does not require this package."
readme = "README.md"
requires-python = ">=3.10"
license = { text = "Proprietary" }
authors = [{ name = "Eamon" }]
dependencies = [
    "pydantic>=2.6",
    "pyyaml>=6.0",
    "python-frontmatter>=1.1",
]

[tool.hatch.build.targets.wheel]
packages = ["tools"]
```

Note: no `[project.scripts]`, no `typer`, no `rich`, no `anthropic`, no `[project.optional-dependencies]`, no `[tool.pytest.ini_options]`. The `hatch` wheel config is kept so `uv pip install -e .` still works for anyone who wants to put the tools on PATH, but this is optional — the tools are also runnable as plain `python tools/<name>.py`.

- [ ] **Step 3: Save point — verify**

Run: `cat pyproject.toml | head -20`
Expected: shows the new content; no mention of `sirengm = "sirengm.cli:app"`.

---

## Task 3: Port save/pack Pydantic schemas into `tools/_models.py`

**Files:**
- Create: `tools/_models.py`
- Source (do not modify): `archive/legacy_python_app/src/sirengm/save/models.py`
- Source (do not modify): `archive/legacy_python_app/src/sirengm/pack/models.py`

Purpose: the lint/render/inspect tools need to validate & serialize the same shapes the agent writes. Centralizing the schemas in `tools/_models.py` prevents drift.

- [ ] **Step 1: Create `tools/` directory**

Run: `mkdir -p tools`
Expected: `ls tools` prints nothing.

- [ ] **Step 2: Read both source model files**

Run: `wc -l archive/legacy_python_app/src/sirengm/save/models.py archive/legacy_python_app/src/sirengm/pack/models.py`
Expected: two line counts, for orientation.

- [ ] **Step 3: Write `tools/_models.py`**

Compose by concatenating — in this order — the full contents of:
1. `archive/legacy_python_app/src/sirengm/save/models.py` (keep all classes: `InventoryItem`, `PlayerState`, `ActiveThread`, `WorldState`, `Relationship`, `RelationshipState`, `OpenLoop`, `OpenLoops`, `SessionLogEntry`, `DivergenceNote`, `Save`, and the three `Literal` type aliases).
2. The full entity-model contents of `archive/legacy_python_app/src/sirengm/pack/models.py` (all pack models: the genre / user `Pack` model plus `Character`, `Faction`, `Location`, `Arc`, `Event`, `SystemPage`).

Adjustments when copying:
- Dedupe imports at the top; the combined file has one single `from __future__ import annotations`, one `from datetime import datetime`, one `from typing import Literal`, one `from pydantic import BaseModel, ConfigDict, Field`.
- Remove any `from sirengm...` imports — the file must not import from the archived package.
- Keep every `ConfigDict(extra=...)`, field description, and default unchanged. These contracts are the whole point.
- Do not add any behavior (no I/O, no helpers).

Top of the file should look like:

```python
"""Canonical Pydantic schemas for SirenGM 2 save state and pack entities.

Kept in sync with the shapes the agent writes under saves/<id>/ and
packs/<name>/. Imported by tools/lint_pack.py, tools/render_save.py,
tools/inspect_save.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
```

- [ ] **Step 4: Smoke-test the schemas load**

Run: `python -c "from tools._models import Save, WorldState, PlayerState; print(Save.model_json_schema()['title'])"`
Expected: prints `Save`. If it errors on import, fix missing imports before proceeding.

- [ ] **Step 5: Save point**

Run: `wc -l tools/_models.py`
Expected: roughly 200–350 lines; both save + pack classes present.

---

## Task 4: Port `tools/chunker.py` as a standalone script

**Files:**
- Create: `tools/chunker.py`
- Source (do not modify): `archive/legacy_python_app/src/sirengm/ingest/chunker.py`

- [ ] **Step 1: Read the source file**

Open `archive/legacy_python_app/src/sirengm/ingest/chunker.py`. The three public pieces are `Chunk`, `chunk_novel`, `write_chunks`. Read/keep private helpers `_find_markers`, `_split_by_markers`, `_split_by_size`, and the `_CHAPTER_PATTERNS` / `DEFAULT_TARGET_CHARS` / `MIN_CHUNK_CHARS` constants.

- [ ] **Step 2: Write `tools/chunker.py`**

The file's top-of-file docstring + code up through `_split_by_size` is identical to the source, minus imports of anything outside stdlib. Then append a `main()` driven by `argparse` so the file is runnable as `python tools/chunker.py <novel> --pack <name>`:

```python
"""Heuristic chapter-splitter for a raw novel text file.

Usage:
    python tools/chunker.py raw/novel/<file>.txt --pack <pack_name>

Writes packs/<pack_name>/.ingest/chunks.jsonl with one JSON object per chunk:
{"id": int, "title": str, "text": str, "start": int}.

The agent reads chunks.jsonl and processes entries one by one during the
extract pass described in playbooks/ingest.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_CHAPTER_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十百千\d]{1,6}[章节回][\s\u3000].*", re.MULTILINE),
    re.compile(r"^Chapter\s+\d+.*", re.MULTILINE),
    re.compile(r"^#\s+.+", re.MULTILINE),
]

DEFAULT_TARGET_CHARS = 3000
MIN_CHUNK_CHARS = 40


@dataclass
class Chunk:
    id: int
    title: str
    text: str
    start: int


def chunk_novel(text: str, *, target_chars: int = DEFAULT_TARGET_CHARS) -> list[Chunk]:
    text = text.replace("\r\n", "\n").strip()
    markers = _find_markers(text)
    if len(markers) >= 2:
        return _split_by_markers(text, markers)
    return _split_by_size(text, target_chars=target_chars)


def write_chunks(pack_dir: Path, chunks: list[Chunk]) -> Path:
    ingest_dir = pack_dir / ".ingest"
    ingest_dir.mkdir(parents=True, exist_ok=True)
    out = ingest_dir / "chunks.jsonl"
    out.write_text(
        "\n".join(json.dumps(asdict(c), ensure_ascii=False) for c in chunks) + "\n",
        encoding="utf-8",
    )
    return out


def _find_markers(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for pat in _CHAPTER_PATTERNS:
        for m in pat.finditer(text):
            found.append((m.start(), m.group(0).strip()))
    found.sort()
    deduped: list[tuple[int, str]] = []
    for pos, title in found:
        if deduped and pos - deduped[-1][0] < 5:
            continue
        deduped.append((pos, title))
    return deduped


def _split_by_markers(text: str, markers: list[tuple[int, str]]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for i, (start, title) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        body = text[start:end].strip()
        if len(body) >= MIN_CHUNK_CHARS:
            chunks.append(Chunk(id=len(chunks), title=title, text=body, start=start))
    return chunks


def _split_by_size(text: str, *, target_chars: int) -> list[Chunk]:
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_len = 0
    start_offset = 0
    running_offset = 0
    for para in paragraphs:
        para_len = len(para) + 2
        if buf_len + para_len > target_chars and buf:
            chunks.append(
                Chunk(id=len(chunks), title=f"chunk-{len(chunks)+1}",
                      text="\n\n".join(buf), start=start_offset)
            )
            buf = []
            buf_len = 0
            start_offset = running_offset
        buf.append(para)
        buf_len += para_len
        running_offset += para_len
    if buf:
        chunks.append(
            Chunk(id=len(chunks), title=f"chunk-{len(chunks)+1}",
                  text="\n\n".join(buf), start=start_offset)
        )
    return chunks


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("novel", type=Path, help="path to the raw novel text file (utf-8)")
    p.add_argument("--pack", required=True, help="target pack name under packs/")
    p.add_argument("--target-chars", type=int, default=DEFAULT_TARGET_CHARS)
    p.add_argument("--packs-root", type=Path, default=Path("packs"))
    args = p.parse_args(argv)

    if not args.novel.is_file():
        print(f"error: novel file not found: {args.novel}", file=sys.stderr)
        return 2
    text = args.novel.read_text(encoding="utf-8")
    chunks = chunk_novel(text, target_chars=args.target_chars)
    pack_dir = args.packs_root / args.pack
    out = write_chunks(pack_dir, chunks)
    print(f"wrote {len(chunks)} chunks to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Smoke-test on a tiny input**

Run:
```bash
printf '# Chapter One\nHello.\n\n# Chapter Two\nWorld.\n' > /tmp/tiny.txt
mkdir -p packs && python tools/chunker.py /tmp/tiny.txt --pack _smoke_chunker
cat packs/_smoke_chunker/.ingest/chunks.jsonl
rm -rf packs/_smoke_chunker
```
Expected: prints `wrote 2 chunks to packs/_smoke_chunker/.ingest/chunks.jsonl` followed by two JSON lines with `"title": "# Chapter One"` and `"# Chapter Two"`.

- [ ] **Step 4: Save point**

Run: `python tools/chunker.py --help | head -3`
Expected: prints the docstring first line and usage.

---

## Task 5: Port `tools/lint_pack.py` as a standalone script

**Files:**
- Create: `tools/lint_pack.py`
- Source (do not modify): `archive/legacy_python_app/src/sirengm/lint/pack_lint.py`
- Source (do not modify): `archive/legacy_python_app/src/sirengm/pack/loader.py`
- Uses: `tools/_models.py` (from Task 3)

The lint is the heaviest port — it needs a `load_pack(pack_dir)` function. In the archived code that lived in `src/sirengm/pack/loader.py`. Port the minimum needed.

- [ ] **Step 1: Read both source files**

Run: `wc -l archive/legacy_python_app/src/sirengm/pack/loader.py archive/legacy_python_app/src/sirengm/lint/pack_lint.py`
Expected: two line counts for orientation.

- [ ] **Step 2: Write `tools/lint_pack.py`**

Structure:
1. Module docstring explaining CLI usage.
2. `load_pack(pack_dir: Path) -> Pack` — ported from `archive/legacy_python_app/src/sirengm/pack/loader.py`, with imports repointed to `tools._models` (or a relative import if invoked as a script; see Step 3).
3. `lint_pack(pack_dir, *, genre_packs_root=None) -> list[str]` — verbatim from `archive/legacy_python_app/src/sirengm/lint/pack_lint.py`, with `from sirengm.pack.loader import load_pack` replaced by the local `load_pack` defined above.
4. `main(argv)` — an `argparse`-driven entry point:

```python
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Rule-based lint for a genre or user pack.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--pack", help="user pack name under packs/")
    g.add_argument("--genre", help="genre pack name under genre_packs/")
    p.add_argument("--packs-root", type=Path, default=Path("packs"))
    p.add_argument("--genre-packs-root", type=Path, default=Path("genre_packs"))
    args = p.parse_args(argv)

    if args.pack:
        pack_dir = args.packs_root / args.pack
        issues = lint_pack(pack_dir, genre_packs_root=args.genre_packs_root)
    else:
        pack_dir = args.genre_packs_root / args.genre
        issues = lint_pack(pack_dir)

    if not issues:
        print(f"ok: {pack_dir} has no lint issues")
        return 0
    print(f"{len(issues)} issue(s) in {pack_dir}:")
    for i in issues:
        print(f"  - {i}")
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

- [ ] **Step 3: Decide the import strategy for `tools/_models.py`**

Because `tools/` is a package (it has `_models.py`) and `lint_pack.py` imports from it, the script needs to work when run as `python tools/lint_pack.py --genre xianxia` from repo root. Use this import pattern at the top of `tools/lint_pack.py`:

```python
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _models import Pack, Character, Faction, Location, Arc, Event, SystemPage
else:
    from ._models import Pack, Character, Faction, Location, Arc, Event, SystemPage
```

This lets the file run both as a module (`python -m tools.lint_pack ...`) and as a direct script (`python tools/lint_pack.py ...`).

- [ ] **Step 4: Smoke-test on the genre pack**

Run: `python tools/lint_pack.py --genre xianxia`
Expected: prints `ok: genre_packs/xianxia has no lint issues` and exits 0. If it reports issues, read them; they should only be real schema problems in the pack, not import errors.

- [ ] **Step 5: Smoke-test on a missing pack (negative case)**

Run: `python tools/lint_pack.py --pack does_not_exist; echo "exit=$?"`
Expected: prints `1 issue(s) in packs/does_not_exist:` and `- pack dir not found: packs/does_not_exist`, then `exit=1`.

- [ ] **Step 6: Save point**

Run: `python tools/lint_pack.py --help | head -3`
Expected: usage line prints without import error.

---

## Task 6: Port `tools/render_save.py` as a standalone script

**Files:**
- Create: `tools/render_save.py`
- Source (do not modify): `archive/legacy_python_app/src/sirengm/save/render.py`
- Source (do not modify): `archive/legacy_python_app/src/sirengm/save/store.py` (for the save-loading side)
- Uses: `tools/_models.py` (from Task 3)

The agent writes `saves/<id>/world_state.json`, `relationship_state.json`, `open_loops.json`, `player.json`, `meta.json`, plus `session_log.jsonl`. `render_save.py` reads those JSONs and writes/overwrites the markdown surfaces: `current_scene.md`, `player.md`, `session_log.md`, `hidden_truths.md`.

- [ ] **Step 1: Read the source files**

Run: `wc -l archive/legacy_python_app/src/sirengm/save/render.py archive/legacy_python_app/src/sirengm/save/store.py`
Expected: two line counts for orientation.

- [ ] **Step 2: Build the loader**

At the top of `tools/render_save.py`, write a `load_save(save_dir: Path) -> Save` function that reads the JSON files the agent writes and assembles a `Save` Pydantic instance. The on-disk layout is:

- `saves/<id>/meta.json` — `{"save_id": str, "pack_name": str, "hidden_truths": str}` (last two optional with defaults).
- `saves/<id>/world_state.json` — matches `WorldState.model_dump()`.
- `saves/<id>/relationship_state.json` — `{"by_slug": {slug: {...}}}` matching `RelationshipState`.
- `saves/<id>/open_loops.json` — `{"items": [...]}` matching `OpenLoops`.
- `saves/<id>/player.json` — mirror of `world_state.player` (re-derive from `world_state.json` if this file is missing; this is a convenience mirror only).
- `saves/<id>/session_log.jsonl` — authoritative log; one `SessionLogEntry` JSON per line.
- `saves/<id>/divergences.jsonl` — authoritative append-only divergence log; one `DivergenceNote` JSON per line; file may be absent.

Implementation:

```python
import json

def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_save(save_dir: Path) -> Save:
    meta = _read_json(save_dir / "meta.json")
    world = WorldState(**_read_json(save_dir / "world_state.json"))
    relationships = RelationshipState(**_read_json(save_dir / "relationship_state.json")) \
        if (save_dir / "relationship_state.json").is_file() else RelationshipState()
    open_loops = OpenLoops(**_read_json(save_dir / "open_loops.json")) \
        if (save_dir / "open_loops.json").is_file() else OpenLoops()
    session_log = [SessionLogEntry(**row) for row in _read_jsonl(save_dir / "session_log.jsonl")]
    divergences = [DivergenceNote(**row) for row in _read_jsonl(save_dir / "divergences.jsonl")]
    return Save(
        save_id=meta["save_id"],
        pack_name=meta["pack_name"],
        world=world,
        relationships=relationships,
        open_loops=open_loops,
        session_log=session_log,
        divergences=divergences,
        hidden_truths=meta.get("hidden_truths", ""),
    )
```

- [ ] **Step 3: Copy the rendering functions verbatim**

Copy `render_all`, `render_current_scene`, `render_player_md`, `render_session_log`, `_entry_to_json` from `archive/legacy_python_app/src/sirengm/save/render.py` into `tools/render_save.py`. Adjust the signature of `render_all` to take a single `save_dir: Path` argument (the directory, not a `saves_root` + id):

```python
def render_all(save_dir: Path, save: Save) -> None:
    save_dir.mkdir(parents=True, exist_ok=True)
    (save_dir / "current_scene.md").write_text(render_current_scene(save), encoding="utf-8")
    (save_dir / "player.md").write_text(render_player_md(save), encoding="utf-8")
    session_md, session_jsonl = render_session_log(save)
    (save_dir / "session_log.md").write_text(session_md, encoding="utf-8")
    (save_dir / "session_log.jsonl").write_text(session_jsonl, encoding="utf-8")
    hidden = save.hidden_truths.strip()
    (save_dir / "hidden_truths.md").write_text(
        ("# Hidden Truths\n\n" + hidden + "\n") if hidden else "# Hidden Truths\n\n(empty)\n",
        encoding="utf-8",
    )
```

Rationale: the old signature took `saves_root` plus a `save.save_id` and combined them; the standalone tool is simpler if the caller just passes the directory.

- [ ] **Step 4: Add `main()`**

```python
def main(argv: list[str] | None = None) -> int:
    import argparse, sys
    p = argparse.ArgumentParser(description="Re-render markdown surfaces of a save from its JSON state.")
    p.add_argument("--save", required=True, help="save id under saves/")
    p.add_argument("--saves-root", type=Path, default=Path("saves"))
    args = p.parse_args(argv)
    save_dir = args.saves_root / args.save
    if not save_dir.is_dir():
        print(f"error: save dir not found: {save_dir}", file=sys.stderr)
        return 2
    save = load_save(save_dir)
    render_all(save_dir, save)
    print(f"re-rendered markdown surfaces for {save_dir}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

- [ ] **Step 5: Use the same dual-mode import trick as Task 5, Step 3**

Same pattern for importing from `_models`.

- [ ] **Step 6: Smoke-test with a hand-authored minimal save**

Run:

```bash
mkdir -p saves/_smoke_render
cat > saves/_smoke_render/meta.json <<'JSON'
{"save_id": "_smoke_render", "pack_name": "tests"}
JSON
cat > saves/_smoke_render/world_state.json <<'JSON'
{
  "turn": 0, "day": 0, "time_of_day": "morning",
  "current_location": "loc_home", "present_entities": [],
  "active_threads": [], "current_objectives": [], "risk_level": "calm",
  "player": {"slug":"mc","name":"张三","cultivation_stage":"气感期一层","status":"alive","inventory":[],"titles":[]},
  "flags": {}
}
JSON
python tools/render_save.py --save _smoke_render
ls saves/_smoke_render
cat saves/_smoke_render/current_scene.md
rm -rf saves/_smoke_render
```
Expected: the `ls` shows `current_scene.md  hidden_truths.md  meta.json  player.md  session_log.jsonl  session_log.md  world_state.json`. `current_scene.md` contains a YAML frontmatter block with `turn: 0`, `location: loc_home`.

- [ ] **Step 7: Save point**

Run: `python tools/render_save.py --help | head -3`
Expected: usage line prints.

---

## Task 7: Write `tools/inspect_save.py`

**Files:**
- Create: `tools/inspect_save.py`
- Uses: `tools/_models.py`, reuses `load_save` from `render_save.py`

The purpose is a compact, one-screen text summary the agent (or a human) can read to orient quickly — not a re-render. It doesn't write files.

- [ ] **Step 1: Write the file**

```python
"""Compact, read-only summary of a save's canonical state.

Usage:
    python tools/inspect_save.py --save <save_id>

Prints turn/day/location/risk, player status, present entities,
active threads, objectives, open loops (count + titles), last narration
preview, and divergence count. Output is plain text, one save per invocation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_save import load_save
else:
    from .render_save import load_save


def format_summary(save) -> str:
    w = save.world
    p = w.player
    lines: list[str] = [
        f"save:     {save.save_id}",
        f"pack:     {save.pack_name}",
        f"turn:     {w.turn}   day: {w.day}   time: {w.time_of_day}   risk: {w.risk_level}",
        f"location: {w.current_location}",
        f"player:   {p.name} ({p.slug})  {p.cultivation_stage}  {p.status}" + (f"  sect={p.sect}" if p.sect else ""),
    ]
    if w.present_entities:
        lines.append("present:  " + ", ".join(w.present_entities))
    if w.active_threads:
        lines.append("threads:")
        for t in w.active_threads:
            lines.append(f"  - [{t.priority}] {t.id}: {t.title}")
    if w.current_objectives:
        lines.append("objectives:")
        for o in w.current_objectives:
            lines.append(f"  - {o}")
    open_items = [l for l in save.open_loops.items if l.status == "open"]
    if open_items:
        lines.append(f"open_loops ({len(open_items)}):")
        for l in open_items:
            lines.append(f"  - {l.id}: {l.title}")
    if save.session_log:
        last = save.session_log[-1]
        preview = last.narration.strip().splitlines()[0] if last.narration.strip() else ""
        lines.append(f"last turn {last.turn}: {preview[:80]}")
    if save.divergences:
        lines.append(f"divergences: {len(save.divergences)}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--save", required=True)
    p.add_argument("--saves-root", type=Path, default=Path("saves"))
    args = p.parse_args(argv)
    save_dir = args.saves_root / args.save
    if not save_dir.is_dir():
        print(f"error: save dir not found: {save_dir}", file=sys.stderr)
        return 2
    save = load_save(save_dir)
    sys.stdout.write(format_summary(save))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke-test against the fixture from Task 6 Step 6** (redo the setup)

Run the setup from Task 6 Step 6, then:
```bash
python tools/inspect_save.py --save _smoke_render
rm -rf saves/_smoke_render
```
Expected: prints 4–6 lines starting with `save:     _smoke_render`.

- [ ] **Step 3: Save point**

Run: `python tools/inspect_save.py --help | head -3`
Expected: usage prints.

---

## Task 8: Write `tools/README.md`

**Files:**
- Create: `tools/README.md`

- [ ] **Step 1: Write the exact content**

```markdown
# tools/

Optional deterministic helper scripts for the SirenGM 2 llm-wiki workflow.
None of these are required for the main product path — the agent writes and
reads files directly. They exist to make three chores cheaper than having
the agent do them by hand:

| script | purpose |
|---|---|
| `chunker.py` | Split a raw novel text file into chapter-sized chunks under `packs/<pack>/.ingest/chunks.jsonl`. Used by `playbooks/ingest.md`. |
| `lint_pack.py` | Rule-based validation of a genre pack (`--genre <name>`) or user pack (`--pack <name>`): schema, cross-refs, orphan wiki-links. |
| `render_save.py` | Re-render every markdown surface of a save (`current_scene.md`, `player.md`, `session_log.md`, `hidden_truths.md`) from the canonical JSON state. Run after every turn. |
| `inspect_save.py` | One-screen plain-text summary of a save's state. Read-only. |

All scripts are plain `python tools/<name>.py ...` — no install step required.
They only depend on `pydantic`, `pyyaml`, and `python-frontmatter`.

## Conventions

- Every script exits 0 on success, 1 on validation failure (e.g. lint issues),
  2 on usage error (missing file / bad args).
- Scripts never delete files.
- Scripts never call an LLM. They are purely deterministic.
- Scripts use the repo root as the working directory; paths default to
  `packs/`, `saves/`, and `genre_packs/` at that root. Override with the
  `--packs-root`, `--saves-root`, `--genre-packs-root` flags if needed.

## When the agent should use them

- After writing `world_state.json` for a turn → run `render_save.py`.
- After drafting pack pages in ingest → run `lint_pack.py --pack <name>`.
- When orienting on an existing save → run `inspect_save.py --save <id>`.
- At the start of ingest → run `chunker.py <novel> --pack <name>`.

When the agent should NOT use them:
- Never substitute `lint_pack.py` output for the agent's own content judgment.
  The lint catches schema and reference bugs, not narrative quality.
- Never treat the rendered markdown as authoritative. JSON wins. The markdown
  is a display surface only.
```

- [ ] **Step 2: Save point**

Run: `head -20 tools/README.md`
Expected: title + table visible.

---

## Task 9: Re-frame the genre-pack prompt files as agent-facing instructions

**Files:**
- Modify: `genre_packs/xianxia/prompts/ingest_extract_system.md`
- Modify: `genre_packs/xianxia/prompts/ingest_draft_system.md`
- Modify: `genre_packs/xianxia/prompts/gm_system_fragment.md`

The three files were written as fragments to splice into an LLM `system` message. In the new world, the agent reads them directly as playbook sub-documents. Content is correct; only the framing header needs to change.

- [ ] **Step 1: Inspect each file's current header**

Run: `head -10 genre_packs/xianxia/prompts/ingest_extract_system.md genre_packs/xianxia/prompts/ingest_draft_system.md genre_packs/xianxia/prompts/gm_system_fragment.md`
Expected: each starts with YAML frontmatter + a title line like `# Ingest Extract · Genre-level 系统提示`. The word 系统提示 ("system prompt") is the one that no longer fits.

- [ ] **Step 2: Edit `ingest_extract_system.md`**

Replace the opening paragraph below the frontmatter. Find the line `# Ingest Extract · Genre-level 系统提示` and replace with:

```markdown
# Ingest Extract · Xianxia genre instructions

These are genre-level instructions the agent follows during the **extract**
step of `playbooks/ingest.md`. Read this file once before processing any
chunk; then, for each chunk in `packs/<pack>/.ingest/chunks.jsonl`, follow
the rules below to produce a line in `packs/<pack>/.ingest/mentions.jsonl`.
```

Leave everything after that paragraph unchanged — the field-by-field rules and constraints are correct as written.

- [ ] **Step 3: Edit `ingest_draft_system.md`**

Apply the same style of edit: replace the `系统提示`-framed header with:

```markdown
# Ingest Draft · Xianxia genre instructions

These are genre-level instructions the agent follows during the **draft**
step of `playbooks/ingest.md`. For each entity discovered during extract,
consolidate mentions into a single schema-valid page under
`packs/<pack>/<kind>/<slug>.md`. Schemas live in
`genre_packs/xianxia/schemas/<kind>.schema.md`.
```

Keep all remaining body content unchanged.

- [ ] **Step 4: Edit `gm_system_fragment.md`**

Replace its opening framing with:

```markdown
# GM · Xianxia genre instructions

These are genre-level instructions the agent follows when narrating a turn
in `playbooks/play-turn.md`. They supplement the repo-root narration rules
and the user pack's `canon_guardrails.md`. When user-pack rules conflict
with genre rules, user-pack rules win.
```

Keep the rest unchanged.

- [ ] **Step 5: Re-lint the genre pack**

Run: `python tools/lint_pack.py --genre xianxia`
Expected: `ok: genre_packs/xianxia has no lint issues`. The edits should not break anything — they only touched prose body, not frontmatter or schemas.

- [ ] **Step 6: Save point**

Run: `grep -l "系统提示" genre_packs/xianxia/prompts/*.md || echo "no more 系统提示 framing"`
Expected: `no more 系统提示 framing` — the agent-facing rewrite is complete.

---

## Task 10: Write `playbooks/ingest.md`

**Files:**
- Create: `playbooks/ingest.md`

This is the playbook the agent reads when the user says "ingest `raw/novel/<file>.txt` into pack `<name>`." The content below is the whole file:

- [ ] **Step 1: Create `playbooks/` dir**

Run: `mkdir -p playbooks`
Expected: exits 0.

- [ ] **Step 2: Write `playbooks/ingest.md`**

```markdown
# Playbook · ingest

Compile a novel into a user pack. Invoked when the user says something like
"ingest `raw/novel/<file>.txt` as pack `<name>` with genre xianxia."

**Preconditions:**
- `raw/novel/<file>.txt` exists and is utf-8.
- `genre_packs/<genre>/` exists and lints clean.
- `packs/<name>/` does not exist yet, or the user has explicitly agreed to
  overwrite / resume.

**Layers touched:** creates `packs/<name>/`; reads `raw/novel/<file>.txt`
and `genre_packs/<genre>/**`; never writes `raw/`.

---

## Stage 1 · chunk

Split the novel into chapter-sized chunks. Prefer the deterministic helper:

```bash
python tools/chunker.py raw/novel/<file>.txt --pack <name>
```

This writes `packs/<name>/.ingest/chunks.jsonl`. Verify line count is sane
(a 200k-char novel should yield roughly 20–80 chunks). If the novel is
short (<5 chapters) or has no chapter markers, the chunker falls back to
~3000-char paragraph-boundary chunks.

## Stage 2 · extract

Read `genre_packs/<genre>/prompts/ingest_extract_system.md` once. Then
iterate `chunks.jsonl` chunk by chunk.

For each chunk, produce zero or more JSON objects describing mentions of
`character`, `faction`, `location`, `system_item`, `event`, `relationship`
found in the chunk. Append each as one JSON line to
`packs/<name>/.ingest/mentions.jsonl`. Include `source_chunk: <id>` and a
short `evidence` quote (≤60 chars) on every mention.

Guardrails: never fabricate entities that do not appear in the chunk; keep
slugs stable across chunks (same entity → same slug). If you're uncertain
whether two mentions refer to the same entity, emit them as separate slugs
and let Stage 4 (index) record the ambiguity.

Resumability: Stage 2 is append-only per chunk. If interrupted, inspect the
highest `source_chunk` in `mentions.jsonl` and resume from the next chunk.

## Stage 3 · draft

Read `genre_packs/<genre>/prompts/ingest_draft_system.md` once. Read the
per-kind schemas under `genre_packs/<genre>/schemas/*.schema.md`.

Group `mentions.jsonl` by `(kind, slug)`. For each group, draft a single
schema-valid page at `packs/<name>/<kind_plural>/<slug>.md`. Kinds and
their directories:

| kind | dir |
|---|---|
| character | `packs/<name>/characters/` |
| faction | `packs/<name>/factions/` |
| location | `packs/<name>/locations/` |
| arc | `packs/<name>/arcs/` |
| event | `packs/<name>/events/` |
| system_item | absorb into the relevant system page in `genre_packs/<genre>/systems/` context; do NOT create a user-pack `systems/` dir for MVP |

Every page has YAML frontmatter matching its schema and a short markdown
body synthesized from the mentions.

Guardrails:
- No numeric combat stats. Use qualitative language.
- Cross-references to other entities must use `[[slug]]` syntax.
- If mentions conflict, prefer the latest chunk and record the older claim
  under `packs/<name>/contradictions/ambiguous_points.md` (append-only).

## Stage 4 · index

Write (or regenerate) three files:

- `packs/<name>/index.md` — frontmatter `name: <name>`, `kind: user`,
  `inherits_genre: <genre>`; body links every page by category.
- `packs/<name>/relationships/relationship_matrix.md` — bullet list of
  relationship mentions grouped by `from` slug.
- `packs/<name>/contradictions/ambiguous_points.md` — any ambiguities you
  logged during draft.
- `packs/<name>/timeline.md` — chronological list of events with their
  chunk provenance.
- `packs/<name>/canon_guardrails.md` — novel-specific overrides on top of
  the genre guardrails (may be empty but must exist with a heading).
- `packs/<name>/overview.md` — 200–400 word synopsis.

## Stage 5 · lint

```bash
python tools/lint_pack.py --pack <name>
```

If issues are reported, loop back to Stage 3 for the affected pages. Do
NOT proceed to `playbooks/new-game.md` until lint is clean.

## What to tell the user at the end

Report: chunk count, mention count, page counts per kind, lint status,
and one-paragraph summary of the overall synopsis. Do NOT start a game
yet — wait for the user to invoke `playbooks/new-game.md`.
```

- [ ] **Step 3: Save point**

Run: `wc -l playbooks/ingest.md`
Expected: ~90–130 lines.

---

## Task 11: Write `playbooks/new-game.md`

**Files:**
- Create: `playbooks/new-game.md`

- [ ] **Step 1: Write the file**

```markdown
# Playbook · new-game

Bootstrap a fresh save from a compiled user pack. Invoked when the user says
"start a new game against pack `<name>`, save as `<save_id>`."

**Preconditions:**
- `packs/<name>/` exists and passes `python tools/lint_pack.py --pack <name>`.
- `saves/<save_id>/` does not exist.

## Step 1 · Pick a protagonist

Read `packs/<name>/characters/*.md`. Prefer the character with
`role: protagonist` in its frontmatter. If multiple, ask the user to pick.

## Step 2 · Propose an opening scene

Based on the protagonist's `location` (if set), the pack's `timeline.md`,
and the pack's `overview.md`, propose:

- `current_location` (slug, must exist in `packs/<name>/locations/`),
- 1–3 `present_entities` (slugs),
- 1–2 `active_threads` (short titles; `priority: active`),
- 1–2 `current_objectives` (short strings),
- `risk_level` (`calm` / `tense` / `dangerous` / `lethal`).

Ask the user to confirm before writing anything.

## Step 3 · Write the canonical save JSONs

Create `saves/<save_id>/` and write:

- `meta.json` — `{"save_id": "<save_id>", "pack_name": "<name>", "hidden_truths": ""}`
- `world_state.json` — the schema is defined in `tools/_models.py::WorldState`.
  Fields: `turn: 0`, `day: 0`, `time_of_day: "morning"`, `current_location`,
  `present_entities`, `active_threads`, `current_objectives`, `risk_level`,
  `player` (mirrors chosen protagonist entity), `flags: {}`.
- `relationship_state.json` — `{"by_slug": {}}` (empty; populated as the
  player meets NPCs).
- `open_loops.json` — `{"items": []}`.
- `player.json` — duplicate of `world_state.json::player`.
- `session_log.jsonl` — empty file (`touch` it).
- `divergences.jsonl` — empty file.

## Step 4 · Render markdown surfaces

```bash
python tools/render_save.py --save <save_id>
```

This creates `current_scene.md`, `player.md`, `session_log.md`,
`hidden_truths.md`.

## Step 5 · Confirm

```bash
python tools/inspect_save.py --save <save_id>
```

Paste the output back to the user. Then wait for the first turn per
`playbooks/play-turn.md`.
```

- [ ] **Step 2: Save point**

Run: `wc -l playbooks/new-game.md`
Expected: ~50–70 lines.

---

## Task 12: Write `playbooks/play-turn.md`

**Files:**
- Create: `playbooks/play-turn.md`

This is the most consequential playbook: it replaces the archived two-call runtime loop. The agent **is** the narrator and state updater; the playbook describes the discipline that keeps structured state and narration in sync.

- [ ] **Step 1: Write the file**

```markdown
# Playbook · play-turn

One turn of gameplay against a save. Invoked implicitly whenever the user
types in-game text (e.g. "我走进药阁问掌柜").

## Load context

Before reading the user's turn input, load:

1. `saves/<id>/world_state.json`, `relationship_state.json`, `open_loops.json`.
2. Last 6 entries of `saves/<id>/session_log.jsonl` (`tail -n 6`).
3. `saves/<id>/hidden_truths.md`.
4. `packs/<name>/index.md`; then, for each slug in
   `world_state.present_entities` and `current_location`, read its page.
5. For each `active_threads[*].id`, if it maps to an arc slug, read that
   arc page.
6. `genre_packs/<genre>/style_guide.md`,
   `genre_packs/<genre>/canon_guardrails.md`,
   `genre_packs/<genre>/prompts/gm_system_fragment.md`, and
   `packs/<name>/canon_guardrails.md`.

**Never** scrape `current_scene.md` or `session_log.md` for scene state.
Those are display surfaces; they can drift. The JSON files are canonical.

## Step 1 · Narrate

Using the loaded context, write 150–400 characters of Chinese prose
responding to the user's input. Style follows `style_guide.md`. Guardrails:

- Do not violate `canon_guardrails.md` (genre or pack).
- Do not skip cultivation stages.
- Do not introduce modern technology, numeric combat stats, or
  meta-commentary.
- Do not introduce a novel entity slug without an `emergent:` prefix.
- Do not silently invent facts that should be in structured state
  (see Step 2).

## Step 2 · Patch structured state

Produce a patch that covers everything the narration implies. A patch is a
JSON object with these optional top-level keys:

- `world_state` — partial `WorldState` fields to overwrite (turn auto-advances
  by 1 unless `advance_turn: false`).
- `present_entities_add` / `present_entities_remove` — lists of slugs.
- `active_threads_add` / `active_threads_remove` — items / ids.
- `objectives_add` / `objectives_remove` — strings.
- `relationship_updates` — `{slug: {affinity_delta?, trust_delta?, status?, notes?}}`.
- `open_loops_add` — full `OpenLoop` entries.
- `open_loops_close` — list of loop ids.
- `inventory_add` / `inventory_remove` — items / slugs.
- `hidden_truths_append` — paragraph to append to `hidden_truths.md`.
- `divergence` — `{reason, detail}` to append to `divergences.jsonl` when
  the narration implied something the patch can't faithfully encode.

Apply the patch to the in-memory state. Validate using the schemas in
`tools/_models.py` — if validation fails, drop the invalid sub-patch and
log a divergence; do not abort the turn.

Slug-existence rule: any slug referenced in a patch (entity, location,
thread arc id) must exist in `packs/<name>/` or start with `emergent:`.
If neither holds, drop the sub-patch and log a divergence.

## Step 3 · Persist

Write the updated:
- `world_state.json` (with `turn += 1`),
- `relationship_state.json`,
- `open_loops.json`,
- `player.json` (mirror of `world_state.player`),
- append one entry to `session_log.jsonl`:
  `{turn, at, player_input, narration, summary}`.

If `hidden_truths_append` was used, append to `hidden_truths.md`.
If `divergence` was used, append to `divergences.jsonl`.

## Step 4 · Re-render markdown

```bash
python tools/render_save.py --save <id>
```

This regenerates `current_scene.md`, `player.md`, `session_log.md`,
`hidden_truths.md` from JSON.

## Step 5 · Respond to the user

Output **only** the narration from Step 1 to the user. The JSON writes and
`render_save.py` call happen before the reply; the user sees prose, not
state. On request, the user can ask `python tools/inspect_save.py --save <id>`
to inspect.

## Failure handling

- If the user's input is out-of-character (meta, tool-use, debugging),
  handle it as a tooling request — do not treat it as in-world action and
  do not advance the turn counter.
- If state validation fails catastrophically (e.g. the on-disk JSON is
  malformed), stop and tell the user. Never overwrite a malformed state
  with a guess.
```

- [ ] **Step 2: Save point**

Run: `wc -l playbooks/play-turn.md`
Expected: ~95–130 lines.

---

## Task 13: Write `playbooks/lint.md`

**Files:**
- Create: `playbooks/lint.md`

- [ ] **Step 1: Write the file**

```markdown
# Playbook · lint

Health checks, invoked when the user says "lint the pack" or "lint the save."

## Pack lint

```bash
python tools/lint_pack.py --pack <name>
python tools/lint_pack.py --genre xianxia
```

Exit 0 = clean. Exit 1 = issues listed on stdout. Categorize issues:

- **Schema violations** (frontmatter missing required fields) — fix the page.
- **Cross-ref violations** (unknown sect / leader / location slug) — either
  create the missing entity page or correct the slug on the referring page.
- **Orphan wiki-links** (`[[slug]]` with no matching entity) — same fix.
- **Genre purity violations** (novel-specific content in a genre pack) —
  move it into a user pack. Genre packs are templates, never novel data.

Do not silence lint by editing `tools/lint_pack.py`. If a rule is wrong,
discuss with the user and update the rule intentionally.

## Save lint

There is no dedicated save-lint script in the current tools layer. To
lint a save, read it via `python tools/inspect_save.py --save <id>` and
verify by hand:

- `turn` matches `len(session_log.jsonl)`.
- Every slug in `present_entities`, `current_location`,
  `active_threads[*].id` (when it maps to an arc), and inventory items
  exists in `packs/<pack_name>/` or begins with `emergent:`.
- `relationships.by_slug` keys are all known entity slugs.
- `divergences.jsonl` line count is not suspiciously high (>10 in a 20-turn
  game suggests narrator/patcher discipline problems).

Report findings; do not auto-fix save state without user confirmation.
```

- [ ] **Step 2: Save point**

Run: `ls playbooks`
Expected: `ingest.md  lint.md  new-game.md  play-turn.md`.

---

## Task 14: Rewrite `CLAUDE.md` as the operating schema

**Files:**
- Modify: `CLAUDE.md` (complete rewrite; preserve section spirit, replace Python-app specifics)

The existing `CLAUDE.md` documents the two-call Python runtime. The new `CLAUDE.md` documents the file layout, layer hierarchy, canonical-state rule, and points to `playbooks/` for workflows.

- [ ] **Step 1: Read the existing `CLAUDE.md`**

Run: `wc -l CLAUDE.md`
Expected: ~150–180 lines. Skim to confirm which sections survive intact.

- [ ] **Step 2: Overwrite with the new version**

Write this exact content to `CLAUDE.md`:

```markdown
# CLAUDE.md — Operating schema for SirenGM 2

Read this before doing anything in this repo. Codex users: `AGENTS.md`
points here.

## The thesis

**AI compiles a novel into a playable world.** A user drops a xianxia
(修仙) novel into `raw/novel/`, asks the agent to ingest it, and the
agent produces a user pack under `packs/<name>/`. The user then plays
turns against that pack + a save in `saves/<id>/`, and the agent
maintains both the pack and the save over the course of the run.

We are validating: a 20–50-turn run against an ingested pack feels
coherent. We are NOT validating "play inside a prebuilt world." There is
no product-path demo pack; the main path is ingest.

## The operating layers

```
raw/novel/             — immutable, user-provided source text
genre_packs/<genre>/   — reusable template (style, guardrails, schemas, systems)
packs/<user_pack>/     — AI-compiled wiki: characters, factions, locations, arcs, events
saves/<save_id>/       — per-run canonical JSON state + rendered markdown
```

- **raw/** is never modified by the agent. Sources are immutable.
- **genre_packs/** is reusable across novels; never contains novel-specific
  characters/places/timelines. xianxia ships in MVP.
- **packs/<name>/** is written by the agent during ingest and occasionally
  amended when play uncovers genuine contradictions.
- **saves/<id>/** is written by the agent after every turn.

The agent (Claude Code or Codex) is the runtime. There is no Python
process that drives the turn loop; the agent reads files, calls its
model, and writes files. A thin `tools/` layer provides deterministic
helpers (chunker, lint, render, inspect) but is optional. The archived
Python app under `archive/legacy_python_app/` is kept for reference
only; do not run it.

## Canonical state rule

**Structured JSON is the source of truth.** Markdown surfaces in a save
are **re-rendered** from structured state after every patch.

Canonical files in `saves/<save_id>/`:
- `world_state.json` — must contain `current_location`, `present_entities`,
  `active_threads`, `current_objectives`, `risk_level`, plus `turn`, `day`,
  `time_of_day`, `flags`, `player`. Schema: `tools/_models.py::WorldState`.
- `relationship_state.json` — per-slug `{affinity, trust, status, last_interaction_turn, notes}`.
- `open_loops.json`
- `player.json` (mirror of `world_state.player`)
- `meta.json` (`save_id`, `pack_name`, `hidden_truths`)
- `session_log.jsonl` — append-only authoritative turn record.
- `divergences.jsonl` — append-only record of dropped patches.

Rendered (non-authoritative) surfaces in `saves/<save_id>/`:
- `current_scene.md`, `player.md`, `session_log.md`, `hidden_truths.md`.
- Regenerated by `python tools/render_save.py --save <id>` after every turn.

**If the narration and structured state disagree, structured state wins.**
Either promote the narrative fact into a structured field via the patch,
or drop it and append a `DivergenceNote`. Never silently accept narrative
facts into state.

**Scene context is derived from structured fields**, never by scraping
markdown. The agent looks up entities via `world_state.present_entities`
+ `current_location` + `active_threads`, not by matching slugs against
prose.

## Pack schema

### Genre pack (`genre_packs/<name>/`)

- `index.md` — frontmatter `name`, `kind: genre`, `version`.
- `style_guide.md` — narrative conventions.
- `canon_guardrails.md` — genre-level rules (no cultivation-stage skipping,
  no modern tech, etc.).
- `systems/*.md` — genre mechanics.
- `schemas/*.schema.md` — frontmatter contracts for user-pack entity kinds.
- `prompts/*.md` — agent-facing instruction files for extract, draft, and
  narration (read by the agent during the relevant playbook).

**Forbidden** under genre packs: `characters/`, `factions/`, `locations/`,
`arcs/`, `events/`. The lint (`tools/lint_pack.py --genre <name>`) enforces
this.

### User pack (`packs/<user_pack>/`)

- `index.md` — frontmatter `name`, `kind: user`, `inherits_genre: <genre>`.
- `overview.md`, `canon_guardrails.md` (novel-specific overrides),
  `timeline.md`.
- `characters/<slug>.md`, `factions/<slug>.md`, `locations/<slug>.md`,
  `arcs/<slug>.md`, `events/<slug>.md`.
- `relationships/relationship_matrix.md`.
- `contradictions/ambiguous_points.md`.
- `.ingest/` — chunker/extract checkpoints (`chunks.jsonl`, `mentions.jsonl`).

Entity frontmatter fields are defined by Pydantic models in
`tools/_models.py`. Any field named there is canonical; extras pass
through but don't participate in validation.

## Workflows

The agent follows these playbooks:

- `playbooks/ingest.md` — compile a novel into a pack (chunk → extract → draft → index → lint).
- `playbooks/new-game.md` — bootstrap a save from a pack.
- `playbooks/play-turn.md` — the two-step turn loop (narrate → patch → persist → render).
- `playbooks/lint.md` — health checks.

The agent reads the relevant playbook at the start of the work.

## Tools

Optional, deterministic, offline. Never call an LLM.

| tool | when |
|---|---|
| `python tools/chunker.py <novel> --pack <name>` | ingest, stage 1 |
| `python tools/lint_pack.py --pack <name>` or `--genre xianxia` | after drafting pack pages; on demand |
| `python tools/render_save.py --save <id>` | after every turn |
| `python tools/inspect_save.py --save <id>` | on demand to summarize a save |

All tools have `--help`. See `tools/README.md`.

## Adding a new genre

1. `mkdir genre_packs/<name>/` and populate with `index.md` (`kind: genre`),
   `style_guide.md`, `canon_guardrails.md`, `systems/*.md`,
   `schemas/*.schema.md`, `prompts/ingest_extract_system.md`,
   `prompts/ingest_draft_system.md`, `prompts/gm_system_fragment.md`.
2. `python tools/lint_pack.py --genre <name>` to verify purity.
3. User packs declare `inherits_genre: <name>` in their `index.md`.

Do not include novel-specific characters/places/timelines in a genre
pack, even as "examples." That's what user packs are for.

## Local dev quirks

- macOS `hidden` flag on `.venv` files: if you do `uv pip install -e .`,
  run `chflags -R nohidden .venv` after — Python 3.10's `site.py` skips
  `.pth` files flagged hidden.
- Python 3.10+ for the tools. No other runtime is required.

## Things not to do

- Do not reintroduce a hand-authored product-path user pack. The only
  hand-authored pack in the repo is the archived
  `archive/legacy_python_app/tests/fixtures/mini_user_pack/`, which is a
  legacy test fixture — not a product path.
- Do not scrape markdown for scene state. The JSON files are canonical.
- Do not expand MVP scope without asking (multi-genre beyond xianxia,
  new CLI apps, web UI, combat formulas — all deferred).
- Do not silently accept narrator facts the state patch cannot express.
  Drop them and log a `DivergenceNote`.
- Do not reinstate the Python app as the product path. If a helper is
  missing, add a new script under `tools/`, not a new CLI.
- Do not call `tools/` scripts on anything under `raw/` — those files
  are immutable input.
```

- [ ] **Step 3: Save point**

Run: `wc -l CLAUDE.md && head -5 CLAUDE.md`
Expected: new file length ~160–200 lines; first heading is `# CLAUDE.md — Operating schema for SirenGM 2`.

---

## Task 15: Create `AGENTS.md` as the Codex entry point

**Files:**
- Create: `AGENTS.md`

- [ ] **Step 1: Write the file**

```markdown
# AGENTS.md — Codex entry point

Read [`CLAUDE.md`](./CLAUDE.md) first. Every rule in that file applies to
Codex sessions as well as Claude Code sessions.

The only Codex-specific notes:

- Codex's file tools behave the same as Claude Code's for this repo's
  purposes. Read, Write, Edit, Grep, Glob, and Bash are all fine.
- When running `tools/*.py`, use the repo root as the working directory.
- Don't use Codex's agent-mode scaffolding to re-invoke a "sirengm CLI" —
  there isn't one. The product path is you reading `CLAUDE.md` and the
  relevant `playbooks/<op>.md`.
```

- [ ] **Step 2: Save point**

Run: `cat AGENTS.md | head -5`
Expected: title + first body line visible.

---

## Task 16: Rewrite `README.md` for the file-driven workflow

**Files:**
- Modify: `README.md` (complete rewrite)

- [ ] **Step 1: Read the current README**

Run: `wc -l README.md`
Expected: ~125 lines. It's CLI-centric — everything below "Install" and the CLI table needs to go.

- [ ] **Step 2: Overwrite with the new version**

```markdown
# SirenGM 2

A file-driven, agent-native MVP that validates:

> **AI can compile a user-uploaded xianxia novel into a runnable Story Pack,
> and an agent (Claude Code or Codex) can then run a coherent 20–50-turn
> game against that pack with persistent state across save/load.**

The thesis is **"compile novel → playable world,"** not "play inside a
prebuilt world." There is no ready-made sample pack — the main path is
ingest.

Adapted from the [llm-wiki](./llm-wiki.md) pattern: raw sources are
immutable, the pack is an LLM-maintained persistent middle layer, and
runtime reads from the compiled pack + structured save instead of
re-deriving from raw text on every turn.

## Architecture

```
  raw/novel/             ←  your novel text (immutable)
        │
        │  agent reads playbooks/ingest.md
        ▼
  genre_packs/xianxia/   ←  reusable genre template (style, guardrails,
                            systems, schemas, agent-facing prompts)
        │ +
        ▼
  packs/<user_pack>/     ←  generated user pack (characters, factions,
                            locations, arcs, events) specific to your novel
        │ +
        ▼
  saves/<save_id>/       ←  per-run state
                            •  world_state.json   (CANONICAL)
                            •  relationship_state.json   (CANONICAL)
                            •  open_loops.json   (CANONICAL)
                            •  player.json   (CANONICAL)
                            •  session_log.jsonl   (CANONICAL, append-only)
                            •  current_scene.md / session_log.md / ...   (rendered only)
```

**Rule of the architecture:** structured JSON is the single source of
truth. Markdown surfaces are re-rendered from JSON after every patch. If
narrator prose and structured state disagree, structured state wins.

## How to use it

1. Open this folder in Claude Code (or Codex).
2. Drop a xianxia novel into `raw/novel/`:
   ```bash
   cp my_xianxia.txt raw/novel/my_xianxia.txt
   ```
3. Tell the agent:
   > "Ingest `raw/novel/my_xianxia.txt` as pack `mypack`, genre xianxia."

   The agent reads [`CLAUDE.md`](./CLAUDE.md) and
   [`playbooks/ingest.md`](./playbooks/ingest.md) and compiles the novel
   into `packs/mypack/`. Expect 10–60 minutes depending on novel length.
4. When ingest is done, tell the agent:
   > "Start a new game against pack `mypack`, save as `save_001`."

   It reads [`playbooks/new-game.md`](./playbooks/new-game.md) and writes
   `saves/save_001/`.
5. Play turns by sending in-character text. The agent follows
   [`playbooks/play-turn.md`](./playbooks/play-turn.md).

There is no CLI. The agent is the CLI.

## Optional deterministic tools

A thin `tools/` layer helps the agent with chores. None are required.

| script | purpose |
|---|---|
| `python tools/chunker.py <novel> --pack <name>` | Split raw novel into chapter chunks. |
| `python tools/lint_pack.py --pack <name>` | Validate a user or genre pack. |
| `python tools/render_save.py --save <id>` | Re-render markdown surfaces from JSON. |
| `python tools/inspect_save.py --save <id>` | Compact state summary. |

Install dependencies once (optional):
```bash
uv venv --python 3.10 .venv
uv pip install pydantic pyyaml python-frontmatter
# macOS-in-Documents quirk:
chflags -R nohidden .venv
```

See [`tools/README.md`](./tools/README.md) and the playbooks.

## What's out of scope for MVP

- Multi-genre (only xianxia). Other genres are a future
  `genre_packs/<name>/` addition.
- Multiplayer, accounts, network services.
- Web UI, TUI.
- Numeric combat systems, damage formulas.
- Images, voice, avatars.
- Vector DB / embeddings — index-scan over the pack is enough at MVP scale.
- Any novel producing a "perfect" pack. The thesis is that ingest produces
  a *runnable* pack with minor manual polish, not a flawless one.

## Directory layout

```
Project SirenGM 2/
  CLAUDE.md                — operating schema
  AGENTS.md                — Codex entry point
  README.md                — this file
  llm-wiki.md              — design inspiration

  genre_packs/xianxia/     — reusable xianxia template
  raw/novel/               — drop your novel text here (immutable)
  packs/                   — generated user packs
  saves/                   — per-run save states

  playbooks/               — workflow instructions for the agent
  tools/                   — optional deterministic helper scripts
  docs/                    — plans and design docs

  archive/legacy_python_app/  — prior Python-CLI implementation (reference only)
```
```

- [ ] **Step 3: Save point**

Run: `head -5 README.md && echo --- && grep -c '`sirengm' README.md || true`
Expected: new title visible; `grep -c` prints `0` (the old `sirengm` CLI references are gone).

---

## Task 17: End-to-end smoke-test of the new workflow

**Files:**
- Create (temporarily): `raw/novel/_smoke.txt`
- Create (temporarily): `packs/_smoke/` via `tools/chunker.py`
- No permanent changes.

Purpose: exercise the new flow with the tools and playbooks actually in place, to shake out any path bugs, missing dir creation, or broken imports.

- [ ] **Step 1: Write a tiny fake novel**

```bash
cat > raw/novel/_smoke.txt <<'NOVEL'
第一章 山门
张三十五岁这日，踏入青云门山门。师尊抚须道：「后辈可堪造就。」

第二章 炼气
入门三月，张三勉强凝气成丝，却听说师兄李四已入气感期三层。
NOVEL
```

- [ ] **Step 2: Chunk it**

Run: `python tools/chunker.py raw/novel/_smoke.txt --pack _smoke`
Expected: `wrote 2 chunks to packs/_smoke/.ingest/chunks.jsonl`.

- [ ] **Step 3: Lint the genre pack**

Run: `python tools/lint_pack.py --genre xianxia`
Expected: `ok: genre_packs/xianxia has no lint issues`.

- [ ] **Step 4: Write a minimal hand-authored user pack** (skipping the real ingest — that's the agent's job at runtime, not the plan's)

```bash
mkdir -p packs/_smoke/characters packs/_smoke/factions packs/_smoke/locations packs/_smoke/relationships packs/_smoke/contradictions
cat > packs/_smoke/index.md <<'MD'
---
name: _smoke
kind: user
inherits_genre: xianxia
---

# _smoke

Smoke-test pack generated by docs/superpowers/plans/2026-04-15-llm-wiki-refactor.md Task 17.
MD
cat > packs/_smoke/overview.md <<'MD'
# Overview

A two-chapter smoke test.
MD
cat > packs/_smoke/canon_guardrails.md <<'MD'
# Pack canon guardrails

(none)
MD
cat > packs/_smoke/timeline.md <<'MD'
# Timeline

1. 张三入青云门。
2. 张三勉强凝气成丝。
MD
cat > packs/_smoke/characters/zhang_san.md <<'MD'
---
slug: zhang_san
name: 张三
role: protagonist
sect: qingyun_sect
location: qingyun_mountain
---

# 张三

Protagonist.
MD
cat > packs/_smoke/factions/qingyun_sect.md <<'MD'
---
slug: qingyun_sect
name: 青云门
seat: qingyun_mountain
leaders: []
alignment: orthodox
---

# 青云门
MD
cat > packs/_smoke/locations/qingyun_mountain.md <<'MD'
---
slug: qingyun_mountain
name: 青云山
kind: mountain
controlled_by: qingyun_sect
---

# 青云山
MD
cat > packs/_smoke/relationships/relationship_matrix.md <<'MD'
# Relationships

(none yet)
MD
cat > packs/_smoke/contradictions/ambiguous_points.md <<'MD'
# Ambiguous points

(none)
MD
```

- [ ] **Step 5: Lint the user pack**

Run: `python tools/lint_pack.py --pack _smoke`
Expected: `ok: packs/_smoke has no lint issues`. If it reports missing fields, check each entity frontmatter against `genre_packs/xianxia/schemas/<kind>.schema.md` and `tools/_models.py` and fix the fixture here in the plan — this means the smoke test caught a real schema drift.

- [ ] **Step 6: Bootstrap a save**

```bash
mkdir -p saves/_smoke_save
cat > saves/_smoke_save/meta.json <<'JSON'
{"save_id": "_smoke_save", "pack_name": "_smoke", "hidden_truths": ""}
JSON
cat > saves/_smoke_save/world_state.json <<'JSON'
{
  "turn": 0, "day": 0, "time_of_day": "morning",
  "current_location": "qingyun_mountain",
  "present_entities": ["zhang_san"],
  "active_threads": [{"id":"t_induction","title":"入门","priority":"active"}],
  "current_objectives": ["熟悉青云门"],
  "risk_level": "calm",
  "player": {"slug":"zhang_san","name":"张三","sect":"qingyun_sect","cultivation_stage":"气感期一层","status":"alive","inventory":[],"titles":[]},
  "flags": {}
}
JSON
echo '{"by_slug": {}}' > saves/_smoke_save/relationship_state.json
echo '{"items": []}' > saves/_smoke_save/open_loops.json
cat saves/_smoke_save/world_state.json | python -c 'import json,sys; d=json.load(sys.stdin); json.dump(d["player"], open("saves/_smoke_save/player.json","w"), ensure_ascii=False)'
: > saves/_smoke_save/session_log.jsonl
```

- [ ] **Step 7: Render markdown surfaces**

Run: `python tools/render_save.py --save _smoke_save`
Expected: `re-rendered markdown surfaces for saves/_smoke_save`.
Then: `grep -E '^- \*\*Location\*\*' saves/_smoke_save/current_scene.md`
Expected: the line mentions `qingyun_mountain`.

- [ ] **Step 8: Inspect**

Run: `python tools/inspect_save.py --save _smoke_save`
Expected: five-plus lines starting with `save:     _smoke_save`.

- [ ] **Step 9: Clean up smoke artifacts**

```bash
rm -rf packs/_smoke saves/_smoke_save raw/novel/_smoke.txt
```
Expected: `ls packs saves raw/novel` returns only pre-existing content.

- [ ] **Step 10: Save point — final verification**

Run:
```bash
ls CLAUDE.md AGENTS.md README.md llm-wiki.md pyproject.toml
ls playbooks tools genre_packs packs saves raw archive
test -d archive/legacy_python_app/src/sirengm
test ! -e src && test ! -e tests
python tools/lint_pack.py --genre xianxia
```
Expected: all listed paths exist; legacy Python app is archived, not at root; genre lint is clean.

---

## Self-review (checked at plan-write time)

**Spec coverage:**
- User requirement 1 (Claude Code / Codex as main runtime): Task 14 (CLAUDE.md rewrite), Task 15 (AGENTS.md), Tasks 10–13 (playbooks). ✓
- User requirement 2 (CLAUDE.md as core operating schema): Task 14. ✓
- User requirement 3 (genre_packs/xianxia/ as reusable template): kept intact; Task 9 only re-frames prompt headers. ✓
- User requirement 4 (raw/novel/ immutable): Tasks 10 (ingest.md) + 14 (CLAUDE.md) both state this; no task writes to `raw/`. ✓
- User requirement 5 (packs/<user_pack>/ as AI-compiled wiki): Tasks 10 (ingest playbook) + 5 (lint) cover its shape. ✓
- User requirement 6 (saves/<save_id>/ as persistent game state): Tasks 11 (new-game) + 12 (play-turn) + 6 (render) cover its shape. ✓
- Thin `tools/` with chunker / lint_pack / render_save / inspect_save: Tasks 4, 5, 6, 7. ✓
- Tools are optional helpers, not main path: Task 2 (slim pyproject), Task 8 (tools/README.md first paragraph), Task 14 (CLAUDE.md "Tools" section). ✓
- Remove or archive the Python app: Task 1. ✓
- Rewrite the implementation plan: this document. ✓

**Placeholder scan:** no TBDs, TODOs, "fill in later," "handle edge cases," or "similar to Task N." Every step specifies files and expected outputs.

**Type consistency:** `WorldState`, `Save`, `Relationship`, `OpenLoop`, `SessionLogEntry`, `DivergenceNote` names are used identically across Tasks 3, 6, 7, 11, 12, 14. The patch keys in `playbooks/play-turn.md` (`world_state`, `present_entities_add`, etc.) are the agent's interface; they are the agent's responsibility to construct, and do not require matching Pydantic models in `tools/_models.py` — the models validate the *resulting* state, not the patch verbs.

**Gaps intentionally left:** no equivalent of the archived `save/patch.py` or `runtime/*` modules is ported. That logic is now the agent's job per `playbooks/play-turn.md`. This is the point of the refactor, not a miss.
