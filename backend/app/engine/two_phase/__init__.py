"""Two-phase engine - Separated parsing (Interactor) and narration (Narrator).

Key components (import directly from submodules):
- TwoPhaseProcessor: Main action processing pipeline (processor.py)
- TwoPhaseStateManager: Game state management (state.py)
- RuleBasedParser: Fast-path movement parsing (parser.py)
- DefaultVisibilityResolver: Item/NPC visibility (visibility.py)
- Validators: Movement, Examine, Take validation (validators/)
"""

# Note: Imports are done lazily to avoid circular import issues.
# Import directly from submodules:
#   from app.engine.two_phase.processor import TwoPhaseProcessor
#   from app.engine.two_phase.state import TwoPhaseStateManager
