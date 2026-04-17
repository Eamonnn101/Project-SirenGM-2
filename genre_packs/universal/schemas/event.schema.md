---
name: event_schema
entity: event
---

# Event Frontmatter Schema

User-pack `events/<slug>.md` frontmatter. An event is a single
happening the world has queued — planned or conditional.

## Required

- `slug` (string).
- `name` (string): event title in the pack's language.
- `kind` (enum):
  - `intended` — the novel's planned beat. **Not mandatory.** The GM
    may stage it when the scene calls for it. If the player's
    trajectory moves past the trigger conditions, the event is skipped
    (default `can_skip: true`). Skipping is normal, not a divergence.
  - `triggerable` — a conditional event that fires when its
    `preconditions` are all met. Also skippable by default.
  - `player_boundary` — a protective beat the GM stages only when the
    player is about to do something that would break the novel's
    canon. Default `can_skip: false`: these may not be silently
    skipped.

## Optional

- `preconditions` (list[string]): free-form trigger tags, e.g.
  `turn<=3`, `at:outer_gate`, `relationship:mira>=3`,
  `has_item:scroll`.
- `can_skip` (bool): overrides the kind's default. Set
  `can_skip: false` on an `intended` event only if the novel's logic
  truly requires it to fire (and understand this tightens the rails —
  use sparingly). Set `can_skip: true` on a `player_boundary` event
  only if the boundary is advisory rather than load-bearing.

## Body

Cover: how the event should feel in prose; exactly which state-patch
ops should fire when it triggers (e.g. "append to
`hidden_truths`", "add `loop:missing_elder` to `open_loops`"); and any
follow-on arcs it hands off to. Keep it to a page.

Cross-references use the piped wiki-link dialect `[[slug|Display]]`;
see `prompts/ingest_draft_system.md`. Bare `[[slug]]` is only valid
when the target entity's `name` is ASCII.
