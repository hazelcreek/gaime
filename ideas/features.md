# GAIME Feature Ideas

This document is the **feature backlog** - a collection of ideas and enhancements for GAIME.

> **Progress Tracking**: See [planning/roadmap.md](../planning/roadmap.md) for implementation status and priorities.

---

## Narrative & Immersion

### Player Character Backstory System

The main character should have a rich background story defined during world building to increase immersion. This backstory can be:
- Slowly revealed through NPC dialogues during gameplay
- Used to motivate specific skills or abilities the player has
- Referenced by NPCs who have history with the character
- Unlocked through interactive flashback sequences

### Environmental Storytelling

Subtle details in location descriptions that reveal world history and lore when examined closely. Objects and environments tell stories without explicit exposition.

### Emotional State Tracking

Track the player character's emotional state (fear, confidence, anger, etc.) which affects:
- Narration style and tone
- Available dialogue options
- How NPCs perceive and react to the player

### Consequences & Ripple Effects

Actions have delayed consequences that surface later in the game. Helping someone early might lead to unexpected aid later; being rude might close off opportunities.

### Multiple Endings / Branching Paths

Different outcomes based on cumulative choices and actions throughout the game. Major decisions create meaningful divergence in the story.

### Narrative Recap on Resume

"Previously on..." style summary when returning to a saved game, helping players remember context and recent events.

### Interactive Flashbacks

Playable memory sequences tied to the player's backstory that unlock as the game progresses, revealing character history through gameplay.

---

## Puzzles & Challenges

### Explicit Puzzle System

First-class puzzle definitions in YAML with:
- Clear conditions and solutions
- Multi-step puzzle sequences
- Dependency tracking between puzzles
- Hint definitions at multiple levels

### Puzzle Validation

Developer tools to verify puzzle design:
- Check that puzzles are solvable
- Detect unreachable puzzle states
- Verify hint availability
- Validate puzzle dependencies

### Exit & Location Puzzle Integration

Enhanced exit/location mechanics for puzzle design:
- Locked exits with specific unlock conditions
- Conditional exit visibility (hidden until discovered)
- Multi-step sequences to access areas
- Exit state tracking (opened, locked, blocked)

### Narrative Puzzle Weaving

Integrate puzzles into storytelling:
- LLM constraints to not reveal puzzle solutions
- Contextual hints that feel natural in dialogue
- Puzzle progress tracked in narrative memory
- NPCs react to puzzle-solving attempts

---

## Audio & Visual

### Audio Narration

Text-to-speech narration of game narrative, with configurable voice settings and the ability to toggle on/off.

### Background Music

Ambient music that matches the current location's atmosphere and adapts to game events (tension during danger, calm during exploration).

### Sound Effects

Audio feedback for actions, environmental sounds, and atmospheric effects to enhance immersion.

### Varied Storytelling Tone

More variation in the tone of narration - serious, humorous, mysterious, etc. - configurable per world or adapting to game events.

### Visual Style Variation

More variety in image generation styles - different art styles, color palettes, and visual treatments that can be configured per world or location.

---

## World State & Dynamics

### Extensive World State Management

NPCs and environments respond to game events:
- NPCs behave differently after certain actions or events
- Locations change based on player actions
- World state persists and evolves throughout gameplay

### Dynamic Time & Weather System

Time of day and weather conditions that affect:
- Atmosphere and location descriptions
- NPC availability (some appear only at certain times)
- Available actions (weather affects outdoor activities)

### Ambient Events

Periodic atmospheric descriptions and minor events that make the world feel alive without requiring player action.

---

## NPCs & Dialogue

### Dialog Mode with NPCs

A dedicated conversation mode where players can:
- Type questions directly to NPCs
- Have multi-turn conversations
- Affect game progress through dialogue choices

### Smarter NPC Behavior

NPCs with improved intelligence:
- Behave appropriately based on whether they know the player character
- Remember previous interactions
- Respond less repetitively with more varied dialogue
- Have moods and attitudes that affect conversations

### Reputation & Relationship System

Track how NPCs feel about the player based on interactions:
- Affects dialogue options and NPC cooperation
- Can open or close questlines and information access
- NPCs may gossip, affecting relationships with others

---

## Items & Discovery

### Sophisticated Item Discovery

More varied ways to find items:
- Some items are visible and obvious in room descriptions
- Some items are hidden and require specific actions (open drawer, look under bed)
- Environmental clues hint at hidden items
- Discovering items can involve multi-step processes

### Inventory Examination Depth

Detailed examination of items reveals:
- Additional information and lore
- Hidden features or compartments
- Clues and hints for puzzles
- Connections to the player's backstory

---

## UI & Player Experience

### Player Journal / Notes

Automatic or manual recording of:
- Important discoveries and clues
- NPC information and conversation summaries
- Key events and locations visited
- Player notes and reminders

### Adaptive Hint System

Contextual hints that appear if the player seems stuck:
- Subtle enough to not break immersion
- Escalating from vague to more specific if needed
- Can be toggled off for hardcore players

---

## Developer Tools

### Debug Mode

Comprehensive debugging capabilities for:
- **Gameplay**: View game state, teleport, spawn items, trigger events
- **World Building**: Validate world files, preview content, test connections
- **Image Generation**: Preview prompts, regenerate images, test styles

---

## Future Exploration

Ideas that need more research before becoming concrete features:

- **Modding Support** - Community-created worlds with easy sharing
- **Mobile App** - Native mobile experience
- **Voice Input** - Speak commands instead of typing
- **Procedural World Generation** - AI-generated worlds from simple prompts (aligns with "Surprise Me" World Builder mode)
- **Achievement System** - Track milestones and accomplishments (keep minimal per Vision's "no RPG complexity")
- **Accessibility Features** - Screen reader support, colorblind modes, font scaling

---

## Out of Scope per Vision

The following ideas conflict with the [Vision document](../docs/VISION.md) and are not planned for implementation:

- **Multiplayer / Shared Worlds** - Vision explicitly states "Single-player only" as a key constraint. GAIME is designed as a solo narrative experience.

- **AI Dungeon Master Personality** - Configurable narrator personalities could conflict with the curated world experience. The Vision emphasizes that each world has its own authored tone and style, rather than a generic AI personality layer.

See [docs/VISION.md](../docs/VISION.md) for the full product and technical vision.

---

*Last updated: December 2025*
