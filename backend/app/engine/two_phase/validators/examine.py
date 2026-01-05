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
from app.engine.two_phase.visibility import _check_entity_visibility

if TYPE_CHECKING:
    from app.engine.two_phase.models.state import TwoPhaseGameState
    from app.engine.two_phase.visibility import DefaultVisibilityResolver
    from app.models.world import WorldData


class ExamineValidator:
    """Validates EXAMINE actions against world rules.

    Checks:
        1. Target exists (item, detail, exit, or inventory item)
        2. Target is visible (for items/exits/details, uses visibility rules)
        3. Returns context with entity description and on_examine effects for Narrator

    Returns ValidationResult with:
        - valid=True: includes entity info and on_examine effects in context
        - valid=False: includes rejection code and reason

    Example:
        >>> resolver = DefaultVisibilityResolver()
        >>> validator = ExamineValidator(resolver)
        >>> result = validator.validate(intent, state, world)
        >>> if result.valid:
        ...     description = result.context["description"]
        ...     on_examine = result.context.get("on_examine")
    """

    def __init__(self, visibility_resolver: "DefaultVisibilityResolver"):
        """Initialize the examine validator.

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
        location = world.get_location(state.current_location)

        # Check inventory items first
        if target_id in state.inventory:
            item = world.get_item(target_id)
            if item:
                return self._build_item_result(item, target_id, in_inventory=True)

        # Check location details (includes on_examine effects)
        if location and location.details:
            if target_id in location.details:
                detail_def = location.details[target_id]
                # Check detail visibility
                is_visible, _ = _check_entity_visibility(
                    detail_def.hidden, detail_def.find_condition, state.flags
                )
                if not is_visible:
                    return invalid_result(
                        code=RejectionCode.TARGET_NOT_FOUND,
                        reason="You don't see anything like that here.",
                    )
                return self._build_detail_result(detail_def, target_id)

        # Check exits (can examine visible exits to learn about them)
        if location and target_id in location.exits:
            exit_def = location.exits[target_id]
            # Check exit visibility
            is_visible, _ = _check_entity_visibility(
                exit_def.hidden, exit_def.find_condition, state.flags
            )
            if not is_visible:
                return invalid_result(
                    code=RejectionCode.TARGET_NOT_FOUND,
                    reason="You don't see anything like that here.",
                )
            return self._build_exit_result(exit_def, target_id, world)

        # V3: Check items at location via item_placements
        item = world.get_item(target_id)
        if item and location and target_id in location.item_placements:
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

            return self._build_item_result(item, target_id, in_inventory=False)

        # Item exists but not at this location
        if item:
            return invalid_result(
                code=RejectionCode.ITEM_NOT_HERE,
                reason="You don't see that here.",
            )

        # V3: Check NPCs via npc_placements
        if location and target_id in location.npc_placements:
            npc = world.get_npc(target_id)
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

    def _build_item_result(
        self,
        item: "Item",  # noqa: F821
        item_id: str,
        in_inventory: bool,
    ) -> ValidationResult:
        """Build validation result for examining an item.

        Args:
            item: The Item definition
            item_id: The item's ID
            in_inventory: Whether the item is in inventory

        Returns:
            ValidationResult with item info and on_examine effects
        """
        from app.models.world import Item

        item: Item  # type hint for IDE
        description = item.examine_description or f"You examine the {item.name}."

        # Build on_examine effects dict if present
        on_examine = None
        if item.on_examine:
            on_examine = {
                "sets_flag": item.on_examine.sets_flag,
                "reveals_exit_destination": item.on_examine.reveals_exit_destination,
                "narrative_hint": item.on_examine.narrative_hint,
            }

        return valid_result(
            entity_type="item",
            entity_id=item_id,
            entity_name=item.name,
            description=description,
            scene_description=item.scene_description,
            in_inventory=in_inventory,
            on_examine=on_examine,
        )

    def _build_detail_result(
        self,
        detail_def: "DetailDefinition",  # noqa: F821
        detail_id: str,
    ) -> ValidationResult:
        """Build validation result for examining a detail.

        Args:
            detail_def: The DetailDefinition
            detail_id: The detail's ID

        Returns:
            ValidationResult with detail info and on_examine effects
        """
        # Use examine_description if available, otherwise scene_description
        description = detail_def.examine_description or detail_def.scene_description

        # Build on_examine effects dict if present
        on_examine = None
        if detail_def.on_examine:
            on_examine = {
                "sets_flag": detail_def.on_examine.sets_flag,
                "reveals_exit_destination": detail_def.on_examine.reveals_exit_destination,
                "narrative_hint": detail_def.on_examine.narrative_hint,
            }

        return valid_result(
            entity_type="detail",
            entity_id=detail_id,
            entity_name=detail_def.name,
            description=description,
            in_inventory=False,
            on_examine=on_examine,
        )

    def _build_exit_result(
        self,
        exit_def: "ExitDefinition",  # noqa: F821
        direction: str,
        world: "WorldData",
    ) -> ValidationResult:
        """Build validation result for examining an exit.

        Args:
            exit_def: The ExitDefinition
            direction: The exit direction (e.g., "north")
            world: World data for destination lookup

        Returns:
            ValidationResult with exit info and destination reveal effect
        """
        # Use examine_description if available, otherwise scene_description
        description = exit_def.examine_description or exit_def.scene_description
        if not description:
            description = f"A passage leading {direction}."

        # Get destination name for context
        dest_location = world.get_location(exit_def.destination)
        dest_name = dest_location.name if dest_location else exit_def.destination

        # Build on_examine effects - include reveal_destination_on_examine
        on_examine = None
        if exit_def.reveal_destination_on_examine:
            on_examine = {
                "reveal_destination_on_examine": True,
                "direction": direction,
            }

        return valid_result(
            entity_type="exit",
            entity_id=direction,
            entity_name=f"Exit to {direction}",
            description=description,
            in_inventory=False,
            destination_id=exit_def.destination,
            destination_name=dest_name,
            destination_known=exit_def.destination_known,
            on_examine=on_examine,
        )
