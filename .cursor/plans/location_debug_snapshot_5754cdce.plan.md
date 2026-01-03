---
name: Location Debug Snapshot
overview: Extend the VisibilityResolver to build a comprehensive "LocationDebugSnapshot" that merges world definitions with game state, then expose this through the /state endpoint and display it in the StateOverlay component.
todos:
  - id: debug-models
    content: Create LocationDebugSnapshot models in perception.py
    status: completed
  - id: visibility-method
    content: Add build_debug_snapshot() to DefaultVisibilityResolver
    status: completed
    dependencies:
      - debug-models
  - id: api-endpoint
    content: Extend /state endpoint to include location_debug
    status: completed
    dependencies:
      - visibility-method
  - id: frontend-types
    content: Add TypeScript types for location debug in client.ts
    status: completed
    dependencies:
      - api-endpoint
  - id: state-overlay-ui
    content: Add Current Location section to StateOverlay component
    status: completed
    dependencies:
      - frontend-types
  - id: fetch-on-open
    content: Update useGame to fetch extended state when overlay opens
    status: completed
    dependencies:
      - frontend-types
  - id: docs-pattern
    content: Add docs/DEBUG_SNAPSHOT.md explaining the pattern and extension guidelines
    status: completed
    dependencies:
      - visibility-method
  - id: cursor-rules
    content: Update .cursorrules with model sync requirements for debug snapshot
    status: completed
    dependencies:
      - debug-models
---

# Location Debug Snapshot with Unified Visibility Logic

## Motivation

The logic for merging world definitions with game state is needed in multiple places:

- Interactor/Parser (what player can reference)
- Action validation (what actions are valid)
- Narrator (what to describe)
- Debug view (what we're building)

This plan centralizes that logic in the `VisibilityResolver` while adding a debug-focused snapshot.

## Key Insight

`PerceptionSnapshot` shows **what the player CAN see** (for Narrator). The debug view needs **everything with visibility status** - items that are hidden (marked as hidden), NPCs that aren't appearing (marked with reason), etc.

## Implementation

### 1. Create Debug Snapshot Models

Add to [`backend/app/engine/two_phase/models/perception.py`](backend/app/engine/two_phase/models/perception.py):

```python
class LocationItemDebug(BaseModel):
    """Item at location with full visibility analysis."""
    item_id: str
    name: str
    found_description: str
    is_visible: bool
    is_in_inventory: bool
    visibility_reason: str  # "visible", "hidden", "taken", "condition_not_met"
    placement: str | None  # from item_placements

class LocationNPCDebug(BaseModel):
    """NPC at location with full visibility analysis."""
    npc_id: str
    name: str
    role: str
    appearance: str
    is_visible: bool
    visibility_reason: str  # "visible", "condition_not_met:flag_x", "removed", etc.
    placement: str | None

class LocationExitDebug(BaseModel):
    """Exit with accessibility analysis."""
    direction: str
    destination_id: str
    destination_name: str
    is_accessible: bool
    access_reason: str  # "accessible", "requires_flag:x", "requires_item:y"
    description: str | None

class LocationDebugSnapshot(BaseModel):
    """Full location state for debug view - shows everything with status."""
    location_id: str
    name: str
    atmosphere: str
    exits: list[LocationExitDebug]
    items: list[LocationItemDebug]
    npcs: list[LocationNPCDebug]
    details: dict[str, str]
    interactions: list[dict]  # Simplified interaction info
```



### 2. Extend VisibilityResolver

Add `build_debug_snapshot()` method to [`backend/app/engine/two_phase/visibility.py`](backend/app/engine/two_phase/visibility.py):

```python
def build_debug_snapshot(
    self,
    state: "TwoPhaseGameState",
    world: "WorldData",
) -> LocationDebugSnapshot:
    """Build complete debug snapshot with ALL entities and their visibility status."""
```

This reuses the existing visibility logic (`is_item_visible`, `_check_npc_appears`, etc.) but returns everything with status flags rather than filtering.

### 3. Update API Response

Modify [`backend/app/api/game.py`](backend/app/api/game.py) `/state/{session_id}` endpoint to include `location_debug`:

```python
@router.get("/state/{session_id}")
async def get_state(session_id: str):
    # ... existing code ...
    resolver = DefaultVisibilityResolver()
    location_debug = resolver.build_debug_snapshot(state, world)
    return {
        "state": state,
        "engine": engine,
        "location_debug": location_debug,  # NEW
    }
```



### 4. Update Frontend Types

Add TypeScript interfaces to [`frontend/src/api/client.ts`](frontend/src/api/client.ts) mirroring the backend models.

### 5. Update StateOverlay

Add "Current Location" section to [`frontend/src/components/StateOverlay.tsx`](frontend/src/components/StateOverlay.tsx) that displays:

- Location name and atmosphere
- Exits table (direction, destination, accessible status)
- Items table (name, visible status, reason)
- NPCs table (name, visible status, reason)
- Details and interactions

### 6. Fetch on Overlay Open

Update [`frontend/src/hooks/useGame.tsx`](frontend/src/hooks/useGame.tsx) to fetch extended state when overlay opens (avoids bloating every action response).

## Future Extensibility

When world models are extended:

1. Add fields to `LocationDebugSnapshot` models
2. Update `build_debug_snapshot()` to populate them
3. Update frontend types and UI

The single `build_debug_snapshot()` method is the source of truth for merged state.

### 7. Extensibility Documentation (Three-Pronged Approach)

**A. Documentation (`docs/DEBUG_SNAPSHOT.md`)**

- Explain the relationship between world models and debug snapshot models
- Document the pattern: world model change → debug model update → frontend type update
- List the mapping between `models/world.py` fields and `LocationDebugSnapshot` fields

**B. Inline Code Comments**

- Docstrings in debug models referencing source world models
- Comments in `build_debug_snapshot()` explaining visibility logic
- TypeScript JSDoc comments linking to backend models

**C. Cursor Rules (`.cursorrules`)**Add to Documentation Maintenance table:| Change Type | Docs to Update ||-------------|----------------|| New Location fields (`models/world.py`) | `LocationDebugSnapshot` + `LocationExitDebug` + frontend types || New Item fields (`models/world.py`) | `LocationItemDebug` + frontend types || New NPC fields (`models/world.py`) | `LocationNPCDebug` + frontend types || New visibility rules | `DefaultVisibilityResolver.build_debug_snapshot()` |

## Files Changed
