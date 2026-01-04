"""
Examine handler for the two-phase game engine.

This handler processes EXAMINE actions, wrapping the ExamineValidator
and providing state execution and event creation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.two_phase.models.event import Event, EventType
from app.engine.two_phase.models.validation import ValidationResult
from app.engine.two_phase.validators.examine import ExamineValidator

if TYPE_CHECKING:
    from app.engine.two_phase.models.intent import ActionIntent, Intent
    from app.engine.two_phase.models.state import TwoPhaseGameState
    from app.engine.two_phase.state import TwoPhaseStateManager
    from app.engine.two_phase.visibility import DefaultVisibilityResolver
    from app.models.world import WorldData


class ExamineHandler:
    """Handles EXAMINE actions in the two-phase engine.

    Examining objects doesn't change state, so checks_victory=False.

    Attributes:
        checks_victory: False - examining doesn't trigger victory
        validator: The ExamineValidator for validation logic
        visibility_resolver: For checking item visibility

    Example:
        >>> handler = ExamineHandler(visibility_resolver)
        >>> result = handler.validate(intent, state, world)
        >>> if result.valid:
        ...     event = handler.create_event(intent, result, state, world)
    """

    checks_victory: bool = False

    def __init__(self, visibility_resolver: "DefaultVisibilityResolver"):
        """Initialize the examine handler.

        Args:
            visibility_resolver: For checking item visibility
        """
        self.visibility_resolver = visibility_resolver
        self.validator = ExamineValidator(visibility_resolver)

    def validate(
        self,
        intent: "Intent",
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> ValidationResult:
        """Validate the examine intent.

        Args:
            intent: The EXAMINE ActionIntent
            state: Current game state
            world: World data

        Returns:
            ValidationResult with entity info in context if valid
        """
        # Type narrowing - this handler only handles ActionIntent
        action_intent: ActionIntent = intent  # type: ignore[assignment]
        return self.validator.validate(action_intent, state, world)

    def execute(
        self,
        intent: "Intent",
        result: ValidationResult,
        state_manager: "TwoPhaseStateManager",
    ) -> None:
        """Execute the examine action (no-op for examine).

        Examining doesn't change state.

        Args:
            intent: The validated EXAMINE intent
            result: Validation result
            state_manager: State manager (unused)
        """
        # Examining doesn't change state
        pass

    def create_event(
        self,
        intent: "Intent",
        result: ValidationResult,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> Event:
        """Create the ITEM_EXAMINED or DETAIL_EXAMINED event.

        Args:
            intent: The processed intent
            result: The validation result with entity info
            state: Current game state
            world: World data

        Returns:
            ITEM_EXAMINED or DETAIL_EXAMINED event for narration
        """
        entity_type = result.context.get("entity_type", "item")
        if entity_type == "detail":
            event_type = EventType.DETAIL_EXAMINED
        else:
            event_type = EventType.ITEM_EXAMINED

        return Event(
            type=event_type,
            subject=str(result.context.get("entity_id")),
            context={
                "entity_name": result.context.get("entity_name"),
                "description": result.context.get("description"),
                "in_inventory": result.context.get("in_inventory", False),
                "scene_description": result.context.get("scene_description"),
            },
        )
