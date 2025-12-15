---
name: World Builder Schema Fix
overview: Fix world builder schema drift by making Pydantic models the source of truth, implementing auto-fix validation with logging, and migrating existing worlds to the correct schema.
todos:
  - id: migrate-worlds
    content: Create migration script and fix 5 existing worlds with hallucinated fields
    status: pending
  - id: schema-generator
    content: Create Pydantic schema extractor for theme-neutral prompt examples
    status: pending
  - id: update-prompts
    content: Update world builder prompts with correct schema and generic examples
    status: pending
  - id: world-fixer
    content: Create auto-fix module for common validation errors
    status: pending
  - id: integrate-validation
    content: Wire validation loop into world generator with extensive logging
    status: pending
  - id: update-cursorrules
    content: Add schema maintenance reminders to .cursorrules
    status: pending
---

# World Builder Schema Compliance & Validation

## Problem Summary

The world builder prompts contain incorrect schema examples (e.g., `dialogue_hints`, `personality: "string"`), causing generated worlds to have invalid fields. The TUI validation is superficial compared to runtime validation, and 6 existing worlds need migration.

---

## Part 1: Schema from Pydantic Models

### Approach

Create a schema extractor that generates **theme-neutral** YAML examples from Pydantic models. This becomes the source of truth for world builder prompts.

### Key Files

- **Source**: [`backend/app/models/world.py`](backend/app/models/world.py) - Pydantic models
- **Target**: [`gaime_builder/core/prompts/world_builder/world_builder_prompt.txt`](gaime_builder/core/prompts/world_builder/world_builder_prompt.txt)
- **New**: `gaime_builder/core/schema_generator.py` - extracts schema from models

### Implementation

1. Create `schema_generator.py` that introspects Pydantic models and generates:

                                                                                                                                                                                                                                                                                                                                                                                                - Field names with types
                                                                                                                                                                                                                                                                                                                                                                                                - Required vs optional markers
                                                                                                                                                                                                                                                                                                                                                                                                - **Theme-neutral placeholder examples** (no haunted manor references)

2. Update `world_builder_prompt.txt` to use generic examples:
```yaml
# Instead of "Jenkins the butler"
npc_id:
  name: "NPC Display Name"
  role: "Their role in the story"
  personality:
    traits: ["trait_one", "trait_two"]
    speech_style: "How they speak"
    quirks: ["Behavioral quirk 1"]
  knowledge:
  - "Fact they know"
  dialogue_rules:
  - "Rule for how they communicate"
```

3. Add validation at startup/test time that compares prompt schema examples against actual Pydantic model fields

### Cursorrule Addition

Add to `.cursorrules` under "Documentation Maintenance":

```
| World schema model changes | `gaime_builder/core/prompts/world_builder/*.txt` |
```

---

## Part 2: Auto-Fix Validation Loop

### Approach

After YAML generation, run the full `WorldValidator` and attempt automatic fixes. Log extensively for troubleshooting while keeping the user experience spoiler-free.

### Key Files

- **Validator**: [`backend/app/engine/validator.py`](backend/app/engine/validator.py) - comprehensive validation
- **Generator**: [`gaime_builder/core/world_generator.py`](gaime_builder/core/world_generator.py) - needs validation integration
- **New**: `gaime_builder/core/world_fixer.py` - auto-fix logic

### Validation Flow (up to 3 attempts)

```
┌─────────────────────────────────────────────────────────────────┐
│                     World Generation Flow                        │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────┐
│ Pass 1: Brief │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ Pass 2: YAML  │
└───────┬───────┘
        │
        ▼
┌───────────────────┐    ┌─────────────────┐
│ Parse YAML into   │───►│ WorldValidator  │
│ Pydantic models   │    │ (full runtime)  │
└───────────────────┘    └────────┬────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
            ┌──────────────┐           ┌──────────────┐
            │   Valid ✓    │           │   Errors     │
            └──────────────┘           └──────┬───────┘
                                              │
                                              ▼
                                      ┌──────────────┐
                                      │  Auto-Fix    │◄───┐
                                      │  Attempt     │    │ (up to 3x)
                                      └──────┬───────┘    │
                                              │           │
                                      ┌───────┴───────┐   │
                                      │               │   │
                                      ▼               ▼   │
                               ┌──────────┐   ┌──────────┴┐
                               │  Fixed   │   │  Retry    │
                               └──────────┘   └───────────┘
```

### Auto-Fixable Errors

| Error Type | Auto-Fix Strategy |

|------------|-------------------|

| Flag checked but never set | Add interaction that sets the flag |

| Invalid location reference | Find closest match or remove reference |

| Invalid item reference | Find closest match or remove reference |

| Victory location invalid | Use player starting location |

| Missing required fields | Add sensible defaults |

### Logging Strategy

- **INFO**: Validation started, attempt number, final result
- **DEBUG**: Each validation check, each fix attempted
- **WARNING**: Errors that couldn't be auto-fixed
- **ERROR**: Complete failure after 3 attempts

All logs go to file, not shown to user (spoiler-free experience).

---

## Part 3: Migrate Existing Worlds

### Worlds to Migrate

| World | Issues |

|-------|--------|

| `islay-mist-mystery` | `dialogue_hints`, `personality` as string, `constraints` in location |

| `whistlewood_fable` | `dialogue_hints`, `personality` as string |

| `hazel_city_1885` | `dialogue_hints`, `personality` as string |

| `detention_survival_high` | `dialogue_hints`, `personality` as string |

| `echoes_of_subjugation` | `dialogue_hints`, `personality` as string |

| `cursed-manor` | Already correct (reference) |

| `uss-enterprise-d` | Already correct (reference) |

### Migration Script: `scripts/migrate_worlds.py`

**NPC Migration Logic:**

```python
# Old format:
personality: "Gruff, suspicious, superstitious."
dialogue_hints:
  greeting: "'Ay? Who are you?'"

# New format:
personality:
  traits: ["gruff", "suspicious", "superstitious"]
  speech_style: "Speaks with Scottish dialect, guarded"
  quirks: ["Says 'Ay?' when addressed"]
dialogue_rules:
 - "Greets strangers with suspicion"
```

**Location Migration Logic:**

```python
# Old format (islay-mist tasting_room):
constraints:
 - "locked_exit: north requires code_revealed flag"

# New format:
requires:
  flag: code_revealed
```

### Script Features

- Dry-run mode (show changes without applying)
- Backup original files before modifying
- Detailed logging of all transformations
- Validation after migration

---

## Part 4: Updated Cursorrules

Add to `.cursorrules` "Documentation Maintenance" table:

```markdown
| World schema model changes (`models/world.py`) | `gaime_builder/core/prompts/world_builder/*.txt`, run schema validation |
| New NPC/Item/Location fields | Update prompt examples + `WORLD_AUTHORING.md` |
```

---

## Implementation Order

1. **Migration script** - Fix existing worlds first (unblocks testing)
2. **Schema generator** - Create Pydantic → schema extractor
3. **Update prompts** - Replace themed examples with generic ones
4. **World fixer** - Auto-fix logic for common validation errors
5. **Integration** - Wire fixer into world generator with logging
6. **Cursorrules** - Add maintenance reminders

---

## Files Changed

| File | Change Type |

|------|-------------|

| `scripts/migrate_worlds.py` | New |

| `gaime_builder/core/schema_generator.py` | New |

| `gaime_builder/core/world_fixer.py` | New |

| `gaime_builder/core/world_generator.py` | Modified (add validation loop) |

| `gaime_builder/core/prompts/world_builder/world_builder_prompt.txt` | Modified (generic examples) |

| `gaime_builder/core/prompts/world_builder/design_brief_prompt.txt` | Modified (if needed) |

| `.cursorrules` | Modified (add maintenance reminders) |

| `worlds/islay-mist-mystery/*.yaml` | Modified (migration) |

| `worlds/whistlewood_fable/*.yaml` | Modified (migration) |

| `worlds/hazel_city_1885/*.yaml` | Modified (migration) |

| `worlds/detention_survival_high/*.yaml` | Modified (migration) |

| `worlds/echoes_of_subjugation/*.yaml` | Modified (migration) |