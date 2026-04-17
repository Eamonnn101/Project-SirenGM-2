# raw/novel/

Drop a novel text file here (plain `.txt`, UTF-8) — any genre, any
language. Then open the repo in Claude Code or Codex and tell the
agent:

> "Ingest `raw/novel/yourfile.txt` as pack `yourpack`."

(If you want to override the auto-detected language, add
"...in <language>" to the request.)

The agent follows [`playbooks/ingest.md`](../../playbooks/ingest.md)
and writes the compiled user pack into `packs/<yourpack>/`, with
intermediate checkpoints under `packs/<yourpack>/.ingest/`.

This directory is **immutable source of truth**: the agent and `tools/`
scripts read from it but never write back. If a source file changes,
the next ingest picks it up — no in-place edits.

Your novel file is not checked into git (`raw/novel/*` is ignored
except this README). That's intentional: source texts are your
property, not the repo's.
