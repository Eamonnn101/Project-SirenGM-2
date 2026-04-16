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
