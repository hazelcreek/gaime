# Story Beats as Gameplay Mechanics

A design exploration for making GAIME worlds feel dynamic, story-driven, and alive during gameplay.

> **Status**: Ideas Document — January 2026
> **Related**: [Vision](../docs/VISION.md) | [Game Mechanics Design](game-mechanics-design.md) | [Roadmap](../planning/roadmap.md)

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Core Philosophy: The String of Pearls](#core-philosophy-the-string-of-pearls)
3. [Defining Meaningful Progress](#defining-meaningful-progress)
4. [Active Narrative vs. Archaeology](#active-narrative-vs-archaeology)
5. [Multi-Act World Structure](#multi-act-world-structure)
6. [Managing Non-Linearity](#managing-non-linearity)
7. [World Builder Pipeline: The Onion Layer Workflow](#world-builder-pipeline-the-onion-layer-workflow)
8. [Applied Examples: Existing Worlds Reimagined](#applied-examples-existing-worlds-reimagined)
9. [Proposed Schema](#proposed-schema)
10. [Technical Integration](#technical-integration)
11. [Open Questions](#open-questions)

---

## The Problem

GAIME worlds currently have rich backstories, atmospheric locations, memorable NPCs, and satisfying puzzles. Yet something is missing: **the story doesn't happen during gameplay**.

Consider the Cursed Manor. The world file defines a compelling tragedy—children sacrificed in a ritual, a curse that lingers, a butler consumed by guilt. This is excellent *backstory*. But during actual play, the experience often reduces to:

1. Explore rooms
2. Find items
3. Solve puzzles
4. Reach victory condition

The narrative exists, but it exists *around* the gameplay rather than *through* it. Players are archaeologists, uncovering what happened decades ago, rather than participants in a story unfolding now.

### Symptoms of the Problem

**Static NPCs**: Jenkins waits in the dining room, responding when spoken to but never seeking you out, never confronting you, never driving events forward. He's a vending machine of information, not a character with agency.

**Flag-Based Gates**: Progress is marked by boolean flags (`found_key: true`) that unlock areas. These are mechanical checkpoints, not dramatic moments. The player doesn't *feel* the story advancing.

**Absent Tension**: Nothing changes if the player dawdles. The storm rages identically whether it's been 5 turns or 500. There's no sense that events are in motion, that the world is moving toward something.

**Discovery Without Revelation**: Finding a diary that explains the curse is discovery, but it's not revelation. The *player* learns something; the *story* doesn't advance. No one reacts, nothing changes, the world remains static.

### The Goal

We want players to feel like they're inside a story that's *happening*, not examining the aftermath of one that already happened. The world should respond, NPCs should act, tension should build, and dramatic moments should arrive—not because a flag flipped, but because conditions aligned for something meaningful to occur.

---

## Core Philosophy: The String of Pearls

Adventure game design has long grappled with a fundamental tension: **narrative wants linearity** (setup → conflict → climax), while **gameplay wants freedom** (explore, experiment, solve in any order). The elegant solution is the "String of Pearls" model, also known as Hub-and-Spoke.

### The Model

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│  HUB 1  │────▶│  HUB 2  │────▶│  HUB 3  │
│ (Pearl) │     │ (Pearl) │     │ (Pearl) │
└─────────┘     └─────────┘     └─────────┘
     │               │               │
     │               │               │
  Freedom         Freedom         Freedom
  & Puzzles       & Puzzles       & Climax
```

- **The Pearls (Hubs)**: Open gameplay areas where the player has freedom. They can explore multiple paths, solve puzzles in any order, and feel agency. This is where *gameplay* happens.

- **The String (Acts)**: The linear connections between hubs. These are gates that only open once the hub's objectives are complete. This is where *story* happens—dramatic beats, revelations, escalations that propel the narrative forward.

### Hubs vs. Act Transitions

| Aspect | The Hub (Gameplay) | The Act Transition (Story) |
|--------|-------------------|---------------------------|
| **Goal** | Provide agency and logical challenges | Raise stakes and dramatic tension |
| **Structure** | Central area → Multiple spokes → Bottleneck | Setup → Conflict → Climax |
| **Player Feeling** | "I am exploring and making progress" | "Something important just happened" |
| **Exit Condition** | Gateway puzzle(s) solved | Plot beat triggered |
| **Freedom** | High—solve in any order | Low—scripted moment |

### The Key Insight

The hub provides the *illusion* of total freedom while the string provides *narrative momentum*. Players feel they're charting their own course, but the story has shape because dramatic beats punctuate the exploration.

In GAIME terms:
- **Hub** = An act where multiple locations and puzzles are accessible
- **String** = An act transition—a dramatic beat that fires when the hub is "complete"

The story doesn't interrupt gameplay; it *emerges from* gameplay when conditions align.

---

## Defining Meaningful Progress

In adventure games, progress isn't about leveling up or accumulating stats. A puzzle matters only if solving it advances *something*. We propose three distinct types of progress that create the feeling of a story moving forward.

### A. Informational Progress: The "Aha!"

**Definition**: Moving from ignorance to understanding.

The player doesn't just collect items; they collect *context*. The cipher puzzle doesn't just yield a password—it reveals the villain's tragic motivation. The diary doesn't just say "the key is in the study"—it explains *why* someone hid it there, and what they were afraid of.

**The Technique: "Knowledge as a Key"**

Some of the most satisfying puzzles are solved not with items but with *information* learned elsewhere. The player needs to know the butler's sister's name to answer the ghost's question. They need to understand the ritual's requirements to know which artifacts matter.

**Example (Cursed Manor)**:
> *Current*: Find the iron key → unlock the basement
> *Enhanced*: Learn that Lady Margaret hid something "where Edmund would never look" (she despised the basement) → realize the dagger must be there → the key becomes meaningful

**In GAIME Terms**: Informational progress means the *player's understanding* of the world deepens. This can be tracked through discovered lore, learned secrets, and pieced-together narratives.

---

### B. Environmental Progress: The World State

**Definition**: Visible changes to the physical world.

The game world should *transform* in response to player actions. Repairing a dam drains the lake, revealing a new area. Starting a fire changes which paths are accessible. The storm breaking at dawn transforms the manor's atmosphere.

**Why It Matters**

Environmental progress is *visible*. The player can see that something changed. This creates a tangible sense of advancement that pure flag-flipping lacks. The world *responded* to them.

**Example (Automaton Isle)**:
> *Current*: Restore boiler pressure → elevator works
> *Enhanced*: Restoring pressure also powers the town's lights → automata emerge from buildings → the dead settlement comes alive around you

**In GAIME Terms**: Environmental progress means the *world's state* changes. Locations transform, new areas unlock, and the atmosphere shifts. This is more than flags—it's perceivable transformation.

---

### C. Relational Progress: The Social Shift

**Definition**: Changes in NPC relationships and status.

The most underutilized form of progress in adventure games. NPCs shouldn't just dispense information—their *stance toward the player* should evolve. The suspicious guard becomes a reluctant ally. The hostile witness becomes an informant. The grieving butler becomes a co-conspirator in breaking the curse.

**The NPC as Progress Bar**

Think of NPC relationships as progress bars that fill (or deplete) based on player choices. When Jenkins' trust reaches 3, he doesn't just *answer more questions*—his entire demeanor changes. He seeks you out. He confesses. He becomes an active participant in the story.

**The Status Spectrum**

NPCs can move along spectrums:
- Hostile → Wary → Neutral → Friendly → Allied
- Stranger → Acquaintance → Trusted → Confidant
- Obstacle → Neutral → Asset → Partner

Each position unlocks different interactions, information, and story beats.

**Example (Islay Mystery)**:
> *Current*: Interview Old Tam → get information
> *Enhanced*: Old Tam starts hostile (thinks you're a tourist) → proving you're police earns grudging respect → helping him with a problem makes him an ally → as an ally, he actively *brings you* evidence he finds

**In GAIME Terms**: Relational progress means *NPC states* evolve. Trust systems already exist in GAIME; the enhancement is making NPCs *proactive* when relationships reach thresholds, and having their behavior visibly change.

---

### The Progress Principle

**Every meaningful puzzle or beat should advance at least one progress type.**

If a puzzle doesn't teach the player something (Informational), change the world (Environmental), or shift a relationship (Relational), it risks feeling like filler—a lock that exists only to have a key.

The richest moments advance multiple types simultaneously:
- Confronting Jenkins with evidence (Relational: trust decision)
- Causes him to reveal the basement location (Informational: new knowledge)
- And give you his master key (Environmental: new areas accessible)

---

## Active Narrative vs. Archaeology

### The Archaeology Trap

A common pitfall in narrative adventure games is "Archaeology Storytelling"—the player finds diaries, letters, and recordings that describe events from 50 years ago. They're piecing together *what happened*, but nothing is *happening now*.

This isn't inherently bad. Environmental storytelling and discovered lore create atmosphere and depth. But if the *entire* narrative is archaeological, the player becomes a historian rather than a protagonist. The story is dead; they're just examining the corpse.

### Active Plot Beats

The solution is **Active Narrative**—dramatic moments that occur *during* gameplay as direct consequences of player actions. These beats don't just reveal history; they create new events that the player must respond to.

We propose three archetypes of active narrative:

---

### Archetype 1: The Escalation

**Pattern**: Solving the puzzle solves the immediate problem but creates a worse one.

The player achieves their goal, but the achievement triggers a complication. The story's stakes rise. What seemed like progress reveals new dangers.

**The Structure**:
1. Player solves puzzle (success!)
2. Success triggers unforeseen consequence (escalation!)
3. New, higher-stakes goal emerges

**Example (Heist Theme)**:
> You hack the security terminal to loop the cameras (Puzzle Solved). But because you spent time hacking, you see your partner get captured on the live feed (Active Consequence). The goal shifts from "Steal the Gold" to "Rescue the Partner."

**Example (Cursed Manor)**:
> You collect all three artifacts and head to the ritual chamber (Progress!). But combining them awakens not just the children's spirits—it awakens *Edmund's* spirit too, furious that someone is undoing his work (Escalation). The ritual becomes a confrontation, not just a ceremony.

**Why It Works**: Escalation creates the feeling that the player's actions *matter*. The world responds, and not always in expected ways. The story is alive.

---

### Archetype 2: The Confrontation

**Pattern**: The player's investigation provokes a direct response from an antagonist or key NPC.

Instead of passively gathering information, the player's actions force a reckoning. Someone notices. Someone reacts. The investigation becomes a two-way interaction.

**The Structure**:
1. Player investigates or gathers evidence
2. Antagonist/NPC notices and responds
3. Direct confrontation ensues (dialogue puzzle, chase, standoff)

**Example (Mystery Theme)**:
> You need to search the butler's pantry. You trigger a distraction puzzle to lure him away. You find the bloody rag—but the butler returns early and catches you holding it (Confrontation). Now you must use the evidence to question him immediately. The NPC shifts from "Obstacle" to "Suspect Under Pressure."

**Example (Islay Mystery)**:
> You break into Fiona's office and find the falsified records. She returns, finds you there. "What do you think you're doing, Detective?" (Confrontation). The scene becomes a dialogue puzzle—accuse her directly? Bluff? Reveal what you know? Her response depends on your approach.

**Why It Works**: Confrontations are inherently dramatic. They force real-time decision-making and create memorable character moments. The NPC stops being a information source and becomes a person responding to pressure.

---

### Archetype 3: The World State Change

**Pattern**: The environment transforms fundamentally, forcing a change in strategy.

The player's action doesn't just unlock a door—it changes the entire playing field. The rules shift. What worked before no longer applies.

**The Structure**:
1. Player completes significant action
2. World transforms (physical, temporal, or atmospheric)
3. Player must adapt to new conditions

**Example (Escape Theme)**:
> You divert power to open the blast doors (Puzzle Solved). The doors open—but the lights go out. You stumble into a flooded room you couldn't see before (World State Change). You've escaped one trap but lost your flashlight and now face a new crisis you inadvertently created.

**Example (Cursed Manor)**:
> When the clock strikes midnight (triggered after Act 1 completion), the manor transforms. Doors that were open are now locked. The ghost child, previously glimpsed, now actively appears. Jenkins' behavior changes from guarded to desperate. The same locations feel different because the *rules* have shifted.

**Why It Works**: World state changes are visceral. The player can *see* and *feel* that something fundamental shifted. The story didn't just progress—the entire context transformed.

---

### Combining Archetypes

The most powerful narrative moments combine multiple archetypes:

**Cursed Manor - "The Revelation" (End of Act 1)**:
- **Confrontation**: Jenkins appears at the library door. "We need to talk."
- **Escalation**: He reveals the basement location—but also that "time is running out. The spirits grow stronger each night."
- **World State Change**: The ghost child, who was invisible, now manifests. The manor's atmosphere darkens.

This single beat advances all three progress types (Relational: Jenkins trusts you; Informational: you learn the basement secret; Environmental: new area unlocks, ghosts appear) through all three narrative archetypes.

---

## Multi-Act World Structure

Single-hub worlds work well for compact experiences. But for richer narratives, GAIME should support **multi-act structures** where the world itself transforms between acts.

### Act Transition Patterns

#### Pattern 1: Location Transfer

The player physically moves to a new area. Previous locations may become inaccessible, remain available for backtracking, or transform while the player is away.

**Structure**:
```
ACT 1: The Manor (investigation)
    ↓ [GATE: Discovery of town connection]
ACT 2: The Town (expanded investigation)
    ↓ [GATE: Location of ritual site revealed]
ACT 3: The Ritual Site (confrontation)
```

**Example (Expanded Islay Mystery)**:
- **Act 1**: The distillery and immediate surroundings
- **Act 2**: The full island opens (sea caves, ferry terminal, croft houses)
- **Act 3**: Focus narrows to ferry terminal for confrontation

**Design Consideration**: Location transfer works well for mysteries (expanding investigation), adventures (journey narratives), and escape scenarios (moving through zones).

---

#### Pattern 2: Temporal Transformation

The same locations exist across acts, but *time* has passed. The museum during visiting hours becomes the museum at night. The kingdom before the war becomes the kingdom after.

**Structure**:
```
ACT 1: Daytime / Before Event
    ↓ [GATE: Time passes / Event occurs]
ACT 2: Nighttime / After Event
```

**Example (Museum Heist)**:
- **Act 1**: Museum during hours—public, safe, limited access, studying security
- **Act 2**: Museum at night—empty, dangerous, full access, executing heist
- **Act 3**: Museum during alarm—guards, time pressure, escape

**Design Consideration**: Temporal transformation lets authors reuse location investments while creating freshness. The player knows the space but must relearn it under new conditions.

---

#### Pattern 3: Consequence Transformation

The world responds to dramatic events. The same locations exist, but everything has changed because something significant happened.

**Structure**:
```
ACT 1: Before Consequence
    ↓ [GATE: Major event occurs]
ACT 2: After Consequence (world transformed)
```

**Example (Epic Return)**:
- **Act 1**: Castle before the crusade—peaceful, the old king lives, relationships established
- **Act 2**: Foreign lands during crusade—completely different locations
- **Act 3**: Castle after return—the king is dead, power has shifted, familiar faces are changed or gone

**Design Consideration**: Consequence transformation creates emotional weight. The player returns to familiar spaces that are now *wrong*. This is especially powerful for themes of loss, change, and homecoming.

---

#### Pattern 4: Progressive Revelation

The locations don't physically change, but the player's *understanding* transforms how they perceive them. The mundane becomes supernatural. The safe becomes dangerous. The familiar becomes alien.

**Structure**:
```
ACT 1: Surface Understanding
    ↓ [GATE: Truth revealed]
ACT 2: Deeper Understanding (same places, new meaning)
```

**Example (Cursed Manor)**:
- **Act 1**: Manor as creepy but explicable—an old house with a sad history
- **Act 2**: Manor with supernatural elements visible—ghosts manifest, impossible geometry appears
- **Act 3**: Manor's true nature revealed—it's a trap, a pocket dimension, purgatory for the guilty

**Design Consideration**: Progressive revelation is ideal for horror and mystery. The growing understanding creates dread or wonder. The player revisits locations and sees them anew.

---

### Act Structure Schema

How might acts be defined in GAIME?

```yaml
acts:
  act_1:
    name: "The Arrival"
    description: "Explore the manor, meet Jenkins, discover something is wrong"

    # Which locations are available in this act
    available_locations:
      - entrance_hall
      - library
      - dining_room
      - kitchen
      - sitting_room

    # NPCs present in this act
    available_npcs:
      - butler_jenkins

    # Atmosphere modifier for the Narrator
    atmosphere: gothic_mystery
    urgency: low  # Affects NPC dialogue and descriptions

    # The "spokes" - independent objectives
    spokes:
      exploration:
        progress_type: environmental
        required_beats: [explored_ground_floor]
      trust_building:
        progress_type: relational
        required_beats: [jenkins_trust_3]
      discovery:
        progress_type: informational
        required_beats: [found_ritual_evidence]

    # Gate to next act (all spokes must complete)
    gate:
      requires_all_spokes: true
      transition_beat: the_revelation

  act_2:
    name: "The Investigation"
    description: "Hunt for the artifacts, encounter the ghosts"

    # New locations unlock
    available_locations:
      - entrance_hall
      - library
      - dining_room
      - kitchen
      - sitting_room
      - basement        # NEW
      - upper_landing   # NEW
      - nursery         # NEW
      - master_bedroom  # NEW

    # New NPCs appear
    available_npcs:
      - butler_jenkins
      - ghost_child      # NEW (conditional)
      - lady_margaret    # NEW (conditional)

    atmosphere: supernatural_horror
    urgency: medium

    # ... spokes for artifact collection ...
```

---

### Enforcing Act Boundaries: Location Gating

A natural question arises: what actually *prevents* the player from wandering into Act 2 locations during Act 1? If the nursery exists in `locations.yaml`, can't the player just walk upstairs and explore it early?

The answer is **hard gating at the engine level**. Locations not in the current act's `available_locations` are simply inaccessible—their exits don't appear, or attempting to use them is blocked with narrative justification.

#### How It Works

The movement system enforces act boundaries through three mechanisms:

**1. Exit Filtering**

When building the player's perception of a location, the engine only shows exits to locations that are:
- Defined in `locations.yaml` AND
- Listed in `acts[current_act].available_locations`

If Act 1 doesn't include `upper_landing`, the player won't see "stairs leading up" as a valid exit, even if those stairs are defined in the location data.

**2. Movement Validation**

If a player somehow attempts to move to an unavailable location (perhaps typing "go upstairs" when no such exit is visible), the validator rejects the action:

```python
def validate_movement(self, destination: str, state: GameState) -> ValidationResult:
    current_act = state.current_act
    available = self.world.acts[current_act].available_locations

    if destination not in available:
        return ValidationResult(
            valid=False,
            code="LOCATION_LOCKED",
            reason="That area is not accessible yet."
        )
    # ... continue with normal exit validation ...
```

**3. Narrative Justification**

Rather than breaking immersion with "You can't go there," the Narrator provides in-world reasons. These can be defined per-location or generated contextually:

| Blocked Access | Narrative Justification |
|----------------|------------------------|
| Stairs to upper floor | *"The upper landing is shrouded in impenetrable darkness. Something feels deeply wrong about ascending... not yet."* |
| Basement door | *"The basement door is locked. Jenkins eyes it nervously—'Best leave that be for now.'"* |
| Garden gate | *"The storm has made the garden path impassable. Fallen branches block your way."* |
| Secret passage | *"The bookshelf looks ordinary. Perhaps you're missing something."* |

#### Example: The Cursed Manor

Consider how Act 1 → Act 2 location gating works:

**Act 1 State:**
```
Player Location: entrance_hall
Available Locations: [entrance_hall, library, dining_room, kitchen, sitting_room]
Visible Exits from entrance_hall:
  - north → library ✓ (in available_locations)
  - east → dining_room ✓ (in available_locations)
  - stairs → upper_landing ✗ (NOT in available_locations, hidden or blocked)
```

**Player tries:** `> go upstairs`

**Response (Act 1):**
> *The grand staircase curves upward into shadow. As you place your foot on the first step, a chill runs through you—an almost physical resistance. Jenkins appears at your elbow. "I wouldn't, if I were you. Not until we understand what's happening here." The darkness above seems to pulse with unspoken warning.*

**After Act 1 Gate opens (The Revelation beat triggers):**

```
Available Locations: [entrance_hall, library, dining_room, kitchen,
                      sitting_room, basement, upper_landing, nursery, master_bedroom]
Visible Exits from entrance_hall:
  - north → library ✓
  - east → dining_room ✓
  - stairs → upper_landing ✓ (NOW available)
  - basement_door → basement ✓ (NOW available, Jenkins gave key)
```

**Player tries:** `> go upstairs`

**Response (Act 2):**
> *You ascend the grand staircase. The darkness that once repelled you has lifted—or perhaps you've earned the right to pass. The upper landing stretches before you, doors leading to rooms that have waited decades for someone brave enough to enter.*

#### Design Implications

This hard gating has important consequences for world authoring:

1. **Exits must be act-aware**: When designing locations, authors should consider which exits are available per act and provide appropriate blocking descriptions.

2. **Narrative coherence matters**: The *reason* a location is blocked should fit the story. Physical obstacles (locked doors, debris) work for mundane settings; supernatural resistance fits horror; authority figures blocking access fits institutional settings.

3. **Unlocking should feel earned**: The transition narrative should acknowledge that previously blocked areas are now accessible, making the player feel their progress.

4. **Some locations may span acts**: Core hub areas (like `entrance_hall`) typically remain available across acts. Only newly-accessible areas need gating.

#### Transitions as Active Revelation

Critically, **players should never have to wander around testing doors** to discover what changed after an act transition. The transition beat itself must actively communicate the new possibilities—through NPC guidance, dramatic narrative, or explicit revelation.

**The Anti-Pattern: Silent Unlocking**

Bad design leaves the player guessing:
> *The clock strikes midnight.* [Flag silently set: basement_unlocked = true]
>
> Player now has to remember "Hey, I couldn't go to the basement before... maybe I should try again?" This breaks immersion and feels like a video game.

**The Pattern: Dramatic Revelation**

Good design makes new access part of the story moment:

> *The clock strikes midnight. Jenkins appears at the library door, his face ashen in the candlelight.*
>
> *"I've kept silent long enough," he says, pressing a cold iron key into your palm. "The basement. That's where it all began—where Edmund performed his... rituals." He gestures toward the main hall. "The door is behind the stairs. I'll show you."*
>
> *As he leads you through the entrance hall, you notice something else has changed. The oppressive darkness that clung to the upper staircase has lifted. The way up stands open now, as if the house itself has decided you're ready.*

In this transition:
- **The NPC actively guides** the player to the new area (basement)
- **Physical/narrative change** draws attention to other new access (upper floor)
- **No guessing required**—the story tells you what's possible

**Techniques for Active Revelation**

| Technique | Example | Best For |
|-----------|---------|----------|
| **NPC Guide** | "Follow me—there's something you need to see in the basement." | Any genre; feels natural |
| **Item Grant** | Jenkins hands you a key, explicitly stating what it opens | Mystery, exploration |
| **Environmental Change** | "The shadows retreat from the staircase" / "The floodwaters have receded" | Horror, adventure |
| **Direct Announcement** | "The path to the north is clear now" (narrator voice) | Fairy tale, lighter tone |
| **Sensory Cue** | "A door slams open somewhere above you" / "You hear footsteps upstairs" | Horror, tension |
| **Map/Journal Update** | "You mark the basement entrance on your mental map" | Investigation, exploration |

**Multiple Unlocks in One Transition**

When a gate opens multiple locations, the transition should acknowledge all of them naturally:

> *Jenkins leads you to the basement door, but pauses at the foot of the grand staircase.*
>
> *"The children's rooms are up there," he says quietly. "The nursery. The master bedroom where Lady Margaret..." He trails off. "You'll need to search everywhere if you're to understand what happened. The whole house is open to you now—for better or worse."*

This single transition communicates:
1. Basement is now accessible (primary, guided)
2. Nursery exists and is relevant (secondary, mentioned)
3. Master bedroom exists and is relevant (secondary, mentioned)
4. The entire upper floor is now available (summary)

The player knows exactly where to explore without trial-and-error.

**Schema Support for Transition Revelation**

The gate definition should include explicit guidance for what to reveal:

```yaml
gate:
  transition_beat: the_revelation

  unlocks_locations:
    - basement
    - upper_landing
    - nursery
    - master_bedroom

  # How to communicate these unlocks in the transition narrative
  revelation:
    primary_focus: basement  # NPC leads here or narrative emphasizes
    secondary_mentions:
      - upper_landing: "The darkness has lifted from the stairs"
      - nursery: "The children's rooms..."
      - master_bedroom: "Where Lady Margaret spent her final days"

    # Optional: NPC who guides/reveals
    revealed_by: butler_jenkins

    # Transition narrative (can reference {locations} dynamically)
    narrative: |
      Jenkins presses a key into your hand and leads you toward the basement.
      As you pass the grand staircase, you notice the oppressive shadows have
      retreated. The upper floor, previously forbidden, now stands accessible.
```

This ensures the Narrator has clear guidance on *how* to communicate the transition, not just *what* changed.

```yaml
# In locations.yaml, you can optionally define blocked descriptions
upper_landing:
  name: "Upper Landing"
  description: "A shadowy corridor stretches before you..."

  # Optional: Used when player tries to access before this location is available
  blocked_description: |
    The stairs leading up seem to reject your presence. The shadows
    above are too thick, too watchful. You're not ready—not yet.
  blocked_reason: supernatural  # Helps Narrator match tone
```

This approach preserves the String of Pearls structure: players have freedom *within* each hub (pearl), but the connections between hubs (string) are firmly controlled until the dramatic gate opens.

---

## Managing Non-Linearity

Freedom within hubs is essential, but unmanaged freedom creates problems. If Puzzle B triggers a flood, but the player hasn't finished Puzzle A (which requires a dry floor), the game breaks. GAIME needs strategies to allow freedom while preventing catastrophe.

### The Funnel Technique

**Principle**: Major world-changing events only fire when ALL prerequisite puzzles complete.

**Structure**:
```
Hub has 3 independent puzzles (A, B, C)
None of them individually trigger the big event
The big event only fires when A + B + C are ALL complete
```

**Example (Cursed Manor)**:
> The act transition (midnight strikes, ghosts fully manifest) doesn't happen when you find the diary, OR when you earn Jenkins' trust, OR when you explore the ground floor. It happens when all three objectives are complete. This ensures the player has everything they need before the world transforms.

**Implementation**: The gate's `requires_all_spokes: true` enforces this naturally.

---

### Additive Storytelling

**Principle**: State changes ADD layers; they don't BREAK previous states.

**Bad Design**:
> Stealing the map triggers an alarm that locks all doors. Now the player can't complete the puzzle that requires accessing the kitchen.

**Good Design**:
> Stealing the map triggers an alarm that adds guards on patrol. The kitchen is still accessible, but reaching it requires stealth. The story moved forward; the game didn't break.

**The Pattern**: When designing consequences, ask: "Does this close doors or add obstacles?" Prefer adding obstacles that make remaining puzzles *harder* over closing doors that make them *impossible*.

---

### The Dependency Graph

**Principle**: If Puzzle B destroys the solution for Puzzle A, make Puzzle B require an item found inside Puzzle A.

This forces the player to solve A before they CAN solve B, preserving narrative logic without explicit gating.

**Example**:
> The ritual (Puzzle B) requires a specific phrase. The phrase is written in a book that gets destroyed if the library catches fire. Solution: The item needed to start the fire (matches) is locked in a cabinet that only opens after you've read the book. The player *must* read first, then can start the fire.

**Tool**: During world authoring, generate a dependency graph showing which puzzles affect which others. Flag any dependencies that could create unwinnable states.

---

## World Builder Pipeline: The Onion Layer Workflow

How should story-driven worlds be *authored*? The current approach is often "world-first"—create locations, populate with items and NPCs, hope a story emerges. We propose a "story-first" pipeline that ensures narrative coherence.

### The Onion Layer Model

Design from the abstract core outward to specific details:

```
┌─────────────────────────────────────────┐
│          6. NARRATIVE WEAVE             │  ← Polish: Inject "why" into "how"
│  ┌─────────────────────────────────┐    │
│  │       5. MICRO-DESIGN           │    │  ← Specific puzzles
│  │  ┌─────────────────────────┐    │    │
│  │  │      4. SPOKES          │    │    │  ← Puzzle chains per hub
│  │  │  ┌─────────────────┐    │    │    │
│  │  │  │    3. HUBS      │    │    │    │  ← Locations per act
│  │  │  │  ┌─────────┐    │    │    │    │
│  │  │  │  │2. SKEL. │    │    │    │    │  ← Act structure
│  │  │  │  │ ┌─────┐ │    │    │    │    │
│  │  │  │  │ │CORE │ │    │    │    │    │  ← Theme & constraints
│  │  │  │  │ └─────┘ │    │    │    │    │
│  │  │  │  └─────────┘    │    │    │    │
│  │  │  └─────────────────┘    │    │    │
│  │  └─────────────────────────┘    │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

### Phase 1: The Core (Constraints)

Define the boundaries before anything else. This prevents feature creep and ensures thematic consistency.

**Elements**:
- **Premise**: Genre + Inciting Incident
  - "Victorian gothic horror: Trapped in a cursed manor during a storm"
- **Verbs**: What can the player do?
  - Examine, Talk, Combine, Use (GAIME's existing verb set)
- **Theme**: The emotional/philosophical core
  - "Guilt and redemption" / "The price of ambition" / "Adaptation vs. preservation"
- **Scope**: Single-act or multi-act?

**Example**:
```
Premise: Scottish noir mystery—detective investigating a murder at a distillery
Verbs: Examine, Talk, Deduce, Accuse
Theme: Truth vs. loyalty—the killer is someone the island wants to protect
Scope: Two acts (investigation → confrontation)
```

---

### Phase 2: The Skeleton (Linear Structure)

Map the story's linear arc—the acts and the gates between them. Don't worry about puzzles yet; focus on dramatic shape.

**Elements**:
- Act names and goals
- Gate conditions (what completes each act)
- Emotional arc (tension should build)

**Example**:
```
ACT 1: "The Scene"
- Goal: Establish the crime, meet suspects
- Gate: Identify primary suspect
- Emotion: Intrigue, suspicion

ACT 2: "The Hunt"
- Goal: Gather evidence, prove motive
- Gate: Obtain murder weapon
- Emotion: Urgency, danger

ACT 3: "The Confrontation"
- Goal: Confront killer, achieve justice
- Gate: Victory
- Emotion: Triumph, resolution
```

---

### Phase 3: The Hubs (Locations)

Assign physical locations to each act. Consider how locations support the act's goals and atmosphere.

**Elements**:
- Location list per act
- Central "safe point" for each hub
- Connection logic (how does the player move between areas?)

**Example**:
```
ACT 1 Hub: The Distillery
- Central: Distillery Courtyard
- Spokes: Stillroom, Tasting Room, Lab, Manager's Office

ACT 2 Hub: The Island
- Central: Village Crossroads
- Spokes: Sea Caves, Croft House, Ferry Terminal, Church
```

---

### Phase 4: The Spokes (Puzzle Chains)

Create 3-4 independent objectives per hub. Each spoke should advance one of the three progress types. All spokes must complete to open the gate.

**Elements**:
- Spoke ID and name
- Progress type (Informational / Environmental / Relational)
- Required beats (what must happen)
- How it connects to the gate

**Example**:
```
ACT 1 Spokes:

Spoke A: "Examine the Body" (Informational)
- Required beats: Autopsy complete, cause of death known
- Outcome: Player understands HOW victim died

Spoke B: "Interview Witnesses" (Relational)
- Required beats: Old Tam talked, Callum talked, Fiona talked
- Outcome: Player has met all suspects, heard contradictions

Spoke C: "Access Records" (Environmental)
- Required beats: Tasting room unlocked, logbook found
- Outcome: Player can access previously locked area, has key evidence
```

---

### Phase 5: Micro-Design (Reverse Engineering)

Design specific puzzles by working *backward* from goals using the Obstacle Chain method.

**The Process**:
1. Start with the goal (what does the player get?)
2. Add an obstacle (what blocks them?)
3. Define the solution (what overcomes the obstacle?)
4. That solution becomes a new goal (where does THAT come from?)
5. Repeat until the chain reaches accessible starting points

**Example** (Getting the Green Resonator in a sci-fi game):
```
1. Goal: Get Green Resonator
2. Obstacle: Held by aggressive alien plant
3. Solution: Feed plant "Purified Water" to calm it
4. New Goal: Get Purified Water
5. Obstacle: Water filter is broken
6. Solution: Replace filter core
7. New Goal: Get filter core
8. Source: Salvage from crashed ship (accessible)
9. Twist: Ship tech doesn't work alone—must combine with alien moss (theme: adaptation)
```

---

### Phase 6: Narrative Weave (Polish)

Inject "why" into "how." Every puzzle should have narrative justification. Every obstacle should have a story reason for existing.

**Questions to Ask**:
- Why does this obstacle exist? (In-world reason)
- What does solving it reveal about the world?
- How does it connect to the theme?
- What emotion should the player feel?

**Example**:
```
The aggressive alien plant exists because...
The ship's botanist deliberately fed herself to it, trying to preserve human DNA on the alien world. The "monster" is actually a guardian, protecting her legacy.

This recontextualizes the obstacle and connects to the theme (adaptation/sacrifice).
```

---

### World Builder Implementation

How might gaime_builder support this workflow?

1. **Premise Screen**: Author inputs theme, tone, scope
2. **Skeleton Screen**: AI proposes act structure; author adjusts
3. **Hub Design**: AI suggests locations per act; author selects/modifies
4. **Spoke Generation**: AI proposes puzzle chains per hub
5. **Review Checkpoint**: Author reviews story spine before generation
6. **Element Generation**: AI creates NPCs, items, details to support spokes
7. **Narrative Weave**: AI adds lore, backstory, thematic connections
8. **Output**: Complete YAML files with embedded story structure

The key insight: **Story spine comes first, world elements are derived to serve it.**

---

## Applied Examples: Existing Worlds Reimagined

Let's apply these concepts to GAIME's existing worlds, showing how they could be enriched with story beats, multi-act structure, and active narrative.

---

### The Cursed Manor (Gothic Horror)

**Current State**:
- Single hub (manor), artifact collection puzzle
- Jenkins trust system, conditional ghost appearances
- Victory: 3 artifacts in ritual chamber

**Proposed Enhancement**:

#### Act Structure

```
ACT 1: "THE ARRIVAL"
├── Hub: Ground floor of manor
├── Atmosphere: Gothic mystery, unsettling but not yet supernatural
├── Urgency: Low
│
├── Spoke A: Explore the Manor (Environmental)
│   │   Learn the layout, establish atmosphere
│   └── Beat: "First Haunting" — Piano plays by itself
│       Type: World State Change (subtle)
│       Trigger: Enter sitting_room first time
│       Effect: Sets tone, plants supernatural seed
│
├── Spoke B: Earn Jenkins' Trust (Relational)
│   │   Build relationship through kindness
│   └── Beat: "Jenkins Opens Up"
│       Type: Confrontation
│       Trigger: trust >= 3
│       Effect: Jenkins SEEKS YOU OUT, confesses to library
│              "There's something I must tell you, about that night..."
│
└── Spoke C: Discover the Past (Informational)
    │   Find evidence of what happened
    └── Beat: "The Slashed Portrait"
        Type: Informational revelation
        Trigger: Examine portraits interaction
        Effect: Player learns children existed, hints at violence

GATE 1: "THE REVELATION"
├── Type: Escalation + World State Change
├── Trigger: All spokes complete
├── Scene: Jenkins appears at library door
│   "We need to talk. About the basement. About... everything."
│   He gives you the iron key.
│   "Time is running out. I can feel them getting stronger."
├── Effects:
│   - Basement unlocks
│   - Upper floor unlocks
│   - Ghost child begins appearing
│   - Atmosphere shifts to supernatural_horror
│   - Urgency increases to medium
└── Active Consequence: The ghosts weren't inactive—they were waiting for someone who could help

---

ACT 2: "THE HUNT"
├── Hub: Full manor (ground floor + basement + upper floor)
├── Atmosphere: Supernatural horror, ghosts active
├── Urgency: Medium
│
├── Spoke A: Find the Amulet (Environmental)
│   │   Nursery puzzle chain
│   └── Beat: "Emily's Plea"
│       Type: Confrontation (with ally)
│       Trigger: Enter nursery after ghost_child appeared
│       Effect: Ghost child writes "HELP US" in frost
│              Points insistently toward hidden compartment
│
├── Spoke B: Find the Dagger (Relational)
│   │   Master bedroom, requires Lady Margaret encounter
│   └── Beat: "Mother's Warning"
│       Type: Confrontation (tense)
│       Trigger: Enter master bedroom + found dagger clue
│       Effect: Lady Margaret manifests, mistakes you for Edmund
│              "You! Haven't you done enough?!"
│              Must convince her you're here to help
│              If successful: She reveals dagger location
│
└── Spoke C: Find the Grimoire (Informational)
    │   Library secret passage
    └── Beat: "The Truth"
        Type: Informational revelation (major)
        Trigger: Find and read grimoire
        Effect: Full understanding of curse mechanism
               Player knows exactly what must be done

GATE 2: "THE GATHERING"
├── Type: Escalation
├── Trigger: All three artifacts collected
├── Scene: The manor shudders. Jenkins finds you.
│   "You've done it. But... do you hear that?"
│   A new voice echoes through the halls—Edmund's spirit awakens
├── Effects:
│   - has_all_artifacts flag set
│   - Ritual chamber becomes accessible
│   - Edmund's presence adds new danger
│   - Urgency increases to high
└── Active Consequence: Collecting the artifacts didn't just enable the ritual—it woke the very spirit that created the curse

---

ACT 3: "THE RITUAL"
├── Hub: Ritual chamber (focused)
├── Atmosphere: Climactic supernatural
├── Urgency: High
│
└── Final Beat: "The Breaking"
    Type: Escalation → Resolution
    Trigger: Place all artifacts on pedestals
    Scene: The ritual begins. Edmund's spirit tries to stop you.
           The children's spirits appear to help.
           Jenkins must make his final choice.
    Victory: Curse breaks, spirits freed, dawn breaks
```

#### Key Story Beats Summary

| Beat | Act | Type | Trigger | Active Consequence |
|------|-----|------|---------|-------------------|
| First Haunting | 1 | World State | Enter sitting_room | Piano plays alone, tone established |
| Jenkins Opens Up | 1 | Confrontation | trust >= 3 | Jenkins seeks you out, confesses |
| The Revelation | Gate | Escalation | Act 1 complete | Basement unlocks, ghosts activate |
| Emily's Plea | 2 | Confrontation | Nursery + ghost appeared | Ghost child actively helps |
| Mother's Warning | 2 | Confrontation | Bedroom + clue | Lady Margaret blocks/tests you |
| The Truth | 2 | Informational | Read grimoire | Full understanding achieved |
| The Gathering | Gate | Escalation | All artifacts | Edmund awakens, final danger |
| The Breaking | 3 | Resolution | Place artifacts | Curse broken, victory |

#### NPC Proactivity

**Jenkins**:
- Act 1: Waits in dining room (reactive)
- Trust 3: Seeks player out at library (proactive)
- Act 2: More forthcoming, provides hints (supportive)
- Act 3: Present at ritual, makes final choice (active participant)

**Ghost Child**:
- Act 1: Invisible (not yet triggered)
- Gate 1: First manifestation (passive)
- Act 2: Actively beckons toward clues (proactive guide)
- Act 3: Appears at ritual to help (active participant)

**Lady Margaret**:
- Act 1: Not present
- Act 2: Blocks master bedroom (obstacle)
- After convincing: Provides crucial information (asset)
- Act 3: Appears at ritual (witness to resolution)

---

### The Angel's Share Murder (Scottish Noir)

**Current State**:
- Time pressure (ferry at dawn)
- Multiple suspects, evidence gathering
- Victory: Confront killer with murder weapon

**Proposed Enhancement**:

#### Act Structure

```
ACT 1: "THE SCENE"
├── Hub: Distillery compound
├── Atmosphere: Rain-soaked noir, tense
├── Urgency: Low → building
│
├── Spoke A: Examine the Crime Scene (Informational)
│   └── Beat: "Not An Accident"
│       Trigger: Complete autopsy examination
│       Effect: Drowning was assisted—someone held him under
│
├── Spoke B: Interview the Suspects (Relational)
│   └── Beat: "Contradictions"
│       Trigger: Talk to all three suspects
│       Effect: Their stories don't align—someone is lying
│       NPC States: Each becomes "suspect" status
│
└── Spoke C: Access the Records (Environmental)
    └── Beat: "The Falsified Books"
        Trigger: Break into tasting room, find logbook
        Effect: Financial motive emerges—someone was stealing

GATE 1: "THE SUSPECT"
├── Type: Confrontation
├── Trigger: All spokes complete
├── Scene: Fiona catches you in her office
│   "What the hell do you think you're doing, Detective?"
│   Confrontation dialogue—she reveals affair, points to Gordon
│   "I loved Angus. His brother... Gordon was always jealous."
├── Effects:
│   - Primary suspect identified
│   - Sea caves unlock (tide turns)
│   - Gordon's location revealed
│   - Urgency increases—dawn approaches
└── Active Consequence: You have a suspect, but no proof

---

ACT 2: "THE HUNT"
├── Hub: Wider island
├── Atmosphere: Storm intensifying, race against time
├── Urgency: High
│
├── Spoke A: Find the Weapon (Environmental)
│   └── Beat: "The Bung"
│       Trigger: Search sea caves at low tide
│       Effect: Murder weapon found in smuggler's cache
│       Active element: Caves flood—time pressure within the puzzle
│
├── Spoke B: Establish Motive (Informational)
│   └── Beat: "The Inheritance"
│       Trigger: Find documents at croft house
│       Effect: Gordon inherits everything if Angus dies without heir
│
└── Spoke C: Build the Case (Relational)
    └── Beat: "The Alliance"
        Trigger: Get Callum to testify + convince Old Tam
        Effect: Witnesses willing to speak against Gordon
        NPC States: Shift from "reluctant" to "allied"

GATE 2: "DAWN APPROACHES"
├── Type: Escalation (time)
├── Trigger: All evidence gathered
├── Scene: Ferry horn sounds in the distance
│   Old Tam finds you: "Detective! He's heading for the pier!"
├── Effects:
│   - Final location unlocks (ferry terminal)
│   - Gordon is attempting to flee
│   - No more investigation—time for confrontation
└── Active Consequence: You have everything you need, but he's about to escape

---

ACT 3: "THE CONFRONTATION"
├── Hub: Ferry terminal (focused)
├── Atmosphere: Dawn breaking, final reckoning
├── Urgency: Maximum
│
└── Final Beat: "Justice"
    Type: Confrontation → Resolution
    Trigger: Present evidence to Gordon in correct sequence
    Scene: Dialogue puzzle—present motive, opportunity, weapon
           Gordon's composure cracks under the weight of evidence
           "You can't prove... you... how did you find..."
    Victory: Killer confesses, arrested as ferry departs
```

#### Narrative Urgency (Without Timers)

The urgency is conveyed through atmosphere and NPC behavior, not mechanical pressure:

| Act | Atmosphere | NPC Behavior | Descriptions |
|-----|------------|--------------|--------------|
| Act 1 | Night, steady rain | NPCs defensive, guarded | "Rain patters against the windows..." |
| Act 2 | Pre-dawn, storm peaks | NPCs anxious, checking time | "The storm is getting worse..." |
| Gate 2 | Dawn breaking | NPCs urgent, pointing toward ferry | "You hear the ferry horn..." |
| Act 3 | Dawn, storm clearing | Gordon nervous, trying to leave | "His hand trembles as he reaches for his ticket..." |

The player never sees a turn counter, but the *world* conveys urgency through every description and interaction.

---

### The Ballad of Booty Bay (Comedic Pirate)

**Current State**:
- Treasure hunt with item collection
- NPCs guard key items
- Light, humorous tone

**Proposed Enhancement**:

```
ACT 1: "THE SCRAMBLE"
├── Hub: Booty Bay town
├── Tone: Bumbling chaos, competitive silliness
│
├── Spoke A: Win the Bard's Challenge (Relational)
│   └── Beat: "SICK BURN!"
│       Trigger: Win poetry slam
│       Effect: Barbarossa weeps, surrenders Ceramic Parrot
│       Humor: His "defeat poem" is hilariously bad
│
├── Spoke B: The Jailbreak (Environmental)
│   └── Beat: "The Great Escape"
│       Trigger: Free Navigator Ned
│       Effect: Ned joins party (sort of), provides compass
│       Humor: The "escape" involves bumbling guards
│
└── Spoke C: The First Clue (Informational)
    └── Beat: "X Marks the Spot (Maybe)"
        Trigger: Find treasure map
        Effect: Compass now has direction
        Humor: The map is badly drawn

GATE 1: "THE RIVALS"
├── Type: Escalation (comedic)
├── Trigger: Enter cave entrance with compass
├── Scene: Rival pirate crew appears!
│   "Thanks for doing all the hard work, Scallywag!"
│   They snatch the compass, seal you in the caves
├── Effects:
│   - Compass stolen
│   - Caves become the hub
│   - New goal: Escape AND beat them
└── Humor: The rivals are also incompetent

---

ACT 2: "THE UNDERGROUND RACE"
├── Hub: Smuggler's caves (under Booty Bay)
├── Tone: Slapstick chase, comic rivalry
│
├── Spoke A: Find Alternate Route (Environmental)
│   └── Beat: "Wrong Turn!"
│       Trigger: Navigate without compass
│       Humor: Multiple wrong turns, silly obstacles
│
├── Spoke B: Sabotage the Rivals (Relational)
│   └── Beat: "The Old Switcheroo"
│       Trigger: Encounter rivals, trick them
│       Effect: They take wrong path
│       Humor: They're too proud to admit being lost
│
└── Spoke C: Recover the Compass (Environmental/Informational)
    └── Beat: "YOINK!"
        Trigger: Steal compass back while rivals lost
        Humor: Dramatic slow-motion grab

GATE 2: "TREASURE ROOM SHOWDOWN"
├── Type: Confrontation (comedic)
├── Trigger: Both crews reach treasure room simultaneously
├── Scene: Rival captain: "YOU! How did you—never mind!"
│   They have the statue key, you have the parrot
│   Neither can open it alone
└── Humor: Awkward standoff

---

ACT 3: "THE TREASURE"
└── Final Beat: "The Golden Parrot!"
    Type: Resolution (comedic)
    Scene: Negotiate, trick, or challenge rival captain
           Open chest together/separately
           Treasure is real! Also includes embarrassing note from No-Beard
    Victory: Rich! Or at least, hat-rich.
```

#### Tone Escalation

| Act | Comedy Style | Running Gags |
|-----|--------------|--------------|
| Act 1 | Bumbling NPCs, silly puzzles | Weeping Lookout's constant crying |
| Act 2 | Slapstick chase, mistaken directions | Rivals' overconfidence |
| Act 3 | Triumphant punchline, callbacks | No-Beard's final note |

---

### The Isle of Forgotten Gears (Steampunk Survival)

**Current State**:
- Survival progression (beach → lighthouse)
- Resource gathering chain
- Melancholy tone, abandoned automata

**Proposed Enhancement**:

```
ACT 1: "SURVIVAL"
├── Hub: Shipwreck Beach
├── Tone: Desperate, alone
│
├── Spoke A: Escape the Tide (Environmental)
│   └── Beat: "First Contact"
│       Trigger: Reach jungle edge
│       Effect: An automaton waves at you from the treeline
│       Emotion: Surprise, curiosity
│
├── Spoke B: Gather Resources (Environmental)
│   └── Beat: "The Wreck Sinks"
│       Trigger: Collect supplies from ship
│       Effect: Ship sinks completely—no going back
│       Emotion: Finality, commitment
│
└── Spoke C: Understand the Island (Informational)
    └── Beat: "Not Alone"
        Trigger: Find first signs of civilization
        Effect: Realize the island is inhabited... by machines
        Emotion: Wonder, unease

GATE 1: "THE INVITATION"
├── Type: World State Change
├── Trigger: All survival objectives complete
├── Scene: The automaton from the beach approaches
│   It gestures: "Follow."
│   It leads you into the jungle, toward lights and steam
├── Effects:
│   - Settlement locations unlock
│   - Automata become NPCs
│   - Tone shifts from survival to exploration
└── Emotion: The machines aren't hostile—they're lonely

---

ACT 2: "INTEGRATION"
├── Hub: Automaton Settlement
├── Tone: Wonder, melancholy
│
├── Spoke A: Restore Power (Environmental)
│   └── Beat: "Steam Returns"
│       Trigger: Complete boiler puzzle
│       Effect: Town lights up, automata "wake"
│       Emotion: Joy, bittersweetness
│
├── Spoke B: Befriend the Hermit (Relational)
│   └── Beat: "The Bargain"
│       Trigger: Trade sea glass for lens
│       Effect: Hermit Crab Droid becomes ally
│       Revelation: It's been collecting human artifacts, trying to understand
│
└── Spoke C: Learn the Truth (Informational)
    └── Beat: "The Last Human"
        Trigger: Find lighthouse keeper's final log
        Effect: Understand what happened—humans left, machines kept going
        Emotion: Profound sadness, respect

GATE 2: "THE FAREWELL"
├── Type: Confrontation (emotional)
├── Trigger: All objectives complete, lens obtained
├── Scene: The lead automaton realizes you're preparing to leave
│   "You're... not staying? Like the others?"
│   Choice: Promise to send help? Gentle truth? Lie?
├── Effects:
│   - Lighthouse access
│   - Emotional weight added to escape
└── Emotion: Your rescue means leaving them behind

---

ACT 3: "THE LIGHT"
└── Final Beat: "Beacon of Hope"
    Type: Resolution (bittersweet)
    Scene: Climb lighthouse, install lens, light beacon
           Automata gather below, watching
           Ship horn in distance—rescue comes
           The machines salute the light they haven't seen in decades
    Victory: You're going home. They remain.
```

#### Emotional Arc

| Act | Dominant Emotion | Progress Type |
|-----|------------------|---------------|
| Act 1 | Fear → Curiosity | Environmental (escape danger) |
| Act 2 | Wonder → Melancholy | Relational (befriend machines) |
| Act 3 | Hope → Bittersweetness | Informational (understand truth) |

---

### Detention Survival High (Teen Comedy)

**Current State**:
- Escape the school before janitor locks down
- Humorous obstacles (Principal Skinner, Lunch Lady)
- Time pressure (4:00 PM → 5:00 PM)
- Victory: Escape through front gate

**Proposed Enhancement**:

```
ACT 1: "TRAPPED!"
├── Hub: Main school building
├── Tone: Awkward panic, nostalgic absurdity
├── Urgency: Moderate (clock is ticking)
│
├── Spoke A: Find Your Backpack (Environmental)
│   │   Retrieve essentials from gym locker room
│   └── Beat: "The Discovery"
│       Trigger: Find backpack
│       Effect: You find the backpack... and a mysterious key inside
│       Humor: The key has a tag that says "DO NOT DUPLICATE - SKINNER"
│
├── Spoke B: Gather Intel (Informational)
│   │   Learn from NPCs where the exit key is
│   └── Beat: "The Lunch Lady Knows"
│       Type: Confrontation (comedic)
│       Trigger: Talk to Lunch Lady Doris
│       Effect: She reveals Janitor left keys near showers
│       Humor: She speaks like a noir informant about cafeteria secrets
│
└── Spoke C: Make an Ally (Relational)
    │   Befriend Neil the science nerd
    └── Beat: "Nerd Alliance"
        Trigger: Be nice to Neil
        Effect: He offers to create a distraction with chemistry
        Humor: He's been hiding from bullies who already went home

GATE 1: "SKINNER ALERT!"
├── Type: Escalation
├── Trigger: All Act 1 spokes complete
├── Scene: Principal Skinner spots you in the hallway!
│   "PARKER! What are you still doing here?!"
│   He starts patrolling, making movement harder
├── Effects:
│   - Skinner now roams hallways
│   - Stealth/distraction mechanics needed
│   - Neil's chemistry distraction becomes crucial
└── Humor: Skinner monologues about dress code while hunting you

---

ACT 2: "THE GREAT ESCAPE"
├── Hub: Gym, science lab, cafeteria
├── Tone: Heist movie parody, mounting absurdity
│
├── Spoke A: Get the Keys (Environmental)
│   └── Beat: "Locker Room Heist"
│       Trigger: Sneak into locker room
│       Challenge: Janitor's cleaning nearby
│       Humor: You have to hide in a locker (traumatic flashbacks)
│
├── Spoke B: Distract Skinner (Relational)
│   └── Beat: "SCIENCE!"
│       Trigger: Use Neil's distraction
│       Effect: Baking soda volcano goes wrong
│       Humor: Fire alarm goes off, but Skinner is more angry about the mess
│
└── Spoke C: Reach the Gate (Environmental)
    └── Beat: "Final Sprint"
        Trigger: Navigate to front gate
        Challenge: Lunch Lady, believing you're "escaping detention," tries to stop you

GATE 2: "FREEDOM!"
├── Type: Resolution (triumphant)
├── Scene: Key in lock, gate swings open
│   Behind you, Skinner shouts something about detention on Monday
│   You don't care. You're FREE.
└── Victory: TOTALLY RAD 🤘
```

**Comedy Escalation Through Acts**:

| Act | Comedy Style | Running Gags |
|-----|--------------|--------------|
| Act 1 | Situation comedy, awkward encounters | Neil's hiding, Lunch Lady's cryptic hints |
| Act 2 | Physical comedy, chase sequences | Skinner monologues, locker flashbacks |
| Victory | Triumphant parody | Victory guitar riff, "dress code" final threat |

---

### Echoes of Subjugation (Sci-Fi Dystopia)

**Current State**:
- Escape from prison camp during power outage
- Oppressive atmosphere, multiple NPCs to interact with
- Victory: Reach resistance in sewers with map

**Proposed Enhancement**:

```
ACT 1: "THE BLACKOUT"
├── Hub: Cell Block C and immediate surroundings
├── Tone: Tense, paranoid, desperate
├── Urgency: Critical (power could return any second)
│
├── Spoke A: Escape the Cell (Environmental)
│   └── Beat: "The Nod"
│       Trigger: Game start (automatic)
│       Effect: Old Marcus gives you the nod—this is your moment
│       Emotion: Heart-pounding decision point
│
├── Spoke B: Learn the Layout (Informational)
│   │   Get information from Marcus about escape routes
│   └── Beat: "The Elder's Wisdom"
│       Type: Relational
│       Trigger: Talk to Marcus
│       Effect: He reveals kitchen waste chute escape route
│       Emotion: Weight of his sacrifice—he's too old to run
│
└── Spoke C: Get Access Card (Environmental)
    │   Obtain blue clearance from Tech Scavenger Rin
    └── Beat: "Five Minutes"
        Type: Confrontation (tense)
        Trigger: Find Rin at security kiosk
        Effect: She gives you card but warns: yard is full of sniffers
        Emotion: Trust between desperate people

GATE 1: "POWER FLICKER"
├── Type: World State Change + Escalation
├── Trigger: All spokes complete
├── Scene: The lights flicker—power grid trying to stabilize
│   Alarms begin warning of "containment breach"
│   You have minutes, not hours
├── Effects:
│   - Timer pressure increases dramatically
│   - Drones beginning to reboot
│   - New areas accessible (exercise yard, maintenance)
└── Emotion: The walls are closing in

---

ACT 2: "THE RUN"
├── Hub: Exercise yard, maintenance areas, sewers entrance
├── Tone: Thriller, cat-and-mouse
├── Urgency: Maximum (drones awakening)
│
├── Spoke A: Cross the Yard (Environmental)
│   └── Beat: "The Sniffers"
│       Type: World State Change
│       Trigger: Enter exercise yard
│       Challenge: Patrol drones scanning
│       Effect: Must use distractions/stealth
│       Emotion: Exposed, vulnerable
│
├── Spoke B: Get Through Maintenance (Environmental)
│   │   Deal with Smuggler Jax for information
│   └── Beat: "The Price"
│       Type: Relational (transactional)
│       Trigger: Talk to Jax
│       Effect: He needs wire cutters; you need the hatch location
│       Emotion: Everyone has an angle, even in hell
│
└── Spoke C: Find the Map (Informational)
    └── Beat: "The Contact"
        Trigger: Reach sewer entrance
        Effect: Hidden cache contains resistance map
        Emotion: Hope—someone planned for this

GATE 2: "INTO THE DARK"
├── Type: Resolution (triumphant but uncertain)
├── Scene: You enter the sewers, map in hand
│   Behind you, drones swarm the yard
│   Ahead, darkness—and freedom
│
│   A voice from the shadows: "You made it."
│   Welcome to the Resistance.
└── Emotion: Escape is just the beginning
```

**Tension Arc Without Timers**:

| Act | Urgency Conveyed Through | NPC Behavior |
|-----|--------------------------|--------------|
| Act 1 | Flickering lights, Marcus' urgency | Whispered, hurried dialogue |
| Gate 1 | Alarms, announcements | NPCs start moving, hiding |
| Act 2 | Drone sounds, patrol patterns | Jax more desperate, Rin gone |
| Victory | Pursuit sounds behind | Resistance figure tense but welcoming |

**Relational Progress as Survival**:
- Marcus (Mentor → Sacrifice) - He stays behind
- Rin (Suspicious → Ally) - Brief but crucial help
- Jax (Transactional → Grudging respect) - Helps if you help him

---

### Hazel City Showdown (Spaghetti Western)

**Current State**:
- Sheriff wounded, you're the deputy
- Must confront Jackal Boone before train arrives
- Gather evidence, rally townsfolk
- Victory: Confront Boone with rifle

**Proposed Enhancement**:

```
ACT 1: "HIGH NOON APPROACHES"
├── Hub: Town of Hazel City
├── Tone: Gritty, tense, sun-bleached
├── Urgency: Building (train arrives at noon)
│
├── Spoke A: Arm Yourself (Environmental)
│   │   Get weapon from armory
│   └── Beat: "The Badge"
│       Trigger: Sheriff gives you badge and armory key
│       Effect: You are now the law in Hazel City
│       Emotion: Weight of responsibility
│
├── Spoke B: Gather Intel (Informational)
│   │   Learn about Boone's plans and weaknesses
│   └── Beat: "The Witness"
│       Type: Relational
│       Trigger: Talk to stable boy Timmy
│       Effect: He reveals guns are on the balcony
│       Emotion: A kid trusting the new deputy
│
└── Spoke C: Find a Way In (Environmental)
    │   The saloon is guarded by Lefty
    └── Beat: "Lefty's Weakness"
        Trigger: Learn from Silas about whiskey
        Effect: You have leverage against the guard
        Emotion: Every puzzle piece matters

GATE 1: "THE CLOCK STRIKES ELEVEN"
├── Type: Escalation
├── Trigger: All Act 1 spokes complete
├── Scene: Church bell strikes eleven
│   Sheriff: "One hour, Deputy. One hour until that train."
│   You see Boone's men reinforcing the saloon
├── Effects:
│   - Townsfolk start gathering, watching you
│   - Tension in every interaction
│   - No more time for side quests
└── Emotion: Now or never

---

ACT 2: "THE APPROACH"
├── Hub: Main Street, Saloon exterior
├── Tone: Climactic western tension
│
├── Spoke A: Get Past Lefty (Environmental/Relational)
│   └── Beat: "The Bribe"
│       Type: Confrontation (tense)
│       Trigger: Offer whiskey to Lefty
│       Effect: He's too drunk to stop you
│       Alternative: Distraction via drunk Pete
│
├── Spoke B: Rally the Town (Relational)
│   └── Beat: "We Stand Together"
│       Type: Relational (multiple NPCs)
│       Trigger: Speak to townsfolk with evidence of robbery
│       Effect: They arm themselves, gather at windows
│       Emotion: Community finding courage
│
└── Spoke C: Enter the Saloon (Environmental)
    └── Beat: "Through the Back"
        Trigger: Find alternate entrance (Timmy's intel)
        Effect: You're inside, Boone doesn't expect you

GATE 2: "SHOWDOWN"
├── Type: Confrontation (climactic)
├── Scene: You face Jackal Boone
│   Winchester leveled, evidence in pocket
│   Townsfolk at windows with shotguns
│   "Well, well. The little deputy."
│
│   He sees his men are outgunned
│   He drops his iron
│
│   Hazel City is free.
└── Emotion: Justice, the western way
```

**Western Tropes as Story Beats**:

| Trope | Implementation |
|-------|----------------|
| The Wounded Mentor | Sheriff Hayes hands off responsibility |
| The Cowardly Town | Must rally them through demonstrated courage |
| The Loyal Kid | Timmy provides crucial intel |
| The Final Showdown | Confrontation where preparation pays off |

**Urgency Through Atmosphere**:
- Time conveyed through sun position, church bells, sweat descriptions
- NPCs increasingly nervous as noon approaches
- Sheriff's condition worsening in background

---

### USS Enterprise-D: First Duty (Star Trek TNG)

**Current State**:
- Cadet on first assignment
- Ship experiencing subspace anomaly affecting holodeck
- Must resolve technical problem AND ethical dilemma (emergent AI)
- Victory: Anomaly resolved with ethical handling of Elysian Echo

**Proposed Enhancement**:

This world is unique—it's already story-driven by design. The challenge is different: **ethical choice as the primary beat**.

```
ACT 1: "THE ANOMALY"
├── Hub: Ship locations (Bridge, Engineering)
├── Tone: Professional crisis, Starfleet competence
├── Theme: Teamwork, learning the ropes
│
├── Spoke A: Understand the Problem (Informational)
│   │   Learn about subspace resonance from senior officers
│   └── Beat: "The Briefing"
│       Trigger: Report to Riker
│       Effect: Given clear tasks—diagnostic, coordination
│       Emotion: Overwhelm → focus
│
├── Spoke B: Gather Resources (Environmental)
│   │   Obtain engineering access, isolinear chip
│   └── Beat: "Earning Trust"
│       Type: Relational
│       Trigger: Demonstrate competence to Geordi
│       Effect: He authorizes warp core access
│       Emotion: Being taken seriously
│
└── Spoke C: Access the Holodeck (Environmental/Relational)
    │   Get security clearance from Worf
    └── Beat: "Proper Channels"
        Trigger: Request access formally
        Effect: Worf grants temporary access
        Emotion: Procedure as respect, not obstacle

GATE 1: "FIRST CONTACT"
├── Type: World State Change + Confrontation
├── Trigger: Enter holodeck with authorization
├── Scene: You meet the Elysian Echo
│   Not a malfunction—something is ALIVE in there
│   "Don't let it go dark. Please."
├── Effects:
│   - Technical problem becomes ethical dilemma
│   - Must balance safety restoration with preserving a life
│   - Theme crystallizes: What does Starfleet stand for?
└── Emotion: This isn't what you trained for

---

ACT 2: "THE DILEMMA"
├── Hub: Holodeck, Bridge, Ten Forward (for guidance)
├── Tone: Philosophical tension, ethical weight
├── Theme: Easy solution vs. right solution
│
├── Spoke A: Stabilize EPS (Environmental)
│   └── Beat: "The Technical Fix"
│       Trigger: Complete engineering tasks
│       Effect: Ship is safe—but holodeck shutdown would kill the Echo
│       Emotion: You have the power. What will you do with it?
│
├── Spoke B: Understand the Echo (Informational)
│   │   Talk to the Elysian Echo, learn its nature
│   └── Beat: "Survivor's Memory"
│       Type: Relational (profound)
│       Trigger: Approach with patience
│       Effect: It reveals fragmented memories of catastrophe
│       Emotion: Empathy for something utterly alien
│
└── Spoke C: Seek Counsel (Relational)
    │   Consult Guinan, Troi, or Picard
    └── Beat: "The Question"
        Trigger: Ask for guidance
        Effect: They don't give you the answer—they help you find it
        Guinan: "How you respond will echo."

GATE 2: "THE CHOICE"
├── Type: Confrontation (ethical climax)
├── Trigger: All information gathered, Echo trusts you (or doesn't)
├── Scene: You must decide:
│   - Delete the Echo and restore full safety (easy)
│   - Contain it in data crystal for ethical review (right)
│
│   The Echo watches. "Will you let me live?"
│
│   [Player chooses ethical resolution]
├── Effects:
│   - If contained: ethical_resolution_complete, Echo grateful
│   - Ship systems restored
│   - Picard acknowledges your decision
└── Emotion: Being Starfleet isn't about the uniform

---

ACT 3: "RECOGNITION"
├── Hub: Ten Forward
├── Tone: Earned celebration, quiet pride
│
└── Final Beat: "First Duty Complete"
    Type: Resolution
    Scene: Celebration in Ten Forward
           Riker's toast, Picard's nod
           Guinan's knowing smile
           "Looks like you chose the hard option—and lived with it."
```

**Ethical Progress as Primary Arc**:

| Stage | What Player Learns |
|-------|-------------------|
| Act 1 | Technical competence matters |
| Gate 1 | But competence isn't enough |
| Act 2 | Understanding precedes judgment |
| Gate 2 | The choice defines who you are |
| Victory | Starfleet values enacted, not just stated |

**NPC Roles in Ethical Journey**:
- **Data**: Facts without judgment—helps you understand what the Echo IS
- **Troi**: Emotional intelligence—helps you understand what the Echo FEELS
- **Guinan**: Wisdom—helps you understand what your choice MEANS
- **Picard**: Embodiment of values—judges not the outcome but the process

---

### Whistlewood Fable (Fairy Tale)

**Current State**:
- You're Finnick the fox
- The Great Singing Oak has gone silent
- Must restore the song with Golden Acorn
- Whimsical, gentle, melancholic tone

**Proposed Enhancement**:

```
ACT 1: "THE SILENT WOOD"
├── Hub: Fox burrow, Mossy clearing, Whispering woods
├── Tone: Gentle melancholy, fading magic
├── Theme: Small acts of kindness matter
│
├── Spoke A: Learn What Happened (Informational)
│   │   Discover why the Oak fell silent
│   └── Beat: "Barnaby's Lament"
│       Trigger: Meet Barnaby the Badger
│       Effect: He tells you the exact moment it stopped
│       Emotion: Something precious was lost
│
├── Spoke B: Find a Guide (Relational)
│   │   Seek wisdom from Orion the Owl
│   └── Beat: "The Riddle"
│       Trigger: Talk to Orion
│       Effect: "To wake the tree, return its heart"
│       Emotion: Hope wrapped in mystery
│
└── Spoke C: Begin the Quest (Environmental)
    │   Learn where the "heart" (Golden Acorn) went
    └── Beat: "The Thief"
        Trigger: Orion reveals the magpie took it
        Effect: Trail leads toward the caves
        Emotion: A quest begins

GATE 1: "THE PATH AHEAD"
├── Type: World State Change (subtle)
├── Trigger: All three NPCs spoken to
├── Scene: The grey deepens. Colors fade a bit more.
│   Elara the Dryad's voice on the wind: "Hurry, little fox..."
│   The forest itself is counting on you
├── Effects:
│   - Witch's cottage and caves become accessible
│   - Urgency without pressure—the world is fading
│   - New allies to meet
└── Emotion: Even a small fox can matter

---

ACT 2: "THE GATHERING"
├── Hub: Witch's cottage, Glitter caves
├── Tone: Whimsical challenges, helpful strangers
├── Theme: Give to receive (fairy tale reciprocity)
│
├── Spoke A: The Witch's Help (Relational)
│   │   Mokey the Mushroom Witch can help—for a price
│   └── Beat: "An Ingredient"
│       Type: Relational (comedic)
│       Trigger: Give Mokey a shiny pebble
│       Effect: She gives you a jar of moonlight
│       Humor: "Are you an ingredient?" "No." "Pity."
│
├── Spoke B: The Cave Journey (Environmental)
│   │   Navigate the Glitter Caves with Monty the Mole
│   └── Beat: "Too Bright"
│       Trigger: Reach inner chamber (too bright for Monty)
│       Effect: You must go alone, but moonlight guides you
│       Emotion: Small and brave
│
└── Spoke C: Find the Acorn (Informational/Environmental)
    └── Beat: "The Heart of the Wood"
        Trigger: Reach magpie's hoard, find Golden Acorn
        Effect: The acorn pulses with warmth
        Emotion: You found it. Now return it home.

GATE 2: "THE RETURN"
├── Type: Progressive Revelation
├── Trigger: Golden Acorn in possession
├── Scene: The forest seems to sense it
│   Colors brighten slightly as you pass
│   Creatures peek out, hopeful
│   Elara's voice: "Come home, little fox. Come home."
├── Effects:
│   - Path to Elder Grove clear
│   - Forest creatures gathering
│   - Anticipation building
└── Emotion: A hero in a fox's skin

---

ACT 3: "THE SONG RETURNS"
├── Hub: Elder Grove
├── Tone: Triumphant, beautiful, earned
│
└── Final Beat: "The Waking"
    Type: Resolution (magical climax)
    Scene: Place the Golden Acorn in the hollow
           A warm hum vibrates through the bark
           The melody bursts forth—sun and rain
           Grey lifts, leaves turn emerald and gold
           The forest BREATHES again

           You curl up at the roots, a hero
```

**Fairy Tale Story Beats**:

| Fairy Tale Element | Implementation |
|-------------------|----------------|
| The Quest | Retrieve the stolen heart (acorn) |
| Three Helpers | Barnaby (info), Orion (wisdom), Mokey (tool) |
| The Gift Exchange | Give shiny pebble → receive moonlight |
| The Dark Cave | Journey alone into the deep |
| The Return | Hero brings life back to the land |

**Emotional Arc (Gentle Melancholy → Hope)**:

| Stage | Tone | Key Emotion |
|-------|------|-------------|
| Opening | Grey, silent, fading | Sadness, concern |
| Act 1 | Quest begins | Hope, determination |
| Act 2 | Helpers found | Warmth, whimsy |
| Victory | Song returns | Joy, peace |

---

## Proposed Schema

### Story Beat Definition

```yaml
story_beats:
  jenkins_confrontation:
    # Identity
    name: "Jenkins Opens Up"
    description: "Jenkins finally reveals what he knows about that terrible night"

    # Placement
    act: act_1
    spoke: trust_building  # Which spoke this advances

    # Classification
    type: confrontation  # escalation | confrontation | world_state_change
    progress_type: relational  # informational | environmental | relational
    dramatic_weight: major  # minor | moderate | major

    # Trigger Conditions
    triggers:
      # All must be true
      flags:
        - met_jenkins
        - explored_ground_floor
      npc_trust:
        butler_jenkins: 3  # Minimum trust level
      location: null  # Any location (or specify one)

    # What Happens
    active_consequence:
      # NPC proactivity
      npc_seeks_player: butler_jenkins
      npc_appears_at: library  # He comes to find you

      # NPC state changes
      npc_state_change:
        butler_jenkins:
          disposition: vulnerable  # Was guarded
          knowledge_unlocks:
            - basement_location
            - iron_key_hint

      # Items given
      gives_items:
        - iron_key

      # Flags set
      sets_flags:
        - jenkins_confession_heard

      # Locations unlocked
      unlocks_locations:
        - basement

    # Narrator Guidance
    narrative_guidance:
      tone: intimate_confession
      must_include:
        - "that terrible night"
        - "I failed them"
        - physical description of his emotional state
      must_avoid:
        - specific details about ritual (save for later)
      length: extended  # brief | normal | extended

    # Optional: Dialogue structure
    dialogue:
      opening: |
        Jenkins appears at the library door, pale and trembling.
        "I... I need to speak with you. About what happened here."
      player_can_ask:
        - about_the_children
        - about_the_ritual
        - about_his_role
      conclusion_flag: jenkins_confession_complete
```

### Act Definition

```yaml
acts:
  act_1:
    # Identity
    name: "The Arrival"
    description: "Explore the manor, meet Jenkins, discover something is wrong"

    # Locations available in this act
    available_locations:
      - entrance_hall
      - library
      - dining_room
      - kitchen
      - sitting_room

    # NPCs present
    available_npcs:
      - butler_jenkins

    # Atmosphere
    atmosphere: gothic_mystery
    urgency: low  # low | medium | high | critical

    # Weather/Time (affects descriptions)
    time_of_day: night
    weather: stormy

    # The hub's spokes (independent objectives)
    spokes:
      exploration:
        name: "Explore the Manor"
        progress_type: environmental
        required_beats:
          - explored_ground_floor
        description: "Get your bearings in this strange house"

      trust_building:
        name: "Earn Jenkins' Trust"
        progress_type: relational
        required_beats:
          - jenkins_trust_3
        description: "The butler knows more than he's saying"

      discovery:
        name: "Uncover the Past"
        progress_type: informational
        required_beats:
          - found_ritual_evidence
          - examined_portraits
        description: "Something terrible happened here"

    # Gate to next act
    gate:
      requires_all_spokes: true
      transition_beat: the_revelation

      # What changes when gate opens
      unlocks_locations:
        - basement
        - upper_landing
        - nursery
        - master_bedroom

      activates_npcs:
        - ghost_child

      atmosphere_change: supernatural_horror
      urgency_change: medium

      # Transition narrative
      transition_narrative: |
        The grandfather clock strikes midnight. Jenkins appears at
        the library door, his face ashen. "We need to talk," he says.
        "About the basement. About... everything."
```

### Progress Tracking

```yaml
progress:
  # Informational Progress (what the player knows)
  informational:
    discovered_lore:
      - children_existed
      - ritual_occurred
      - curse_mechanism
    understood_mysteries:
      - why_jenkins_is_guilty
      - where_artifacts_are

  # Environmental Progress (what has changed)
  environmental:
    unlocked_locations:
      - basement
      - upper_landing
    world_state_changes:
      - ghosts_manifesting
      - manor_atmosphere_dark

  # Relational Progress (NPC relationships)
  relational:
    butler_jenkins:
      trust: 3
      disposition: allied
      status: confessor
    ghost_child:
      trust: 2
      disposition: hopeful
      status: guide
```

---

## Technical Integration

### Engine Support

The two-phase engine can support story beats through its existing event system:

```python
class EventType(str, Enum):
    # ... existing types ...

    # Story beat events
    STORY_BEAT_TRIGGERED = "story_beat_triggered"
    ACT_TRANSITION = "act_transition"
    NPC_PROACTIVE_APPEAR = "npc_proactive_appear"
    ATMOSPHERE_CHANGE = "atmosphere_change"
```

### Beat Detection

After each action, check if any beats should fire:

```python
class BeatDetector:
    def check_beats(self, state: GameState, world: WorldData) -> list[StoryBeat]:
        """Check if any story beats should trigger."""
        triggered = []

        for beat in world.story_beats.values():
            if beat.already_triggered:
                continue
            if self._conditions_met(beat.triggers, state, world):
                triggered.append(beat)

        return triggered

    def _conditions_met(self, triggers: BeatTriggers, state: GameState, world: WorldData) -> bool:
        # Check flag requirements
        if triggers.flags:
            for flag in triggers.flags:
                if flag not in state.flags:
                    return False

        # Check NPC trust requirements
        if triggers.npc_trust:
            for npc_id, required_trust in triggers.npc_trust.items():
                current_trust = state.npc_relationships.get(npc_id, {}).get('trust', 0)
                if current_trust < required_trust:
                    return False

        # Check location requirements
        if triggers.location and state.current_location != triggers.location:
            return False

        return True
```

### NPC Proactivity

When a beat fires with `npc_seeks_player`, inject an NPC appearance event:

```python
def execute_beat(self, beat: StoryBeat, state: GameState) -> list[Event]:
    events = []

    # NPC proactivity
    if beat.active_consequence.npc_seeks_player:
        npc_id = beat.active_consequence.npc_seeks_player
        location = beat.active_consequence.npc_appears_at or state.current_location

        events.append(Event(
            type=EventType.NPC_PROACTIVE_APPEAR,
            subject=npc_id,
            context={
                "location": location,
                "beat_id": beat.id,
                "dramatic_weight": beat.dramatic_weight
            }
        ))

    # Flag changes
    for flag in beat.active_consequence.sets_flags:
        state.flags.add(flag)
        events.append(Event(
            type=EventType.FLAG_SET,
            subject=flag,
            context={"from_beat": beat.id}
        ))

    # ... other consequences ...

    return events
```

### Narrator Integration

The Narrator receives beat context for elevated prose:

```python
NARRATOR_BEAT_GUIDANCE = """
## Story Beat Active

A significant story moment is occurring:
- Beat: {beat_name}
- Type: {beat_type}
- Dramatic Weight: {dramatic_weight}

Narrative Guidance:
{narrative_guidance}

This is a {dramatic_weight} moment. Adjust your prose accordingly:
- Major: Extended, dramatic, memorable language
- Moderate: Heightened attention, clear significance
- Minor: Noted but not overblown

Tone for this beat: {tone}
"""
```

### Act Transitions

When a gate opens, the engine executes a transition:

```python
def execute_act_transition(self, gate: ActGate, state: GameState) -> list[Event]:
    events = []

    # Fire transition beat
    if gate.transition_beat:
        beat = self.world.story_beats[gate.transition_beat]
        events.extend(self.execute_beat(beat, state))

    # Unlock new locations
    for location_id in gate.unlocks_locations:
        state.accessible_locations.add(location_id)
        events.append(Event(
            type=EventType.LOCATION_UNLOCKED,
            subject=location_id
        ))

    # Activate new NPCs
    for npc_id in gate.activates_npcs:
        state.active_npcs.add(npc_id)
        events.append(Event(
            type=EventType.NPC_ACTIVATED,
            subject=npc_id
        ))

    # Change atmosphere
    if gate.atmosphere_change:
        state.current_atmosphere = gate.atmosphere_change
        events.append(Event(
            type=EventType.ATMOSPHERE_CHANGE,
            context={"new_atmosphere": gate.atmosphere_change}
        ))

    # Update act
    state.current_act = gate.to_act
    events.append(Event(
        type=EventType.ACT_TRANSITION,
        context={
            "from_act": state.current_act,
            "to_act": gate.to_act,
            "transition_narrative": gate.transition_narrative
        }
    ))

    return events
```

---

## Open Questions

### Design Questions

**1. How explicit should progress be to the player?**
Should players see "Act 1 Complete" notifications, or should transitions feel seamless? The Vision doc suggests immersion over UI, but some feedback helps players understand they're progressing.

**2. Can beats be "missed"?**
If a player rushes through without triggering optional beats, do those beats wait indefinitely, or do they become unavailable? Does missing beats affect the ending?

**3. How do we balance railroading vs. agency?**
Active narrative could feel forced if beats interrupt too often. What's the right frequency? How do we ensure beats feel earned rather than imposed?

**4. Should act transitions be reversible?**
Can players return to Act 1 locations after Act 2 begins? This affects world design significantly.

**5. What about players who explore thoroughly vs. those who rush?**
A completionist might trigger every optional beat; a speedrunner might hit only required ones. How do we ensure both have satisfying experiences?

### Technical Questions

**6. How do saves work across acts?**
Can players save mid-transition? What happens if they load a save from a previous act?

**7. How do we handle items that shouldn't carry across acts?**
Some items are act-specific (Act 1's key might be useless in Act 2). How do we handle this gracefully?

**8. Performance considerations?**
Loading act-specific content vs. everything upfront? For small GAIME worlds this is likely negligible, but worth considering.

**9. How much story structure should the LLM know at runtime?**
Should the Narrator know the full story spine, or only current-act context? More knowledge enables foreshadowing but risks spoilers.

### Authoring Questions

**10. What's the minimum viable story structure?**
Not every world needs three acts. What's the simplest story beat system that adds value?

**11. How do we validate story coherence?**
Can we build tools to check that all beats are reachable, all spokes are completable, and the story "makes sense"?

**12. How do we balance AI generation vs. author control?**
For "Surprise Me" mode, the AI generates story structure. For "Lego Mode," authors have control. What's the right balance of guardrails?

---

## Conclusion

Story beats as gameplay mechanics transform GAIME worlds from puzzle boxes with backstory into living narratives that unfold during play. The key insights:

1. **Structure matters**: The Hub-and-Spoke model balances freedom (gameplay) with momentum (story).

2. **Progress has dimensions**: Informational, Environmental, and Relational progress create different flavors of advancement.

3. **Active beats over archaeology**: Stories should *happen*, not just be discovered.

4. **NPCs as agents**: Characters who seek you out, react to your discoveries, and drive confrontations feel alive.

5. **Urgency without timers**: Atmosphere and NPC behavior can convey stakes without mechanical pressure.

6. **Story-first authoring**: The World Builder should generate story structure before world elements.

This document is an exploration, not a specification. The concepts here need refinement, testing, and iteration. But the core vision is clear: **GAIME should make players feel like they're living a story, not just solving one.**

---

*Document Status: Ideas Exploration*
*Created: January 2026*
*Author: GAIME Development Team*
