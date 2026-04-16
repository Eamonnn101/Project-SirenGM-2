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
