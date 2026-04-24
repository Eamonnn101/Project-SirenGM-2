---
name: systems_readme
---

# Universal · Systems

Shared, genre-agnostic mechanic **seeds** for the v0.5 progression
layer. Novel-specific labels and flavor are not defined here — each
user pack's `packs/<name>/progression_rules.md` re-themes these seeds
at ingest time.

Files in this directory:

- [`stages.md`](stages.md) — the 6 narrative stages the whole run
  moves through (`establish footing` → `rewrite fate`), plus the
  "stage advance guidance" soft rules.
- [`artifacts.md`](artifacts.md) — the 3 artifact archetypes
  (`insight`, `bond_rescue`, `companion`) and their activation
  contracts.
- [`innate_traits.md`](innate_traits.md) — the 5 innate trait
  archetypes (`talent`, `survival`, `social`, `resource`,
  `temperament`) and the "3 distinct archetypes" rule.
- [`destiny_traits.md`](destiny_traits.md) — the 12 destiny trait
  mechanic seeds grouped into 4 families, plus the per-breakthrough
  draw rule.
- [`health_and_death.md`](health_and_death.md) — the 5-state health
  ladder, survival-trigger precedence, and the terminal death flow.
- [`meta_progression.md`](meta_progression.md) — what the per-pack
  `saves/<pack>/meta_progress.json` stores, the unseen-first draft
  bias contract, and explicit MVP non-goals.

Everything in this directory is **universal**. Nothing here names a
specific novel, faction, relic, or vocabulary. Per-novel re-themings
live only in user packs.

Novel-specific power systems, social hierarchies, technology tiers,
and magic/cultivation/skill ladders remain the job of each user
pack's `packs/<name>/novel_rules.md`. The progression layer rides
on top of those — the stages, artifacts, and traits take their voice
from the novel, but their structure is defined here.
