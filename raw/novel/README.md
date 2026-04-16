# raw/novel/

Drop a xianxia novel text file here (plain `.txt`, UTF-8). Then open the
repo in Claude Code or Codex and tell the agent:

> 把 `raw/novel/yourfile.txt` 按 xianxia 编译成 pack `yourpack`。

The agent follows [`playbooks/ingest.md`](../../playbooks/ingest.md) and
writes the compiled user pack into `packs/<yourpack>/`, with intermediate
checkpoints under `packs/<yourpack>/.ingest/`.

This directory is **immutable source of truth**: the agent and `tools/`
scripts read from it but never write back. If a source file changes, the
next ingest picks it up — no in-place edits.

Your novel file is not checked into git (`raw/novel/*` is ignored except
this README). That's intentional: source texts are your property, not
the repo's.
