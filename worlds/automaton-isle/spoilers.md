# Design Brief: The Isle of Forgotten Gears

## Spoiler-Free Pitch
Waking on the soot-stained sands of a lonely island after your cruise ship sinks, you expect solitude. Instead, you find a decaying paradise of brass and steam, populated not by people, but by rusting, melancholy automata continuing their programmed duties long after their masters have vanished. Can you decipher the logic of this clockwork purgatory and find a way home, or will you become just another cog in the machine?

---

## SPOILERS BELOW

## Puzzle Threads

### 1. The Lighthouse Beacon (Primary)
**Gate Type**: sequence_gate
**Gate**: The Lighthouse elevator is non-functional until the central Boiler Room is pressurized, preventing access to the signal mechanism.

**Steps**:
1. Discover the ruined Lighthouse is missing its focusing lens and power source.
2. Trade polished sea glass with the Hermit Crab Droid for a replacement lens.
3. Refuel the Boiler Room furnace using driftwood and coal found in the mines to restore pneumatic pressure.

### 2. The Tinkerer's Workshop
**Gate Type**: locked_exit
**Gate**: A heavy iron gate blocks the path to the workshop, requiring a specific gear-shaped key found elsewhere.

**Steps**:
1. Find the rusty gear-shaped key on the Corpse of the Previous Castaway.
2. Unlock the heavy iron gate leading to the Workshop Courtyard.
3. Repair the Workshop's water wheel to lower the drawbridge to the Northern Cliffs.

## Navigation Loop (Shortcut)
- **Description**: A zipline cable running from the Lighthouse Balcony back down to the starting Beach.
- **Unlocked by**: Repairing the zipline harness using leather straps found in the Captain's Quarters.
- **Connects**: lighthouse_balcony ↔ shipwreck_beach

## Gate Types Used
- sequence_gate
- locked_exit
- hidden_exit

## Critical Items
- **Polished Sea Glass**: Used as a makeshift Fresnel lens for the lighthouse.
  - Found: Hidden inside a giant clam shell in the Tidal Pools.
- **Rusted Gear Key**: Unlocks the Workshop Gate.
  - Found: Clutched in the hand of a skeleton in the Jungle Clearing.
- **Pneumatic Schematic**: Teaches the player the correct valve sequence for the Boiler Room.
  - Found: Found in the dusty library of the Observatory.

## Optional Secrets

### The Memory Archive
**Type**: lore_reveal
A hidden room beneath the statue containing audio logs of the island's creator explaining why they replaced humans with robots.
**Discovery**: Solving a chess puzzle against the Grandmaster Bot reveals a hidden switch under the board.

### Golden Oil Can
**Type**: bonus_item
An item that fully repairs any one robot NPC, unlocking unique dialogue and backstory.
**Discovery**: Inside a hollow tree in the Dense Jungle, accessible only after finding the machete.

## Environmental Storytelling
- **location_a**: The Workshop contains half-finished child-sized robots.
- **location_b**: The Graveyard features a single human tombstone labeled 'My Beloved Daughter', explaining the creator's grief-stricken motivation.

## Victory Condition
- **Location**: lighthouse_balcony
- **Required Items**: polished_sea_glass
- **Required Flags**: boiler_pressure_restored
- **Summary**: The beacon pierces the night fog, signaling a passing supply ship. The robots gather on the beach to wave goodbye.

## Key Constraints
- The Boiler Room furnace cannot be lit without 'Dry Driftwood' or 'Coal'; wet wood from the beach will not work.
- The Lighthouse Elevator buttons do not function until the 'boiler_pressure_restored' flag is set.
- The Hermit Crab Droid will not trade the lens for anything other than the 'Shiny Bauble' (Sea Glass) or a 'Gold Coin'.
