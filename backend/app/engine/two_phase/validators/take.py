"""
Take validator for the two-phase game engine.

This module validates TAKE actions against world rules,
checking visibility, portability, and current possession.

See planning/two-phase-game-loop-spec.md Section: Validation & Rejection Handling
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.two_phase.models.event import RejectionCode
from app.engine.two_phase.models.intent import ActionIntent, ActionType
from app.engine.two_phase.models.validation import (
    ValidationResult,
    invalid_result,
    valid_result,
)

if TYPE_CHECKING:
    from app.engine.two_phase.models.state import TwoPhaseGameState
    from app.engine.two_phase.visibility import DefaultVisibilityResolver
    from app.models.world import WorldData


class TakeValidator:
    """Validates TAKE actions against world rules.

    Checks:
        1. Item is visible (not hidden or in closed container)
        2. Item is at current location
        3. Item is portable
        4. Item not already in inventory

    Returns ValidationResult with:
        - valid=True: includes item info in context
        - valid=False: includes rejection code and reason

    Example:
        >>> resolver = DefaultVisibilityResolver()
        >>> validator = TakeValidator(resolver)
        >>> result = validator.validate(intent, state, world)
        >>> if result.valid:
        ...     item_name = result.context["item_name"]
    """

    def __init__(self, visibility_resolver: "DefaultVisibilityResolver"):
        """Initialize the take validator.

        Args:
            visibility_resolver: Visibility resolver for checking item visibility
        """
        self._visibility_resolver = visibility_resolver

    def validate(
        self,
        intent: ActionIntent,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> ValidationResult:
        """Validate a take intent against game rules.

        Args:
            intent: The parsed TAKE action intent
            state: Current game state
            world: World data with item definitions

        Returns:
            ValidationResult indicating success or failure with reason
        """
        if intent.action_type != ActionType.TAKE:
            return invalid_result(
                code=RejectionCode.TARGET_NOT_FOUND,
                reason="This validator only handles take actions.",
            )

        target_id = intent.target_id

        # Check if already in inventory
        if target_id in state.inventory:
            item = world.get_item(target_id)
            item_name = item.name if item else target_id
            return invalid_result(
                code=RejectionCode.ALREADY_HAVE,
                reason=f"You already have the {item_name}.",
            )

        # Get the item from world
        item = world.get_item(target_id)
        if not item:
            return invalid_result(
                code=RejectionCode.TARGET_NOT_FOUND,
                reason="You don't see anything like that here.",
            )

        # V3: Check if item is at current location via item_placements
        location = world.get_location(state.current_location)
        if not location or target_id not in location.item_placements:
            return invalid_result(
                code=RejectionCode.ITEM_NOT_HERE,
                reason="You don't see that here.",
            )

        # V3: Check visibility using resolver with ItemPlacement
        placement = location.item_placements[target_id]
        is_visible, reason = self._visibility_resolver.analyze_item_visibility(
            placement, target_id, state
        )
        if not is_visible and reason != "taken":
            return invalid_result(
                code=RejectionCode.ITEM_NOT_VISIBLE,
                reason="You don't see anything like that here.",
            )

        # Check portability
        if not item.portable:
            return invalid_result(
                code=RejectionCode.ITEM_NOT_PORTABLE,
                reason=f"You can't take the {item.name}. It's fixed in place.",
            )

        # Item can be taken
        return valid_result(
            item_id=target_id,
            item_name=item.name,
            take_description=item.take_description,
            from_location=state.current_location,
        )
