"""Game engine components.

This package contains the two-phase game engine with separated parsing
(Interactor) and narration (Narrator).

Located in `engine/two_phase/`.

Import directly from submodules to avoid circular imports:
    from app.engine.two_phase.processor import TwoPhaseProcessor
    from app.engine.two_phase.state import TwoPhaseStateManager
"""

# Note: No eager imports to avoid circular import issues
