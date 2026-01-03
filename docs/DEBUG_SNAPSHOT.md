# Debug Snapshot Architecture

This document explains the LocationDebugSnapshot pattern for merging world definitions with game state, and how to extend it when models change.

## Overview

The **LocationDebugSnapshot** provides a unified view of the current location's world data merged with game state visibility information. Unlike `PerceptionSnapshot` (which filters to what the player can see), the debug snapshot shows **everything** with visibility status flags.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        World Data (YAML)                            │
│  locations.yaml, items.yaml, npcs.yaml, world.yaml                  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   models/world.py (Pydantic)                        │
│  Location, Item, NPC, World, WorldData                              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
┌─────────────────────────────┐   ┌─────────────────────────────────┐
│     PerceptionSnapshot      │   │     LocationDebugSnapshot       │
│  (Narrator - filtered)      │   │   (Debug UI - everything)       │
│                             │   │                                 │
│  • visible_items            │   │  • items (all + visibility)     │
│  • visible_npcs             │   │  • npcs (all + visibility)      │
│  • visible_exits            │   │  • exits (all + accessibility)  │
│  • (only what player sees)  │   │  • (everything with status)     │
└─────────────────────────────┘   └─────────────────────────────────┘
                    │                           │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   DefaultVisibilityResolver                         │
│  build_snapshot() → PerceptionSnapshot                              │
│  build_debug_snapshot() → LocationDebugSnapshot                     │
│                                                                     │
│  Single source of truth for visibility logic                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Principles

1. **Single Source of Truth**: `DefaultVisibilityResolver` contains all visibility logic
2. **No Duplication**: Debug snapshot reuses visibility methods from the resolver
3. **Complete Information**: Debug snapshot shows hidden items/NPCs with reasons
4. **Type Safety**: Pydantic models on backend, TypeScript interfaces on frontend

## Model Mapping

| World Model Field | Debug Model | Location |
|-------------------|-------------|----------|
| `Location.name` | `LocationDebugSnapshot.name` | perception.py |
| `Location.atmosphere` | `LocationDebugSnapshot.atmosphere` | perception.py |
| `Location.exits` | `LocationDebugSnapshot.exits[]` | perception.py |
| `Location.items` | `LocationDebugSnapshot.items[]` | perception.py |
| `Location.npcs` | `LocationDebugSnapshot.npcs[]` | perception.py |
| `Location.details` | `LocationDebugSnapshot.details` | perception.py |
| `Location.interactions` | `LocationDebugSnapshot.interactions[]` | perception.py |
| `Location.requires` | `LocationDebugSnapshot.requires` | perception.py |
| `Location.item_placements` | `LocationItemDebug.placement` | perception.py |
| `Location.npc_placements` | `LocationNPCDebug.placement` | perception.py |
| `Item.name` | `LocationItemDebug.name` | perception.py |
| `Item.found_description` | `LocationItemDebug.found_description` | perception.py |
| `Item.examine` | `LocationItemDebug.examine` | perception.py |
| `Item.portable` | `LocationItemDebug.portable` | perception.py |
| `Item.hidden` | Used in `visibility_reason` | visibility.py |
| `Item.find_condition` | Used in `visibility_reason` | visibility.py |
| `NPC.name` | `LocationNPCDebug.name` | perception.py |
| `NPC.role` | `LocationNPCDebug.role` | perception.py |
| `NPC.appearance` | `LocationNPCDebug.appearance` | perception.py |
| `NPC.appears_when` | Used in `visibility_reason` | visibility.py |
| `NPC.location_changes` | Used in `visibility_reason` | visibility.py |

## Extending the Pattern

When you add a new field to a world model, follow these steps:

### Step 1: Update Backend Debug Models

Add the field to the appropriate debug model in `backend/app/engine/two_phase/models/perception.py`:

```python
class LocationItemDebug(BaseModel):
    # ... existing fields ...
    new_field: str | None = None  # NEW: Add description
```

### Step 2: Update Visibility Resolver

Update `build_debug_snapshot()` or its helper methods in `backend/app/engine/two_phase/visibility.py`:

```python
def _get_items_debug(self, ...):
    items.append(
        LocationItemDebug(
            # ... existing fields ...
            new_field=item.new_field,  # NEW
        )
    )
```

### Step 3: Update Frontend Types

Add the field to the TypeScript interface in `frontend/src/api/client.ts`:

```typescript
export interface LocationItemDebug {
  // ... existing fields ...
  /** Description of the new field */
  new_field: string | null;
}
```

### Step 4: Update StateOverlay UI

Display the new field in `frontend/src/components/StateOverlay.tsx`:

```tsx
function ItemRow({ item }: { item: LocationItemDebug }) {
  return (
    <div>
      {/* ... existing UI ... */}
      {item.new_field && (
        <span className="text-terminal-dim">{item.new_field}</span>
      )}
    </div>
  );
}
```

## Files Reference

| File | Purpose |
|------|---------|
| `backend/app/models/world.py` | World definition models (source of truth) |
| `backend/app/engine/two_phase/models/perception.py` | Debug snapshot Pydantic models |
| `backend/app/engine/two_phase/visibility.py` | `build_debug_snapshot()` implementation |
| `backend/app/api/game.py` | `/state` endpoint returns debug snapshot |
| `frontend/src/api/client.ts` | TypeScript interfaces for debug models |
| `frontend/src/components/StateOverlay.tsx` | Debug UI component |
| `frontend/src/hooks/useGame.tsx` | State management for debug data |

## Visibility Reasons

The debug snapshot includes visibility reasons explaining why entities are visible or hidden:

### Items (`visibility_reason`)
- `"visible"` - Item is visible to player
- `"taken"` - Item is in player's inventory
- `"hidden"` - Item is hidden with no reveal condition
- `"condition_not_met:{flag}"` - Hidden, requires flag to be set

### NPCs (`visibility_reason`)
- `"visible"` - NPC is visible to player
- `"removed"` - NPC was removed via `location_changes` with `move_to: null`
- `"wrong_location:{loc}"` - NPC is at a different location
- `"condition_not_met:has_flag:{flag}"` - Requires flag to appear
- `"condition_not_met:trust_above:{value}"` - Requires trust level

### Exits (`access_reason`)
- `"accessible"` - Exit can be used
- `"requires_flag:{flag}"` - Destination requires flag
- `"requires_item:{item}"` - Destination requires item

## Testing

When adding new fields, verify:

1. **Backend**: The new field appears in `/api/game/state/{session_id}` response
2. **Frontend**: The field is accessible in the StateOverlay component
3. **Types**: TypeScript compilation succeeds with the new types
