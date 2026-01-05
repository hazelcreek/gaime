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

    Examining objects can trigger on_examine effects like setting flags
    or revealing exit destinations.

    Attributes:
        checks_victory: True - on_examine may set flags that trigger victory
        validator: The ExamineValidator for validation logic
        visibility_resolver: For checking item visibility

    Example:
        >>> handler = ExamineHandler(visibility_resolver)
        >>> result = handler.validate(intent, state, world)
        >>> if result.valid:
        ...     handler.execute(intent, result, state_manager)
        ...     event = handler.create_event(intent, result, state, world)
    """

    checks_victory: bool = True  # on_examine may set flags that trigger victory

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
        """Execute the examine action's on_examine effects.

        Processes effects from on_examine:
        - sets_flag: Sets a flag in game state
        - reveals_exit_destination: Marks an exit's destination as revealed
        - reveal_destination_on_examine: For exits, reveals the destination

        Args:
            intent: The validated EXAMINE intent
            result: Validation result with on_examine effects in context
            state_manager: State manager for state mutations
        """
        on_examine = result.context.get("on_examine")
        if not on_examine:
            return

        # Process sets_flag effect
        if on_examine.get("sets_flag"):
            state_manager.set_flag(on_examine["sets_flag"])

        # Process reveals_exit_destination effect (from details/items)
        if on_examine.get("reveals_exit_destination"):
            location_id = state_manager.get_state().current_location
            state_manager.reveal_exit_destination(
                location_id, on_examine["reveals_exit_destination"]
            )

        # Process reveal_destination_on_examine for exits
        if on_examine.get("reveal_destination_on_examine"):
            location_id = state_manager.get_state().current_location
            direction = on_examine.get("direction")
            if direction:
                state_manager.reveal_exit_destination(location_id, direction)

    def create_event(
        self,
        intent: "Intent",
        result: ValidationResult,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> Event:
        """Create the appropriate EXAMINED event.

        Args:
            intent: The processed intent
            result: The validation result with entity info
            state: Current game state
            world: World data

        Returns:
            ITEM_EXAMINED, DETAIL_EXAMINED, or EXIT_EXAMINED event for narration
        """
        entity_type = result.context.get("entity_type", "item")

        if entity_type == "detail":
            event_type = EventType.DETAIL_EXAMINED
        elif entity_type == "exit":
            event_type = EventType.EXIT_EXAMINED
        else:
            event_type = EventType.ITEM_EXAMINED

        # Build context with all relevant info
        context: dict = {
            "entity_name": result.context.get("entity_name"),
            "description": result.context.get("description"),
            "in_inventory": result.context.get("in_inventory", False),
            "scene_description": result.context.get("scene_description"),
        }

        # Include on_examine effects for narrator context
        on_examine = result.context.get("on_examine")
        if on_examine:
            context["on_examine"] = on_examine
            if on_examine.get("narrative_hint"):
                context["narrative_hint"] = on_examine["narrative_hint"]

        # For exits, include destination info
        if entity_type == "exit":
            context["destination_id"] = result.context.get("destination_id")
            context["destination_name"] = result.context.get("destination_name")
            context["destination_known"] = result.context.get("destination_known")
            if on_examine and on_examine.get("reveal_destination_on_examine"):
                context["destination_revealed"] = True

        return Event(
            type=event_type,
            subject=str(result.context.get("entity_id")),
            context=context,
        )
