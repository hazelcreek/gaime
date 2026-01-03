"""
Movement handler for the two-phase game engine.

This handler processes MOVE actions, wrapping the MovementValidator
and providing state execution and event creation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.two_phase.models.event import Event, EventType
from app.engine.two_phase.models.validation import ValidationResult
from app.engine.two_phase.validators.movement import MovementValidator

if TYPE_CHECKING:
    from app.engine.two_phase.models.intent import ActionIntent, Intent
    from app.engine.two_phase.models.perception import PerceptionSnapshot
    from app.engine.two_phase.models.state import TwoPhaseGameState
    from app.engine.two_phase.state import TwoPhaseStateManager
    from app.engine.two_phase.visibility import DefaultVisibilityResolver
    from app.models.world import WorldData


class MovementHandler:
    """Handles MOVE actions in the two-phase engine.

    Movement can change victory conditions, so checks_victory=True.

    Attributes:
        checks_victory: True - movement can trigger victory conditions
        validator: The MovementValidator for validation logic
        visibility_resolver: For building perception snapshots

    Example:
        >>> handler = MovementHandler(visibility_resolver)
        >>> result = handler.validate(intent, state, world)
        >>> if result.valid:
        ...     handler.execute(intent, result, state_manager)
    """

    checks_victory: bool = True

    def __init__(self, visibility_resolver: "DefaultVisibilityResolver"):
        """Initialize the movement handler.

        Args:
            visibility_resolver: For building perception snapshots
        """
        self.validator = MovementValidator()
        self.visibility_resolver = visibility_resolver

    def validate(
        self,
        intent: "Intent",
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> ValidationResult:
        """Validate the movement intent.

        Args:
            intent: The MOVE ActionIntent
            state: Current game state
            world: World data

        Returns:
            ValidationResult with destination in context if valid
        """
        # Type narrowing - this handler only handles ActionIntent
        action_intent: ActionIntent = intent  # type: ignore[assignment]
        return self.validator.validate(action_intent, state, world)

    def execute(
        self,
        intent: "Intent",
        result: ValidationResult,
        state_manager: "TwoPhaseStateManager",
    ) -> bool:
        """Execute the movement, updating player location.

        Args:
            intent: The validated MOVE intent
            result: Validation result with destination
            state_manager: State manager to mutate

        Returns:
            True if this was a first visit to the destination
        """
        destination_id = result.context["destination"]
        first_visit = state_manager.move_to(str(destination_id))
        return first_visit

    def create_event(
        self,
        intent: "Intent",
        result: ValidationResult,
        state: "TwoPhaseGameState",
        world: "WorldData",
        first_visit: bool = False,
        snapshot: "PerceptionSnapshot | None" = None,
    ) -> Event:
        """Create the LOCATION_CHANGED event.

        Args:
            intent: The processed intent
            result: The validation result
            state: Current game state (at new location)
            world: World data
            first_visit: Whether this is a first visit
            snapshot: Perception snapshot at new location

        Returns:
            LOCATION_CHANGED event for narration
        """
        context = {
            "from_location": result.context.get("from_location"),
            "direction": result.context.get("direction"),
            "first_visit": first_visit,
            "destination_name": result.context.get("destination_name"),
        }

        # For first visits, include visible entities for comprehensive description
        if first_visit and snapshot:
            context["visible_items"] = [item.name for item in snapshot.visible_items]
            context["visible_npcs"] = [npc.name for npc in snapshot.visible_npcs]
            context["visible_exits"] = [
                {"direction": e.direction, "destination": e.destination_name}
                for e in snapshot.visible_exits
            ]

        return Event(
            type=EventType.LOCATION_CHANGED,
            subject=str(result.context["destination"]),
            context=context,
        )
