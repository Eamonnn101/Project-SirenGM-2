# raw/novel/

Drop a novel text file here (plain `.txt`, UTF-8) — any genre,
Chinese or English only. Then open the repo in Claude Code or Codex
and tell the agent:

> "导入小说" / "Ingest novels"

That scans this directory and turns each file into its own pack.

To name a single pack yourself instead of letting the filename pick
the slug:

> "将 `raw/novel/yourfile.txt` 导入为 pack `yourpack`" /
> "Ingest `raw/novel/yourfile.txt` as pack `yourpack`"

(To override the auto-detected language, add "，用中文" / "，用英文"
in Chinese, or "...in Chinese" / "...in English" in English.)

The agent follows [`playbooks/ingest.md`](../../playbooks/ingest.md)
and writes the compiled user pack into `packs/<yourpack>/`, with
intermediate checkpoints under `packs/<yourpack>/.ingest/`.

This directory is **immutable source of truth**: the agent and `tools/`
scripts read from it but never write back. If a source file changes,
the next ingest picks it up — no in-place edits.

Your novel file is not checked into git (`raw/novel/*` is ignored
except this README). That's intentional: source texts are your
property, not the repo's.
