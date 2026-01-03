"""
Examine validator for the two-phase game engine.

This module validates EXAMINE actions against world rules,
checking that targets exist and are visible.

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


class ExamineValidator:
    """Validates EXAMINE actions against world rules.

    Checks:
        1. Target exists (item, detail, or inventory item)
        2. Target is visible (for items, uses visibility rules)
        3. Returns context with entity description for Narrator

    Returns ValidationResult with:
        - valid=True: includes entity info in context
        - valid=False: includes rejection code and reason

    Example:
        >>> resolver = DefaultVisibilityResolver()
        >>> validator = ExamineValidator(resolver)
        >>> result = validator.validate(intent, state, world)
        >>> if result.valid:
        ...     description = result.context["description"]
    """

    def __init__(self, visibility_resolver: "DefaultVisibilityResolver | None" = None):
        """Initialize the examine validator.

        Args:
            visibility_resolver: Optional visibility resolver for checking
                                 item visibility. If not provided, uses
                                 inline logic for backwards compatibility.
        """
        self._visibility_resolver = visibility_resolver

    def validate(
        self,
        intent: ActionIntent,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> ValidationResult:
        """Validate an examine intent against game rules.

        Args:
            intent: The parsed EXAMINE action intent
            state: Current game state
            world: World data with entity definitions

        Returns:
            ValidationResult indicating success or failure with reason
        """
        if intent.action_type != ActionType.EXAMINE:
            return invalid_result(
                code=RejectionCode.TARGET_NOT_FOUND,
                reason="This validator only handles examine actions.",
            )

        target_id = intent.target_id

        # Check inventory items first
        if target_id in state.inventory:
            item = world.get_item(target_id)
            if item:
                return valid_result(
                    entity_type="item",
                    entity_id=target_id,
                    entity_name=item.name,
                    description=item.examine or f"You examine the {item.name}.",
                    in_inventory=True,
                )

        # Check location details
        location = world.get_location(state.current_location)
        if location and location.details:
            if target_id in location.details:
                detail_description = location.details[target_id]
                # Create a readable name from the ID
                detail_name = target_id.replace("_", " ").title()
                return valid_result(
                    entity_type="detail",
                    entity_id=target_id,
                    entity_name=detail_name,
                    description=detail_description,
                    in_inventory=False,
                )

        # Check items at location
        item = world.get_item(target_id)
        if item:
            # Check if item is at current location
            # Item can be in location.items list OR have item.location set
            item_at_location = (
                location and target_id in location.items
            ) or item.location == state.current_location

            if item_at_location:
                # Check visibility using resolver if available
                if self._visibility_resolver:
                    is_visible, reason = (
                        self._visibility_resolver.analyze_item_visibility(
                            item, target_id, state
                        )
                    )
                    if not is_visible and reason != "taken":
                        return invalid_result(
                            code=RejectionCode.ITEM_NOT_VISIBLE,
                            reason="You don't see anything like that here.",
                        )
                else:
                    # Fallback: inline visibility check (for backwards compatibility)
                    if item.hidden:
                        if item.find_condition:
                            required_flag = item.find_condition.get("requires_flag")
                            if required_flag and not state.flags.get(
                                required_flag, False
                            ):
                                return invalid_result(
                                    code=RejectionCode.ITEM_NOT_VISIBLE,
                                    reason="You don't see anything like that here.",
                                )
                        else:
                            return invalid_result(
                                code=RejectionCode.ITEM_NOT_VISIBLE,
                                reason="You don't see anything like that here.",
                            )

                return valid_result(
                    entity_type="item",
                    entity_id=target_id,
                    entity_name=item.name,
                    description=item.examine or f"You examine the {item.name}.",
                    found_description=item.found_description,
                    in_inventory=False,
                )

            # Item exists but not at this location
            return invalid_result(
                code=RejectionCode.ITEM_NOT_HERE,
                reason="You don't see that here.",
            )

        # Check NPCs
        if location:
            for npc_id in location.npcs:
                if npc_id == target_id:
                    npc = world.get_npc(npc_id)
                    if npc:
                        return valid_result(
                            entity_type="npc",
                            entity_id=target_id,
                            entity_name=npc.name,
                            description=npc.appearance or f"You see {npc.name}.",
                            in_inventory=False,
                        )

        # Target not found
        return invalid_result(
            code=RejectionCode.TARGET_NOT_FOUND,
            reason="You don't see anything like that here.",
        )
