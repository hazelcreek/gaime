---
name: Phase 0 Foundation
overview: ""
todos:
  - id: engine-enum
    content: Create EngineVersion enum in backend/app/api/engine.py
    status: completed
  - id: api-update
    content: Update game.py with engine param and /engines endpoint
    status: completed
    dependencies:
      - engine-enum
  - id: model-exports
    content: Export two-phase models from models/__init__.py
    status: completed
  - id: frontend-api
    content: Add engine types and listEngines() to frontend API client
    status: completed
    dependencies:
      - api-update
  - id: frontend-ui
    content: Add engine selector to MainMenu component
    status: completed
    dependencies:
      - frontend-api
  - id: frontend-hook
    content: Update useGame hook to pass engine to API
    status: completed
    dependencies:
      - frontend-api
  - id: api-tests
    content: Add unit tests for engine selection API
    status: completed
    dependencies:
      - api-update
  - id: docs-update
    content: Update API.md with engine selection documentation
    status: completed
    dependencies:
      - api-update
---

# Phase 0: Two-Phase Engine Foundation

Complete the foundation for the two-phase game loop by adding engine selection infrastructure. The core data models (intent, event, perception, validation) are already implemented with tests.

## Overview

Add engine selection as lightweight session metadata, a listing endpoint for frontends, and export the new models. The engine version stays out-of-band from `GameState` for easy removal post-migration.

---

## 1. Add EngineVersion Enum

Create [`backend/app/api/engine.py`](backend/app/api/engine.py) with:

```python
from enum import Enum

class EngineVersion(str, Enum):
    CLASSIC = "classic"
    TWO_PHASE = "two_phase"
```

Placing it in `api/` since it's an API-level concern, not core game state.

---

## 2. Update API for Engine Selection

Modify [`backend/app/api/game.py`](backend/app/api/game.py):

- Add `engine: EngineVersion = EngineVersion.CLASSIC` to `NewGameRequest`
- Add `engine_version: EngineVersion` to `NewGameResponse`
- Store engine version alongside session in `game_sessions` (as tuple or wrapper)
- Add new `GET /engines` endpoint
```python
@router.get("/engines")
async def list_engines():
    return {
        "engines": [
            {"id": "classic", "name": "Classic Engine", "description": "..."},
            {"id": "two_phase", "name": "Two-Phase Engine", "description": "..."},
        ],
        "default": "classic"
    }
```


---

## 3. Export New Models

Update [`backend/app/models/__init__.py`](backend/app/models/__init__.py) to export:

- `ActionIntent`, `FlavorIntent`, `ActionType`, `Intent` from `intent.py`
- `Event`, `RejectionEvent`, `EventType`, `RejectionCode` from `event.py`
- `PerceptionSnapshot`, `VisibleEntity`, `VisibleExit` from `perception.py`
- `ValidationResult`, `valid_result`, `invalid_result` from `validation.py`

---

## 4. Add Backend Tests

Create [`backend/tests/unit/test_api/test_engine_selection.py`](backend/tests/unit/test_api/test_engine_selection.py):

- Test `EngineVersion` enum values
- Test `/engines` endpoint returns expected structure
- Test `NewGameRequest` accepts engine parameter
- Test default engine is CLASSIC

---

## 5. Frontend Engine Selection

### 5.1 Update API Client

Modify [`frontend/src/api/client.ts`](frontend/src/api/client.ts):

- Add `EngineInfo` interface
- Add `engine?: string` parameter to `newGame()` method
- Add `listEngines()` method to fetch available engines
```typescript
export interface EngineInfo {
  id: string;
  name: string;
  description: string;
}

async listEngines(): Promise<{ engines: EngineInfo[], default: string }> {
  const response = await fetch(`${API_BASE}/game/engines`);
  return response.json();
}

async newGame(worldId: string, debug: boolean, engine?: string): Promise<NewGameResponse> {
  // ... add engine to body
}
```


### 5.2 Update MainMenu Component

Modify [`frontend/src/components/MainMenu.tsx`](frontend/src/components/MainMenu.tsx):

- Add engine state and selection UI (collapsible "Advanced" section)
- Fetch engines on mount using `gameAPI.listEngines()`
- Pass selected engine to `onStartGame`
```tsx
// Collapsible advanced section with engine dropdown
<details className="...">
  <summary>Advanced Options</summary>
  <select value={selectedEngine} onChange={...}>
    {engines.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
  </select>
</details>
```


### 5.3 Update useGame Hook

Modify [`frontend/src/hooks/useGame.tsx`](frontend/src/hooks/useGame.tsx):

- Update `startNewGame` signature to accept optional engine parameter
- Pass engine to `gameAPI.newGame()`

---

## 6. Update API Documentation

Update [`docs/API.md`](docs/API.md):

- Add `GET /api/game/engines` endpoint documentation
- Update `POST /api/game/new` request/response to show `engine` field
- Note that engine selection is for migration testing

---

## Key Files

| File | Change |

|------|--------|

| `backend/app/api/engine.py` | NEW - EngineVersion enum |

| `backend/app/api/game.py` | Add engine param + /engines endpoint |

| `backend/app/models/__init__.py` | Export two-phase models |

| `backend/tests/unit/test_api/test_engine_selection.py` | NEW - API tests |

| `frontend/src/api/client.ts` | Add engine types + listEngines() |

| `frontend/src/components/MainMenu.tsx` | Add engine selector UI |

| `frontend/src/hooks/useGame.tsx` | Pass engine to API |

| `docs/API.md` | Document engine selection |
