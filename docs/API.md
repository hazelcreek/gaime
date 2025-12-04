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
| POST | `/builder/generate` | Generate world from prompt |
| POST | `/builder/save/{world_id}` | Save generated world |
| GET | `/builder/{world_id}/locations` | List world locations |
| POST | `/builder/{world_id}/images/generate` | Generate all scene images |
| POST | `/builder/{world_id}/images/{location_id}/generate` | Generate single image |
| POST | `/builder/{world_id}/images/{location_id}/generate-variants` | Generate image variants |
| GET | `/builder/{world_id}/images/{location_id}/variants` | Get variant info |
| GET | `/builder/{world_id}/images` | List available images |
| GET | `/builder/{world_id}/images/{location_id}` | Get location image (static) |

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
  "player_name": "Traveler"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| world_id | string | No | "cursed-manor" | ID of world to load |
| player_name | string | No | "Traveler" | Player's name |

**Response**
```json
{
  "session_id": "abc123-def456-...",
  "narrative": "A violent storm has driven you to seek shelter...",
  "state": {
    "session_id": "abc123-def456-...",
    "player_name": "Traveler",
    "current_location": "entrance_hall",
    "inventory": ["pocket_watch", "journal"],
    "stats": {
      "health": 100
    },
    "discovered_locations": ["entrance_hall"],
    "flags": {},
    "turn_count": 0
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
  "action": "look around the room"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| session_id | string | Yes | Game session ID |
| action | string | Yes | Player's action text |

**Response**
```json
{
  "narrative": "You find yourself in a grand entrance hall. Faded portraits line the walls...",
  "state": {
    "session_id": "abc123-def456-...",
    "player_name": "Traveler",
    "current_location": "entrance_hall",
    "inventory": ["pocket_watch", "journal"],
    "stats": {
      "health": 100
    },
    "discovered_locations": ["entrance_hall"],
    "flags": {},
    "turn_count": 1,
    "status": "playing"
  },
  "hints": ["The portraits seem to be watching you..."],
  "game_complete": false,
  "ending_narrative": null
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
    "player_name": "Traveler",
    "current_location": "entrance_hall",
    "inventory": ["pocket_watch", "journal"],
    "stats": {
      "health": 100
    },
    "discovered_locations": ["entrance_hall"],
    "flags": {},
    "turn_count": 5,
    "status": "playing"
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

## Generate World

Use AI to generate a new game world.

```
POST /api/builder/generate
```

**Request Body**
```json
{
  "prompt": "A haunted lighthouse on a remote island",
  "theme": "cosmic horror",
  "num_locations": 6,
  "num_npcs": 3
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| prompt | string | Yes | - | Description of desired world |
| theme | string | No | null | Genre/atmosphere |
| num_locations | int | No | 6 | Number of locations |
| num_npcs | int | No | 3 | Number of NPCs |

**Response**
```json
{
  "world_id": "haunted-lighthouse",
  "world_yaml": "name: The Haunted Lighthouse\ntheme: cosmic horror\n...",
  "locations_yaml": "lighthouse_base:\n  name: Lighthouse Base\n...",
  "npcs_yaml": "keeper_thomas:\n  name: Thomas\n...",
  "items_yaml": "old_logbook:\n  name: Keeper's Logbook\n...",
  "message": "World generated successfully"
}
```

**Errors**
- `500`: Generation failed

---

## Save Generated World

Save AI-generated world content to files.

```
POST /api/builder/save/{world_id}
```

**Request Body**
```json
{
  "world_yaml": "...",
  "locations_yaml": "...",
  "npcs_yaml": "...",
  "items_yaml": "..."
}
```

**Response**
```json
{
  "message": "World 'haunted-lighthouse' saved successfully"
}
```

**Errors**
- `500`: Save failed

---

## List World Locations

Get all locations in a world with their metadata.

```
GET /api/builder/{world_id}/locations
```

**Response**
```json
{
  "world_id": "cursed-manor",
  "locations": [
    {
      "id": "entrance_hall",
      "name": "Entrance Hall",
      "has_image": true,
      "atmosphere": "A grand but decayed entrance hall greets you..."
    }
  ],
  "count": 12
}
```

**Errors**
- `404`: World not found

---

## Generate Scene Images

Generate scene images for all or selected locations in a world.

```
POST /api/builder/{world_id}/images/generate
```

**Request Body**
```json
{
  "location_ids": ["entrance_hall", "library"]
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| location_ids | string[] | No | null | Specific locations (null = all) |

**Response**
```json
{
  "world_id": "cursed-manor",
  "results": [
    {
      "location_id": "entrance_hall",
      "success": true,
      "image_url": "/api/builder/cursed-manor/images/entrance_hall"
    },
    {
      "location_id": "library",
      "success": false,
      "error": "Image generation failed"
    }
  ],
  "message": "Generated 1/2 images successfully"
}
```

**Errors**
- `404`: World not found
- `500`: Generation failed

---

## Generate Single Image

Generate or regenerate the image for a single location.

```
POST /api/builder/{world_id}/images/{location_id}/generate
```

**Response**
```json
{
  "success": true,
  "location_id": "entrance_hall",
  "image_url": "/api/builder/cursed-manor/images/entrance_hall",
  "message": "Image generated for Entrance Hall"
}
```

**Errors**
- `404`: World or location not found
- `500`: Generation failed

---

## Generate Image Variants

Generate all image variants for a location with conditional NPCs.

```
POST /api/builder/{world_id}/images/{location_id}/generate-variants
```

**Response**
```json
{
  "success": true,
  "location_id": "upper_landing",
  "base_image": "/api/builder/cursed-manor/images/upper_landing",
  "variants": [
    {
      "npcs": ["ghost_child"],
      "image_url": "/api/builder/cursed-manor/images/upper_landing__with__ghost_child"
    }
  ],
  "manifest_path": "upper_landing_variants.json",
  "images_generated": 2,
  "message": "Generated 2 image variants"
}
```

**Errors**
- `404`: World or location not found
- `500`: Generation failed

---

## Get Variant Info

Check which image variants exist for a location.

```
GET /api/builder/{world_id}/images/{location_id}/variants
```

**Response (with variants)**
```json
{
  "has_variants": true,
  "location_id": "upper_landing",
  "base_image": "upper_landing.png",
  "variants": [
    {"npcs": ["ghost_child"], "image": "upper_landing__with__ghost_child.png"}
  ],
  "conditional_npcs": ["ghost_child"],
  "variant_count": 1
}
```

**Response (without variants)**
```json
{
  "has_variants": false,
  "location_id": "entrance_hall",
  "conditional_npcs": [],
  "message": "No variants generated yet. Use POST /generate-variants to create them."
}
```

---

## List World Images

List all available images for a world.

```
GET /api/builder/{world_id}/images
```

**Response**
```json
{
  "world_id": "cursed-manor",
  "images": {
    "entrance_hall": "/api/builder/cursed-manor/images/entrance_hall",
    "library": "/api/builder/cursed-manor/images/library"
  },
  "count": 2
}
```

---

## Get Location Image

Retrieve the generated image for a location.

```
GET /api/builder/{world_id}/images/{location_id}
```

**Response**
- Content-Type: `image/png`
- Returns the PNG image file

**Errors**
- `404`: Image not found

---

## Data Models

### GameState

```typescript
interface GameState {
  session_id: string;
  player_name: string;
  current_location: string;
  inventory: string[];
  stats: {
    health: number;
    [key: string]: number;
  };
  discovered_locations: string[];
  flags: Record<string, boolean>;
  turn_count: number;
  npc_trust: Record<string, number>;    // Trust levels with NPCs
  npc_locations: Record<string, string>; // Current NPC locations
  status: "playing" | "won" | "lost";   // Game completion status
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
}
```

### WorldInfo

```typescript
interface WorldInfo {
  id: string;
  name: string;
  theme: string;
  description?: string;
}
```

### ImageGenerationResult

```typescript
interface ImageGenerationResult {
  location_id: string;
  success: boolean;
  image_url?: string;
  error?: string;
}
```

### GenerateImagesResponse

```typescript
interface GenerateImagesResponse {
  world_id: string;
  results: ImageGenerationResult[];
  message: string;
}
```

### LocationInfo

```typescript
interface LocationInfo {
  id: string;
  name: string;
  has_image: boolean;
  atmosphere: string;
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

