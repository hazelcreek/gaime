"""
Visibility resolver for the two-phase game engine.

This module computes what the player can currently see, building
PerceptionSnapshots for the Narrator.

See planning/two-phase-game-loop-spec.md Section: Visibility & Discovery Model
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.two_phase.models.perception import (
    PerceptionSnapshot,
    VisibleEntity,
    VisibleExit,
)

if TYPE_CHECKING:
    from app.engine.two_phase.models.state import TwoPhaseGameState
    from app.models.world import Location, WorldData


class DefaultVisibilityResolver:
    """Determines what the player can see.

    This resolver builds PerceptionSnapshots for the Narrator by filtering
    entities based on visibility rules.

    Phase 1 implementation:
        - All non-hidden items at location are visible
        - All exits are visible
        - Items in closed containers are NOT visible
        - Hidden items require their reveal condition to be met

    Example:
        >>> resolver = DefaultVisibilityResolver()
        >>> snapshot = resolver.build_snapshot(state, world)
        >>> print(snapshot.location_name)
        "The Study"
    """

    def build_snapshot(
        self,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> PerceptionSnapshot:
        """Build a complete perception snapshot for the narrator.

        The snapshot includes all visible entities at the current
        location, the player's inventory, and relevant context.

        Args:
            state: Current game state
            world: World data for entity definitions

        Returns:
            PerceptionSnapshot with all visible entities
        """
        location = world.get_location(state.current_location)

        if not location:
            # Fallback for missing location
            return PerceptionSnapshot(
                location_id=state.current_location,
                location_name="Unknown Location",
                location_atmosphere="",
                first_visit=state.current_location not in state.visited_locations,
            )

        # Build visible exits
        visible_exits = self._get_visible_exits(location, world)

        # Build visible items at location
        visible_items = self._get_visible_items(state, world, location)

        # Build visible details (scenery)
        visible_details = self._get_visible_details(location)

        # Build inventory
        inventory = self._get_inventory_entities(state, world)

        # Check if first visit
        first_visit = state.current_location not in state.visited_locations

        return PerceptionSnapshot(
            location_id=state.current_location,
            location_name=location.name,
            location_atmosphere=location.atmosphere or None,
            visible_items=visible_items,
            visible_details=visible_details,
            visible_exits=visible_exits,
            visible_npcs=[],  # NPCs not implemented in Phase 1
            inventory=inventory,
            affordances={},  # Affordances not implemented in Phase 1
            known_facts=[],  # Known facts not implemented in Phase 1
            first_visit=first_visit,
        )

    def _get_visible_exits(
        self,
        location: "Location",
        world: "WorldData",
    ) -> list[VisibleExit]:
        """Get all visible exits from the current location.

        Args:
            location: The current location
            world: World data for destination lookups

        Returns:
            List of VisibleExit objects
        """
        exits = []

        for direction, dest_id in location.exits.items():
            dest_location = world.get_location(dest_id)
            dest_name = dest_location.name if dest_location else dest_id

            # Get exit description from location details if available
            description = location.details.get(direction) if location.details else None

            exits.append(
                VisibleExit(
                    direction=direction,
                    destination_name=dest_name,
                    description=description,
                    is_locked=False,  # Lock checking not implemented in Phase 1
                    is_blocked=False,
                )
            )

        return exits

    def _get_visible_items(
        self,
        state: "TwoPhaseGameState",
        world: "WorldData",
        location: "Location",
    ) -> list[VisibleEntity]:
        """Get all visible items at the location.

        Items are visible if:
        - They are not hidden, OR
        - Their find_condition flag is set

        Items in the player's inventory are NOT included here.

        Args:
            state: Current game state
            world: World data for item lookups
            location: The current location

        Returns:
            List of VisibleEntity objects for visible items
        """
        visible = []

        for item_id in location.items:
            # Skip items already in inventory
            if item_id in state.inventory:
                continue

            item = world.get_item(item_id)
            if not item:
                continue

            # Check visibility
            if item.hidden:
                # Hidden items need their condition met
                if item.find_condition:
                    required_flag = item.find_condition.get("requires_flag")
                    if required_flag and not state.flags.get(required_flag, False):
                        continue  # Condition not met, skip
                else:
                    continue  # Hidden with no condition, skip

            visible.append(
                VisibleEntity(
                    id=item_id,
                    name=item.name,
                    description=item.found_description or item.examine or None,
                    is_new=False,  # TODO: Track newly revealed items
                )
            )

        return visible

    def _get_visible_details(
        self,
        location: "Location",
    ) -> list[VisibleEntity]:
        """Get all examinable details (scenery) at the location.

        Args:
            location: The current location

        Returns:
            List of VisibleEntity objects for details
        """
        details = []

        if location.details:
            for detail_id, description in location.details.items():
                # Skip direction-based details (those are exit descriptions)
                if detail_id in ("north", "south", "east", "west", "up", "down"):
                    continue

                details.append(
                    VisibleEntity(
                        id=detail_id,
                        name=detail_id.replace("_", " ").title(),
                        description=description,
                        is_new=False,
                    )
                )

        return details

    def _get_inventory_entities(
        self,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> list[VisibleEntity]:
        """Get all items in the player's inventory.

        Args:
            state: Current game state
            world: World data for item lookups

        Returns:
            List of VisibleEntity objects for inventory items
        """
        inventory = []

        for item_id in state.inventory:
            item = world.get_item(item_id)
            if item:
                inventory.append(
                    VisibleEntity(
                        id=item_id,
                        name=item.name,
                        description=item.examine or None,
                        is_new=False,
                    )
                )
            else:
                # Item not found in world data - include anyway
                inventory.append(
                    VisibleEntity(
                        id=item_id,
                        name=item_id,
                        description=None,
                        is_new=False,
                    )
                )

        return inventory

    def is_item_visible(
        self,
        item_id: str,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> bool:
        """Check if an item is visible to the player.

        An item is visible if:
        - It's in the player's inventory, OR
        - It's at the current location AND not hidden (or condition met)

        Args:
            item_id: The item to check
            state: Current game state
            world: World data for item definitions

        Returns:
            True if the item is visible, False otherwise
        """
        # Items in inventory are always visible
        if item_id in state.inventory:
            return True

        item = world.get_item(item_id)
        if not item:
            return False

        # Check if item is at current location
        location = world.get_location(state.current_location)
        if not location or item_id not in location.items:
            # Also check item.location field
            if item.location != state.current_location:
                return False

        # Check visibility based on hidden state
        if item.hidden:
            if not item.find_condition:
                return False
            required_flag = item.find_condition.get("requires_flag")
            if required_flag and not state.flags.get(required_flag, False):
                return False

        return True
