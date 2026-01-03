"""Game engine components.

This package contains both the classic engine and the two-phase engine.

- Classic Engine: Single LLM call for action processing and narration.
  Located in `engine/classic/`.

- Two-Phase Engine: Separated parsing (Interactor) and narration (Narrator).
  Located in `engine/two_phase/`.

Import directly from submodules to avoid circular imports:
    from app.engine.classic.processor import ActionProcessor
    from app.engine.classic.state import GameStateManager
    from app.engine.two_phase.processor import TwoPhaseProcessor
    from app.engine.two_phase.state import TwoPhaseStateManager
"""

# Note: No eager imports to avoid circular import issues
