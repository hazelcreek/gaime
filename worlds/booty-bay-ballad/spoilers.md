# Design Brief: The Ballad of Booty Bay

## Spoiler-Free Pitch
Welcome to Booty Bay, the saltiest, silliest port in the Caribbean, where the seagulls steal your eye-patch and the rum tastes like old boots. You’ve arrived in search of Captain 'No-Beard' McGee's legendary treasure, rumored to be hidden somewhere on this very island. Navigate through a bustling pirate tavern, a suspiciously crowded brig, and a jungle teeming with incompetent buccaneers. It's a race against witless rivals to solve the riddle of the Golden Parrot before high tide washes the clues away!

---

## SPOILERS BELOW

## Puzzle Threads

### 1. The Curse of the Tone-Deaf Parrot (Primary)
**Gate Type**: hidden_exit
**Gate**: The stairs to the Smuggler's Cove are completely invisible until the statue is completed.

**Steps**:
1. Step 1: Discover that the Statue of Captain No-Beard in the Town Square is missing its ceramic parrot accessory.
2. Step 2: Win the 'Insult Poetry Slam' against NPC 'Bard Barbarossa' in the Tavern to receive the Ceramic Parrot.
3. Step 3: Place the Ceramic Parrot on the Statue to reveal the hidden staircase beneath the plinth.

### 2. The Grog-Soaked Jailbreak
**Gate Type**: locked_exit
**Gate**: The Brig is locked with a rusty padlock that cannot be picked, only opened with the Sticky Jail Key.

**Steps**:
1. Step 1: Learn from the weeping lookout in the Crow's Nest that he dropped the Jail Key into a barrel of 'Extra Spicy Grog' on the Docks.
2. Step 2: Use the 'Ladle of Infinite Scooping' (found in the Galley) on the Grog Barrel to retrieve the Sticky Jail Key.
3. Step 3: Unlock the Brig door to free NPC 'Navigator Ned', who gives you the Ancient Compass.

## Navigation Loop (Shortcut)
- **Description**: A zipline created by tying a rope from the high Crow's Nest back down to the Ship's Deck.
- **Unlocked by**: Cutting the counterweight rope in the Crow's Nest with the Rusty Cutlass.
- **Connects**: crows_nest ↔ ships_deck

## Gate Types Used
- hidden_exit
- locked_exit

## Critical Items
- **Ceramic Parrot**: Used on the Statue to open the path to the finale.
  - Found: Held by the winner of the poetry slam in the Tavern.
- **Sticky Jail Key**: Unlocks the Brig to free the Navigator.
  - Found: At the bottom of a grog barrel on the Docks.
- **Ancient Compass**: Required to navigate the dark tunnels of Smuggler's Cove.
  - Found: Given by Navigator Ned after freeing him.
- **Ladle of Infinite Scooping**: Tool used to empty the Grog Barrel.
  - Found: Lying in the ship's Galley amidst dirty dishes.

## Optional Secrets

### The Ghost Pirate's Diary
**Type**: lore_reveal
A diary revealing that Captain No-Beard didn't have a beard because he was actually three children in a trench coat.
**Discovery**: Found by examining the loose floorboard in the Captain's Cabin.

### The Golden Tooth
**Type**: bonus_item
A purely valuable item that lets the player buy a round of drinks for the whole tavern (narrative flair).
**Discovery**: Hidden inside the mouth of the mounted shark head in the Tavern.

## Environmental Storytelling
- **location_a**: The Tavern has a 'Help Wanted' sign for a cook who doesn't use sawdust as a spice.
- **location_b**: The Galley contains a sack labeled 'Premium Flour' that is clearly full of sawdust, explaining the previous cook's firing.

## Victory Condition
- **Location**: treasure_cave
- **Required Items**: ancient_compass
- **Required Flags**: statue_unlocked
- **Summary**: The player uses the Compass to navigate the cove, finds the chest, and discovers the real treasure was the friendships... no, wait, it's actually gold. Lots of gold.

## Key Constraints
- The Grog Barrel cannot be tipped over or drunk; it is too heavy and too spicy. The Ladle must be used.
- The Brig door is too sturdy to be kicked down; only the Sticky Jail Key works.
- The Statue cannot be moved by force; the mechanism requires the weight of the Ceramic Parrot specifically.
