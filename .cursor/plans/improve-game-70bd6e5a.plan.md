<!-- 70bd6e5a-d3cc-4843-b6cb-04762878eb9e 60e5ddf4-8f77-470b-b8ca-4f9e0529104b -->
# Improve Game Realism, Consistency, and Playability

## Problem Analysis

Three fundamental issues identified:

1. **Location/context ambiguity** - Players don't know where they are; exits exist without narrative justification
2. **Hidden items** - `found_description` exists but isn't passed to the LLM
3. **No ending** - Games have no victory condition or completion state

---

## Implementation

### 1. Enhance Game Master Prompts

**File:** [`backend/app/llm/game_master.py`](backend/app/llm/game_master.py)

**Changes to `SYSTEM_PROMPT`:**

- Add rule: "When describing the scene, ALWAYS mention the current location name and physical context"
- Add rule: "When player looks around, describe ALL visible items using their found_description"
- Add rule: "Exits should be described narratively with context (e.g., 'a flickering barrier to the north' not just 'north')"
- Add rule: "If an exit seems implausible, explain why it's accessible in the narrative"

**Changes to `_build_system_prompt()`:**

- Include `found_description` for each item at the location (not just names)
- Add location's `details` dict to help the LLM describe the scene
- Include `starting_situation` if it exists in world data

**Changes to `SYSTEM_PROMPT`** (additional):

- Add rule: "When player enters a new location, describe visible items using their found_description"

**Changes to `OPENING_PROMPT`:**

- Reference `starting_situation` from world data to establish WHY the player can act now
- (Item description rules already covered by system prompt above)

### 2. Add Victory Conditions to World Schema

**File:** [`backend/app/models/world.py`](backend/app/models/world.py)

Add new models:

```python
class VictoryCondition(BaseModel):
    """Win condition for the game"""
    location: str | None = None  # Must be at this location
    flag: str | None = None      # Must have this flag set
    item: str | None = None      # Must have this item
    narrative: str = ""          # Ending narrative when won

class World(BaseModel):
    # ... existing fields ...
    starting_situation: str = ""  # Initial narrative context
    victory: VictoryCondition | None = None
```

**File:** [`backend/app/models/game.py`](backend/app/models/game.py)

Add game status:

```python
class GameState(BaseModel):
    # ... existing fields ...
    status: str = "playing"  # "playing", "won", "lost"
```

### 3. Implement Victory Check

**File:** [`backend/app/engine/state.py`](backend/app/engine/state.py)

Add method to `GameStateManager`:

```python
def check_victory(self) -> tuple[bool, str]:
    """Check if victory conditions are met, return (won, narrative)"""
```

**File:** [`backend/app/api/game.py`](backend/app/api/game.py)

After processing action, check victory and return ending if won.

### 4. Add World Builder Validation Rules

**File:** [`backend/app/llm/world_builder.py`](backend/app/llm/world_builder.py)

Enhance `WORLD_BUILDER_PROMPT` with:

- "Every exit must have narrative justification in the atmosphere or details"
- "Starting location must explain WHY the player can begin acting"
- "Add `starting_situation` field explaining the initial scenario"
- "Include a `victory` condition with location and/or flag requirements"
- "Every item MUST have a `found_description` that naturally integrates into room description"

Add validation in `validate_world()`:

- Check all items have `found_description`
- Check `victory` condition references valid location/flag/item
- Warn if starting location has exits without detail explanations

### 5. Update Echoes Scenario

**File:** [`worlds/echoes_of_subjugation/world.yaml`](worlds/echoes_of_subjugation/world.yaml)

Add:

```yaml
starting_situation: |
  The power grid stutters, and for a precious few seconds, the energy barrier
  to your cell flickers and dies. Old Marcus catches your eye and nods...

victory:
  location: old_sewers
  item: resistance_map
  narrative: |
    You emerge from the tunnels into a moonlit chamber. A figure steps from
    the shadows - the Resistance has found you. You're finally free...
```

**File:** [`worlds/echoes_of_subjugation/locations.yaml`](worlds/echoes_of_subjugation/locations.yaml)

Update `cell_block_c`:

- Add detail explaining barrier: `barrier: "The energy barrier to the north flickers weakly - the power fluctuation has left it vulnerable."`
- Update atmosphere to mention the cell door situation

### 6. Runtime Consistency Guardrails

**File:** [`backend/app/llm/game_master.py`](backend/app/llm/game_master.py)

Add to system prompt a "Consistency Rules" section:

- "If player attempts to move, verify the destination makes sense narratively"
- "Track what the player has been told exists - don't mention items not in the location"
- "Maintain physical reality constraints from the world's theme"

Add post-processing validation in `process_action()`:

- If LLM returns a location change, verify it's a valid exit
- If LLM mentions an item, verify it exists at location or in inventory

---

## Files to Modify

| File | Changes |

|------|---------|

| `backend/app/llm/game_master.py` | Enhanced prompts, item descriptions, validation |

| `backend/app/models/world.py` | Add `VictoryCondition`, `starting_situation` |

| `backend/app/models/game.py` | Add `status` field |

| `backend/app/engine/state.py` | Add `check_victory()` method |

| `backend/app/api/game.py` | Victory check after actions |

| `backend/app/llm/world_builder.py` | Enhanced prompts, validation |

| `worlds/echoes_of_subjugation/world.yaml` | Add victory, starting_situation |

| `worlds/echoes_of_subjugation/locations.yaml` | Fix cell_block_c narrative |

### To-dos

- [ ] Enhance game master system prompt with location/item/consistency rules
- [ ] Pass found_description for items to LLM context
- [ ] Add VictoryCondition model and starting_situation to world schema
- [ ] Add status field to GameState model
- [ ] Implement check_victory() in GameStateManager
- [ ] Add victory check after action processing in API
- [ ] Enhance world builder prompt and validation
- [ ] Update echoes scenario with victory conditions and fixed narratives
