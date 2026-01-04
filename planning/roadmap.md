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

### Two-Phase Engine Migration

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Foundation (data models) | ✅ Complete |
| 1 | Simple Movement | ✅ Complete |
| 2 | Examination & Taking | ✅ Complete |
| - | Classic Engine Deprecated | ✅ Complete |
| 3 | Interactions & USE Actions | ⚪ Planned |
| 4 | Full Narrator | ⚪ Planned |
| 5 | Containers & Visibility | ⚪ Planned |
| 6 | Polish | ⚪ Planned |

See [two-phase-game-loop-spec.md](two-phase-game-loop-spec.md) for full specification.

### Visibility & Examination System

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Schema Definition | ✅ Complete |
| 2 | World Migration | ✅ Complete |
| 3 | Code Integration | ⚪ Planned |
| 4 | Examination Mechanics | ⚪ Planned |
| 5 | Narrator Integration | ⚪ Planned |
| 6 | Image Generation | ⚪ Planned |
| 7 | World Builder Updates | ⚪ Planned |
| 8 | Documentation | ⚪ Planned |

See [visibility-examination-spec.md](visibility-examination-spec.md) for full specification.

**Legend**: ✅ Complete | 🟡 In Progress | ⚪ Planned

---

## Two-Phase Engine Architecture

*See [two-phase-game-loop-spec.md](two-phase-game-loop-spec.md) for full specification.*

Separating action parsing from narrative generation enables deterministic state management with AI-powered prose.

### Phase 0: Foundation ✅
- [x] Data models: `ActionIntent`, `FlavorIntent`, `ActionType`
- [x] Data models: `Event`, `RejectionEvent`, `EventType`, `RejectionCode`
- [x] Data models: `PerceptionSnapshot`, `VisibleEntity`, `VisibleExit`
- [x] Data models: `ValidationResult` with factory functions

### Phase 1: Simple Movement ✅
- [x] `RuleBasedParser` for direction patterns
- [x] `MovementValidator` with precondition checking
- [x] `LOCATION_CHANGED` events with first-visit detection
- [x] Basic Narrator prompt for locations
- [x] Two-phase flow for movement only
- [x] "Command not understood" for non-movement (no fallback - complete engine separation)
- [x] `TwoPhaseGameState` and `TwoPhaseStateManager` (separate from classic)
- [x] `DefaultVisibilityResolver` for PerceptionSnapshot building
- [x] Unit tests (79 tests) and integration tests (16 tests)

### Phase 2: Examination & Taking ✅
- [x] `InteractorAI` for LLM-based entity resolution
- [x] `ExamineValidator` for items, details, and inventory
- [x] `TakeValidator` with visibility and portability checks
- [x] `ITEM_EXAMINED`, `DETAIL_EXAMINED`, `ITEM_TAKEN` events
- [x] `FlavorIntent` with `action_hint` for graduated parsing
- [x] Narrator handlers for new event types
- [x] Unit tests for validators and Interactor (33 new tests)

### Phase 3: Interactions & USE
- [ ] Location/detail interactions with flag setting
- [ ] "use X on Y" parsing in InteractorAI
- [ ] USE action validation with `use_actions` lookup
- [ ] NPC communication parsing (TALK, ASK)
- [ ] Dialogue topic resolution (defined vs improvised)
- [ ] `INTERACTION_TRIGGERED`, `FLAG_SET` events

### Phase 4: Full Narrator
- [ ] Rich, context-aware narration
- [ ] Event-specific narration templates
- [ ] NPC dialogue generation
- [ ] Discovery moment narration
- [ ] Natural rejection narration

### Phase 5: Containers & Visibility
- [ ] Container model in world schema
- [ ] OPEN/CLOSE validation
- [ ] Visibility state machine
- [ ] `CONTAINER_OPENED`, `ITEM_REVEALED` events
- [ ] PerceptionSnapshot respects visibility

### Classic Engine Deprecation ✅
- [x] Remove engine selection API and frontend selector
- [x] Delete classic engine code (`engine/classic/`, `llm/classic/`)
- [x] Update tests and documentation
- [x] Simplify API responses (single engine type)

### Phase 6: Polish
- [ ] INVENTORY meta action
- [ ] Remaining action types (GIVE, SHOW, DROP, etc.)
- [ ] Performance optimization
- [ ] Edge case handling

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

### TUI World Builder ✅
- [x] Terminal UI for world creation and management
- [x] Create new worlds from text descriptions
- [x] Batch image generation with progress feedback
- [x] Automatic NPC variant generation
- [x] World validation and inspection

### "Surprise Me" Mode
- [ ] Author provides minimal input (theme, style hints)
- [ ] AI invents everything (backstories, characters, puzzles)
- [ ] Author can play their own world spoiler-free
- [ ] Magic: discover plot twists you didn't anticipate

### "Lego" Mode
- [ ] Step-by-step construction with AI assistance
- [ ] Author guides, AI generates options
- [ ] For modifying existing worlds or precise control

### Cursor Agent (Future)
- [ ] Conversational world building in editor
- [ ] Deep iterative design sessions
- [ ] See planning/worldbuilder-strategy.md for details

### World Validation Tools
- [x] Basic YAML validation
- [x] Deprecated schema detection (personality string, dialogue_hints, locked_exit constraints)
- [x] Consistency check (flags, location/item/NPC references)
- [x] Hybrid fix system (rule-based + LLM-assisted for creative fixes)
- [ ] Completability check (victory reachable)
- [ ] Fairness check (puzzles not obscure)
- [ ] Address remaining validation errors (e.g., unused flags) - decide on handling strategy

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
| 2026-01-04 | Visibility & Examination Phase 2 complete: All 10 worlds migrated to V2 schema (ExitDefinition, DetailDefinition, renamed Item fields), 256 tests passing |
| 2026-01-04 | Visibility & Examination Phase 1 complete: ExitDefinition, DetailDefinition, ExaminationEffect models; Item field aliases; validation script |
| 2026-01-04 | Classic Engine deprecated: removed engine selection, deleted classic engine code, simplified API |
| 2025-12-17 | Two-Phase Engine Phase 2 complete: InteractorAI, ExamineValidator, TakeValidator, 33 new tests, 214 total tests passing |
| 2025-12-17 | Two-Phase Engine Phase 1 complete: movement-only engine with complete separation from classic, 95 new tests |
| 2025-12-17 | Two-Phase Engine Phase 0 complete: data models |
| 2025-12-15 | World validation system: schema generator, deprecated pattern detection, hybrid fixer (rule + LLM), migrated 5 existing worlds |
| 2025-12-12 | Implemented TUI World Builder (gaime_builder package) - terminal UI for world creation and image generation |
| 2025-12-10 | Implemented Visual Style System with MPA architecture and 14 presets |
| 2025-12-10 | Restructured roadmap around Vision document experience goals |
| 2025-12-10 | Added Emotional State Tracking to Phase 4 (was missing after restructuring) |
| 2025-12 | Initial roadmap created from features.md analysis |

---

*Last updated: January 2026*
