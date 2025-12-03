<!-- ed79dd34-a7d4-4e7c-b9b2-76473a187f95 48684781-d6ab-4d03-a5c8-ec40256d09fd -->
# Dynamic NPC Visualization System

## Problem Summary

Static location images show conditional NPCs (like ghost_child) regardless of whether they've actually appeared in the game narrative. This creates a mismatch between what the player sees visually and what the game describes.

## Solution Overview

### 1. Image Variant System

Generate multiple image variants for locations where conditional NPCs can appear, then serve the correct variant based on current game state.

### 2. NPC Location Triggers  

Add support for NPCs to change their location when specific flags are set.

---

## Implementation Details

### A. Variant Image Generation ([image_generator.py](backend/app/llm/image_generator.py))

**Naming Convention:**

- Base image: `{location_id}.png` (no conditional NPCs)
- Variant: `{location_id}__with__{npc_id}.png` (one NPC visible)
- Multi-NPC variant: `{location_id}__with__{npc1}_{npc2}.png` (sorted alphabetically)

**Changes to `_build_location_context()`:**

- Accept optional `include_npcs` filter (list of NPC IDs to include)
- Only add NPCs from that list to the image context

**New function `generate_location_variants()`:**

- Identify all NPCs with `appears_when` conditions for a location
- Calculate required variants (exponential but typically small: 2^n for n conditional NPCs)
- Generate base image + all variants
- Return manifest of generated images

**Manifest structure (stored as `{location_id}_variants.json`):**

```json
{
  "location_id": "upper_landing",
  "base": "upper_landing.png",
  "variants": [
    {"npcs": ["ghost_child"], "image": "upper_landing__with__ghost_child.png"}
  ]
}
```

### B. NPC Location Triggers ([npcs.yaml](worlds/cursed-manor/npcs.yaml) schema)

Add new optional field `location_changes` to NPC definition:

```yaml
butler_jenkins:
  location: dining_room
  location_changes:
    - when_flag: player_explored_upstairs
      move_to: entrance_hall
```

### C. Runtime NPC Location Tracking ([state.py](backend/app/engine/state.py))

**Add to GameState:**

- `npc_locations: dict[str, str]` - current location of each NPC

**Add method `get_npc_current_location(npc_id)`:**

- Check if any `location_changes` trigger is active
- Return the triggered location or default location

**Modify `get_present_npcs()`:**

- Use dynamic location lookup instead of static NPC.locations

### D. Image Selection at Runtime ([game.py](backend/app/api/game.py))

**Modify image serving:**

- Determine which conditional NPCs are currently visible at location
- Look up correct variant from manifest
- Return that image path

### E. World Schema Updates ([world.py](backend/app/models/world.py))

Add new model:

```python
class NPCLocationChange(BaseModel):
    when_flag: str  # Flag that triggers this move
    move_to: str    # New location ID
```

Add to NPC model:

```python
location_changes: list[NPCLocationChange] = Field(default_factory=list)
```

---

## Files to Modify

| File | Changes |

|------|---------|

| `backend/app/llm/image_generator.py` | Add variant generation logic, manifest output |

| `backend/app/models/world.py` | Add `NPCLocationChange` model, extend `NPC` |

| `backend/app/engine/state.py` | Add `npc_locations` tracking, dynamic location lookup |

| `backend/app/models/game.py` | Add `npc_locations` to `GameState` |

| `backend/app/api/game.py` | Add variant-aware image serving |

| `docs/WORLD_AUTHORING.md` | Document new NPC fields |

| `docs/ARCHITECTURE.md` | Document variant system |

---

## Migration for Existing Worlds

For `cursed-manor`:

1. Regenerate images with variant system
2. Update `ghost_child` and `lady_margaret` in npcs.yaml if movement is desired
3. Existing images become the base variants

## Scope Notes

- Start with single-NPC variants (simpler, covers most cases)
- Multi-NPC combinations can be added later if needed
- Image generation is done at authoring time, not runtime (keeps costs predictable)

### To-dos

- [ ] Add NPCLocationChange model and location_changes field to NPC in world.py
- [ ] Add npc_locations dict to GameState model in game.py
- [ ] Implement dynamic NPC location lookup in state.py with location_changes support
- [ ] Add variant generation to image_generator.py with manifest output
- [ ] Implement variant-aware image serving in game.py API
- [ ] Update WORLD_AUTHORING.md and ARCHITECTURE.md with new NPC features