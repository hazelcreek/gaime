# GAIME Development Roadmap

This document tracks development progress across phases. Update this file when completing features or changing priorities.

> **Source of Truth**: This is the primary progress tracker. See [ideas/features.md](../ideas/features.md) for the full feature backlog.

---

## Phase Overview

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Core Polish | 🟡 In Progress |
| 2 | Puzzle System | ⚪ Planned |
| 3 | Narrative Depth | ⚪ Planned |
| 4 | World Dynamics | ⚪ Planned |
| 5 | Player Experience | ⚪ Planned |

**Legend**: ✅ Complete | 🟡 In Progress | ⚪ Planned

---

## Phase 1: Core Polish

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

## Phase 2: Puzzle System

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

### Narrative Integration
- [ ] LLM constraints to protect puzzle solutions
- [ ] Contextual hint system
- [ ] Puzzle progress in narrative memory

---

## Phase 3: Narrative Depth

Richer storytelling and player character development.

### Player Backstory System
- [ ] Backstory definition in world.yaml
- [ ] Backstory reveals through NPC dialogue
- [ ] Skills/abilities from backstory

### Emotional State Tracking
- [ ] Player emotional state model
- [ ] Emotion affects narration style
- [ ] Emotion affects NPC reactions

### Consequences & Ripple Effects
- [ ] Delayed consequence system
- [ ] Action memory for callbacks
- [ ] Branching based on past choices

### Multiple Endings
- [ ] Multiple victory conditions
- [ ] Ending selection based on state
- [ ] Ending narrative variations

---

## Phase 4: World Dynamics

Living world that changes over time.

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

## Phase 5: Player Experience

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
- [ ] Per-world art style configuration
- [ ] More image generation variety
- [ ] UI theme variations

---

## Future Exploration

Ideas requiring more research before planning:

- Multiplayer / shared worlds
- Modding support and world sharing
- Mobile app
- Voice input/output
- Procedural world generation
- Achievement system
- Accessibility features

See [ideas/features.md](../ideas/features.md) for full descriptions.

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12 | Initial roadmap created from features.md analysis |

---

*Last updated: December 2025*

