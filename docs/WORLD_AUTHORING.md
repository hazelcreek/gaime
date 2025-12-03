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
  stats:
    health: 100

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
  
  # Hints for AI narrative generation
  atmosphere: |
    Grand but decayed. A crystal chandelier hangs dark and dusty.
    Faded portraits line the walls. The air smells of old wood and secrets.
  
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

The `atmosphere` field guides AI narrative generation. Good atmosphere:

```yaml
# Good - evocative, sensory, suggestive
atmosphere: |
  The library smells of aged paper and forgotten knowledge.
  Moonlight filters through grimy windows, illuminating
  dust motes that drift like snow. The silence feels heavy.

# Bad - too literal, no mood
atmosphere: "A room with books"
```

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

Be explicit about what NPCs know and will share:

```yaml
# Good - clear boundaries
knowledge:
  - "Knows the curse requires three artifacts to break"
  - "Knows the artifacts are hidden in library, nursery, and basement"
  - "Will NOT reveal artifact locations until trust is maxed"
  
dialogue_rules:
  - "Speaks of 'dark days' but never names the curse directly"
  - "If asked about children, becomes visibly upset and changes subject"
```

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

## AI World Builder

You can use the AI World Builder to generate starter content:

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

## Testing Your World

1. Start the game with your world: `POST /api/game/new { "world_id": "your-world" }`
2. Try expected paths - do puzzles work?
3. Try unexpected inputs - does AI handle gracefully?
4. Check constraints are respected
5. Verify NPC dialogue feels consistent

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| AI ignores constraints | Make constraints specific and testable |
| NPC feels inconsistent | Define clearer personality traits and speech style |
| Puzzles too obscure | Add multiple trigger phrases, provide hints |
| World feels empty | Add more `details` and `interactions` |
| Atmosphere is generic | Use specific sensory details, not abstractions |
| Items not discoverable | Add `found_description` to every item |
| Player confused about location | Add exit details describing what each direction looks like |
| Player confused why they can act | Add `starting_situation` explaining the enabling event |
| Game has no ending | Add `victory` condition with location/flag/item requirements |
| Exits seem unrealistic | Add narrative justification in `details` for each exit direction |
| Items placed unrealistically in images | Add `item_placements` for every item at each location |
| NPCs floating in scene | Add `npc_placements` for every NPC at each location |

