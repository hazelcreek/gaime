> **⚠️ SUPERSEDED**: This document has been merged into the authoritative specification at [`planning/two-phase-game-loop-spec.md`](../../planning/two-phase-game-loop-spec.md). Kept for historical reference.

---

# Event-Driven Game Loop Architecture

This document details the architectural shift from a monolithic LLM game loop to a structured, event-driven pipeline. It fleshes out the concepts introduced in `game-mechanics-design.md` and aligns with the immersive goals of `docs/VISION.md`.

> **Status**: Idea / Proposal  
> **Related**: [Game Mechanics Design](../game-mechanics-design.md), [Vision](../../docs/VISION.md)

---

## 1. Motivation & Overview

The current architecture relies on a single LLM call to both determine game state changes and generate narration. This leads to:
*   **Hallucinations**: The LLM inventing state changes that don't match the game logic.
*   **Inconsistency**: Narrative contradicting the actual game state.
*   **Limited Mechanics**: Difficulty enforcing strict rules (e.g., locked doors, puzzles) when the LLM has full creative freedom in one pass.

We propose a **Pipeline Architecture**:

1.  **Input Processing**: User input $\to$ **Action Intent** (via LLM Parser or Simple Mapper)
2.  **Game Engine**: Action Intent + Current State $\to$ **Events** (Strict Logic & Validation)
3.  **Narration**: Events + New State $\to$ **Prose** (Creative LLM)

This separation ensures **Game Logic** is authoritative and **Narration** is grounded in actual events.

---

## 2. Core Concepts

### Action Intents (The "Request")

An `ActionIntent` is a structured representation of what the user *wants* to do. It is not yet a success; it is a request to the engine.

| Intent | Parameters | Description |
| :--- | :--- | :--- |
| `Move` | `direction` (n, s, e, w, etc.) | Attempt to leave the current location. |
| `Look` | `target` (optional) | Look at the room or a specific item/feature. |
| `Take` | `item_id` | Attempt to pick up an item. |
| `Drop` | `item_id` | Attempt to drop an item. |
| `Use` | `item_id`, `target_id` (optional) | Use an item, optionally on something else. |
| `Interact` | `verb` (string), `target_id` | Generic fallback for rich verbs (e.g., "play piano"). |
| `Talk` | `npc_id`, `topic` (optional) | Initiate or continue dialogue. |
| `Inventory`| - | Check carried items. |
| `System` | `command` (save, load, quit) | Meta-commands. |

### Events (The "Outcome")

An `Event` is a fact that *has happened* in the engine. These are passed to the Narrator to describe *how* it happened.

| Event | Payload | Narrative Implication |
| :--- | :--- | :--- |
| `LocationChanged` | `from`, `to`, `exit_type` | Describe travel (walking, climbing, crawling). |
| `ItemTaken` | `item_id`, `source` | Describe picking it up (weight, texture). |
| `ItemDropped` | `item_id`, `location` | Describe placing/dropping it. |
| `InteractionSuccess`| `verb`, `target`, `result_flags` | Describe the action (e.g., piano plays music). |
| `InteractionFailed` | `verb`, `target`, `reason` | Describe *why* it failed (e.g., locked, stuck). |
| `StateChanged` | `entity_id`, `old_state`, `new_state` | Visual changes (candle lit, door opened). |
| `Discovery` | `entity_id` (item/exit/feature) | Something new was noticed. |
| `Message` | `text` | System messages or direct information. |

---

## 3. The Game Loop Flows

### Flow A: Successful Action (e.g., "Open Drawer")

1.  **User Input**: "Open the drawer."
2.  **Parser**: Resolves "drawer" to `desk_drawer` (item/interaction ID).
    *   *Output*: `ActionIntent(Interact, verb="open", target="desk_drawer")`
3.  **Engine**:
    *   Checks: Is `desk_drawer` present? Yes. Is it locked? No. Is it already open? No.
    *   Update State: `desk_drawer.state = open`.
    *   *Triggers*: Opening drawer reveals `rusty_key`. Update `rusty_key.visible = true`.
    *   *Output*: `[Event(StateChanged, desk_drawer, closed->open), Event(Discovery, rusty_key)]`
4.  **Narrator**:
    *   Input: Events + Context (Location: Office, Atmosphere: Dusty).
    *   *Output*: "You pull the handle. The drawer slides open with a squeak. Inside, amidst scattered papers, a rusty key glints."

### Flow B: Validation Fault (e.g., "Go North" - Locked Door)

1.  **User Input**: "Go north."
2.  **Parser**:
    *   *Output*: `ActionIntent(Move, direction="north")`
3.  **Engine**:
    *   Checks: Is there an exit north? Yes (`library_door`). Is it passable? No (`locked=true`).
    *   *Output*: `[Event(InteractionFailed, verb="move", target="library_door", reason="locked_by_key")]`
4.  **Narrator**:
    *   Input: Failure Event + Context (Exit Description: "Heavy oak door").
    *   *Output*: "You try the handle, but the heavy oak door is locked tight. It won't budge."

### Flow C: Rich Verbs (e.g., "Play the Piano")

1.  **User Input**: "Sit down and play a sad song on the piano."
2.  **Parser**:
    *   LLM identifies verb "play", target "piano", nuance "sad song".
    *   *Output*: `ActionIntent(Interact, verb="play", target="piano", parameters={style: "sad"})`
3.  **Engine**:
    *   Looks up `piano` entity.
    *   Checks `interactions`: Does it have a handler for `play`? Yes.
    *   Executes handler: Sets `flag: piano_played`, triggers `audio: sad_melody`.
    *   *Output*: `[Event(InteractionSuccess, verb="play", target="piano", flavor="sad")]`
4.  **Narrator**:
    *   *Output*: "You sit at the bench and let your fingers drift over the keys. A melancholic melody fills the room, echoing off the empty walls."

---

## 4. Handling Visibility & State

The key challenge is: **How does the Narrator know what to reveal?**

### The Visibility Model
The Narrator should **never** decide what is visible. It only describes what the State/Events say is visible.

**Example: The Key in the Drawer**

*   **Initial State**:
    *   `desk_drawer`: `state=closed`
    *   `rusty_key`: `location=desk_drawer`, `hidden=true`
*   **Prompt to Narrator (Room Description)**:
    *   "Describe `Office`. Visible items: `[Desk, Chair, Bookshelf]`."
    *   *Result*: Narrator describes the desk but NOT the key.

*   **Action**: "Open drawer"
*   **Engine Logic**:
    *   Applies `open` logic.
    *   Change: `desk_drawer.state = open`.
    *   Logic: Items inside open containers become visible.
    *   Change: `rusty_key.hidden = false`.
*   **Event**: `Discovery(rusty_key)`
*   **Prompt to Narrator (Action Outcome)**:
    *   "Describe event: Drawer opened. New discovery: Rusty Key."
    *   *Result*: Narrator explicitly mentions the key appearing.

**Subsequent Turns**:
*   **Prompt to Narrator (Room Description)**:
    *   "Describe `Office`. Visible items: `[Desk, Chair, Bookshelf, Rusty Key (in drawer)]`."

**Strict Rule**: If it's not in the `visible_items` list or the `Events` payload, the Narrator prompts should explicitly instruct the LLM *not* to invent items.

---

## 5. Prompt Architecture

### A. The Interaction/Parser AI (Optional/Advanced)
Used when simple regex/keyword matching fails.

**System Prompt**:
```text
You are the Input Parser for a game engine.
Your job is to translate user natural language into a JSON ActionIntent.

Available Intents:
- Move(direction)
- Take(item_name)
- Use(item_name, target_name)
- Interact(verb, target_name)
...

Current Context:
- Visible Items: [piano, candle, matches]
- Exits: [north, west]

User Input: "{input}"

Output JSON only. If ambiguous, assume the most logical interaction based on context.
```

### B. The Narrator AI
Generates the prose.

**System Prompt**:
```text
You are the Narrator of a text adventure.
Your goal is to describe the events provided by the engine in an atmospheric style.
Style: {world_style} (e.g., Gothic Horror, Cyberpunk).

Rules:
1. Describe ONLY the events listed. Do not invent new actions or consequences.
2. If an item is listed as 'Found' or 'Discovered', emphasize it.
3. If an action Failed, explain why based on the 'reason' provided.
4. Keep it concise (max 2-3 sentences) unless the event is a major plot point.

Context:
- Location: {location_name} - {location_atmosphere}
- Events: {events_json}

Generate the response.
```

---

## 6. Implementation Strategy

To implement this without breaking the current game, we will use a **Parallel Engine** approach.

### Step 1: The `GameLoop` Interface
Refactor the backend to support pluggable loops.

```python
class GameLoop(ABC):
    @abstractmethod
    async def process_turn(self, state: GameState, input: str) -> TurnResult:
        pass
```

*   `LegacyGameLoop`: The current implementation.
*   `EventGameLoop`: The new implementation.

### Step 2: Implementation of EventLoop

1.  **Simple Mappings First**:
    *   Hardcode `north`, `n` -> `ActionIntent(Move, "north")`.
    *   Hardcode `look` -> `ActionIntent(Look)`.
    *   Skip the LLM Parser initially; use regex.

2.  **Engine & Event Bus**:
    *   Create a `handle_action(state, intent)` function.
    *   It returns `List[Event]`.
    *   Implement basic validation (e.g., valid direction).

3.  **Narrator Integration**:
    *   Create the `NarrationPrompt` builder that takes the `List[Event]`.

### Step 3: Startup Selection
In `App.tsx` or a new startup screen, allow the user to toggle:
*   [ ] Use Experimental Engine (Event-Driven)

This allows us to ship, test, and compare the "feel" of the two engines side-by-side.

