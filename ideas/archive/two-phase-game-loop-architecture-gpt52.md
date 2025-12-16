> **⚠️ SUPERSEDED**: This document has been merged into the authoritative specification at [`planning/two-phase-game-loop-spec.md`](../../planning/two-phase-game-loop-spec.md). Kept for historical reference.

---

# Evented Game Loop Spec (ActionIntents + Events + Narration)

> **Status**: Draft specification — December 2025  
> **Context**: Extends the "Two‑Phase LLM" section in `ideas/game-mechanics-design.md` and aligns with `docs/VISION.md` (story-first, guided freedom, no unwinnable states, in-world explanations).

This document specifies a **new gameplay loop** where:

- **Player input** is mapped to an **`ActionIntent`** (initially via deterministic parsing for movement).
- A deterministic **game engine** validates and applies the intent, producing **`ActionEvent`s** (and/or **`ValidationFault`s**).
- A **Narrator AI** generates prose strictly from the **validated outcome + player-visible state**, never inventing state changes.

The new loop should **co-exist** with the current "single LLM does mechanics + prose" loop to compare gameplay.

---

## Goals (from Vision)

- **Natural UX**: Players can type natural language, not rigid commands.
- **Rules enforcement**: World/engine rules must be enforced deterministically.
- **Immersion-preserving failures**: When an action can't happen, the player gets an **in-world** explanation (not "Error:").
- **No unwinnable states**: Engine prevents game-breaking actions (e.g. destroying critical items).
- **Debuggable**: We can log: input → intent → validation → events → narration.

---

## Non-goals (for the first iteration)

- Full general natural-language understanding for all verbs.
- Modeling physics, continuous simulation, combat systems, or RPG stats.
- Perfect "commonsense" reasoning (we'll use affordances + authored interactions).

---

## High-level Architecture

### Legacy loop (today)

- One LLM call returns `{ narrative, state_changes }`; engine applies changes with minimal validation.

### New loop (evented)

1. **Intent Resolution** (deterministic for v0 movement; optional LLM parser later)
2. **Validation** (deterministic)
3. **State Transition** (deterministic) → emits **events**
4. **Narration** (LLM or templates) from **player-visible snapshot + events**

Key separation: the Narrator **never decides mechanics**.

---

## Core Contracts (Implementation-driving)

This section defines the types that should exist as Pydantic models (backend) and TS types (frontend).

### `ActionIntent`

**Purpose**: canonical representation of what the player is trying to do.

Common fields:

- `intent_id: str` — UUID
- `type: str` — discriminator
- `raw_text: str` — original player input
- `actor: str = "player"`
- `created_at: str` — ISO timestamp
- `confidence: float | None` — set by parser/heuristics when applicable

#### Intent types (initial set)

**Movement (Phase 0 / first implementation)**

- `MoveIntent`
  - `direction: Literal["north","south","east","west","up","down","in","out","back"]`
  - `mode: Literal["absolute","relative"]` (e.g. `back` is relative)

**Perception**

- `LookIntent`
  - `target: str | None` (none = "look around")
- `ExamineIntent`
  - `target: str` (entity ref or player text span)

**Inventory / Object manipulation**

- `TakeIntent`
  - `item: str`
- `DropIntent`
  - `item: str`
- `OpenIntent`
  - `target: str` (container/door/etc.)
- `CloseIntent`
  - `target: str`
- `UseIntent`
  - `item: str`
  - `target: str | None`
  - `instrument: str | None` (rare; e.g. "light candle with matches" ⇒ item=matches target=candle)

**Social**

- `TalkIntent`
  - `npc: str`
  - `topic: str | None`

**Richer verbs / "anything else"**

To keep the UX natural *without* letting the LLM invent mechanics, we funnel most freeform verbs into one of these:

- `PerformInteractionIntent`
  - `interaction_id: str` (author-defined interaction / affordance)
  - `primary_target: str | None`
  - `secondary_target: str | None`
- `FlavorIntent`
  - `verb: str`
  - `direct_object: str | None`
  - `prepositional_object: str | None`
  - `notes: str | None`

**Rule**: If the engine doesn't recognize or authorize the intent, it must become either:

- a **rejected** action with an in-world explanation, or
- a **FlavorIntent** (no state change; narrator makes it fun and consistent).

### `ValidationFault`

**Purpose**: machine-readable reasons an intent can't be applied.

Fields:

- `code: str` — stable enum-like string
- `message: str` — player-facing *seed* text (narrator may rewrite but must keep meaning)
- `blocking_entity: str | None` — e.g. `exit:kitchen_to_basement`
- `details: dict` — optional structured data for debugging/UI

Recommended `code` set (expand over time):

- `NO_EXIT` — direction not available
- `EXIT_NOT_VISIBLE` — exit exists but is undiscovered
- `EXIT_LOCKED` — locked
- `EXIT_BLOCKED` — blocked (rubble, fire, etc.)
- `PRECONDITION_FAILED` — missing flag/item/light/etc.
- `ITEM_NOT_VISIBLE` — can't take/use what you can't see
- `ITEM_NOT_PORTABLE` — fixed in place
- `ITEM_TOO_HEAVY` — portable but too heavy
- `TOOL_INSUFFICIENT` — e.g. "knife too dull"
- `AMBIGUOUS_TARGET` — multiple matches ("take key" but two keys)
- `ALREADY_DONE` — repeated one-time interaction
- `SAFETY_GUARDRAIL` — would create unwinnable state / violates design rules

### `ActionEvent`

**Purpose**: event stream describing what happened, to drive narration, UI, logging, achievements, etc.

Common fields:

- `event_id: str` — UUID
- `type: str` — discriminator
- `turn: int`
- `timestamp: str` — ISO

#### Event types (recommended baseline)

**Lifecycle**

- `ActionResolved`
  - `intent_id`
  - `success: bool`
- `ActionRejected`
  - `intent_id`
  - `fault: ValidationFault`

**Movement**

- `MoveAttempted`
  - `from_location`
  - `direction`
  - `to_location: str | None`
- `LocationChanged`
  - `from_location`
  - `to_location`
  - `via_direction`
- `LocationEntered`
  - `location`
  - `first_time: bool`

**Visibility / discovery**

- `ExitRevealed`
  - `exit_id`
- `EntityRevealed`
  - `entity_id` (e.g. `item:key`)
  - `how` (e.g. `container_opened`, `flag_set`, `interaction`)

**Containers / doors (open/close)**

- `ContainerOpened`
  - `container_id`
- `ContainerClosed`
  - `container_id`

**Inventory**

- `ItemAddedToInventory`
  - `item_id`
- `ItemRemovedFromInventory`
  - `item_id`

**State flags**

- `FlagSet`
  - `flag`
  - `value: bool`

### `ActionResult` (engine output)

Fields:

- `intent: ActionIntent`
- `success: bool`
- `events: list[ActionEvent]`
- `fault: ValidationFault | None`
- `state_patch: dict | None` — optional structured patch/diff for debugging (not required for narrator)

### `PerceptionSnapshot` (what the Narrator sees)

**Rule**: Narrator gets **only player-visible information**.

Fields (minimum viable):

- `location`
  - `id`, `name`, `atmosphere_prompt`
- `visible_details[]` *(optional but recommended)*
  - `id`, `label`, `description` (examinable "features" like `desk`, `portrait`, `drawer`)
- `visible_exits[]`
  - `direction`, `destination_name`, `description`
- `visible_items[]`
  - `id`, `name`, `found_description` / placement text
- `visible_npcs[]`
  - `id`, `name`, `role`, `placement`
- `inventory[]`
  - `id`, `name`
- `known_facts[]` (optional) — derived from flags/discoveries
- `affordances[]` (optional but important) — **spoiler-safe** hints like:
  - `openable_containers: ["desk_drawer"]`
  - `usable_tools_in_inventory: ["matches"]`
  - `obvious_interactions_here: ["play_piano"]`

**Explicit anti-spoiler rule**: hidden contents (e.g. the key inside a closed drawer) **must not appear** in `visible_items[]`.

---

## Flow: Success vs Validation Fault

### Success path (generic)

1. Player text → `ActionIntent`
2. Engine `validate(intent, state)` → ok
3. Engine `apply(intent, state)` → updates state deterministically
4. Engine emits `ActionEvent[]` (including `ActionResolved(success=True)`)
5. Narrator receives:
   - `intent`
   - `events`
   - **post-action** `PerceptionSnapshot`
   - optional **pre-action** snapshot for contrast (useful for "newly revealed")
6. Narrator outputs prose (and optional UI metadata)

### Validation-fault path (generic)

1. Player text → `ActionIntent`
2. Engine `validate` → fails with `ValidationFault`
3. Engine emits:
   - `ActionRejected(fault=...)`
   - `ActionResolved(success=False)`
4. Narrator receives:
   - `intent`
   - `fault`
   - unchanged `PerceptionSnapshot`
5. Narrator produces an **in-world** explanation + optional gentle suggestion.

**Important**: On failure, the narrator must not describe changes that didn't happen.

---

## Richer Verbs: How we keep UX natural *and* rules strict

We support player language like "play piano", "jump around", "eat apple", "light candle with matches" by combining:

1. **Canonical intents** for common mechanics (move/take/open/use/talk/look).
2. **World-defined interactions (affordances)** for bespoke verbs:
   - Authors define an `interaction_id` (e.g. `play_piano`) with triggers and deterministic effects.
3. **Flavor actions** as a safety valve:
   - If it's not a real mechanic but is harmless, treat it as `FlavorIntent` and narrate it without state change.

### Authoring rule of thumb

- If an action should **change state** or unlock progress ⇒ define a deterministic **interaction** (producing events).
- If it's just immersion ⇒ allow as **FlavorIntent**.

### Example mappings

- "play piano"
  - If location has interaction `play_piano` ⇒ `PerformInteractionIntent(interaction_id="play_piano")`
  - Else ⇒ `FlavorIntent(verb="play", direct_object="piano")`

- "light candle with matches"
  - If both items exist and rules allow ⇒ `UseIntent(item="matches", target="candle")`
  - Validation may yield `PRECONDITION_FAILED` (no matches), `TOOL_INSUFFICIENT` (matches are wet), etc.

- "eat apple"
  - If apple is consumable and in inventory ⇒ `UseIntent(item="apple", target=None)` with deterministic effect `ItemRemovedFromInventory`
  - Else ⇒ `ITEM_NOT_VISIBLE` / `PRECONDITION_FAILED`

---

## Visibility & Discovery Model (Desk → Drawer → Key)

### Design decision

To prevent accidental spoilers, the Narrator should **not** receive hidden entities at all.  
Instead, the deterministic engine reveals entities by modifying **world state / perception state**, which then appears in subsequent narrator prompts.

### Minimal state needed (conceptual)

In addition to `flags` and `inventory`, we need **runtime state** for:

- `container_state[container_id].is_open: bool`
- `discovered_entities: set[str]` (or `visibility_overrides: dict[entity_id, visibility]`)

### Example world setup (conceptual YAML)

```yaml
locations:
  study:
    name: "Study"
    atmosphere: "Dusty lamplight, a hush of old paper."
    details:
      desk: "A heavy oak desk with a single narrow drawer."
    interactions:
      open_desk_drawer:
        triggers: ["open drawer", "open the desk drawer", "pull drawer"]
        effects:
          - open_container: desk_drawer

items:
  desk_drawer:
    name: "Desk Drawer"
    categories: ["container"]
    portable: false
    initial_state: closed
    contains: ["brass_key"]

  brass_key:
    name: "Brass Key"
    portable: true
    hidden: true            # hidden until container open
    found_description: "Inside the drawer, a small brass key catches the light."
```

### Prompt flow for the example

#### 1) Player enters the Study (initial narration)

Engine state:

- `desk_drawer.is_open = false`
- `brass_key` is not in `visible_items`

Narrator receives a `PerceptionSnapshot` that includes:

- visible items: *(none)* (or just the desk if modeled as an item/detail)
- affordances: `openable_containers=["desk_drawer"]`

Narrator output: describes the room, mentions the desk/drawer **without** revealing the key.

#### 2) Player: "open drawer"

Intent:

- `OpenIntent(target="desk_drawer")` **or** `PerformInteractionIntent("open_desk_drawer")`

Validation:

- If drawer is locked ⇒ `ActionRejected(code="EXIT_LOCKED"/"PRECONDITION_FAILED")` with in-world reason
- Else apply:
  - `desk_drawer.is_open = true`
  - reveal contents: `brass_key` becomes visible

Events:

- `ActionResolved(success=True)`
- `ContainerOpened(container_id="desk_drawer")` *(if we add this event type)*
- `EntityRevealed(entity_id="item:brass_key", how="container_opened")`

Narrator receives **post-action** snapshot where:

- `visible_items` now includes `brass_key` with its `found_description`

Narrator output: describes opening the drawer and noticing the key.

#### 3) Player: "take key"

Intent:

- `TakeIntent(item="brass_key")`

Validation:

- now passes because key is visible

Events:

- `ItemAddedToInventory(item_id="brass_key")`

Narrator output: describes picking up the key.

---

## Prompt Templates (Interaction AI vs Narrator AI)

### Interaction AI (optional; Phase 0 can skip)

**Purpose**: map player text → `ActionIntent` (structured JSON).

**Key constraint**: Interaction AI must not invent entities. It may only reference:

- visible entities in `PerceptionSnapshot`
- inventory entities
- explicitly listed affordances / interactions

#### Template: `interaction_ai/system_prompt.txt` (spec)

- You are a rules-focused parser.
- Output **only JSON** conforming to the `ActionIntent` schema.
- If ambiguous, output `type="AmbiguousIntent"` with `candidates[]` + a `question` to ask the player.
- Never narrate.

#### Template: `interaction_ai/user_prompt.txt` (spec payload)

- `raw_text`
- `perception_snapshot` (visible exits/items/npcs/details + affordances)
- `known_interactions[]` (IDs + triggers)
- `inventory[]`
- `language`, `tone_profile` (optional)

### Narrator AI (recommended even when mechanics are deterministic)

**Purpose**: generate prose from validated outcomes.

#### Template: `narrator_ai/system_prompt.txt` (spec)

- You are the Narrator of a text adventure.
- You must be immersive and consistent with world tone.
- You must **not** invent mechanics or state changes.
- You must not reveal hidden information.
- When an action fails, explain it in-world and keep the player engaged.

#### Template: `narrator_ai/user_prompt.txt` (spec payload)

- `raw_text`
- `intent` (canonical)
- `result.success`
- `events[]`
- `fault` (if any)
- `pre_snapshot` (optional)
- `post_snapshot` (player-visible)
- `style_profile` (tone, verbosity, safety filters)
- `narrative_memory` (short summaries only, not full logs)

#### Narrator output schema (recommended)

```json
{
  "narrative": "string",
  "hints": ["optional short suggestions"],
  "ui": {
    "sound": null,
    "image_suggestion": null,
    "emotional_beat": "optional"
  }
}
```

---

## Co-existence Plan (compare old vs new)

### Session-level engine selection

At game/session start, choose:

- `engine_mode="legacy_llm"` — current behavior
- `engine_mode="evented_v2"` — new intent→validate→events→narrate

Implementation hint: store `engine_mode` on the session state (or session manager) and route `process(action)` to the selected processor.

### Logging (critical for comparison)

For each turn, record:

- input text
- resolved intent
- validation outcome (fault or ok)
- emitted events
- narrator prompt + response
- legacy mode: original GM prompt + response

This enables qualitative comparison and automated regression checks later.

---

## Implementation Phases (recommended)

### Phase 0 — deterministic movement (no Interaction AI)

- Map inputs like `north/east/up/down/back` (and `go north`) → `MoveIntent`
- Deterministic engine validates exits/locks/visibility and emits events
- Narration:
  - either templated text, or Narrator AI using snapshots/events

### Phase 1 — expanded movement language

- Add heuristics and/or Interaction AI for:
  - "leave", "go back", "head outside", "return", "enter"
- Keep the engine deterministic.

### Phase 2 — interactions & object verbs

- Introduce `PerformInteractionIntent` backed by world-authored interaction definitions
- Add visibility/discovery state (containers, hidden items)

### Phase 3 — broader verbs with safe fallback

- Use Interaction AI to map freeform to:
  - canonical intents, or
  - known affordances (`interaction_id`), or
  - `FlavorIntent` (no state change)

