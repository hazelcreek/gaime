# Items and Interaction Mechanics Specification

A specification for item use mechanics, interaction gating, and constraint enforcement in the two-phase game engine.

> **Status**: SKELETON — January 2026
> **Related**: [Two-Phase Game Loop](./two-phase-game-loop-spec.md) | [Visibility & Examination](./visibility-examination-spec.md)

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Motivating Examples](#motivating-examples)
3. [Item Use Mechanics](#item-use-mechanics)
4. [Interaction Gating](#interaction-gating)
5. [Constraint Enforcement](#constraint-enforcement)
6. [Schema Changes](#schema-changes)
7. [Implementation Phases](#implementation-phases)

---

## Problem Statement

### The Constraint Enforcement Gap

Currently, world authors can define **narrative constraints** in `world.yaml`:

```yaml
constraints:
  - "The player cannot take a photo of the Pigeon King while he is on the 'high_perch'; he is too far away."
```

However, these constraints have **no mechanical enforcement**. The LLM may understand the constraint narratively, but the game engine doesn't prevent the action. Players can:
- Take photos without luring the subject closer
- Use items in contexts where they shouldn't work
- Bypass prerequisite actions entirely

### The Result

The "bagel_placed" pattern from frosted-metropolis:

```yaml
# rooftop location
interactions:
  place_bagel:
    triggers: ["put everything_bagel on ledge", "place bagel"]
    sets_flag: bagel_placed                    # ← Flag is SET
    narrative_hint: "The Pigeon King swoops down to eat it!"

  take_photo:
    triggers: ["use vintage_camera on pigeon_king", "photograph pigeon"]
    sets_flag: has_pigeon_photo               # ← No requires_flag check!
    narrative_hint: "Click! You capture the Pigeon King."
```

**Bug**: The player can `take_photo` without first `place_bagel`. The `bagel_placed` flag is set but never checked.

---

## Motivating Examples

### Example 1: Prerequisite Actions (bagel_placed)

**Intent**: Player must lure the Pigeon King down before photographing him.

**Current (broken)**:
- `place_bagel` sets `bagel_placed`
- `take_photo` works regardless of `bagel_placed`

**Fixed (with gating)**:
```yaml
interactions:
  take_photo:
    triggers: ["use vintage_camera on pigeon_king", "photograph pigeon"]
    requires_flag: bagel_placed              # ← NEW: Gate the interaction
    rejection_message: "The Pigeon King is too far away on his perch."
    sets_flag: has_pigeon_photo
    narrative_hint: "Click! You capture the King at close range."
```

### Example 2: Item Use Mechanics (`use X on Y`)

**Intent**: Player uses ice_scraper on snowbank to reveal frozen_metrocard.

**Current (interaction-based)**:
```yaml
interactions:
  scrape_snow:
    triggers: ["use ice_scraper on snowbank", "scrape snow"]
    sets_flag: snowbank_scraped
    narrative_hint: "You chip away the ice, revealing a frozen card."
```

**Issue**: What if player doesn't have ice_scraper? The interaction triggers anyway if the words match.

**Needed**: Item-in-inventory check + automatic item consumption/durability.

### Example 3: Multi-Step Puzzle (MetroCard thawing)

**Intent**: Frozen card → microwave → thawed card → usable on turnstile.

**Required mechanics**:
1. `use frozen_metrocard on microwave` → transforms item OR reveals new item
2. Turnstile interaction requires `thawed_metrocard` in inventory
3. Frozen card should NOT work on turnstile (rejection message)

---

## Item Use Mechanics

> **TODO**: Design the `use X on Y` command system

### Core Concepts

1. **Item Requirements**: Interactions can require specific items in inventory
2. **Item Consumption**: Using an item may remove it from inventory
3. **Item Transformation**: Using an item may replace it with another
4. **Item Durability**: Some items have limited uses (future enhancement)

### Proposed Schema

```yaml
# In items.yaml
ice_scraper:
  name: "Rusty Ice Scraper"
  portable: true
  use_on:
    snowbank:
      sets_flag: snowbank_scraped
      narrative_hint: "You chip away at the ice."
    ice_block:
      sets_flag: ice_chipped
      consumes_item: false  # Scraper survives
```

```yaml
# Alternative: In locations.yaml
interactions:
  scrape_snow:
    triggers: ["use ice_scraper on snowbank"]
    requires_item: ice_scraper              # ← Must have item
    sets_flag: snowbank_scraped
    consumes_item: false                    # ← Item survives use
```

### Open Questions

- [ ] Should `use X on Y` be defined in items.yaml or locations.yaml?
- [ ] How to handle item transformation (frozen_metrocard → thawed_metrocard)?
- [ ] Should we support item combinations (use X with Y)?
- [ ] How to validate item requirements at generation time?

---

## Interaction Gating

> **TODO**: Implement `requires_flag` and `requires_item` for interactions

### Proposed Fields

```yaml
interactions:
  interaction_id:
    triggers: ["action phrase"]

    # Gating conditions (all must be met)
    requires_flag: flag_name                 # Player must have set this flag
    requires_item: item_id                   # Player must have this item
    requires_not_flag: flag_name             # Must NOT have this flag (one-time actions)

    # Rejection handling
    rejection_message: "Custom message when gating fails"

    # Effects
    sets_flag: flag_name
    gives_item: item_id
    removes_item: item_id
    narrative_hint: "What happens on success"
```

### Validator Integration

The WorldValidator should check:
- Every `requires_flag` has a corresponding `sets_flag` somewhere
- Every `requires_item` exists in items.yaml and is obtainable
- No circular requirements (flag A requires flag B requires flag A)

---

## Constraint Enforcement

> **TODO**: Connect world.yaml constraints to mechanical gates

### The Goal

When the world author writes:
```yaml
constraints:
  - "The player cannot photograph the Pigeon King while he is on the high perch"
```

The World Builder should automatically generate:
```yaml
interactions:
  take_photo:
    requires_flag: pigeon_king_accessible   # Generated from constraint
    rejection_message: "The Pigeon King is too far away on his perch."
```

### Approaches

1. **Prompt Engineering**: Instruct LLM to translate constraints to `requires_flag`
2. **AI Analysis Pass**: Post-generation check that constraints have mechanical enforcement
3. **Schema Enhancement**: Formalize constraints as structured data with built-in gating

### Recommendation

Start with approach #1 (prompt engineering) for immediate improvement, then implement approach #2 (AI analysis) for validation.

---

## Schema Changes

> **TODO**: Define exact Pydantic model changes

### InteractionEffect Updates

```python
class InteractionEffect(BaseModel):
    """Enhanced interaction with gating support"""
    triggers: list[str] = Field(default_factory=list)

    # Gating (NEW)
    requires_flag: str | None = None
    requires_item: str | None = None
    requires_not_flag: str | None = None
    rejection_message: str | None = None

    # Effects (existing)
    narrative_hint: str = ""
    sets_flag: str | None = None
    gives_item: str | None = None
    removes_item: str | None = None

    # Item handling (NEW)
    consumes_item: bool = False  # Remove requires_item after use
```

### Validator Updates

```python
def _validate_interaction_gating(self):
    """Validate that all interaction gates can be satisfied"""
    for loc_id, location in self.world_data.locations.items():
        for int_id, interaction in location.interactions.items():
            if interaction.requires_flag:
                if interaction.requires_flag not in self.flags_set:
                    self.result.add_error(
                        f"Interaction '{int_id}' at '{loc_id}' requires_flag "
                        f"'{interaction.requires_flag}' but no interaction sets this flag"
                    )
            if interaction.requires_item:
                if interaction.requires_item not in self.world_data.items:
                    self.result.add_error(
                        f"Interaction '{int_id}' requires_item "
                        f"'{interaction.requires_item}' but item doesn't exist"
                    )
```

---

## Implementation Phases

### Phase 1: Interaction Gating (Foundation)
- [ ] Add `requires_flag`, `requires_item`, `rejection_message` to InteractionEffect
- [ ] Update InteractionValidator to check gating conditions
- [ ] Update WorldValidator to verify gates can be satisfied
- [ ] Update prompts to generate gated interactions

### Phase 2: Item Use Commands
- [ ] Implement `use X on Y` command parsing in RuleBasedParser
- [ ] Add item requirement checking to interaction handling
- [ ] Support `consumes_item` and `removes_item` effects
- [ ] Update frontend to support item use UI

### Phase 3: Item Transformation
- [ ] Design item transformation schema
- [ ] Implement item replacement mechanics (frozen → thawed)
- [ ] Add transformation validation to WorldValidator

### Phase 4: Constraint Automation
- [ ] Update prompts to translate constraints to requires_flag
- [ ] Add AI analysis pass for constraint enforcement verification
- [ ] Consider structured constraint schema for formalization

---

*Last updated: January 2026*
