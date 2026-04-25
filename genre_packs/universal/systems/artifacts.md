---
name: artifacts
kind: progression
---

# Universal · Artifact archetypes

Every run starts with **exactly one artifact**, chosen by the player
at new-game (Step 1.5). The artifact is immutable for the rest of
the run. It is stored on the save as
`PlayerState.artifact: PlayerArtifact | None`, distinct from
`inventory` because its mechanics are special: one per run, tagged
with a universal archetype, possibly exhausted by the
survival-trigger flow.

Three archetype seeds. User packs flavor one instance per archetype
in `progression_rules.md` §3 — name, slug, lore fit, activation
rule. The universal key stays stable so the renderer, lint, and
the survival-trigger logic keep working across novels.

## `insight` — reveal / learn / detect

**Mechanic seed.** Once per scene (or per conflict, at the GM's
discretion), the player may use the artifact to reveal a hidden
weakness, truth, or pattern — or to copy-learn a single move or
line from an opponent. Cross-genre shapes:

- a mystical mirror that shows one true intention
- a forensic scanner that reads a concealed signature
- a rhetorical ear that hears the unsaid
- a quiet talent for reading the room deeper than anyone expected

The artifact is **not** consumed by normal use; it is a repeatable
edge. It does **not** carry death-prevention semantics.

## `bond_rescue` — one-shot survival / relocation

**Mechanic seed.** Once per run, when the PC is about to die, the
artifact fires, pulling them out of the lethal lock to a
`critical` state. Often tied to a relationship hook: an oathbound
ally, a protective spirit, a rescue protocol, a debt being called
in. Cross-genre shapes:

- a life-saving talisman gifted by a master
- an emergency extraction tied to a safehouse
- a familiar that hurls itself in the way
- a standing oath someone must honor when invoked

After firing the artifact is marked `used: true` and cannot be
used again this run. This is precedence **1** in the
survival-trigger order; see `systems/health_and_death.md`.

## `companion` — recruit / store / dispatch

**Mechanic seed.** The artifact can summon, store, or dispatch a
helper unit or leveraged resource. Unlike `bond_rescue`, it is
repeatable (though with in-world cost each time). Cross-genre
shapes:

- a spirit bird the PC can send to scout or carry messages
- a cloud-stored drone swarm that can be deployed on call
- a pocket ally the PC can wake in emergencies
- an animal familiar that can be sent on limited errands

The `companion` archetype does **not** carry death-prevention
semantics; it is not a survival trigger.

## Engine contract (common to all archetypes)

- `PlayerArtifact.archetype` ∈ `{"insight", "bond_rescue",
  "companion"}`. Lint rejects anything else.
- Activation notes go in `PlayerArtifact.notes` (free-form, pack
  language). The GM reads these as the activation contract.
- The artifact is chosen exactly once, at new-game Step 1.5.
  `player_artifact_set` is rejected by the patch engine after
  `turn > 0` unless `artifact is None` (never happens in normal
  play).
- The compact turn HUD shows the artifact every turn as a single
  line: novel-themed name + archetype label + ready/used status
  (`<name>〔<archetype> · 待用/已用〕` in zh,
  `<name>〔<archetype> · Ready/used〕` in en). The full activation
  contract from `progression_rules.md` lives in `player.md`
  (Layer B); the compact HUD never repeats it, and the prose
  must not re-narrate it either.

## Labeled option presence (load-bearing)

Presence in the prose is governed by **labeled options**, not by
re-narration. The GM exposes a `[Artifact · <name>]` (en) /
`〔法宝・<name>〕` (zh) labeled option **only on key beats** —
the same key-beat list that gates trait labels (see
`genre_packs/universal/prompts/gm_system_fragment.md`
§ *Key beats*). Default cadence is **zero per turn**.

Per-archetype priming shapes:

- `insight` — primed at a pivot beat where revealing a hidden
  truth, weakness, or pattern would change the player's options
  (an investigation breakthrough; a conflict opening or endgame
  where reading the opponent matters).
- `bond_rescue` — primed only when `health_state` ∈
  {`badly_hurt`, `critical`} AND the artifact is unused. Outside
  that envelope it stays in the HUD but is never offered as a
  labeled option.
- `companion` — primed at a conflict pivot (open / endgame) or
  on `risk_level == "lethal"` where dispatching, scouting, or
  recruiting the artifact's helper unit changes the situation.

Even when primed, the GM may emit zero labeled options if the
turn is not a true pivot — exposition, recap, mid-conflict pacing
turns without escalation. Across artifact + innate + destiny
combined, **at most one labeled option appears per turn**. See
*Pre-options scan*, *Key beats*, and *Labeled special options*
in `genre_packs/universal/prompts/gm_system_fragment.md`.

### What artifact labeled options are

- A *special approach* the player may take. Picking the option
  does **not** automatically succeed — the conflict ledger still
  records costs and the outcome still has to play out.
- An option body that **refers to the artifact by name** and
  describes the *move*, not the artifact's mechanic. Re-narrating
  the full activation contract in the option body is a failure;
  the HUD already names the artifact.
- A way to grant: information reveal (`insight`), survival
  redirect / relocation (`bond_rescue`), or recruit/scout/dispatch
  reach (`companion`) — within the activation rule from
  `progression_rules.md` §3.

## What artifacts are NOT

- Not a weapon stat. No damage numbers, no tier, no numeric
  upgrade.
- Not tradeable. The player cannot swap or sell the artifact
  mid-run. The player does not acquire a second artifact.
- Not the only way to prevent death. Destiny traits
  `not_meant_to_die` and `last_barrier` also sit in the survival
  precedence order.
- Not exclusive to magical/xianxia settings. A political drama's
  `insight` artifact might be a cultivated network of informants.
  The archetype describes the *mechanic*, not the setting's
  vocabulary.
