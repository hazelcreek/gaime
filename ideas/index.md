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
| [two-phase-game-loop-architecture-gemini.md](two-phase-game-loop-architecture-gemini.md) | Event-driven game loop architecture proposal for splitting the game loop into Parser -> Engine -> Narrator pipeline |
| [two-phase-game-loop-architecture-gpt52.md](two-phase-game-loop-architecture-gpt52.md) | Evented game loop specification with ActionIntents, Events, and Narration separation (GPT-5.2 version) |
| [two-phase-game-loop-architecture-grok.md](two-phase-game-loop-architecture-grok.md) | Two-Phase Game Loop Architecture specification (Grok version) — separating mechanics from narration |
| [two-phase-game-loop-architecture-opus.md](two-phase-game-loop-architecture-opus.md) | **Two-Phase Game Loop Architecture** (Claude Opus version) — Detailed specification for separating mechanics (parsing/validation) from narration to improve reliability and enable rich verb support |
| [world-builder-quality-quick-wins.md](world-builder-quality-quick-wins.md) | Minimal-effort plan to improve World Builder output richness (puzzle depth, gating, NPC knowledge) |
| [world-builder-agent-refactor.md](world-builder-agent-refactor.md) | Proposal for moving World Builder from UI to an in-editor Cursor agent experience |

---

## File Naming Convention

Use **lowercase kebab-case** for all files:

- ✅ `my-feature-idea.md`
- ❌ `My Feature Idea.md`
- ❌ `MY_FEATURE_IDEA.md`
