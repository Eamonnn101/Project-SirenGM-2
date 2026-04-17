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
- **Orphan wiki-links** (`[[slug]]` with no matching entity) — same fix.
- **Genre purity violations** (novel-specific content in the universal
  genre pack) — move it into the user pack's `novel_rules.md`. Genre
  packs are templates, never novel data.

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

Exit 0 = clean. Exit 1 = issues. Do not auto-fix save state without user
confirmation. A high `divergences.jsonl` line count (>10 per 20 turns) is
a narrator/patcher discipline problem rather than a lint issue — read the
notes and decide with the user whether to loosen the patch vocabulary or
tighten narration.
