---
name: location_schema
entity: location
---

# Location Frontmatter Schema

User-pack `locations/<slug>.md` frontmatter.

## Required

- `slug` (string, snake_case, ASCII).
- `name` (string): display name in the pack's language.
- `danger` (enum): `safe`, `guarded`, `hostile`, `deadly`. Drives the
  default `risk_level` when the player enters.

## Optional

- `region` (string): free-form parent region name.
- `controlled_by` (string): slug of the faction that holds the
  location.

## Novel-specific frontmatter

Extra fields pass through (`climate`, `era`, `terrain_type`, etc.).

## Body

Cover: physical layout, who is usually present, environmental cues,
typical hazards, entry requirements if any are strictly enforced.
Cross-references use `[[slug]]`.
