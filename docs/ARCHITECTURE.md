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
- Validates against schema
- Provides world context to LLM

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
     "state_changes": { "flags": { "examined_painting": true } }
   }
         │
         ▼
6. State Manager applies changes
         │
         ▼
7. Response returned to frontend:
   {
     "narrative": "The painting depicts...",
     "state": { ... updated state ... }
   }
         │
         ▼
8. Frontend updates display
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
    "flags": { "door_opened": true }
  },
  "hints": ["The air feels colder here..."]
}
```

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
    flags: dict[str, bool]  # story progress
    turn_count: int
```

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

## Future Considerations

- Multiplayer sessions
- Save/load game files
- Voice input/output
- Image generation for scenes

