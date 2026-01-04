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

## Start New Game

Begin a new game session.

```
POST /api/game/new
```

**Request Body**
```json
{
  "world_id": "cursed-manor",
  "debug": false
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| world_id | string | No | "cursed-manor" | ID of world to load |
| debug | boolean | No | false | Enable LLM debug info in response |

**Response**
```json
{
  "session_id": "abc123-def456-...",
  "narrative": "A violent storm has driven you to seek shelter...",
  "pipeline_debug": null,
  "state": {
    "session_id": "abc123-def456-...",
    "current_location": "entrance_hall",
    "inventory": ["pocket_watch", "journal"],
    "visited_locations": ["entrance_hall"],
    "container_states": {},
    "flags": {},
    "turn_count": 0,
    "status": "playing"
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
    "visited_locations": ["entrance_hall"],
    "container_states": {},
    "flags": {},
    "turn_count": 1,
    "status": "playing"
  },
  "events": [],
  "game_complete": false,
  "ending_narrative": null,
  "pipeline_debug": null
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
    "visited_locations": ["entrance_hall"],
    "container_states": {},
    "flags": {},
    "turn_count": 5,
    "status": "playing"
  },
  "location_debug": {
    "location_id": "entrance_hall",
    "name": "Entrance Hall",
    "atmosphere": "...",
    "exits": [...],
    "items": [...],
    "npcs": [...],
    "details": {...},
    "interactions": [...],
    "requires": null
  }
}
```

**Errors**
- `404`: Session not found

---

## Debug Game State

Get detailed debug information about game state, flags, and visibility.

Useful for understanding why items or NPCs aren't appearing.

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
  "inventory": ["candlestick", "old_letter"],
  "visited_locations": ["entrance_hall", "library", "upper_landing", "nursery"],
  "container_states": {}
}
```

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
  visited_locations: string[];          // Set of visited location IDs
  container_states: Record<string, boolean>;  // container_id -> is_open
  flags: Record<string, boolean>;       // World-defined flags (set by interactions)
  turn_count: number;
  status: "playing" | "won" | "lost";   // Game completion status
}
```

### NewGameResponse

```typescript
interface NewGameResponse {
  session_id: string;
  narrative: string;
  state: GameState;
  pipeline_debug?: PipelineDebugInfo;   // Debug info when debug=true
}
```

### ActionResponse

```typescript
interface ActionResponse {
  narrative: string;
  state: GameState;
  events: object[];              // List of events that occurred
  game_complete: boolean;        // True if game has ended
  ending_narrative?: string;     // Victory/defeat narrative if game ended
  pipeline_debug?: PipelineDebugInfo;  // Debug info when debug=true
}
```

### PipelineDebugInfo

Returned when `debug=true` is passed in the request. Shows debug info at each pipeline stage.

```typescript
interface PipelineDebugInfo {
  raw_input: string;             // Player's raw input
  parser_type: string;           // "rule_based" or "interactor_ai"
  parsed_intent: object | null;  // Parsed intent
  interactor_debug: LLMDebugInfo | null;  // LLM debug for interactor (if used)
  validation_result: object | null;       // Validation result
  events: object[];              // Generated events
  narrator_debug: LLMDebugInfo | null;    // LLM debug for narrator
}

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
