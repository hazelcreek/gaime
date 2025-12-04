<!-- 644337e2-66b7-44da-b66d-6a5e173043bc 06e06188-f836-4dbe-9cae-953e2fe9c429 -->
# Fix NPC Knowledge, Flag Namespacing, and World Validation

## Problems Found

1. Lady Margaret says dagger is in the library (wrong) - actual location is basement
2. LLM creates arbitrary flags like `knows_dagger_location` without namespace separation
3. No validation of world definitions - bugs like mismatched flag names go undetected
4. **Existing bug**: `thornwood_amulet` requires `examined_drawings` flag, but nursery sets `understood_sacrifice`

## Solution

### 1. Make NPC Knowledge Explicit

Update [`worlds/cursed-manor/npcs.yaml`](worlds/cursed-manor/npcs.yaml) - Lady Margaret's knowledge:

```yaml
# Before
- "Knows where she hid the dagger to prevent the ritual's completion"

# After  
- "She hid the ritual dagger in the basement, among debris in the corner"
```

### 2. Add LLM Prompt Constraints

Update [`backend/app/llm/game_master.py`](backend/app/llm/game_master.py) - add explicit anti-hallucination rules:

```
## Factual Accuracy (CRITICAL)
- NEVER invent locations for items - only mention locations from the world data
- NEVER make up where items are hidden - use only the knowledge provided
- If you don't know where something is, say so - don't guess
```

### 3. Separate LLM-Generated Flags

Add `llm_flags` field to GameState in [`backend/app/models/game.py`](backend/app/models/game.py):

```python
llm_flags: dict[str, bool] = {}  # AI-generated contextual flags
```

Update game_master.py prompt to use `llm_flags` for LLM-generated state.

### 4. World Validator

Create [`backend/app/engine/validator.py`](backend/app/engine/validator.py) - validates:

| Check | Description |

|-------|-------------|

| Flag consistency | Flags checked (`requires_flag`, `appears_when`, `find_condition`) are set somewhere |

| Location refs | All exits, item locations, NPC locations reference valid location IDs |

| Item refs | `requires_item`, `unlocks` reference valid item IDs |

| Orphan detection | Flags set but never checked (warnings, not errors) |

**Validator invocation:**

- CLI: `python -m app.engine.validator <world_id>`
- Startup: `WorldLoader.load_world()` runs validation, raises on errors

### 5. Fix Existing Bug

Update [`worlds/cursed-manor/locations.yaml`](worlds/cursed-manor/locations.yaml) nursery interaction:

```yaml
# Change sets_flag from understood_sacrifice to examined_drawings
# (or update items.yaml to use understood_sacrifice)
```

## Files to Modify

- `worlds/cursed-manor/npcs.yaml` - explicit dagger location
- `worlds/cursed-manor/locations.yaml` - fix flag mismatch
- `backend/app/models/game.py` - add llm_flags field
- `backend/app/llm/game_master.py` - add constraints, use llm_flags
- `backend/app/engine/state.py` - add llm_flag handling
- `backend/app/engine/validator.py` - NEW: world validator
- `backend/app/engine/world.py` - integrate validator on load
- `backend/app/api/game.py` - update debug output
- `docs/ARCHITECTURE.md` - document flag separation
- `docs/WORLD_AUTHORING.md` - document validator and flag conventions

### To-dos

- [ ] Update Lady Margaret's knowledge in npcs.yaml with explicit dagger location
- [ ] Add llm_flags field to GameState model
- [ ] Update LLM system prompt and parsing to use llm_flags
- [ ] Add llm_flag handling to GameStateManager
- [ ] Update debug output to show both flag types separately
- [ ] Document the flag separation in ARCHITECTURE.md