# tools/

Optional deterministic helper scripts for the SirenGM 2 workflow.
None of these are required for the main product path — the agent writes and
reads files directly. They exist to make three chores cheaper than having
the agent do them by hand:

| script | purpose |
|---|---|
| `chunker.py` | Split a raw novel text file into chapter-sized chunks under `packs/<pack>/.ingest/chunks.jsonl`. Used by `playbooks/ingest.md`. |
| `checkpoint_save.py` | Apply a compact backup patch to a save, append detailed session-log entries, append a new `context_summary.md` segment whenever 10+ turns have slid out without summary, and optionally render/lint once at the end. |
| `lint_pack.py` | Rule-based validation of a genre pack (`--genre <name>`) or user pack (`--pack <name>`): required files, schema, cross-refs, orphan wiki-links, bare slugs on non-ASCII-named entities. |
| `lint_save.py` | Rule-based validation of a save (`--save <pack>/<save_id>`): JSON legality, `turn ≡ len(session_log)`, `player.json ≡ world_state.player`, rendered-surface drift, `hidden_truths` consistency, slug existence against the pack. |
| `render_save.py` | Re-render every markdown surface of a save (`current_scene.md`, `player.md`, detailed-window `session_log.md`, `hidden_truths.md`) from the canonical JSON state. Full `session_log.jsonl` remains the archive. |

Saves live at `saves/<pack>/<save_id>/`, so the canonical `--save`
argument is `<pack>/<save_id>` (e.g. `mypack/save_001`). The `--save`
value is joined onto `saves_root` as-is, so any path under `saves/`
works — a bare `<save_id>` still resolves if that directory exists.

All scripts are plain `python tools/<name>.py ...` — no install step required.
They only depend on `pydantic`, `pyyaml`, and `python-frontmatter`.

If your shell has no global `python`, substitute `.venv/bin/python` (or
`uv run python`). Every example in this file, the playbooks, and
`CLAUDE.md` uses the bare `python` form for brevity; both forms are
equivalent.

## Conventions

- Every script exits 0 on success, 1 on validation failure (e.g. lint issues),
  2 on usage error (missing file / bad args).
- Scripts never delete files.
- Scripts never call an LLM. They are purely deterministic.
- Scripts use the repo root as the working directory; paths default to
  `packs/`, `saves/`, and `genre_packs/` at that root. Override with the
  `--packs-root`, `--saves-root`, `--genre-packs-root` flags if needed.

## When the agent should use them

- For backup persistence → prefer
  `checkpoint_save.py --save <pack>/<save_id> --patch <patch.json> --render --lint`.
- After manual backup JSON edits → run `render_save.py`, then `lint_save.py`.
- After drafting pack pages in ingest → run `lint_pack.py --pack <pack>`.
- When orienting on an existing save → open `current_scene.md` + `player.md`.
- When recovering from disk after losing conversation context → read
  `context_summary.md` and `session_log.md` (latest ten detailed
  turns), plus `current_scene.md` + `player.md` for the present state.
- At the start of ingest → run `chunker.py <novel> --pack <pack>`.
- Before relying on any save (e.g. for a save/load check) → run `lint_save.py --save <pack>/<save_id>`.

`checkpoint_save.py` accepts either one patch object or a `{"turns": [...]}`
wrapper. Supported keys are `world_state`, `flags_merge`,
`relationship_updates`, `open_loops_add`, `open_loops_update`,
`open_loops_close`, `hidden_truths_append`, `session_log_entries`,
and `context_summary_rewrite`. The detail window is the latest 10
turns. When 10+ turns have slid out of that window without summary,
the next patch must include exactly one `context_summary_rewrite`
covering the indicated range; the helper appends it as a new segment
to `context_summary.md`. Below the threshold, omit the field —
existing segments are never edited.

When the agent should NOT use them:
- Never substitute `lint_pack.py` output for the agent's own content judgment.
  The lint catches schema and reference bugs, not narrative quality.
- Never treat the rendered markdown as authoritative. JSON wins. The markdown
  is a display surface only.
- Never read `session_log.jsonl` into the prompt to continue play. It is the
  complete archive for lint, audit, and replay tooling.
