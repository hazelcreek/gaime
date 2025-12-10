# GAIME Development Roadmap

This document tracks development progress across phases, aligned with the [Vision](../docs/VISION.md).

> **Source of Truth**: This is the primary progress tracker. See [ideas/features.md](../ideas/features.md) for the full feature backlog.

---

## Vision Alignment

The roadmap is organized around **experience goals** from the Vision document:

1. **Core Promise**: "Finishing a great short story you played through"
2. **Safety Net**: "No unwinnable states, no player death"
3. **Fair Puzzles**: Challenging but not frustrating
4. **Guided Freedom**: Story structure with player agency

---

## Phase Overview

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation Complete | 🟡 In Progress |
| 2 | Safety & Fairness | ⚪ Planned |
| 3 | Puzzle System | ⚪ Planned |
| 4 | Story Structure | ⚪ Planned |
| 5 | World Builder Enhancement | ⚪ Planned |
| 6 | Living World | ⚪ Planned |
| 7 | Player Experience | ⚪ Planned |

**Legend**: ✅ Complete | 🟡 In Progress | ⚪ Planned

---

## Phase 1: Foundation Complete

Complete foundational features that are partially implemented.

### Audio System
- [x] Menu music with track selection
- [x] Mute toggle with localStorage persistence
- [x] Fade transitions
- [ ] World-specific background music
- [ ] Location-based ambient sounds

### Debug & Developer Tools
- [x] State overlay (view game state)
- [x] LLM debug modal (view prompts/responses)
- [ ] Teleport command
- [ ] Item spawn command
- [ ] Flag trigger command

### NPC Narrative Memory
- [x] Encounter tracking
- [x] Topics discussed
- [x] Player/NPC dispositions
- [x] Notable moments
- [ ] More varied dialogue generation

### World State Management
- [x] Flag-based mechanics
- [x] NPC trust levels
- [x] NPC location changes via triggers
- [x] Conditional NPC appearances
- [ ] Location state changes

---

## Phase 2: Safety & Fairness

*Vision requirement: "No unwinnable states, no player death" - engine must protect game integrity.*

This phase ensures every world is completable and player-friendly.

### Unwinnable State Prevention
- [ ] Action validation layer in engine
- [ ] In-world rejection narratives (not error messages)
- [ ] Game state rollback detection

### Key Item Protection
- [ ] `critical: true` flag for quest items in items.yaml
- [ ] Engine blocks destruction of critical items
- [ ] Narrative explanations for blocked actions ("The letter is too precious to burn")

### Death Prevention
- [ ] Narrative deflection for lethal actions
- [ ] No "game over" states - only setbacks
- [ ] Graceful handling of dangerous player choices

### Exit & Path Validation
- [ ] Ensure all required exits are reachable
- [ ] Validate victory path is always accessible
- [ ] World Builder warns about unreachable areas

---

## Phase 3: Puzzle System

*Vision requirement: "Fair puzzles" - challenging enough to satisfy, not so obscure they frustrate.*

Explicit puzzle modeling with validation and narrative integration.

### Explicit Puzzle Definitions
- [ ] Puzzle schema in YAML (conditions, solutions, hints)
- [ ] Multi-step puzzle sequences
- [ ] Puzzle dependency graphs

### Exit & Location Enhancements
- [ ] Locked exits with unlock conditions
- [ ] Conditional exit visibility
- [ ] Exit-specific descriptions and state

### Puzzle Validation
- [ ] Validator checks puzzles are solvable
- [ ] Detect unreachable puzzle states
- [ ] Hint availability verification
- [ ] Fairness scoring (obscurity detection)

### Narrative Integration
- [ ] LLM constraints to protect puzzle solutions
- [ ] Contextual hint system
- [ ] Puzzle progress in narrative memory

---

## Phase 4: Story Structure

*Vision requirement: "Guided freedom" - players feel free to explore, but story structure is protected.*

Story arc modeling with victory path protection.

### Story Progression Model
- [ ] Act/chapter structure in world.yaml
- [ ] Progression tracking beyond flags
- [ ] Story beat validation

### Victory Path
- [ ] Victory path always reachable (validated)
- [ ] Multiple victory conditions (optional)
- [ ] Ending variations based on journey

### Player Backstory
- [ ] Backstory definition in world.yaml
- [ ] Backstory reveals through NPC dialogue
- [ ] Skills/abilities from backstory

### Emotional State Tracking
- [ ] Track player character's emotional state (fear, confidence, anger, etc.)
- [ ] Emotional state affects narration style and tone
- [ ] Emotional state affects available dialogue options
- [ ] NPCs perceive and react to player's emotional state

### Consequences & Ripple Effects
- [ ] Delayed consequence system
- [ ] Action memory for callbacks
- [ ] Branching based on past choices

---

## Phase 5: World Builder Enhancement

*Vision requirement: Two AI personalities - creative World Builder and disciplined Game Master.*

### "Surprise Me" Mode
- [ ] Author provides minimal input (theme, style hints)
- [ ] AI invents everything (backstories, characters, puzzles)
- [ ] Author can play their own world spoiler-free
- [ ] Magic: discover plot twists you didn't anticipate

### "Lego" Mode
- [ ] Step-by-step construction with AI assistance
- [ ] Author guides, AI generates options
- [ ] For modifying existing worlds or precise control

### World Validation Tools
- [ ] Completability check (victory reachable)
- [ ] Fairness check (puzzles not obscure)
- [ ] Consistency check (no orphan references)

### Historical World Research (Future)
- [ ] AI researches authentic settings
- [ ] Models interactive stories on real foundations
- [ ] Revolutionary Paris, Ancient Rome, etc.

---

## Phase 6: Living World

*Lower priority - dynamics are nice but not core to "short story" goal.*

### Time & Weather System
- [ ] Time progression model
- [ ] Time-based NPC schedules
- [ ] Weather effects on gameplay

### Ambient Events
- [ ] Random atmospheric events
- [ ] Location-specific ambiance
- [ ] Event triggers based on state

### Advanced World State
- [ ] Location appearance changes
- [ ] Persistent world modifications
- [ ] Cross-location effects

---

## Phase 7: Player Experience

Quality of life and engagement features.

### Player Journal
- [ ] Automatic discovery logging
- [ ] NPC conversation summaries
- [ ] Manual note-taking

### Adaptive Hint System
- [ ] Stuck detection
- [ ] Escalating hint levels
- [ ] Hint toggle for hardcore mode

### Visual Enhancements
- [x] Per-world art style configuration (MPA-based style presets)
- [ ] More image generation variety
- [ ] UI theme variations

---

## Future Exploration

Ideas requiring more research before planning:

- Modding support and world sharing
- Mobile app
- Voice input/output
- Procedural world generation (aligns with "Surprise Me" mode)
- Achievement system
- Accessibility features

See [ideas/features.md](../ideas/features.md) for full descriptions.

---

## Style System

*Per Vision: Multi-sensory atmosphere (prose tone, visual direction, audio mood) is important for immersion.*

### Visual Style (Implemented)
- [x] Modular Prompt Architecture (MPA) for image generation
- [x] 14 style presets (classic-fantasy, dark-fantasy, noir, cyberpunk, anime, watercolor, childrens-book, horror, steampunk, pixel-art, photorealistic, comic-book, simpsons, teen-comedy)
- [x] Per-world style configuration in world.yaml
- [x] Preset + override system for customization
- [x] AI-authorable presets with documentation
- [x] Anti-style system to prevent style drift
- [x] NPC variant generation preserves style

### Remaining Style Work
- [ ] Prose tone configuration per world
- [ ] Audio mood per world
- [ ] Age-appropriateness content filters
- [ ] Genre conventions for narrative

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-10 | Implemented Visual Style System with MPA architecture and 14 presets |
| 2025-12-10 | Restructured roadmap around Vision document experience goals |
| 2025-12-10 | Added Emotional State Tracking to Phase 4 (was missing after restructuring) |
| 2025-12 | Initial roadmap created from features.md analysis |

---

*Last updated: December 2025*
