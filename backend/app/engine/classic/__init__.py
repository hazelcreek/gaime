"""Classic engine - Single LLM call for action processing and narration.

Key components (import directly from submodules):
- ActionProcessor: Main action processing (processor.py)
- GameStateManager: Game state management (state.py)
- Models: GameState, ActionResponse, etc. (models.py)

Import directly from submodules:
    from app.engine.classic.processor import ActionProcessor
    from app.engine.classic.state import GameStateManager
    from app.engine.classic.models import GameState, ActionResponse
"""

# Note: No eager imports to avoid circular import issues
