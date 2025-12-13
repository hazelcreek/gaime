# Design Brief: The Angel's Share Murder

## Spoiler-Free Pitch
You arrive on the windswept, rain-lashed shores of Islay, tasked with investigating the death of Master Distiller Angus MacNeil, found drowned in a vat of his own award-winning single malt. As a Glasgow detective, you must navigate the tight-knit island community, decipher ancient Celtic folklore, and untangle the feuds simmering within the Lochindaal Distillery. The peaty air hangs heavy with secrets, and the distillery's ancient pot stills seem to whisper truths that no living soul wants heard. Can you separate the truth from the hearsay before the killer escapes on the morning ferry?

---

## SPOILERS BELOW

## Puzzle Threads

### 1. The Distiller's Logbook (Primary)
**Gate Type**: sequence_gate
**Gate**: The Tasting Room is electronically locked and requires specific coordinates that are only obtained by chemically treating the logbook page.

**Steps**:
1. Discover a torn page of the victim's logbook hidden in the Malt Barn detailing a 'secret blend'.
2. Use the chemical reagent from the Lab on the torn page to reveal invisible ink coordinates.
3. Unlock the private Tasting Room using the coordinates to retrieve the murder weapon (a heavy cask bung).

### 2. The Smuggler's Cove
**Gate Type**: hidden_exit
**Gate**: The exit to the cove does not exist in the room description until the player speaks the correct phrase near the wall.

**Steps**:
1. Translate the Gaelic inscription on the Founder's Statue using the Old Celtic Dictionary.
2. Recite the translated phrase at the 'Weeping Wall' in the Sea Caves.
3. Access the hidden Smuggler's Cove containing historical evidence of illegal trade.

## Navigation Loop (Shortcut)
- **Description**: A rusty service dumbwaiter shaft connects the Sea Caves below back up to the Manager's Office, bypassing the main grounds.
- **Unlocked by**: Repairing the winch mechanism in the Sea Caves with the spanner found in the Boiler Room.
- **Connects**: sea_caves ↔ managers_office

## Gate Types Used
- hidden_exit
- sequence_gate
- locked_exit

## Critical Items
- **Torn Logbook Page**: Contains the hidden code for the Tasting Room, but must be treated first.
  - Found: Stuffed inside a sack of barley in the Malt Barn.
- **Iodine Solution**: Reveals invisible ink on the logbook page.
  - Found: On a shelf in the Distillery Lab.
- **Old Celtic Dictionary**: Used to translate the statue inscription.
  - Found: In the Distillery Library/Study.
- **Bloodied Cask Bung**: The murder weapon needed to confront the killer.
  - Found: Hidden inside a display case in the Locked Tasting Room.

## Optional Secrets

### The Ghost of the Excise Man
**Type**: lore_reveal
Discovering a diary from the 1800s reveals the distillery was founded on a murder, mirroring the current crime.
**Discovery**: Found by examining the loose floorboard in the Bell Tower.

### Vintage 1902 Bottle
**Type**: bonus_item
An incredibly rare bottle of whisky that can be used to bribe a reluctant witness for extra dialogue.
**Discovery**: Hidden behind a false brick in the Smuggler's Cove.

## Environmental Storytelling
- **location_a**: The Manager's Office contains a framed photo of two brothers fighting over a woman.
- **location_b**: The Graveyard features a tombstone for one of the brothers with a fresh flower, implying the survivor's guilt and recontextualizing the Manager's gruff demeanor.

## Victory Condition
- **Location**: ferry_terminal
- **Required Items**: heavy_bung, signed_confession
- **Required Flags**: killer_confronted
- **Summary**: The player confronts the killer at the docks just as the ferry arrives, presenting the bloodied bung as definitive proof, forcing a confession before the police take them away.

## Key Constraints
- The Tasting Room door is reinforced steel; players cannot break it down or pick the lock without the code.
- The Sea Caves are flooded at high tide; players can only enter during 'low tide' turns or after manipulating the sluice gate.
- The Gaelic inscription appears as gibberish text until the Dictionary is held in inventory.
- NPC 'Old Tam' will not speak to the player until they have found the 'Distillery Badge' proving they are not a tourist.
