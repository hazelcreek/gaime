# World Authoring Guide

This guide explains how to create game worlds for GAIME using YAML files.

## Overview

A GAIME world consists of four YAML files:

| File | Purpose |
|------|---------|
| `world.yaml` | Theme, premise, player setup, constraints |
| `locations.yaml` | Rooms, exits, atmosphere hints |
| `npcs.yaml` | Characters, personalities, dialogue rules |
| `items.yaml` | Objects, uses, puzzle connections |

## Directory Structure

```
worlds/
└── your-world-name/
    ├── world.yaml
    ├── locations.yaml
    ├── npcs.yaml
    └── items.yaml
```

## Schema Reference

### world.yaml

Defines the overall game world and player starting conditions.

```yaml
# World metadata
name: "The Cursed Manor"
theme: "Victorian gothic horror"
tone: "atmospheric, mysterious, unsettling"
hero_name: "Eleanor Ashford"  # Protagonist name that NPCs will use in dialogue

# Visual language for image generation (5-10 sentences)
visual_setting: |
  The Cursed Manor is a decaying Victorian estate, steeped in gothic horror. Expect dark,
  ornate interiors with heavy, dust-laden furniture, peeling wallpaper, and flickering,
  unreliable light sources. Materials are dark wood, tarnished brass, faded velvet, and
  cold stone. The color palette is muted and somber, dominated by deep greys, faded blues,
  and dark browns, with occasional unsettling flashes of red or sickly green. Architecture
  is grand but crumbling, with high ceilings, long corridors, and hidden passages.
  Apparitions are subtle, often seen in reflections or at the periphery of vision,
  appearing as translucent, sorrowful figures in period attire.

# Opening premise shown to player
premise: |
  A violent storm has driven you to seek shelter in an old manor.
  The elderly butler who answered the door seems... troubled.
  Something is wrong in this house.

# IMPORTANT: Explain WHY the player can act NOW
starting_situation: |
  The heavy front door has just slammed shut behind you. Lightning flashes
  through the grimy windows. The storm rages outside - there's no leaving
  tonight. The butler, Jenkins, has retreated into the shadows. You have
  until dawn to uncover the manor's secrets.

# Victory condition - defines how to win/end the game
victory:
  location: ritual_chamber    # Must be at this location
  flag: has_all_artifacts     # Must have this flag set
  # item: some_item           # Optional: must have this item
  narrative: |
    With trembling hands, you place the final artifact upon its pedestal.
    The symbols on the floor blaze with ethereal light. The curse is broken.

    CONGRATULATIONS - You have completed the adventure!

# Player starting state
player:
  starting_location: entrance_hall
  starting_inventory:
    - pocket_watch
    - journal

# Global rules the AI must follow
constraints:
  - "The basement is locked until the player finds the iron key"
  - "Jenkins will only reveal the family secret after 3 trust-building interactions"
  - "The ghost only appears after examining the nursery"
  - "The curse cannot be broken without all three artifacts"

# Optional: special commands
commands:
  help: "Show available actions"
  inventory: "List carried items"
  look: "Describe current location"
```

**Key Fields:**

| Field | Required | Purpose |
|-------|----------|---------|
| `hero_name` | Recommended | Protagonist name that NPCs use in dialogue (default: "the hero") |
| `visual_setting` | Recommended | World-level visual language for image generation (5-10 sentences) |
| `starting_situation` | Recommended | Explains WHY the player can act now (prevents confusion) |
| `victory` | Recommended | Defines win condition and ending narrative |
| `victory.location` | Optional | Player must be at this location to win |
| `victory.flag` | Optional | This flag must be set to win |
| `victory.item` | Optional | Player must have this item to win |
| `victory.narrative` | Optional | Ending text shown when player wins |

### locations.yaml

Defines the game map and interactive elements.

```yaml
entrance_hall:
  name: "Entrance Hall"

  # Hints for AI narrative generation (ambience, sounds, smells)
  atmosphere: |
    Grand but decayed. A crystal chandelier hangs dark and dusty.
    Faded portraits line the walls. The air smells of old wood and secrets.

  # Pure visual scene description for image generation (3-5 sentences)
  # Focus on environmental elements, props, and background extras NOT listed as items/NPCs
  visual_description: |
    A vast, echoing hall with a checkered marble floor, cracked and worn. Towering,
    dark wood panels line the walls, adorned with faded, unsettling portraits whose
    eyes seem to follow you. A massive, dust-shrouded crystal chandelier hangs
    precariously from the high ceiling, casting long, dancing shadows as lightning
    flashes outside the grimy, leaded windows.

  # Connected locations
  exits:
    north: library
    east: dining_room
    up: upper_landing

  # Items found here (reference items.yaml)
  items:
    - old_letter
    - candlestick

  # WHERE items are placed in this specific location (improves images and narration)
  item_placements:
    old_letter: "lies crumpled on the dusty side table near the door"
    candlestick: "sits on the fireplace mantel, cold and unlit"

  # NPCs present (reference npcs.yaml)
  npcs:
    - butler_jenkins

  # WHERE NPCs are positioned in this location
  npc_placements:
    butler_jenkins: "stands rigidly by the grandfather clock, pale hands clasped"

  # Interactive elements (things player can examine)
  details:
    portraits: "Five family portraits: parents and three children"
    chandelier: "Once magnificent, now dark and cobwebbed"
    floor: "Marble tiles, cracked and dusty"
    # IMPORTANT: Add details for exits to provide narrative context
    north: "An archway leads north to the library, its darkness beckoning"
    east: "Double doors to the east open into what appears to be a dining room"
    up: "A grand staircase climbs upward into shadow"

  # Special interactions
  interactions:
    examine_portraits:
      triggers: ["examine portraits", "look at portraits", "study paintings"]
      narrative_hint: "One portrait has been slashed across the face"
      sets_flag: examined_portraits

library:
  name: "The Library"
  atmosphere: |
    Floor-to-ceiling bookshelves stuffed with ancient tomes.
    A cold draft suggests hidden passages. Dust motes drift in pale moonlight.

  exits:
    south: entrance_hall
    hidden: secret_passage  # Only available when discovered

  items:
    - dusty_tome
    - reading_glasses

  # Conditional access
  requires: null  # No requirements

  interactions:
    pull_red_book:
      triggers: ["pull red book", "examine red book", "tug red book"]
      narrative_hint: "A mechanical click, the bookshelf swings open"
      reveals_exit: secret_passage
      sets_flag: found_secret_passage

secret_passage:
  name: "Secret Passage"
  atmosphere: |
    A narrow corridor behind the bookshelf. Cobwebs thick as curtains.
    The walls are stone, older than the manor itself.

  exits:
    back: library
    down: ritual_chamber

  requires:
    flag: found_secret_passage
```

### npcs.yaml

Defines characters and their behavior.

```yaml
butler_jenkins:
  name: "Jenkins"
  role: "The elderly butler, last remaining servant"

  # Where they can be found
  location: entrance_hall  # Can move based on story

  # Physical description for AI
  appearance: |
    Gaunt and pale, impeccably dressed in dated formal wear.
    His hands tremble slightly. Dark circles under watchful eyes.

  # Personality for dialogue generation
  personality:
    traits:
      - formal
      - secretive
      - guilt-ridden
      - protective
    speech_style: "Victorian formal English, speaks in hints, deflects direct questions"
    quirks:
      - "Glances nervously at the basement door"
      - "Changes subject when family is mentioned"

  # What they know (for AI context)
  knowledge:
    - "Knows the truth about the curse and the family tragedy"
    - "Was present the night of the ritual"
    - "Believes he failed to protect the children"
    - "Knows where artifacts are hidden"

  # Dialogue constraints
  dialogue_rules:
    - "Never directly answers questions about the curse"
    - "Speaks cryptically about 'that terrible night'"
    - "Shows warmth if player mentions helping the spirits"

  # Trust/relationship mechanics
  trust:
    initial: 0
    threshold: 3  # Interactions to unlock secrets
    build_actions:
      - "Show kindness or sympathy"
      - "Find evidence of his innocence"
      - "Speak of helping the children"

ghost_child:
  name: "The Whisper"
  role: "Spirit of the youngest child"

  # Appears in multiple locations
  locations:
    - nursery
    - upper_landing
    - library

  appearance: |
    A translucent figure of a young girl, perhaps eight years old.
    Her form flickers like candlelight. She points but cannot speak.

  personality:
    traits:
      - innocent
      - helpful
      - sad
    speech_style: "Does not speak - communicates through gestures and leading"

  # Appearance conditions
  appears_when:
    - condition: "has_flag"
      value: "examined_nursery"

  behavior: |
    Points toward clues, leads to hidden areas.
    Disappears when approached too quickly.
    Shows fear near the ritual chamber.

# Example NPC that moves based on story progress
mansion_guard:
  name: "The Guard"
  role: "Security patrol"

  # Default location
  location: front_gate

  # Location changes based on flags (checked in order, last match wins)
  location_changes:
    - when_flag: alarm_triggered
      move_to: main_hallway
    - when_flag: player_discovered
      move_to: player_last_location
```

### items.yaml

Defines interactive objects.

```yaml
old_letter:
  name: "Crumpled Letter"

  # Can player carry it?
  portable: true

  # Description when examined
  examine: |
    A yellowed letter, hastily crumpled then smoothed out again.
    The elegant handwriting reads:

    "My dearest Margaret,

    The ritual must never be completed. I have hidden the final
    component where the children played their secret games.

    Forgive me.
    - Edmund"

  # CRITICAL: How the item appears in the room scene
  # This is used when player "looks around" - without it, items are invisible!
  found_description: "A crumpled letter lies on the side table"

  take_description: "You pocket the fragile letter carefully"

  # Puzzle connections
  clues:
    - hint_for: nursery_puzzle
    - reveals: "Final artifact is in the nursery"

iron_key:
  name: "Heavy Iron Key"
  portable: true

  examine: |
    An old iron key, heavy and cold. The head is shaped like a
    serpent eating its tail. It feels significant.

  # What it does
  unlocks: basement_door

  # Where to find it
  location: library
  hidden: true
  find_condition:
    requires_flag: solved_library_puzzle

ancient_amulet:
  name: "The Thornwood Amulet"
  portable: true

  examine: |
    A silver amulet on a tarnished chain. The pendant shows a
    thorn-wrapped tree. It hums faintly when held.

  # Special properties
  properties:
    artifact: true  # One of three needed to break curse

  # Interactions
  use_actions:
    wear:
      description: "You clasp the amulet around your neck. A calming warmth spreads through you."
      sets_flag: wearing_amulet

candlestick:
  name: "Silver Candlestick"
  portable: true

  examine: "A heavy silver candlestick, unlit. Could serve as a light source... or a weapon."

  use_actions:
    light:
      requires_item: matches
      description: "The flame flickers to life, casting dancing shadows."
      sets_flag: has_light
```

## Best Practices

### Writing Starting Situations

The `starting_situation` explains why the player can begin acting. This prevents confusion about context:

```yaml
# Good - explains the enabling event
starting_situation: |
  The power grid has failed. For a few precious seconds, the energy
  barrier sealing your cell flickers and dies. This is your chance.

# Bad - doesn't explain why player can act
starting_situation: "You are in a prison cell."
```

### Writing Atmosphere Hints

The `atmosphere` field guides AI narrative generation and provides ambience (sounds, smells, mood). Good atmosphere:

```yaml
# Good - evocative, sensory, suggestive
atmosphere: |
  The library smells of aged paper and forgotten knowledge.
  Moonlight filters through grimy windows, illuminating
  dust motes that drift like snow. The silence feels heavy.

# Bad - too literal, no mood
atmosphere: "A room with books"
```

### Visual Setting (world.yaml)

The `visual_setting` field defines the overall visual language for image generation. This describes how the world *looks* consistently across all locations:

```yaml
# Good - describes materials, colors, architecture, character appearance (5-10 sentences)
visual_setting: |
  The world of Booty Bay is a vibrant, slightly exaggerated pirate haven. Expect
  ramshackle wooden structures, colorful flags and banners, and a general sense
  of playful chaos. Materials are weathered wood, rusty iron, and sun-faded canvas.
  Colors are bright and tropical, with deep blues of the ocean, sandy yellows,
  and splashes of red and green from pirate attire and exotic birds. Architecture
  is makeshift and organic, with buildings leaning precariously and connected by
  rope bridges. Characters are caricatured pirates, with oversized hats, eye patches,
  and a general air of roguish charm.

# Bad - too short or focuses on rendering style (that's what style presets are for)
visual_setting: "A pirate town"
visual_setting: "Pixel art style with bright colors"  # Don't describe rendering style!
```

### Visual Description (locations.yaml)

The `visual_description` field provides pure visual details for each location's image. Focus on:
- **Overall scene appearance** (architecture, lighting, layout)
- **Props and background elements** NOT listed as items, NPCs, or details
- **Background extras** (crowds, animals, ambient activity)

Do NOT repeat items, NPCs, details, or exits - those are added separately to the image prompt.

```yaml
# Good - 3-5 sentences of visual elements not covered by interactive elements
visual_description: |
  A rickety wooden pier extends into murky green harbor water, lined with
  barnacle-encrusted pilings. Crates and barrels are stacked haphazardly
  along the dock, some overflowing with fishing nets and old ropes. Distant,
  colorful pirate ships are visible in the bay, their tattered sails flapping
  gently. Seagulls wheel overhead against a bright blue sky.

# Bad - repeats items/NPCs or describes sounds/smells (that's atmosphere)
visual_description: "There is a brass key on the ground."  # That's an item!
visual_description: "The smell of fish fills the air."      # That's atmosphere!
```

### Visual Continuity at Connection Points

Since each location image is generated independently, **shared architectural elements** (doorways, passages, stairs) can look completely different from each side, breaking immersion. Use **entry point mirroring** to maintain visual consistency.

#### The Problem

When a "curtained doorway" connects the tavern to its backroom, the curtain might appear as red velvet from one side and tattered burlap from the other. Similarly, an "underground passage" exit might look like rough stone steps, but the destination looks like an outdoor scene.

#### The Solution: Entry Point Mirroring

In each location's `visual_description`, explicitly describe what the **entry points look like from inside**. Use the same specific details (color, material, condition) in both connected locations.

```yaml
# tavern_entrance - describe what the backroom entrance looks like FROM HERE
visual_description: |
  ...
  To the north, a heavy burgundy velvet curtain with tarnished brass rings
  conceals the private backroom.

# tavern_backroom - describe the SAME curtain as seen FROM INSIDE
visual_description: |
  An intimate private room accessed through a heavy burgundy velvet curtain
  with tarnished brass rings, which hangs in the doorway to the south...
```

#### Entry Point Mirroring Checklist

When writing `visual_description` for each location, include:

1. **Doorways/Passages to adjacent locations** - Describe what each exit looks like from inside this room
2. **Specific architectural details** - Same materials, colors, and distinctive features on both sides
3. **Interior/Exterior consistency** - If exiting into a building, destination must clearly be interior
4. **Lighting transitions** - Mention light coming from connected areas (e.g., "sunlight streaming through the door from the square")

```yaml
# Good - specific, mirrored details
exits:
  west:
    scene_description: Weather-beaten green swinging saloon doors of The Rusty Cutlass
# In visual_description:
visual_description: |
  ...To the west, weather-beaten green swinging saloon doors let in slashes of
  bright Caribbean sunlight from the Town Square...

# In the connected location (tavern_entrance):
visual_description: |
  ...To the east, weather-beaten green swinging saloon doors let in bright
  sunlight from the Town Square...

# Bad - generic, inconsistent
exits:
  west:
    scene_description: The tavern door
# visual_description doesn't mention the door at all
```

#### Common Continuity Pitfalls

| Issue | Example | Fix |
|-------|---------|-----|
| Mismatched doorways | Red curtain from one side, blue from the other | Use identical descriptors: "burgundy velvet curtain with brass rings" |
| Indoor/outdoor mismatch | Exit leads "into a building" but destination looks like outdoors | Rewrite destination to clearly show interior walls, ceiling, door |
| Missing entry points | Underground cave has no visible tunnel exit | Add "At one end, a winding tunnel emerges from the darkness" |
| Generic exit descriptions | "A door leads north" | Specify: "An iron-banded oak door with a rusty padlock" |
| Lighting inconsistency | Dark room connects to sunny plaza with no light spillover | Add "bright sunlight streams through the doorway from the square" |

### Item Found Descriptions

**Every item MUST have a `found_description`** - this is how items become discoverable when the player looks around:

```yaml
# Good - naturally integrates into scene
found_description: "A crumpled letter lies forgotten on the side table"

# Bad - too generic or missing
found_description: "There is a letter here"
found_description: ""  # Item will be invisible!
```

### Exit Details

Add details for each exit direction to help the AI describe them narratively:

```yaml
details:
  # Scene elements
  portraits: "Five family portraits line the walls"

  # Exit descriptions (match your exits keys)
  north: "An archway leads north into darkness"
  east: "Heavy oak doors stand closed to the east"
  up: "A grand staircase climbs into shadow"
```

### Item and NPC Placements

**Every item and NPC should have a placement** describing WHERE in the room they are located. This improves both image generation and game master narratives:

```yaml
# Good - specific placement in room
item_placements:
  old_letter: "lies crumpled on the dusty side table near the door"
  candlestick: "sits on the fireplace mantel, cold and unlit"

npc_placements:
  butler_jenkins: "stands rigidly by the grandfather clock, pale hands clasped"

# Bad - missing placements (items/NPCs won't be positioned realistically)
items:
  - old_letter
  - candlestick
# No item_placements defined!
```

Placements should describe:
- **Physical location**: "on the desk", "beneath the window", "by the fireplace"
- **State/posture** (for NPCs): "standing", "crouching", "seated"
- **Atmospheric details**: "half-hidden in shadow", "catching the moonlight"

### Defining Constraints

Constraints prevent the AI from breaking game logic:

```yaml
# Good - specific, actionable
constraints:
  - "The basement door cannot be opened without the iron key"
  - "Jenkins will not discuss the ritual until trust reaches 3"

# Bad - vague, unenforceable
constraints:
  - "Keep the story interesting"
  - "Don't reveal too much"
```

### NPC Knowledge

Be explicit about what NPCs know and will share. **Include specific locations and facts** to prevent the AI from hallucinating incorrect information:

```yaml
# Good - explicit facts with actual locations
knowledge:
  - "Knows the curse requires three artifacts to break"
  - "The dagger is hidden in the basement, among debris in the corner"
  - "The amulet is beneath a floorboard in the nursery"
  - "The grimoire is in the ritual chamber on the central pedestal"
  - "Will NOT reveal artifact locations until trust is maxed"

dialogue_rules:
  - "Speaks of 'dark days' but never names the curse directly"
  - "If asked about children, becomes visibly upset and changes subject"

# Bad - vague knowledge leads to AI hallucination
knowledge:
  - "Knows where the dagger is hidden"  # AI might invent a wrong location!
  - "Knows artifact locations"           # Too vague - be specific
```

**Critical**: If an NPC "knows" where an item is, include the **actual location** in their knowledge. The AI cannot look up item locations - it will make something up if you don't tell it explicitly.

### Puzzle Design

Connect items, locations, and NPCs:

```yaml
# Item references location
iron_key:
  unlocks: basement_door
  location: library
  find_condition:
    requires_flag: solved_library_puzzle

# Location references item
basement:
  requires:
    item: iron_key

# NPC provides hint
butler_jenkins:
  knowledge:
    - "Hints that 'the master kept important things among his books'"
```

## World Builder Tools

GAIME provides two ways to create worlds with AI assistance:

### TUI (Terminal User Interface) - Recommended

The **GAIME World Builder TUI** is a polished terminal application for creating and managing worlds:

```bash
# From project root, with virtual environment activated
cd /path/to/gaime
source backend/venv/bin/activate
pip install -e .  # First time only
gaime-builder
```

**Features:**
- **Create World**: Enter a description and generate a complete world with locations, NPCs, and items
- **Generate Images**: Batch generate location images with automatic NPC variant support
- **Manage Worlds**: View, validate, and inspect existing worlds

**Keyboard Shortcuts:**
| Key | Action |
|-----|--------|
| `1` | Create World screen |
| `2` | Generate Images screen |
| `3` | Manage Worlds screen |
| `d` | Toggle dark mode |
| `?` | Show help |
| `q` | Quit |
| `Esc` | Go back |

**Image Generation in TUI:**
- Select a world from the dropdown
- Click "Generate All" to create images for all locations (including NPC variants)
- Or select specific locations and click "Regenerate Selected" (variants included automatically)

### REST API

For programmatic access, use the REST API:

```
POST /api/builder/generate
{
  "prompt": "A haunted Victorian mansion with a family curse",
  "theme": "gothic horror",
  "num_locations": 8,
  "num_npcs": 4
}
```

This generates YAML files you can then edit and refine.

## Validating Your World

Before testing, validate your world for consistency issues:

```bash
cd backend
python -m app.engine.validator your-world-name
```

The validator checks:

| Check | What It Validates |
|-------|------------------|
| Flag consistency | Flags that are checked (in `requires`, `appears_when`, `find_condition`) are set somewhere |
| Location references | All exits, item locations, NPC locations point to valid location IDs |
| Item references | `requires_item`, `unlocks`, starting inventory reference valid items |
| Orphan flags | Flags that are set but never checked (warnings only) |

**Example output:**
```
============================================================
World Validation: cursed-manor
============================================================

ERRORS (1):
  ❌ Flag 'examined_drawings' is checked at item:thornwood_amulet/find_condition but never set anywhere

WARNINGS (2):
  ⚠️  Flag 'played_piano' is set at location:sitting_room/interaction:play_piano but never checked anywhere

❌ World has 1 error(s)
```

Fix all errors before testing. Warnings are informational - orphan flags may be intentional for future use.

## Testing Your World

1. Validate your world: `python -m app.engine.validator your-world`
2. Start the game with your world: `POST /api/game/new { "world_id": "your-world" }`
3. Try expected paths - do puzzles work?
4. Try unexpected inputs - does AI handle gracefully?
5. Check constraints are respected
6. Verify NPC dialogue feels consistent

## NPC Dynamic Behavior

### Conditional Appearances

NPCs can appear only when certain conditions are met using `appears_when`:

```yaml
ghost_child:
  appears_when:
    - condition: "has_flag"
      value: "examined_nursery"
    - condition: "trust_above"
      value: 3
```

Conditions are checked at runtime - the NPC only appears if ALL conditions are satisfied.

### Dynamic Location Changes

NPCs can move between locations based on story flags using `location_changes`:

```yaml
butler_jenkins:
  location: dining_room  # Default location

  location_changes:
    - when_flag: heard_noise_upstairs
      move_to: upper_landing
    - when_flag: curse_broken
      move_to: entrance_hall
```

**Rules:**
- Location changes are checked in order
- The **last matching trigger wins**
- If no triggers match, the NPC stays at their default `location`
- Use this for story-driven movement (guard patrols, NPC reactions to events)
- Once triggered, roaming NPCs (with `locations` list) will ONLY be at the new location

### Removing NPCs from the Game

To make an NPC leave the game entirely after an event, use `move_to: null`:

```yaml
ghost_child:
  locations:
    - nursery
    - upper_landing
    - library

  location_changes:
    - when_flag: curse_broken
      move_to: null  # Ghost is freed - disappears from all locations
```

When `move_to` is `null`:
- The NPC will not appear in ANY location
- They are effectively "gone" from the game
- This works for both single-location and roaming NPCs

## Image Variants for Conditional NPCs

When NPCs have `appears_when` conditions, their visibility depends on game state. To ensure images match the narrative, use **image variants**.

### The Problem

If a ghost appears only after examining the nursery, but the location image always shows the ghost, players see a visual/narrative mismatch.

### The Solution: Variant Images

Generate multiple image versions for locations with conditional NPCs:

```bash
# Generate variants for a location
POST /api/builder/{world_id}/images/{location_id}/generate-variants
```

This creates:
- **Base image**: `upper_landing.png` (no conditional NPCs)
- **Variant images**: `upper_landing__with__ghost_child.png`
- **Manifest**: `upper_landing_variants.json`

The game automatically serves the correct variant based on current game state.

### Naming Convention

| File | Contents |
|------|----------|
| `{location}.png` | Base image (unconditional NPCs only) |
| `{location}__with__{npc_id}.png` | Variant with specific NPC visible |
| `{location}_variants.json` | Manifest mapping NPCs to images |

### Checking Variant Status

```bash
# See which locations need variants
GET /api/builder/{world_id}/images/{location_id}/variants
```

Returns information about conditional NPCs and existing variants.

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| AI ignores constraints | Make constraints specific and testable |
| NPC feels inconsistent | Define clearer personality traits and speech style |
| NPC gives wrong item locations | Include explicit locations in `knowledge` (e.g., "The dagger is in the basement") |
| Puzzles too obscure | Add multiple trigger phrases, provide hints |
| World feels empty | Add more `details` and `interactions` |
| Atmosphere is generic | Use specific sensory details, not abstractions |
| Items not discoverable | Add `found_description` to every item |
| Player confused about location | Add exit details describing what each direction looks like |
| Player confused why they can act | Add `starting_situation` explaining the enabling event |
| Game has no ending | Add `victory` condition with location/flag/item requirements |
| Exits seem unrealistic | Add narrative justification in `details` for each exit direction |
| Images lack visual depth | Add `visual_setting` to world.yaml and `visual_description` to each location |
| Images repeat item/NPC descriptions | Focus `visual_description` on background elements and props, not interactive entities |
| Items placed unrealistically in images | Add `item_placements` for every item at each location |
| NPCs floating in scene | Add `npc_placements` for every NPC at each location |
| Conditional NPC visible in image before appearing | Generate image variants with `/generate-variants` |
| NPC doesn't move when expected | Check `location_changes` triggers and flag names match exactly |
| NPC won't leave the game | Use `move_to: null` in `location_changes` to remove NPC entirely |
| Flag mismatch errors | Run `python -m app.engine.validator` to find inconsistencies |
| Item can't be found | Check `find_condition.requires_flag` matches a `sets_flag` somewhere |
