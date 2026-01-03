"""
Intent handlers for the two-phase game engine.

This module provides handler implementations that encapsulate
the complete logic for processing each action type.

Each handler implements the IntentHandler protocol:
    - validate(): Check if the action is allowed
    - execute(): Apply state changes
    - create_event(): Create the event for narration

Example:
    >>> handler = MovementHandler(visibility_resolver)
    >>> result = handler.validate(intent, state, world)
    >>> if result.valid:
    ...     handler.execute(intent, result, state_manager)
    ...     event = handler.create_event(intent, result, state, world)
"""

from app.engine.two_phase.handlers.movement import MovementHandler
from app.engine.two_phase.handlers.examine import ExamineHandler
from app.engine.two_phase.handlers.take import TakeHandler
from app.engine.two_phase.handlers.browse import BrowseHandler
from app.engine.two_phase.handlers.flavor import FlavorHandler

__all__ = [
    "MovementHandler",
    "ExamineHandler",
    "TakeHandler",
    "BrowseHandler",
    "FlavorHandler",
]
