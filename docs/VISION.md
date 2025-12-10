# GAIME Vision

This document defines the product and technical vision for GAIME. It guides all development decisions and should be consulted when planning features or making architectural choices.

> **Status**: Established - December 2025

---

## Product Vision

### Core Experience Goal

**A round of GAIME should feel like finishing a great short story you played through.**

The player experiences:
- **Accomplishment** - from solving puzzles and overcoming challenges
- **Inspiration** - from exploring imaginative, thought-provoking worlds
- **The pull of "one more round"** - wanting to immediately dive into another world

Each world is short and sweet - witty, dramatic, thought-provoking, or emotionally compelling. Not overly lengthy, but satisfying and complete.

### Target Audience

**Imagination lovers.**

GAIME players:
- Love fiction, literature, movies, board games, and video games
- Don't need to be hardcore gamers
- May know text adventures from the 90s, or be younger players drawn to narrative experiences
- Often fans of fantasy, science fiction, and speculative worlds
- Value being transported to other places through story

### What Makes GAIME Unique

**Immersive short-form worlds with multi-sensory atmosphere.**

Unlike a chatbot:
- **Layered atmosphere** - compelling narration, fantasy-inspiring visuals, matching music and sounds
- **Duality of experience** - combines the satisfaction of reading with the engagement of playing
- **Curated worlds** - each world is a crafted experience, not an endless conversation

GAIME drags players into little worlds. Short and sweet. The AI isn't just generating text - it's creating a complete sensory experience.

### Success Criteria

Success for GAIME means:

1. **Personal enjoyment** - being able to experience amazing worlds ourselves
2. **Community world library** - many worlds by many creators, limited only by imagination
3. **Technology exploration** - learning how AI can create immersive, entertaining experiences

No commercial pressure (yet) - this is a passion project with room to experiment.

---

## Technical Vision

### Architecture Principles

**Commit to the vision, not the implementation.**

- Technical decisions should remain flexible and evolve with player feedback
- The core idea of GAIME is the north star; specific solutions can change
- LLM backend should be swappable as the landscape evolves, balancing three factors:
  - **Speed** - response time affects immersion
  - **Quality** - narrative and world-building sophistication
  - **Cost** - sustainable operation as usage scales

### Two AI Personalities

GAIME uses AI differently in two contexts:

| Mode | AI Behavior | Purpose |
|------|-------------|---------|
| **World Building** | Highly creative, surprises even the author, minimal constraints | Generate rich, playable worlds from simple prompts |
| **Gameplay** | Disciplined on rules and cohesion, flourishes in atmospheric storytelling | Deliver immersive narrative while protecting game integrity |

### Design Philosophy

- **Start simple, grow over time** - the core "reading + playing" experience doesn't need fancy features initially
- **Experiment boldly, release stably** - try new things, but each release should be polished enough not to frustrate players
- **Flexibility over commitment** - it's too early to lock in technical decisions; stay adaptable

### Key Constraints

- Single-player only
- Story and atmosphere are primary; mechanics are secondary
- No RPG complexity (no XP, leveling, loot, stats)
- Worlds must be completable - no unwinnable states, no player death

---

## Game Design Vision

### Puzzle Philosophy

**All puzzle types are welcome:**
- Discovery puzzles (finding hidden things, piecing together lore)
- Environmental puzzles (figuring out how the world works)
- Classic adventure puzzles (combine items, solve riddles)
- Logic puzzles (codes, sequences, deduction)
- Social puzzles (convince NPCs, navigate relationships)

**Evolution path**: Start with simpler puzzles, add complexity as the engine matures (e.g., social puzzles when dialogue system is sophisticated).

**Kind design principles**:
- No unwinnable states - engine prevents game-breaking actions with in-world explanations
- No player death - narrative goals require experiencing the full story
- Hints system is secondary - nice to have, not essential

**Balanced difficulty is an AI responsibility**: The World Builder must ensure puzzles are fair - challenging enough to satisfy, but not so obscure they frustrate. This is a quality gate for generated worlds, not just a "nice to have."

### Story Structure

**Guided freedom** - players feel free to explore, but story structure is protected.

- Each world follows a story arc (e.g., 3-act structure) that gives exploring the world a feeling of story progression
- Every world has a predefined victory condition / resolution
- Exploration doesn't happen in prescribed order - dead ends, distractions, and side stories enrich immersion

**The purpose of side content**: Non-critical areas, optional interactions, and narrative tangents aren't filler - they serve the feeling of being *in* a real world. A room with no puzzle still has atmosphere. An NPC with no quest still has personality. This richness makes the world feel alive.

**AI guardrails during gameplay:**

| Player Action | AI Response |
|---------------|-------------|
| Destroy a key item | Gently blocked with in-world excuse |
| Sit on a random chair | Narrated, adds immersion |
| Wander into side areas | Allowed, enriches world |
| Try to skip ahead | Story gates naturally prevent |

**Immersion-preserving constraints**: When the AI must prevent a game-breaking action, it should do so with *in-world explanations* that feel natural, not system messages that break the fourth wall. "The letter is too precious to burn" not "Error: cannot destroy quest item."

### Replayability

**Replay value comes from world variety, not randomization within worlds.**

- Same world = same foundation (locations, NPCs, puzzles, story structure)
- Two players have similar experiences, like classic adventure games
- AI-generated narration adds freshness to prose and dialogue
- Minor flavor interactions (sitting on chairs, examining decorations, idle NPC banter) provide variation across playthroughs without diverging from the main story - these moments are reflected in narration and enhance replayability even within the same world

---

## World Building Vision

### Two Creation Modes

**a) "Surprise Me" Mode**
- Author provides minimal input: theme, setting, style hints
- AI invents everything: backstories, characters, storyline, puzzles
- **The magic**: AI creates worlds with enough depth to genuinely surprise the author during play - discovering plot twists, character motivations, and puzzle solutions they didn't anticipate
- Author can play their own world completely spoiler-free
- Primary mode when the author wants to be a player

**b) "Lego" Mode**
- Step-by-step construction with author making decisions
- AI assists and generates options, but author guides
- Used for modifying existing worlds or precise authorial control
- Author knows the story (cannot play spoiler-free)

### World Library Dream

**No genre limits.** The library should include:

- **Classic fiction**: Fantasy, sci-fi, mystery, horror, thriller
- **Historical**: AI-researched authentic settings (Revolutionary Paris, Ancient Rome) - the World Builder doesn't just invent, it *researches* real historical facts, personas, and events, then models interactive stories on top of authentic foundations
- **Light genres**: Comedy, romance, slice-of-life
- **Kid-friendly**: Age-appropriate adventures with matching tone and visuals
- **Style-driven**: Noir Netflix aesthetic, anime adventure, children's book charm
- **Fan worlds**: Explore beloved universes (inspired by Hogwarts, Star Trek, etc.)

The style system must handle radically different aesthetics - same engine, completely different *feelings* based on prose tone, visual style, and audio atmosphere.

### AI-Generated Atmosphere

Atmosphere is crucial to the GAIME experience. AI generates:

- **Visuals** - images that match the world's style and tone
- **Music & sounds** - audio that enhances immersion
- **Prose style** - narration that fits the genre (noir terseness, fantasy grandeur, comedic wit)

This enables efficient production of a wide variety of worlds.

### The Style System

To support the full range of world aesthetics, the style system must control:

| Dimension | What It Controls | Examples |
|-----------|------------------|----------|
| **Prose tone** | Vocabulary, sentence structure, narrative voice | Hardboiled noir vs. whimsical fairy tale |
| **Visual direction** | Art style, color palette, composition | Anime, photorealistic, children's book illustration |
| **Audio mood** | Music genre, ambient sounds, intensity | Tense orchestral vs. playful chiptune |
| **Age-appropriateness** | Content filters, complexity, themes | Kid-friendly vs. mature horror |
| **Genre conventions** | Tropes, pacing expectations, typical elements | Mystery red herrings vs. fantasy prophecies |

The same engine should produce experiences that *feel* completely different - a cozy mystery and a cyberpunk thriller should each feel native to their genre.

---

## What GAIME Is NOT

Defining the boundaries clarifies the vision:

- ❌ **Endless sandbox** - every world has structure and resolution
- ❌ **Multiplayer/social experience** - single-player focus
- ❌ **Roguelike with permadeath** - no death, no unwinnable states
- ❌ **Monetized mobile game** - no microtransactions (for now, no commercial model)
- ❌ **RPG with stats** - no XP, leveling, loot, character builds
- ❌ **Pure chatbot roleplay** - curated worlds, not open-ended conversation

---

## Summary

GAIME is a **single-player, story-driven text adventure engine** that combines:

- **Classic adventure game design** - puzzles, exploration, narrative progression
- **Modern AI capabilities** - dynamic narration, world generation, atmosphere creation
- **Multi-sensory immersion** - text, visuals, and sound working together

The goal: **short, sweet adventures that feel like playing through great short stories** - each one leaving players inspired and eager to explore the next world.

---

*Established: December 2025*
*Based on vision discovery session*
