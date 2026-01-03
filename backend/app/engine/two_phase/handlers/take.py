"""
Take handler for the two-phase game engine.

This handler processes TAKE actions, wrapping the TakeValidator
and providing state execution and event creation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.two_phase.models.event import Event, EventType
from app.engine.two_phase.models.validation import ValidationResult
from app.engine.two_phase.validators.take import TakeValidator

if TYPE_CHECKING:
    from app.engine.two_phase.models.intent import ActionIntent, Intent
    from app.engine.two_phase.models.state import TwoPhaseGameState
    from app.engine.two_phase.state import TwoPhaseStateManager
    from app.engine.two_phase.visibility import DefaultVisibilityResolver
    from app.models.world import WorldData


class TakeHandler:
    """Handles TAKE actions in the two-phase engine.

    Taking items can change victory conditions, so checks_victory=True.

    Attributes:
        checks_victory: True - taking items can trigger victory
        validator: The TakeValidator for validation logic
        visibility_resolver: For checking item visibility

    Example:
        >>> handler = TakeHandler(visibility_resolver)
        >>> result = handler.validate(intent, state, world)
        >>> if result.valid:
        ...     handler.execute(intent, result, state_manager)
    """

    checks_victory: bool = True

    def __init__(self, visibility_resolver: "DefaultVisibilityResolver"):
        """Initialize the take handler.

        Args:
            visibility_resolver: For checking item visibility
        """
        self.visibility_resolver = visibility_resolver
        self.validator = TakeValidator(visibility_resolver)

    def validate(
        self,
        intent: "Intent",
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> ValidationResult:
        """Validate the take intent.

        Args:
            intent: The TAKE ActionIntent
            state: Current game state
            world: World data

        Returns:
            ValidationResult with item info in context if valid
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
        """Execute the take action, adding item to inventory.

        Args:
            intent: The validated TAKE intent
            result: Validation result with item_id
            state_manager: State manager to mutate
        """
        item_id = result.context.get("item_id")
        if item_id:
            state_manager.add_item(str(item_id))

    def create_event(
        self,
        intent: "Intent",
        result: ValidationResult,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> Event:
        """Create the ITEM_TAKEN event.

        Args:
            intent: The processed intent
            result: The validation result with item info
            state: Current game state
            world: World data

        Returns:
            ITEM_TAKEN event for narration
        """
        item_id = result.context.get("item_id")
        return Event(
            type=EventType.ITEM_TAKEN,
            subject=str(item_id) if item_id else None,
            context={
                "item_name": result.context.get("item_name"),
                "take_description": result.context.get("take_description"),
                "from_location": result.context.get("from_location"),
            },
        )
