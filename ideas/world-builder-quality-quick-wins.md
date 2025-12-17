# World Builder AI: Quality Quick Wins (Minimal Effort, Max Richness)

## Your current constraints (Dec 2025)

- **Primary player is you**, but you still want a **spoiler-free surprise factor** to stay motivated.
- **Baseline world size**: similar to `uss-enterprise-d` (small-to-medium, cohesive).
- **Mechanics focus (now)**: **locations + exits** (reliable navigation, but non-trivial: locked/hidden/conditional paths).
- **NPCs later**: a new dedicated dialog system is planned; world builder should not over-invest here *yet*.
- **Narrative quality is non-negotiable**: bland prose reduces motivation and makes image gen generic (NPC/scene descriptions matter).
- **Single victory condition** per world for now (quests/sidequests later).

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
- **Gates**: at least two distinct gate types (primarily **exit/navigation gates** right now).
- **Optional depth**: at least 2 optional discoveries that don’t block victory but enrich play.

This aligns with GAIME’s direction (more mechanics) while keeping authoring cheap.

---

## “Rich World Contract” (minimum requirements)

These are prompt-level requirements (not engine/schema changes). They should be framed as **musts**.

### A) Navigation-first gating minimums (per world)

- **2 navigation threads**, each at least **3 steps** (discover clue → unlock/enable access → reach new area).
- Include **at least two** of these gate types (prefer the top ones):
  - **hidden exit** gate (exit exists but is not visible until a discovery action sets a flag)
  - **locked exit** gate (exit exists and is visible, but requires a key/tool or condition)
  - **sequence/flag** gate (must do X before Y; e.g., “restore power” before a door will open)
  - **environmental** gate (light/dark; hazard; access requirement) *only if the engine supports it today*
- At least **one “non-trivial navigation loop”**: unlocking a shortcut that changes traversal (not just “final door opens”).

> Note: “alternative solutions” are great, but they can reduce surprise for solo playtesting if too explicit. Treat them as an optional “rich mode” unless you decide otherwise later.

### B) NPC depth minimums

- **Keep NPCs lightweight for now**, but enforce **image/narrative usefulness**:
  - every NPC must have **appearance/description**, **role**, and **placement**
  - at least one NPC should have a **world-grounding purpose** (guard, caretaker, engineer, clerk, etc.)
- Avoid building a full trust/dialogue gating system until the dedicated dialog system exists.

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
- At least **one discovery action** meaningfully changes navigation (reveals/unlocks an exit; sets a flag used later).
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

The backend currently requires only `world_id`, `world_yaml`, `locations_yaml`, `npcs_yaml`, `items_yaml`; extra keys are safe.

#### Spoiler-minimizing tweak (important for solo playtesting)

To preserve your surprise factor, structure it like:

- `spoiler_free_pitch`: 3–6 sentences you can read safely (premise + vibe + what makes it cool, **no solutions**).
- `spoilers`: contains `design_brief` and any explicit puzzle graph/solutions.

Then the TUI can hide `spoilers` by default unless you enable a “show spoilers / debug” toggle.

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

- **Navigation-first: locked + hidden + shortcut loop**
  - a visible locked door + a hidden bypass + a later-unlocked shortcut
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
- **At least one hidden exit** and **one locked/conditional exit** exist, and neither is trivial.
- **Constraints** explicitly forbid trivial bypasses for the major gates.
- **NPCs** have enough description to avoid generic image gen.
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
