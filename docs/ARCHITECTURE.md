# Architecture

This document describes the system architecture of GAIME, including component design, data flow, and key technical decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GAIME System                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌───────────────────┐          ┌───────────────────────────────────────┐ │
│   │                   │          │           Python Backend               │ │
│   │   React Frontend  │  HTTP    │  ┌─────────────────────────────────┐  │ │
│   │                   │◄────────►│  │           FastAPI               │  │ │
│   │  ┌─────────────┐  │  JSON    │  └──────────────┬──────────────────┘  │ │
│   │  │  Terminal   │  │          │                 │                     │ │
│   │  │  Component  │  │          │  ┌──────────────▼──────────────────┐  │ │
│   │  └─────────────┘  │          │  │        Game Engine              │  │ │
│   │                   │          │  │  ┌────────┐  ┌────────────────┐ │  │ │
│   │  ┌─────────────┐  │          │  │  │ State  │  │ Action         │ │  │ │
│   │  │  Sidebar    │  │          │  │  │ Mgr    │  │ Processor      │ │  │ │
│   │  │  Component  │  │          │  │  └────────┘  └────────────────┘ │  │ │
│   │  └─────────────┘  │          │  └──────────────┬──────────────────┘  │ │
│   │                   │          │                 │                     │ │
│   │  ┌─────────────┐  │          │  ┌──────────────▼──────────────────┐  │ │
│   │  │  Command    │  │          │  │         LLM Module              │  │ │
│   │  │  Input      │  │          │  │  ┌────────┐  ┌────────────────┐ │  │ │
│   │  └─────────────┘  │          │  │  │LiteLLM │  │ Game Master    │ │  │ │
│   │                   │          │  │  │ Client │  │ Prompts        │ │  │ │
│   └───────────────────┘          │  │  └────────┘  └────────────────┘ │  │ │
│                                  │  └──────────────┬──────────────────┘  │ │
│                                  │                 │                     │ │
│                                  │  ┌──────────────▼──────────────────┐  │ │
│                                  │  │        World Loader             │  │ │
│                                  │  │     (YAML → Pydantic)           │  │ │
│                                  │  └──────────────┬──────────────────┘  │ │
│                                  └─────────────────┼─────────────────────┘ │
│                                                    │                       │
│                                  ┌─────────────────▼─────────────────────┐ │
│                                  │           worlds/                     │ │
│                                  │  ┌─────────────────────────────────┐  │ │
│                                  │  │  world.yaml    locations.yaml   │  │ │
│                                  │  │  npcs.yaml     items.yaml       │  │ │
│                                  │  └─────────────────────────────────┘  │ │
│                                  └───────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend (React + TypeScript)

**Purpose**: Provide a terminal-style UI for player interaction.

**Key Components**:
- `Terminal.tsx` - Scrolling narrative display
- `CommandInput.tsx` - Player input with history
- `Sidebar.tsx` - Stats, inventory, location display
- `useGame.tsx` - State management hook

**State Management**:
- React Context for global game state
- localStorage for session persistence
- Optimistic updates with error rollback

### Backend (FastAPI + Python)

**Purpose**: Handle game logic, LLM orchestration, and state management.

**Modules**:

| Module | Responsibility |
|--------|---------------|
| `api/` | REST endpoints |
| `engine/` | Game logic, state management |
| `llm/` | LLM client, prompt templates |
| `models/` | Pydantic schemas |

### Game Engine

**State Manager** (`engine/state.py`):
- Maintains current game state
- Handles state transitions
- Validates state changes

**Action Processor** (`engine/actions.py`):
- Parses player input
- Coordinates with LLM
- Applies state changes

**World Loader** (`engine/world.py`):
- Loads YAML world files
- Validates world consistency on load
- Provides world context to LLM

**World Validator** (`engine/validator.py`):
- Validates flag consistency (flags checked are set somewhere)
- Validates location references (exits, item/NPC locations)
- Validates item references (requires_item, unlocks)
- Detects orphan flags (set but never checked)
- CLI: `python -m app.engine.validator <world_id>`

### LLM Integration

**Provider Abstraction** (`llm/client.py`):
- Uses LiteLLM for provider-agnostic calls
- Supports Gemini, OpenAI, Anthropic, Ollama
- Configuration via environment variables

**Game Master** (`llm/game_master.py`):
- System prompt with world context
- Structured output parsing (JSON)
- State change extraction

## Data Flow

### Player Action Flow

```
1. Player types "examine the painting"
         │
         ▼
2. Frontend sends POST /api/game/action
   { session_id: "abc", action: "examine the painting" }
         │
         ▼
3. Backend loads game state for session
         │
         ▼
4. Action Processor builds LLM request:
   - System prompt (world context, current state)
   - User prompt (player action)
         │
         ▼
5. LLM generates response:
   {
     "narrative": "The painting depicts...",
     "state_changes": { "llm_flags": { "noticed_slash_marks": true } }
   }
   Note: World-defined flags (like "examined_portraits") are set by
   interaction triggers, not by the LLM directly.
         │
         ▼
6. State Manager applies changes
         │
         ▼
7. Victory Check - did player win?
   - Check location, flags, inventory against victory conditions
   - If won: set status="won", append victory narrative
         │
         ▼
8. Response returned to frontend:
   {
     "narrative": "The painting depicts...",
     "state": { ... updated state ... },
     "game_complete": false,
     "ending_narrative": null
   }
         │
         ▼
9. Frontend updates display
```

### New Game Flow

```
1. Player clicks "Begin Adventure"
         │
         ▼
2. Frontend sends POST /api/game/new
   { world_id: "cursed-manor", player_name: "Traveler" }
         │
         ▼
3. Backend loads world YAML files
         │
         ▼
4. State Manager creates initial state
         │
         ▼
5. LLM generates opening narrative
         │
         ▼
6. Response with session_id + initial state
```

## Key Design Decisions

### 1. Structured LLM Responses

**Decision**: LLM returns JSON with narrative + state changes, not free text.

**Rationale**:
- Predictable parsing
- Clear separation of narrative from mechanics
- Easier to validate and test

**Implementation**:
```json
{
  "narrative": "The door creaks open, revealing...",
  "state_changes": {
    "inventory": { "add": ["rusty_key"], "remove": [] },
    "location": "secret_passage",
    "llm_flags": { "discovered_hidden_room": true }
  },
  "hints": ["The air feels colder here..."]
}
```

**Note**: World-defined `flags` (like `door_opened`) are set automatically by interaction triggers, not by the LLM. The LLM uses `llm_flags` for contextual narrative tracking.

### 2. State in System Prompt

**Decision**: Include full game state in each LLM request.

**Rationale**:
- LLM is stateless; context must be provided
- Ensures consistency across turns
- Allows recovery from errors

**Trade-off**: Token usage vs. reliability (we choose reliability)

### 3. YAML for World Content

**Decision**: Use YAML files for world definitions.

**Rationale**:
- Human-readable and editable
- Version-controllable with git
- Easy to validate with schemas
- No database needed for prototype

### 4. Provider-Agnostic LLM

**Decision**: Use LiteLLM abstraction layer.

**Rationale**:
- Switch providers without code changes
- Compare quality/cost across providers
- Support local models for privacy/cost

## State Schema

```python
class GameState:
    session_id: str
    player_name: str
    current_location: str
    inventory: list[str]
    stats: dict[str, int]  # health, etc.
    discovered_locations: list[str]
    flags: dict[str, bool]  # World-defined flags (set by interactions)
    llm_flags: dict[str, bool]  # AI-generated contextual flags
    turn_count: int
    npc_trust: dict[str, int]  # trust levels with NPCs
    npc_locations: dict[str, str]  # current NPC locations (for dynamic movement)
    status: str  # "playing", "won", or "lost"
```

### Flag Types

GAIME uses two separate flag namespaces:

| Type | Source | Purpose | Example |
|------|--------|---------|---------|
| `flags` | World interactions | Game mechanics, triggers, victory conditions | `found_secret_passage`, `examined_nursery` |
| `llm_flags` | AI-generated | Contextual narrative tracking | `talked_about_dagger`, `expressed_sympathy` |

**World-defined flags** (`flags`) are set by:
- Location interactions (`sets_flag` in interactions)
- Item use actions (`sets_flag` in use_actions)

**LLM-generated flags** (`llm_flags`) are set by the AI during narrative generation to track contextual details that don't affect game mechanics but help maintain narrative consistency.

This separation ensures:
- Game mechanics remain predictable and testable
- The AI can track narrative state without affecting core gameplay
- Debugging is easier (you can see what the AI "decided" vs. what the game logic set)

## Victory Conditions

Games can define win conditions in `world.yaml`:

```yaml
victory:
  location: final_room     # Player must be here
  flag: quest_complete     # This flag must be set
  item: magic_key          # Player must have this item
  narrative: |
    Congratulations! You have completed the adventure...
```

After each action, the engine checks if victory conditions are met. If so:
1. The game status changes to "won"
2. The victory narrative is appended to the response
3. Further actions are blocked

## Security Considerations

- Session IDs are randomly generated UUIDs
- No authentication in prototype (add for production)
- LLM responses are validated against schema
- User input is sanitized before LLM prompt

## Performance Notes

- In-memory state (prototype only)
- Consider Redis for production scaling
- LLM calls are the bottleneck (~1-3s)
- Frontend shows loading state during LLM calls

## NPC System

### Dynamic NPC Locations

NPCs can move between locations based on game state:

```
1. NPC Definition:
   butler_jenkins:
     location: dining_room
     location_changes:
       - when_flag: alarm_triggered
         move_to: entrance_hall
       - when_flag: escaped
         move_to: null  # NPC leaves the game entirely

2. Runtime Resolution (state.py):
   get_npc_current_location(npc_id):
     - Start with NPC's default location
     - Check each location_change trigger
     - Last matching trigger wins
     - Return current location (or None if NPC has left)
   
   get_present_npcs():
     - Skip NPCs with location = None (they've left the game)
     - For triggered NPCs, only check the specific move_to location
     - For roaming NPCs without triggers, check all locations in list
```

### Conditional NPC Appearances

NPCs with `appears_when` conditions only appear when ALL conditions are met:

```python
# NPC appears only if player has examined_nursery flag
appears_when:
  - condition: "has_flag"
    value: "examined_nursery"

# Runtime check in state.py _check_npc_appears()
```

## Image Variant System

### Problem

Static pre-generated images may show NPCs that shouldn't be visible yet (e.g., ghost appears in image before player triggers its appearance).

### Solution: Variant Images

For locations with conditional NPCs, generate multiple image variants:

```
worlds/cursed-manor/images/
├── upper_landing.png              # Base (no ghost)
├── upper_landing__with__ghost_child.png   # With ghost
└── upper_landing_variants.json    # Manifest
```

### Manifest Format

```json
{
  "location_id": "upper_landing",
  "base": "upper_landing.png",
  "variants": [
    {"npcs": ["ghost_child"], "image": "upper_landing__with__ghost_child.png"}
  ]
}
```

### Runtime Image Selection

```
1. Player enters location
2. API endpoint: GET /api/game/image/{session_id}/{location_id}
3. State Manager determines visible NPCs at location
4. Image generator loads variant manifest
5. Returns appropriate variant (or base image)
```

### Generating Variants

```bash
# Generate all variants for a location
POST /api/builder/{world_id}/images/{location_id}/generate-variants

# Check variant status
GET /api/builder/{world_id}/images/{location_id}/variants
```

## Future Considerations

- Multiplayer sessions
- Save/load game files
- Voice input/output
- Multi-NPC variant combinations (currently single-NPC only)

