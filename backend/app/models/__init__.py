"""Pydantic models for GAIME.

Shared models are kept here in the models package.
Engine-specific models have been moved to their respective engine packages:

- Classic engine models: `engine/classic/models.py`
- Two-phase engine models: `engine/two_phase/models/`

Import directly from submodules to avoid circular imports:
    # World models (shared)
    from app.models.world import World, Location, NPC, Item
    from app.models.game import LLMDebugInfo

    # Classic engine models
    from app.engine.classic.models import GameState, ActionRequest, ActionResponse

    # Two-phase engine models
    from app.engine.two_phase.models.intent import ActionIntent, FlavorIntent, ActionType
    from app.engine.two_phase.models.event import Event, RejectionEvent, EventType
    from app.engine.two_phase.models.perception import PerceptionSnapshot
    from app.engine.two_phase.models.validation import ValidationResult
"""

# Only import shared models that don't cause circular imports
from app.models.world import World, Location, NPC, Item
from app.models.game import LLMDebugInfo

__all__ = [
    # Shared models
    "World",
    "Location",
    "NPC",
    "Item",
    "LLMDebugInfo",
]
