# World Builder AI: Quality Quick Wins (Minimal Effort, Max Richness)

## Context / Problem

The current World Builder (now in the new TUI) reliably outputs **valid YAML**, but the resulting worlds (e.g. high school, forest, hazel city) are often:

- **Mechanically shallow**: “find key → open door” style puzzles; minimal multi-step dependencies.
- **Narratively flat**: fewer memorable set pieces, secrets, and cross-linked lore.
- **Underspecified for the GM**: constraints and NPC knowledge are too coarse to reliably support deeper mechanics.

In contrast, worlds created by a general-purpose Cursor agent (e.g. `cursed-manor`, `uss-enterprise-d`) show stronger:

- **Puzzle structure** (gating + dependencies + optional discoveries)
- **Knowledge distribution** (who knows what; when; under what conditions)
- **Constraints** that prevent trivial solutions
- **“World hooks”** (secrets, environmental storytelling, meaningful items)

The goal here is **not** a big “world builder rewrite”. The goal is to make it easy to produce **test worlds** that stress increasingly sophisticated mechanics with minimal author effort.

---

## Hypothesis: Why the builder underperforms

### 1) The current prompt optimizes for formatting and completeness, not design depth

The current world-builder prompt strongly enforces:
- JSON structure
- snake_case IDs
- placements and exit details

…but it only weakly requests:
- multi-step puzzles
- social/knowledge gates
- non-trivial constraints
- optional content and secrets

Result: the model “plays it safe” and generates minimal, low-risk designs.

### 2) “One-shot full world YAML” encourages conservative, generic content

When the model must create **everything** (world + locations + NPCs + items) in one output, it tends to:
- keep puzzle graphs small
- avoid intricate dependencies that risk inconsistency
- reduce “interlocking” content across files

### 3) There is no explicit “richness contract”

The builder has no measurable definition of:
- what counts as a “good” puzzle
- minimum complexity per world
- required mechanics coverage for testing

So it frequently outputs worlds that *look complete* but *play shallow*.

---

## Design Principle: “Quality via constraints” (not more tokens)

We can raise baseline quality quickly by forcing a **small set of structural commitments**:

- **Puzzle graph**: multiple steps + dependencies + at least one alternative route.
- **Gates**: at least two distinct gate types (item gate, knowledge/social gate, time/sequence gate).
- **Knowledge map**: which NPC knows what; what they refuse to reveal; what changes after player actions.
- **Optional depth**: at least 2 optional discoveries that don’t block victory but enrich play.

This aligns with GAIME’s direction (more mechanics) while keeping authoring cheap.

---

## “Rich World Contract” (minimum requirements)

These are prompt-level requirements (not engine/schema changes). They should be framed as **musts**.

### A) Puzzle + gating minimums (per world)

- **2 puzzle threads**, each at least **3 steps** (discover → unlock → resolve).
- At least **2 gate types** among:
  - item gate (key/tool/artifact)
  - knowledge gate (NPC trust, proof/evidence, dialogue topic unlocked)
  - sequence gate (do X then Y; requires a flag)
  - environmental gate (light/dark; hazard; access condition)
- At least **1 alternative solution** for a major gate (e.g., key OR pick-lock OR persuade NPC).

### B) NPC depth minimums

- At least **2 “major” NPCs** with:
  - **distinct voice** (speech style)
  - **secrets + refusal rules** (what they won’t reveal and when)
  - **useful mechanical role** (gatekeeper, clue source, item holder, etc.)
- A simple **trust/progress mechanism** expressed in flags/constraints and supported by location interactions.

### C) Item design minimums

- Every item must have a clear role:
  - puzzle-critical, clue, tool, trade item, or optional lore reward
- At least **1 “combo” or “use-on-target” item** interaction (even if implemented via an interaction trigger).

### D) Optional richness

- **2 optional discoveries** (secret room, hidden note, lore reveal, optional NPC reaction chain).
- At least **1 environmental storytelling loop**: a detail in Location A points to Location B, which recontextualizes A.

---

## Minimal Implementation Plan (prompt + process only)

### Step 0 — Define success in “playability” terms (1 hour)

Create a “15-turn smoke test” for any generated world:

- Player can discover at least **one non-trivial clue chain** by turn ~5–7.
- At least **one gate** cannot be bypassed by a single obvious item pickup.
- At least **one NPC interaction** meaningfully changes available options (flag/trust/topic).
- There’s at least **one optional secret** that feels rewarding.

This becomes the yardstick for the builder.

### Step 1 — Upgrade the builder system prompt to enforce the Rich World Contract (30–60 min)

Where: `backend/app/llm/prompts/world_builder/system_message.txt`

Change from generic “world designer” to a structured role:

- **Primary objective**: build a world that *plays well* (puzzle depth, gating, secrets).
- **Non-goals**: do not over-index on prose; keep YAML concise but information-dense.
- **Hard minimums**: the contract items above.
- **Anti-patterns to avoid**:
  - single-key single-door victory
  - “all clues in one room”
  - NPCs that don’t gate anything
  - constraints that allow trivial solutions (“you can just break the lock”)

### Step 2 — Add an internal “design brief” section inside the JSON output (30–60 min)

Where: `backend/app/llm/prompts/world_builder/world_builder_prompt.txt`

Without changing server requirements, ask the model to include an **additional JSON field** like:

- `design_brief`: a compact outline containing:
  - puzzle threads (steps + dependencies)
  - gate types used
  - which NPC knows which critical info and when
  - list of optional secrets

The backend currently requires only `world_id`, `world_yaml`, `locations_yaml`, `npcs_yaml`, `items_yaml`; extra keys are safe. This “brief” becomes a debugging lens and can later be used for automated evaluation.

### Step 3 — Two-pass generation (optional, but still small) (1–2 hrs)

If the single-pass still yields shallow worlds, add a second LLM call:

1) **Pass A: Design Brief Only**
   - Output only the puzzle graph, NPC roles, key items, and constraints.
2) **Pass B: YAML Synthesis**
   - Convert the approved brief to YAML with full placements/details.

This is the most reliable way to force deeper structure without “prompt bloat”.

### Step 4 — Add a “mechanics coverage dial” (optional, minimal API surface) (1–2 hrs)

Add a single optional parameter to world builder requests (TUI/UI):

- `target_mechanics`: list of mechanics to include (e.g., `["hidden_exits","social_gate","multi_item_victory","time_pressure"]`)

Then the prompt must explicitly integrate each requested mechanic at least once.

This directly supports your real goal: **generate worlds to test new mechanics**.

---

## “Mechanics Stress-Test World” templates (fastest path to usable worlds)

Even with prompt upgrades, the fastest way to get usable test content is a small internal library of **templates** the builder can instantiate.

### Template set (no engine changes required)

- **Key + knowledge gate + alternative route**
  - locked exit requires key OR convince NPC OR find hidden bypass
- **3-artifact ritual / collection victory**
  - forces multi-step item acquisition + gated access to final chamber
- **Time pressure without real-time clocks**
  - “train arrives at noon” expressed as narrative urgency + flags + constraints (optional)
- **Ethical/choice gate (Star Trek-style)**
  - victory flag requires a specific non-violent resolution path

Implementation: encode templates as short “seed briefs” inside the prompt (or as selectable presets in the TUI).

---

## Acceptance checklist (what “good output” looks like)

When reviewing a generated world, check:

- **Puzzle graph**: can you draw it as a dependency graph with >= 6 meaningful nodes?
- **At least one non-item gate** exists (knowledge/trust/sequence).
- **Constraints** explicitly forbid trivial bypasses for the major gates.
- **NPCs** have secrets + refusal rules + mechanical purpose.
- **Optional content** exists and feels worth pursuing.

If any of these fail, the builder should regenerate (or the enrichment pass should expand).

---

## Risks / Tradeoffs

- Stronger constraints can increase generation time or token usage.
- Over-constraining can produce rigid worlds; mitigate by allowing optional “lightweight” mode.
- Without a true first-class puzzle schema (future work), we rely on flags/interactions; still enough to create multi-step puzzles today.

---

## Clarification questions (to calibrate the plan)

1) **Primary use case**: Are these worlds mainly for *your own playtesting* (you know the mechanics), or for *blind playtesting* (needs stronger in-world hinting)?

2) **Target complexity**: What’s your preferred baseline size for test worlds?
   - e.g., 6 locations / 3 NPCs / 6–10 items, or larger?

3) **Which mechanics must be exercised next** (pick 3–6 from your current priorities)?
   - Examples: hidden exits, trust gating, item combinations, timed events, multi-ending victory, journal/clue tracking, explicit puzzles/hints, NPC memory, etc.

4) **Tone preference for test worlds**: Do you want “serious, compelling” even for test packs, or is “functional but coherent” acceptable as long as puzzles are deep?

5) **Constraint strictness**: Should the builder *always* generate at least one alternative solution for the main gate, or only in “rich mode”?

