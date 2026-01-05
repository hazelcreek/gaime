# Ideas & Brainstorming

Personal notes, feature concepts, and architectural explorations for GAIME. These are working documents—not authoritative reference material.

> **Note for Cursor AI**: Do not use files in this folder as reference unless explicitly asked.

---

## Index

| File | Description |
|------|-------------|
| [agentic-game-master-architecture.md](agentic-game-master-architecture.md) | Feasibility analysis for refactoring the Game Master to a tool-invocation agentic architecture |
| [audio-concept.md](audio-concept.md) | Comprehensive approach to music and sound effects—background music, stems, ambient soundscapes, action-triggered sounds |
| [features.md](features.md) | Feature ideas backlog (see planning/roadmap.md for progress) |
| [game-mechanics-design.md](game-mechanics-design.md) | **Comprehensive Game Design Document** — Entity taxonomy, relationships, state management, and gameplay mechanics with Mermaid diagrams |
| [modular-prompt-architecture.md](modular-prompt-architecture.md) | Seven-layer prompt system (MPA) for stylistically coherent image asset generation |
| [multi-language-support.md](multi-language-support.md) | Technical considerations for supporting multiple player languages (English/German) |
| [plan.md](plan.md) | Original implementation plan and vision for the AI text adventure prototype |
| [story-beats-design.md](story-beats-design.md) | **Story Beats as Gameplay Mechanics** — Hub-and-spoke structure, active narrative archetypes, multi-act worlds, and applied examples from existing worlds |
| [world-builder-quality-quick-wins.md](world-builder-quality-quick-wins.md) | Minimal-effort plan to improve World Builder output richness (puzzle depth, gating, NPC knowledge) |
| [world-builder-agent-refactor.md](world-builder-agent-refactor.md) | Proposal for moving World Builder from UI to an in-editor Cursor agent experience |

---

## Archive

Superseded documents are preserved in the `archive/` folder for historical reference.

| File | Description |
|------|-------------|
| [archive/two-phase-game-loop-architecture-gemini.md](archive/two-phase-game-loop-architecture-gemini.md) | ⚠️ **Superseded** — Original Gemini proposal for event-driven game loop |
| [archive/two-phase-game-loop-architecture-gpt52.md](archive/two-phase-game-loop-architecture-gpt52.md) | ⚠️ **Superseded** — Original GPT-5.2 evented game loop specification |
| [archive/two-phase-game-loop-architecture-grok.md](archive/two-phase-game-loop-architecture-grok.md) | ⚠️ **Superseded** — Original Grok two-phase architecture proposal |
| [archive/two-phase-game-loop-architecture-opus.md](archive/two-phase-game-loop-architecture-opus.md) | ⚠️ **Superseded** — Original Claude Opus detailed specification |

> **Note**: These four documents have been merged into the authoritative specification at [`planning/two-phase-game-loop-spec.md`](../planning/two-phase-game-loop-spec.md).

---

## File Naming Convention

Use **lowercase kebab-case** for all files:

- ✅ `my-feature-idea.md`
- ❌ `My Feature Idea.md`
- ❌ `MY_FEATURE_IDEA.md`
