"""
Movement validator for the two-phase game engine.

This module validates MOVE actions against world rules,
checking exit availability and access requirements.

See planning/two-phase-game-loop-spec.md Section: Validation & Rejection Handling
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.models.intent import ActionIntent, ActionType
from app.models.event import RejectionCode
from app.models.validation import ValidationResult, valid_result, invalid_result

if TYPE_CHECKING:
    from app.models.two_phase_state import TwoPhaseGameState
    from app.models.world import WorldData


class MovementValidator:
    """Validates MOVE actions against world rules.

    Checks:
        1. Exit exists in the specified direction
        2. Destination location has no unmet requirements (flag/item)

    Returns ValidationResult with:
        - valid=True: includes destination and first_visit in context
        - valid=False: includes rejection code and reason

    Example:
        >>> validator = MovementValidator()
        >>> result = validator.validate(intent, state, world)
        >>> if result.valid:
        ...     destination = result.context["destination"]
    """

    def validate(
        self,
        intent: ActionIntent,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> ValidationResult:
        """Validate a movement intent against game rules.

        Args:
            intent: The parsed MOVE action intent
            state: Current game state
            world: World data with location definitions

        Returns:
            ValidationResult indicating success or failure with reason
        """
        if intent.action_type != ActionType.MOVE:
            return invalid_result(
                code=RejectionCode.TARGET_NOT_FOUND,
                reason="This validator only handles movement actions.",
            )

        direction = intent.target_id
        location = world.get_location(state.current_location)

        if not location:
            return invalid_result(
                code=RejectionCode.TARGET_NOT_FOUND,
                reason="You seem to be somewhere undefined.",
            )

        # Handle "back" direction specially
        if direction == "back":
            return self._validate_back(state, world, location)

        # Check if exit exists in the specified direction
        if direction not in location.exits:
            return invalid_result(
                code=RejectionCode.NO_EXIT,
                reason=f"There's no way to go {direction} from here.",
            )

        destination_id = location.exits[direction]
        destination = world.get_location(destination_id)

        if not destination:
            return invalid_result(
                code=RejectionCode.TARGET_NOT_FOUND,
                reason=f"The path leads somewhere undefined.",
            )

        # Check destination access requirements
        if destination.requires:
            validation = self._check_requirements(
                destination.requires, state, world, destination.name
            )
            if not validation.valid:
                return validation

        # Movement is valid
        first_visit = destination_id not in state.visited_locations

        return valid_result(
            destination=destination_id,
            destination_name=destination.name,
            first_visit=first_visit,
            direction=direction,
            from_location=state.current_location,
        )

    def _validate_back(
        self,
        state: "TwoPhaseGameState",
        world: "WorldData",
        location: "app.models.world.Location",
    ) -> ValidationResult:
        """Handle the 'back' direction.

        For "back", we look for a single exit or common return direction.

        Args:
            state: Current game state
            world: World data
            location: Current location object

        Returns:
            ValidationResult for back movement
        """
        # If only one exit, use that
        if len(location.exits) == 1:
            direction = list(location.exits.keys())[0]
            destination_id = location.exits[direction]
            destination = world.get_location(destination_id)

            if destination:
                # Check requirements
                if destination.requires:
                    validation = self._check_requirements(
                        destination.requires, state, world, destination.name
                    )
                    if not validation.valid:
                        return validation

                first_visit = destination_id not in state.visited_locations
                return valid_result(
                    destination=destination_id,
                    destination_name=destination.name,
                    first_visit=first_visit,
                    direction=direction,
                    from_location=state.current_location,
                )

        # Look for south (common return direction)
        if "south" in location.exits:
            destination_id = location.exits["south"]
            destination = world.get_location(destination_id)

            if destination:
                if destination.requires:
                    validation = self._check_requirements(
                        destination.requires, state, world, destination.name
                    )
                    if not validation.valid:
                        return validation

                first_visit = destination_id not in state.visited_locations
                return valid_result(
                    destination=destination_id,
                    destination_name=destination.name,
                    first_visit=first_visit,
                    direction="south",
                    from_location=state.current_location,
                )

        # No clear "back" direction
        return invalid_result(
            code=RejectionCode.NO_EXIT,
            reason="There's no obvious way back from here.",
            hint="Try a specific direction like 'north' or 'south'.",
        )

    def _check_requirements(
        self,
        requires: "app.models.world.LocationRequirement",
        state: "TwoPhaseGameState",
        world: "WorldData",
        destination_name: str,
    ) -> ValidationResult:
        """Check if location requirements are met.

        Args:
            requires: The location's requirements
            state: Current game state
            world: World data
            destination_name: Name of the destination (for error messages)

        Returns:
            ValidationResult - valid if requirements met
        """
        # Check flag requirement
        if requires.flag:
            if not state.flags.get(requires.flag, False):
                return invalid_result(
                    code=RejectionCode.PRECONDITION_FAILED,
                    reason=f"You haven't discovered how to access {destination_name} yet.",
                    requires_flag=requires.flag,
                )

        # Check item requirement
        if requires.item:
            if requires.item not in state.inventory:
                item = world.get_item(requires.item)
                item_name = item.name if item else requires.item
                return invalid_result(
                    code=RejectionCode.PRECONDITION_FAILED,
                    reason=f"You need something to access {destination_name}.",
                    hint=f"Perhaps a {item_name} would help.",
                    requires_item=requires.item,
                )

        return valid_result()

