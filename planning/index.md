# Planning

Project planning documents for GAIME development. These are actively maintained and should be consulted when working on features.

> **Note for Cursor AI**: Consult these files proactively when implementing features or making development decisions.

---

## Index

| File | Description |
|------|-------------|
| [roadmap.md](roadmap.md) | Development phases and progress tracking, aligned with [Vision](../docs/VISION.md) |
| [worldbuilder-strategy.md](worldbuilder-strategy.md) | World builder tooling strategy: TUI + Cursor Agent dual-tool approach |
| [two-phase-game-loop-spec.md](two-phase-game-loop-spec.md) | **Two-Phase Game Loop Architecture** — Authoritative specification for separating action parsing (Interactor) from narrative generation (Narrator) to enable deterministic state management |
| [visibility-examination-spec.md](visibility-examination-spec.md) | **Visibility & Examination System** — Unified visibility semantics, visual descriptions, examination mechanics, destination visibility for exits, and image generation improvements |
| [items-interaction-spec.md](items-interaction-spec.md) | **Items & Interaction Mechanics** (SKELETON) — Item use commands, interaction gating via `requires_flag`/`requires_item`, constraint enforcement |

---

## How to Use

- **Before starting work**: Check the roadmap to see current priorities
- **After completing work**: Update the roadmap to mark items complete
- **When planning**: Reference the roadmap to understand dependencies
- **For game loop changes**: Consult the two-phase-game-loop-spec for architectural guidance
- **For visibility/examination**: Consult the visibility-examination-spec for entity descriptions and examination mechanics
- **For item use/interactions**: Consult the items-interaction-spec for gating, item use commands, and constraint enforcement

---

*Last updated: January 2026*
