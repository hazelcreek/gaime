"""
Visibility resolver for the two-phase game engine.

This module computes what the player can currently see, building
PerceptionSnapshots for the Narrator.

See planning/two-phase-game-loop-spec.md Section: Visibility & Discovery Model
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.two_phase.models.perception import (
    LocationDebugSnapshot,
    LocationExitDebug,
    LocationInteractionDebug,
    LocationItemDebug,
    LocationNPCDebug,
    PerceptionSnapshot,
    VisibleEntity,
    VisibleExit,
)

if TYPE_CHECKING:
    from typing import Protocol

    from app.models.world import (
        ItemPlacement,
        Location,
        NPC,
        WorldData,
    )

    class GameStateProtocol(Protocol):
        """Protocol for game state."""

        current_location: str
        inventory: list[str]
        flags: dict[str, bool]


def _check_entity_visibility(
    hidden: bool,
    find_condition: dict | None,
    flags: dict[str, bool],
) -> tuple[bool, str]:
    """Check if an entity is visible based on hidden flag and find_condition.

    This is the unified visibility check used for items, exits, details, and NPCs
    in the V3 schema where visibility is location-bound.

    Args:
        hidden: Whether the entity is marked as hidden
        find_condition: Condition dict like {requires_flag: "some_flag"}
        flags: Current game state flags

    Returns:
        Tuple of (is_visible, reason_string)
    """
    if not hidden:
        return True, "visible"

    if not find_condition:
        return False, "hidden"

    required_flag = find_condition.get("requires_flag")
    if required_flag:
        if flags.get(required_flag, False):
            return True, "revealed"
        else:
            return False, f"condition_not_met:{required_flag}"

    return False, "hidden"


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
        state: "GameStateProtocol",
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
                first_visit=self._is_first_visit(state),
            )

        # Build visible exits (pass state for destination_known resolution)
        visible_exits = self._get_visible_exits(location, world, state)

        # Build visible items at location
        visible_items = self._get_visible_items(state, world, location)

        # Build visible details (scenery)
        visible_details = self._get_visible_details(location, state)

        # Build visible NPCs at location (V3: uses npc_placements visibility)
        visible_npcs = self._get_visible_npcs(location, world, state)

        # Build inventory
        inventory = self._get_inventory_entities(state, world)

        # Check if first visit (handle both engine state types)
        first_visit = self._is_first_visit(state)

        return PerceptionSnapshot(
            location_id=state.current_location,
            location_name=location.name,
            location_atmosphere=location.atmosphere or None,
            visible_items=visible_items,
            visible_details=visible_details,
            visible_exits=visible_exits,
            visible_npcs=visible_npcs,
            inventory=inventory,
            affordances={},  # Affordances not implemented in Phase 1
            known_facts=[],  # Known facts not implemented in Phase 1
            first_visit=first_visit,
        )

    def _get_visible_exits(
        self,
        location: "Location",
        world: "WorldData",
        state: "GameStateProtocol | None" = None,
    ) -> list[VisibleExit]:
        """Get all visible exits from the current location.

        V3: Filters hidden exits based on find_condition.

        Args:
            location: The current location
            world: World data for destination lookups
            state: Current game state (optional, for destination_known resolution)

        Returns:
            List of VisibleExit objects (only visible ones)
        """
        exits = []
        flags = state.flags if state else {}

        for direction, exit_def in location.exits.items():
            # V3: Check exit visibility
            is_visible, _ = _check_entity_visibility(
                exit_def.hidden, exit_def.find_condition, flags
            )
            if not is_visible:
                continue

            dest_location = world.get_location(exit_def.destination)
            dest_name = dest_location.name if dest_location else exit_def.destination

            # Determine if destination is known:
            # 1. Author set destination_known = True, OR
            # 2. Player has visited the destination, OR
            # 3. reveal_destination_on_flag is set and the flag is True, OR
            # 4. Exit is in revealed_exits for this location
            destination_known = self._check_destination_known(
                exit_def, direction, state
            )

            exits.append(
                VisibleExit(
                    direction=direction,
                    destination_name=dest_name,
                    destination_known=destination_known,
                    description=exit_def.scene_description or None,
                    is_locked=exit_def.locked,
                    is_blocked=exit_def.blocked,
                )
            )

        return exits

    def _check_destination_known(
        self,
        exit_def: "ExitDefinition",  # noqa: F821
        direction: str,
        state: "GameStateProtocol | None",
    ) -> bool:
        """Check if an exit's destination is known to the player.

        Destination is known if ANY of these are true:
        1. Author set destination_known = True
        2. Player has visited the destination
        3. reveal_destination_on_flag is set and the flag is True
        4. Direction is in revealed_exits for this location (Phase 4)

        Args:
            exit_def: The exit definition
            direction: The exit direction
            state: Current game state

        Returns:
            True if the destination is known
        """
        from app.models.world import ExitDefinition

        exit_def: ExitDefinition  # type hint for IDE

        # 1. Author set destination_known = True
        if exit_def.destination_known:
            return True

        if not state:
            return False

        # 2. Player has visited the destination
        if hasattr(state, "visited_locations"):
            if exit_def.destination in state.visited_locations:
                return True

        # 3. reveal_destination_on_flag is set and the flag is True
        if exit_def.reveal_destination_on_flag and state.flags.get(
            exit_def.reveal_destination_on_flag, False
        ):
            return True

        # 4. Direction is in revealed_exits for this location
        if hasattr(state, "revealed_exits"):
            location_id = state.current_location
            if direction in state.revealed_exits.get(location_id, set()):
                return True

        return False

    def _is_first_visit(self, state: "GameStateProtocol") -> bool:
        """Check if this is the first visit to the current location."""
        if hasattr(state, "visited_locations"):
            return state.current_location not in state.visited_locations
        return False

    def _get_visible_items(
        self,
        state: "GameStateProtocol",
        world: "WorldData",
        location: "Location",
    ) -> list[VisibleEntity]:
        """Get all visible items at the location (V3).

        V3: Uses item_placements for visibility. Items are visible if:
        - They have a placement at this location, AND
        - They are not hidden OR their find_condition is met

        Items in the player's inventory are NOT included here.

        Args:
            state: Current game state
            world: World data for item lookups
            location: The current location

        Returns:
            List of VisibleEntity objects for visible items
        """
        visible = []

        # V3: Iterate over item_placements (keys define which items are here)
        for item_id, placement in location.item_placements.items():
            # Skip items already in inventory
            if item_id in state.inventory:
                continue

            item = world.get_item(item_id)
            if not item:
                continue

            # V3: Check visibility from placement, not item
            is_visible, _ = _check_entity_visibility(
                placement.hidden, placement.find_condition, state.flags
            )
            if not is_visible:
                continue

            # Build description: prefer placement, then scene_description
            description_parts = []
            if placement.placement:
                description_parts.append(placement.placement)
            if item.scene_description:
                description_parts.append(item.scene_description)
            description = ". ".join(description_parts) if description_parts else None

            visible.append(
                VisibleEntity(
                    id=item_id,
                    name=item.name,
                    description=description,
                    is_new=False,  # TODO: Track newly revealed items
                )
            )

        return visible

    def _get_visible_details(
        self,
        location: "Location",
        state: "GameStateProtocol | None" = None,
    ) -> list[VisibleEntity]:
        """Get all examinable details (scenery) at the location.

        V3: Filters hidden details based on find_condition.

        Args:
            location: The current location
            state: Current game state (optional, for visibility checking)

        Returns:
            List of VisibleEntity objects for details
        """
        details = []
        flags = state.flags if state else {}

        if location.details:
            for detail_id, detail_def in location.details.items():
                # V3: Check detail visibility
                is_visible, _ = _check_entity_visibility(
                    detail_def.hidden, detail_def.find_condition, flags
                )
                if not is_visible:
                    continue

                details.append(
                    VisibleEntity(
                        id=detail_id,
                        name=detail_def.name,
                        description=detail_def.scene_description,
                        is_new=False,
                    )
                )

        return details

    def _get_visible_npcs(
        self,
        location: "Location",
        world: "WorldData",
        state: "GameStateProtocol",
    ) -> list[VisibleEntity]:
        """Get all visible NPCs at the current location (V3).

        Visibility check order:
        1. NPC must be in npc_placements for this location (presence)
        2. Placement must pass visibility check (hidden + find_condition)
        3. NPC must pass presence check (appears_when, location_changes)

        Args:
            location: The current location
            world: World data for NPC lookups
            state: Current game state

        Returns:
            List of VisibleEntity objects for visible NPCs
        """
        visible_npcs = []
        location_id = state.current_location

        # V3: Iterate over npc_placements (keys define which NPCs are here)
        for npc_id, placement in location.npc_placements.items():
            npc = world.get_npc(npc_id)
            if not npc:
                continue

            # V3: Check visibility from placement (hidden + find_condition)
            is_visible, _ = _check_entity_visibility(
                placement.hidden, placement.find_condition, state.flags
            )
            if not is_visible:
                continue

            # Check NPC-level presence (location_changes, appears_when)
            npc_visible, _, _ = self._analyze_npc_visibility(
                npc, npc_id, location_id, state
            )
            if not npc_visible:
                continue

            # Build description: prefer placement, then appearance
            description_parts = []
            if placement.placement:
                description_parts.append(placement.placement)
            if npc.appearance:
                description_parts.append(npc.appearance)
            description = ". ".join(description_parts) if description_parts else None

            # NPC is visible - add to list
            visible_npcs.append(
                VisibleEntity(
                    id=npc_id,
                    name=npc.name,
                    description=description,
                    is_new=False,
                )
            )

        return visible_npcs

    def _get_inventory_entities(
        self,
        state: "GameStateProtocol",
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
                        description=item.examine_description or None,
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
        state: "GameStateProtocol",
        world: "WorldData",
    ) -> bool:
        """Check if an item is visible to the player (V3).

        An item is visible if:
        - It's in the player's inventory, OR
        - It has a placement at the current location AND not hidden (or condition met)

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

        # V3: Check if item has a placement at current location
        location = world.get_location(state.current_location)
        if not location:
            return False

        placement = location.item_placements.get(item_id)
        if not placement:
            return False

        # V3: Check visibility from placement
        is_visible, _ = _check_entity_visibility(
            placement.hidden, placement.find_condition, state.flags
        )

        return is_visible

    def is_exit_visible(
        self,
        location: "Location",
        direction: str,
        state: "GameStateProtocol",
    ) -> bool:
        """Check if an exit is visible to the player.

        An exit is visible if:
        - It exists at the location, AND
        - It is not hidden OR its find_condition is met

        Args:
            location: The location to check exits for
            direction: The exit direction to check
            state: Current game state

        Returns:
            True if the exit is visible, False otherwise
        """
        if direction not in location.exits:
            return False

        exit_def = location.exits[direction]
        is_visible, _ = _check_entity_visibility(
            exit_def.hidden, exit_def.find_condition, state.flags
        )
        return is_visible

    def is_detail_visible(
        self,
        location: "Location",
        detail_id: str,
        state: "GameStateProtocol",
    ) -> bool:
        """Check if a detail is visible to the player.

        A detail is visible if:
        - It exists at the location, AND
        - It is not hidden OR its find_condition is met

        Args:
            location: The location to check details for
            detail_id: The detail ID to check
            state: Current game state

        Returns:
            True if the detail is visible, False otherwise
        """
        if not location.details or detail_id not in location.details:
            return False

        detail_def = location.details[detail_id]
        is_visible, _ = _check_entity_visibility(
            detail_def.hidden, detail_def.find_condition, state.flags
        )
        return is_visible

    def is_npc_visible(
        self,
        location: "Location",
        npc_id: str,
        world: "WorldData",
        state: "GameStateProtocol",
    ) -> bool:
        """Check if an NPC is visible to the player.

        An NPC is visible if:
        - It has a placement at the location, AND
        - The placement is not hidden OR its find_condition is met, AND
        - The NPC passes presence checks (location_changes, appears_when)

        Args:
            location: The location to check NPCs for
            npc_id: The NPC ID to check
            world: World data for NPC lookups
            state: Current game state

        Returns:
            True if the NPC is visible, False otherwise
        """
        # Check if NPC has a placement at this location
        if npc_id not in location.npc_placements:
            return False

        placement = location.npc_placements[npc_id]

        # Check placement visibility (hidden + find_condition)
        is_visible, _ = _check_entity_visibility(
            placement.hidden, placement.find_condition, state.flags
        )
        if not is_visible:
            return False

        # Check NPC-level presence (location_changes, appears_when)
        npc = world.get_npc(npc_id)
        if not npc:
            return False

        npc_visible, _, _ = self._analyze_npc_visibility(
            npc, npc_id, state.current_location, state
        )
        return npc_visible

    # =========================================================================
    # Debug Snapshot Methods
    # =========================================================================
    #
    # These methods build a complete view of location state for debugging,
    # showing ALL entities with their visibility status (not just visible ones).
    #
    # EXTENSIBILITY: When adding new visibility rules or world model fields,
    # update the corresponding _get_*_debug methods below.
    # See docs/DEBUG_SNAPSHOT.md for the full pattern.
    # =========================================================================

    def build_debug_snapshot(
        self,
        state: "GameStateProtocol",
        world: "WorldData",
    ) -> LocationDebugSnapshot:
        """Build complete debug snapshot with ALL entities and their visibility status.

        Unlike build_snapshot() which filters to visible entities only, this method
        returns everything at the current location with status flags indicating
        why each entity is visible or hidden.

        This is the single source of truth for merging world definitions with
        game state. Used by the debug UI, and can be reused by other components
        that need complete location information.

        Args:
            state: Current game state
            world: World data for entity definitions

        Returns:
            LocationDebugSnapshot with all entities and their status
        """
        location = world.get_location(state.current_location)

        if not location:
            # Fallback for missing location
            return LocationDebugSnapshot(
                location_id=state.current_location,
                name="Unknown Location",
                atmosphere="",
            )

        # Build debug info for all entity types
        # Each method returns ALL entities with visibility analysis
        exits = self._get_exits_debug(location, world, state)
        items = self._get_items_debug(location, world, state)
        npcs = self._get_npcs_debug(location, world, state)
        interactions = self._get_interactions_debug(location)

        # Build details dict from DetailDefinition objects
        details = {
            key: detail_def.scene_description
            for key, detail_def in (location.details or {}).items()
        }

        # Build requires info if location has access requirements
        requires = None
        if location.requires:
            requires = {}
            if location.requires.flag:
                requires["flag"] = location.requires.flag
            if location.requires.item:
                requires["item"] = location.requires.item

        return LocationDebugSnapshot(
            location_id=state.current_location,
            name=location.name,
            atmosphere=location.atmosphere or "",
            exits=exits,
            items=items,
            npcs=npcs,
            details=details,
            interactions=interactions,
            requires=requires,
        )

    def _get_exits_debug(
        self,
        location: "Location",
        world: "WorldData",
        state: "GameStateProtocol",
    ) -> list[LocationExitDebug]:
        """Get all exits with accessibility and visibility analysis.

        V3: Includes is_hidden field for hidden exit support.

        Args:
            location: The current location
            world: World data for destination lookups
            state: Current game state for checking requirements

        Returns:
            List of LocationExitDebug with accessibility status
        """
        exits = []

        for direction, exit_def in location.exits.items():
            dest_id = exit_def.destination
            dest_location = world.get_location(dest_id)
            dest_name = dest_location.name if dest_location else dest_id

            # V3: Check exit visibility
            is_visible, visibility_reason = _check_entity_visibility(
                exit_def.hidden, exit_def.find_condition, state.flags
            )

            # Check accessibility of destination
            is_accessible = True
            access_reason = "accessible"

            # Check exit-level blocking
            if exit_def.blocked:
                is_accessible = False
                access_reason = f"blocked:{exit_def.blocked_reason or 'unknown'}"
            elif exit_def.locked:
                is_accessible = False
                access_reason = f"locked:{exit_def.requires_key or 'unknown'}"
            elif dest_location and dest_location.requires:
                # Check flag requirement
                if dest_location.requires.flag:
                    if not state.flags.get(dest_location.requires.flag, False):
                        is_accessible = False
                        access_reason = f"requires_flag:{dest_location.requires.flag}"

                # Check item requirement (only if flag passed)
                if is_accessible and dest_location.requires.item:
                    if dest_location.requires.item not in state.inventory:
                        is_accessible = False
                        access_reason = f"requires_item:{dest_location.requires.item}"

            # Determine if destination is known (use shared logic)
            destination_known = self._check_destination_known(
                exit_def, direction, state
            )

            exits.append(
                LocationExitDebug(
                    direction=direction,
                    destination_id=dest_id,
                    destination_name=dest_name,
                    is_accessible=is_accessible,
                    access_reason=access_reason,
                    scene_description=exit_def.scene_description or None,
                    destination_known=destination_known,
                    is_hidden=not is_visible,
                    visibility_reason=visibility_reason,
                )
            )

        return exits

    def _get_items_debug(
        self,
        location: "Location",
        world: "WorldData",
        state: "GameStateProtocol",
    ) -> list[LocationItemDebug]:
        """Get all items at location with visibility analysis (V3).

        V3: Uses item_placements for both presence and visibility.

        Returns ALL items defined at the location (via item_placements),
        not just visible ones. Each item includes its visibility status.

        Visibility rules (in order of precedence):
        1. Item in inventory -> "taken"
        2. Placement hidden with no condition -> "hidden"
        3. Placement hidden with unmet condition -> "condition_not_met:{flag}"
        4. Item visible -> "visible" or "revealed"

        Args:
            location: The current location
            world: World data for item lookups
            state: Current game state

        Returns:
            List of LocationItemDebug with visibility status
        """
        items = []

        # V3: Iterate over item_placements
        for item_id, placement in location.item_placements.items():
            item = world.get_item(item_id)
            if not item:
                continue

            # Determine visibility status
            is_in_inventory = item_id in state.inventory

            if is_in_inventory:
                is_visible = False
                visibility_reason = "taken"
            else:
                # V3: Check visibility from placement
                is_visible, visibility_reason = _check_entity_visibility(
                    placement.hidden, placement.find_condition, state.flags
                )

            items.append(
                LocationItemDebug(
                    item_id=item_id,
                    name=item.name,
                    scene_description=item.scene_description or "",
                    is_visible=is_visible,
                    is_in_inventory=is_in_inventory,
                    visibility_reason=visibility_reason,
                    placement=placement.placement,
                    portable=item.portable,
                    examine_description=item.examine_description or "",
                )
            )

        return items

    def analyze_item_visibility(
        self,
        placement: "ItemPlacement",
        item_id: str,
        state: "GameStateProtocol",
    ) -> tuple[bool, str]:
        """Analyze why an item is visible or hidden (V3).

        V3: Uses ItemPlacement for visibility, not Item.

        This is the single source of truth for item visibility logic.
        Use this method instead of duplicating visibility checks.

        Visibility rules (in order of precedence):
        1. Item in inventory -> False, "taken"
        2. Placement hidden with no condition -> False, "hidden"
        3. Placement hidden with unmet condition -> False, "condition_not_met:{flag}"
        4. Item visible -> True, "visible" or "revealed"

        Args:
            placement: The item placement in the location
            item_id: The item's ID
            state: Current game state

        Returns:
            Tuple of (is_visible, reason_string)
        """
        # Check if in inventory first
        if item_id in state.inventory:
            return False, "taken"

        # V3: Check visibility from placement
        return _check_entity_visibility(
            placement.hidden, placement.find_condition, state.flags
        )

    def _get_npcs_debug(
        self,
        location: "Location",
        world: "WorldData",
        state: "GameStateProtocol",
    ) -> list[LocationNPCDebug]:
        """Get all NPCs at location with visibility analysis (V3).

        V3: Uses npc_placements for presence and visibility.

        Returns NPCs that are defined at this location via npc_placements,
        along with their visibility status.

        Visibility rules:
        1. Placement hidden with no condition -> "hidden"
        2. Placement hidden with unmet condition -> "condition_not_met:{flag}"
        3. NPC visible -> "visible" or "revealed"

        Args:
            location: The current location
            world: World data for NPC lookups
            state: Current game state

        Returns:
            List of LocationNPCDebug with visibility status
        """
        npcs = []
        location_id = state.current_location

        # V3: Iterate over npc_placements (keys define which NPCs are here)
        for npc_id, placement in location.npc_placements.items():
            npc = world.get_npc(npc_id)
            if not npc:
                continue

            # V3: Check visibility from placement
            is_visible, visibility_reason = _check_entity_visibility(
                placement.hidden, placement.find_condition, state.flags
            )

            # Check NPC-level visibility (location_changes, appears_when)
            if is_visible:
                npc_visible, npc_reason, _ = self._analyze_npc_visibility(
                    npc, npc_id, location_id, state
                )
                if not npc_visible:
                    is_visible = False
                    visibility_reason = npc_reason

            npcs.append(
                LocationNPCDebug(
                    npc_id=npc_id,
                    name=npc.name,
                    role=npc.role or "",
                    appearance=npc.appearance or "",
                    is_visible=is_visible,
                    visibility_reason=visibility_reason,
                    placement=placement.placement,
                    current_location=location_id if is_visible else None,
                )
            )

        return npcs

    def _analyze_npc_visibility(
        self,
        npc: "NPC",
        npc_id: str,
        location_id: str,
        state: "GameStateProtocol",
    ) -> tuple[bool, str, str | None]:
        """Analyze why an NPC is visible or hidden.

        Args:
            npc: The NPC definition
            npc_id: The NPC's ID
            location_id: The current location ID
            state: Current game state

        Returns:
            Tuple of (is_visible, reason_string, current_location)
        """
        # Determine NPC's current location considering location_changes
        current_loc = npc.location
        has_location_override = False

        for change in npc.location_changes:
            if state.flags.get(change.when_flag, False):
                current_loc = change.move_to
                has_location_override = True

        # Check if NPC was removed (move_to: null)
        if current_loc is None and has_location_override:
            return False, "removed", None

        # Check if NPC is at a different location
        if has_location_override:
            if current_loc != location_id:
                return False, f"wrong_location:{current_loc}", current_loc
        else:
            # For roaming NPCs, check both single location and locations list
            is_here = current_loc == location_id or location_id in npc.locations
            if not is_here:
                return False, f"wrong_location:{current_loc}", current_loc

        # Check appears_when conditions
        if npc.appears_when:
            for condition in npc.appears_when:
                if condition.condition == "has_flag":
                    flag_name = str(condition.value)
                    if not state.flags.get(flag_name, False):
                        return (
                            False,
                            f"condition_not_met:has_flag:{flag_name}",
                            current_loc,
                        )
                elif condition.condition == "trust_above":
                    # Trust checking would need npc_trust from state
                    # For now, we'll note it as a condition
                    return (
                        False,
                        f"condition_not_met:trust_above:{condition.value}",
                        current_loc,
                    )

        return True, "visible", current_loc

    def _get_interactions_debug(
        self,
        location: "Location",
    ) -> list[LocationInteractionDebug]:
        """Get all interactions available at the location.

        V3: reveals_exit removed from InteractionEffect.

        Args:
            location: The current location

        Returns:
            List of LocationInteractionDebug
        """
        interactions = []

        if location.interactions:
            for int_id, interaction in location.interactions.items():
                interactions.append(
                    LocationInteractionDebug(
                        interaction_id=int_id,
                        triggers=interaction.triggers,
                        sets_flag=interaction.sets_flag,
                        gives_item=interaction.gives_item,
                        removes_item=interaction.removes_item,
                    )
                )

        return interactions
