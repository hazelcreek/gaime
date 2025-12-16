# API Reference

This document describes the GAIME backend REST API.

## Base URL

```
http://localhost:8000/api
```

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/worlds` | List available worlds |
| GET | `/game/engines` | List available game engines |
| POST | `/game/new` | Start new game |
| POST | `/game/action` | Process player action |
| GET | `/game/state/{session_id}` | Get current state |
| GET | `/game/debug/{session_id}` | Get debug info (flags, NPC visibility) |
| GET | `/game/image/{session_id}` | Get current location image (state-aware) |
| GET | `/game/image/{session_id}/{location_id}` | Get location image (state-aware) |
| GET | `/audio/menu-tracks` | List available menu music tracks |

---

## Health Check

Check if the server is running.

```
GET /
```

**Response**
```json
{
  "status": "ok",
  "name": "GAIME",
  "version": "0.1.0"
}
```

---

## List Worlds

Get available game worlds.

```
GET /api/worlds
```

**Response**
```json
{
  "worlds": [
    {
      "id": "cursed-manor",
      "name": "The Cursed Manor",
      "theme": "Victorian gothic horror",
      "description": "A haunted mansion with dark secrets"
    }
  ]
}
```

---

## List Engines

Get available game engine versions. Engine selection is primarily for migration testing.

```
GET /api/game/engines
```

**Response**
```json
{
  "engines": [
    {
      "id": "classic",
      "name": "Classic Engine",
      "description": "Single LLM call for action processing and narration"
    },
    {
      "id": "two_phase",
      "name": "Two-Phase Engine",
      "description": "Separated parsing (Interactor) and narration (Narrator)"
    }
  ],
  "default": "classic"
}
```

| Field | Description |
|-------|-------------|
| `engines` | Array of available engine versions |
| `default` | ID of the default engine |

**Note:** The two-phase engine currently supports movement only (Phase 1). Use `classic` for full gameplay.

---

## Start New Game

Begin a new game session.

```
POST /api/game/new
```

**Request Body**
```json
{
  "world_id": "cursed-manor",
  "debug": false,
  "engine": "classic"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| world_id | string | No | "cursed-manor" | ID of world to load |
| debug | boolean | No | false | Enable LLM debug info in response |
| engine | string | No | "classic" | Engine version (see `/game/engines`) |

**Response**
```json
{
  "session_id": "abc123-def456-...",
  "narrative": "A violent storm has driven you to seek shelter...",
  "engine_version": "classic",
  "llm_debug": null,
  "state": {
    "session_id": "abc123-def456-...",
    "current_location": "entrance_hall",
    "inventory": ["pocket_watch", "journal"],
    "discovered_locations": ["entrance_hall"],
    "flags": {},
    "turn_count": 0,
    "npc_trust": {},
    "npc_locations": {},
    "status": "playing",
    "narrative_memory": {
      "recent_exchanges": [],
      "npc_memory": {},
      "discoveries": []
    }
  }
}
```

**Errors**
- `404`: World not found
- `500`: Server error

---

## Process Action

Send a player action and receive narrative response.

```
POST /api/game/action
```

**Request Body**
```json
{
  "session_id": "abc123-def456-...",
  "action": "look around the room",
  "debug": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| session_id | string | Yes | Game session ID |
| action | string | Yes | Player's action text |
| debug | boolean | No | Enable LLM debug info in response (default: false) |

**Response**
```json
{
  "narrative": "You find yourself in a grand entrance hall. Faded portraits line the walls...",
  "state": {
    "session_id": "abc123-def456-...",
    "current_location": "entrance_hall",
    "inventory": ["pocket_watch", "journal"],
    "discovered_locations": ["entrance_hall"],
    "flags": {},
    "turn_count": 1,
    "status": "playing"
  },
  "hints": ["The portraits seem to be watching you..."],
  "game_complete": false,
  "ending_narrative": null,
  "llm_debug": null
}
```

**Errors**
- `404`: Session not found
- `500`: Server/LLM error

---

## Get Game State

Retrieve current game state without taking an action.

```
GET /api/game/state/{session_id}
```

**Response**
```json
{
  "state": {
    "session_id": "abc123-def456-...",
    "current_location": "entrance_hall",
    "inventory": ["pocket_watch", "journal"],
    "discovered_locations": ["entrance_hall"],
    "flags": {},
    "turn_count": 5,
    "npc_trust": {},
    "npc_locations": {},
    "status": "playing",
    "narrative_memory": {
      "recent_exchanges": [...],
      "npc_memory": {...},
      "discoveries": [...]
    }
  }
}
```

**Errors**
- `404`: Session not found

---

## Debug Game State

Get detailed debug information about game state, flags, and NPC visibility.

Useful for understanding why NPCs aren't appearing or which flags are set.

```
GET /api/game/debug/{session_id}
```

**Response**
```json
{
  "session_id": "abc123-def456-...",
  "current_location": "nursery",
  "turn_count": 5,
  "status": "playing",
  "flags": {
    "examined_portraits": true,
    "read_ritual_notes": true
  },
  "narrative_memory": {
    "recent_exchanges": [
      {"turn": 4, "player_action": "talk to jenkins", "narrative_summary": "Jenkins seemed hesitant..."}
    ],
    "npc_memory": {
      "butler_jenkins": {
        "encounter_count": 2,
        "first_met_location": "entrance_hall",
        "topics_discussed": ["the family", "the fire"],
        "player_disposition": "sympathetic",
        "npc_disposition": "warming up",
        "notable_moments": ["He mentioned Lady Margaret with sadness"]
      }
    },
    "discoveries": ["item:candlestick", "feature:slash_marks", "npc:butler_jenkins"]
  },
  "inventory": ["candlestick", "old_letter"],
  "discovered_locations": ["entrance_hall", "library", "upper_landing", "nursery"],
  "npc_trust": {
    "butler_jenkins": 1
  },
  "npc_analysis": [
    {
      "npc_id": "ghost_child",
      "name": "The Whisper",
      "role": "Spirit of the youngest child, Emily",
      "base_location": null,
      "roaming_locations": ["nursery", "upper_landing", "library", "sitting_room"],
      "current_location": null,
      "player_location": "nursery",
      "is_at_player_location": true,
      "has_appears_when": true,
      "conditions": [
        {
          "type": "has_flag",
          "flag": "examined_nursery",
          "required": true,
          "current_value": false,
          "met": false
        }
      ],
      "all_conditions_met": false,
      "would_be_visible": false
    }
  ],
  "interactions_at_location": [
    {
      "id": "examine_drawings",
      "triggers": ["examine drawings", "look at drawings", "study drawings"],
      "sets_flag": "understood_sacrifice",
      "reveals_exit": null
    },
    {
      "id": "examine_nursery",
      "triggers": ["examine nursery", "look around", "search room"],
      "sets_flag": "examined_nursery",
      "reveals_exit": null
    }
  ]
}
```

**NPC Analysis Fields**

| Field | Description |
|-------|-------------|
| `is_at_player_location` | Whether NPC is at the player's current location |
| `has_appears_when` | Whether NPC has appearance conditions |
| `conditions` | Details of each condition and whether it's met |
| `all_conditions_met` | True if all appearance conditions are satisfied |
| `would_be_visible` | True if NPC would appear (at location AND conditions met) |

**In-Game Debug Command**

You can also type `debug` in the game to see formatted state info in the terminal.

**Errors**
- `404`: Session not found

---

## Get Location Image (State-Aware)

Get the appropriate location image based on current game state.

This returns the correct image variant if the location has conditional NPCs.

```
GET /api/game/image/{session_id}/{location_id}
```

**Response**
- Content-Type: `image/png`
- Returns the appropriate PNG image based on which NPCs are visible

**Example**
```
# Before examining nursery (ghost not visible)
GET /api/game/image/abc123/upper_landing
# Returns: upper_landing.png (base image, no ghost)

# After examining nursery (ghost appears)
GET /api/game/image/abc123/upper_landing
# Returns: upper_landing__with__ghost_child.png (variant with ghost)
```

**Errors**
- `404`: Session or image not found

---

## Get Current Location Image

Convenience endpoint to get the image for the player's current location.

```
GET /api/game/image/{session_id}
```

**Response**
- Content-Type: `image/png`
- Returns the image for the session's current location

**Errors**
- `404`: Session not found

---

## List Menu Tracks

Get available menu music tracks. The backend scans `frontend/public/audio/menu/` for `.mp3` files.

```
GET /api/audio/menu-tracks
```

**Response**
```json
{
  "tracks": [
    "/audio/menu/dark-ambient.mp3",
    "/audio/menu/theme-1.mp3"
  ]
}
```

The frontend randomly selects one track from this list for playback.

**Adding New Tracks**

Simply drop `.mp3` files into `frontend/public/audio/menu/` - they will be automatically discovered.

---

## Data Models

### GameState

```typescript
interface GameState {
  session_id: string;
  current_location: string;
  inventory: string[];
  discovered_locations: string[];
  flags: Record<string, boolean>;           // World-defined flags (set by interactions)
  turn_count: number;
  npc_trust: Record<string, number>;        // Trust levels with NPCs
  npc_locations: Record<string, string>;    // Current NPC locations
  status: "playing" | "won" | "lost";       // Game completion status
  narrative_memory: NarrativeMemory;        // Narrative context tracking
}

interface NarrativeMemory {
  recent_exchanges: NarrativeExchange[];    // Last 2-3 turns for continuity
  npc_memory: Record<string, NPCInteractionMemory>;  // Per-NPC interaction history
  discoveries: string[];                    // Typed IDs: "item:key", "npc:ghost"
}

interface NarrativeExchange {
  turn: number;
  player_action: string;
  narrative_summary: string;                // Truncated to ~100 words
}

interface NPCInteractionMemory {
  encounter_count: number;
  first_met_location: string | null;
  first_met_turn: number | null;
  topics_discussed: string[];               // Max 10 topics
  player_disposition: string;               // Freeform: "sympathetic", "hostile"
  npc_disposition: string;                  // How NPC feels toward player
  notable_moments: string[];                // Max 3 moments
  last_interaction_turn: number;
}
```

### NewGameResponse

```typescript
interface NewGameResponse {
  session_id: string;
  narrative: string;
  state: GameState;
  engine_version: string;        // Engine used for this session
  llm_debug?: LLMDebugInfo;      // Debug info when debug=true
}
```

### ActionResponse

```typescript
interface ActionResponse {
  narrative: string;
  state: GameState;
  hints?: string[];
  game_complete: boolean;        // True if game has ended
  ending_narrative?: string;     // Victory/defeat narrative if game ended
  llm_debug?: LLMDebugInfo;      // Debug info when debug=true
}
```

### LLMDebugInfo

Returned when `debug=true` is passed in the request.

```typescript
interface LLMDebugInfo {
  system_prompt: string;         // Full system prompt sent to LLM
  user_prompt: string;           // User prompt for this action
  raw_response: string;          // Raw LLM response before parsing
  parsed_response: object;       // Parsed JSON from LLM
  model: string;                 // Model used (e.g., "gemini/gemini-3-pro")
  timestamp: string;             // ISO timestamp of the interaction
}
```

**Note:** When debug mode is enabled, LLM interactions are also logged to files in `logs/{world_id}/` with timestamps for later review.

### WorldInfo

```typescript
interface WorldInfo {
  id: string;
  name: string;
  theme: string;
  description?: string;
}
```

### EngineInfo

```typescript
interface EngineInfo {
  id: string;           // Engine identifier (e.g., "classic", "two_phase")
  name: string;         // Display name
  description: string;  // Brief description of the engine
}
```

### TwoPhaseGameState

State model for the two-phase engine (separate from classic `GameState`).

```typescript
interface TwoPhaseGameState {
  session_id: string;
  current_location: string;
  inventory: string[];
  flags: Record<string, boolean>;
  visited_locations: string[];          // Set of visited location IDs
  container_states: Record<string, boolean>;  // container_id -> is_open
  turn_count: number;
  status: "playing" | "won" | "lost";
}
```

### TwoPhaseNewGameResponse

Response for two-phase engine game start.

```typescript
interface TwoPhaseNewGameResponse {
  session_id: string;
  narrative: string;
  state: TwoPhaseGameState;            // Note: Different from classic GameState
  engine_version: "two_phase";
  llm_debug?: LLMDebugInfo;
}
```

### TwoPhaseActionResponse

Response from two-phase engine action processing.

```typescript
interface TwoPhaseActionResponse {
  narrative: string;
  state: TwoPhaseGameState;
  events: object[];                    // List of events that occurred
  game_complete: boolean;
  ending_narrative?: string;
  llm_debug?: LLMDebugInfo;
}
```

**Note:** When using the two-phase engine, responses use `TwoPhaseGameState` instead of `GameState`. The state model is simplified and does not include narrative memory (context handled differently).

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad request (invalid input) |
| 404 | Resource not found |
| 500 | Server error |

---

## Example Session

```bash
# 1. Start a new game
curl -X POST http://localhost:8000/api/game/new \
  -H "Content-Type: application/json" \
  -d '{"world_id": "cursed-manor"}'

# Response includes session_id

# 2. Take an action
curl -X POST http://localhost:8000/api/game/action \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "action": "examine the portraits on the wall"
  }'

# 3. Check state
curl http://localhost:8000/api/game/state/YOUR_SESSION_ID
```

---

## CORS

The API allows requests from:
- `http://localhost:5173` (Vite dev server)
- `http://127.0.0.1:5173`

For production, configure allowed origins in `backend/app/main.py`.
