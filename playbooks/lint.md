# Playbook · lint

Health checks, invoked when the user says "lint the pack" or "lint the save."

## Pack lint

```bash
python tools/lint_pack.py --pack <name>
python tools/lint_pack.py --genre universal
```

Exit 0 = clean. Exit 1 = issues listed on stdout. Categorize issues:

- **Schema violations** (frontmatter missing required fields — including
  `language` on user packs) — fix the page.
- **Cross-ref violations** (unknown affiliation / leader / location slug)
  — either create the missing entity page or correct the slug on the
  referring page.
- **Orphan wiki-links** (`[[slug]]` or `[[slug|Display]]` with no
  matching entity) — same fix.
- **Bare slug on non-ASCII-named entity** (e.g. `[[xiao_yan]]`
  pointing at an entity whose `name` is `萧炎`) — rewrite the
  reference as `[[xiao_yan|萧炎]]`. The slug stays canonical; the
  display label keeps prose readable.
- **Genre purity violations** (novel-specific content in the universal
  genre pack) — move it into the user pack's `novel_rules.md`. Genre
  packs are templates, never novel data.
- **Missing `progression_rules.md` sections** — the file must
  contain all 7 required H2 sections (stages, breakthrough
  triggers per stage, artifact archetypes, innate archetypes,
  destiny seeds, health ladder wording, breakthrough voice). Add
  the missing sections per `genre_packs/universal/systems/` +
  `genre_packs/universal/prompts/ingest_draft_system.md`.

Do not silence lint by editing `tools/lint_pack.py`. If a rule is wrong,
discuss with the user and update the rule intentionally.

## Save lint

```bash
python tools/lint_save.py --save <pack>/<save_id>
```

This checks:

- Every canonical JSON file parses and passes the Pydantic schemas.
- `world_state.turn` equals `len(session_log.jsonl)`.
- `player.json` equals `world_state.player`.
- `current_scene.md` frontmatter (turn/day/time_of_day/location/risk_level)
  matches `world_state.json` — drift means someone edited the markdown
  directly or forgot to re-run `render_save.py`.
- `hidden_truths.md` equals the render of `meta.json::hidden_truths`.
- Every slug in `current_location`, `present_entities`, inventory, and
  `relationships.by_slug` exists in the referenced pack (or starts with
  `emergent:`).
- **Progression invariants** (v0.5):
  - After turn 0, `player.innate_traits` must be exactly 3 entries
    with 3 distinct universal archetype keys.
  - After turn 0, `player.artifact` must be set.
  - `player.destiny_traits` count ≤ `player.stage_index`; no
    duplicate destiny archetypes.
  - `player.stage_label` is populated when `stage_index > 0`.
  - `player.health_state == "dead"` requires
    `player.status == "dead"` and a `run_summary.md` file in the
    save directory (the terminal death flow did not run if this is
    missing).
  - The compact turn HUD inside `current_scene.md` matches the
    underlying state; drift means manual edits or a missing
    `render_save.py` re-run.
  - If `saves/<pack>/meta_progress.json` exists, its `pack_name`
    matches this save, it parses, and its `best_stage_index` is
    within bounds.

Exit 0 = clean. Exit 1 = issues. Do not auto-fix save state without user
confirmation. A high `divergences.jsonl` line count (>10 per 20 turns) is
a narrator/patcher discipline problem rather than a lint issue — read the
notes and decide with the user whether to loosen the patch vocabulary or
tighten narration.
