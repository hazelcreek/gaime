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

    from app.models.world import Item, Location, NPC, WorldData

    class GameStateProtocol(Protocol):
        """Protocol for game state."""

        current_location: str
        inventory: list[str]
        flags: dict[str, bool]


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
        visible_details = self._get_visible_details(location)

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
        state: "GameStateProtocol | None" = None,
    ) -> list[VisibleExit]:
        """Get all visible exits from the current location.

        Args:
            location: The current location
            world: World data for destination lookups
            state: Current game state (optional, for destination_known resolution)

        Returns:
            List of VisibleExit objects
        """
        exits = []

        for direction, exit_def in location.exits.items():
            dest_location = world.get_location(exit_def.destination)
            dest_name = dest_location.name if dest_location else exit_def.destination

            # Determine if destination is known:
            # 1. Author set destination_known = True, OR
            # 2. Player has visited the destination
            destination_known = exit_def.destination_known
            if state and hasattr(state, "visited_locations"):
                if exit_def.destination in state.visited_locations:
                    destination_known = True

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
                    description=item.scene_description
                    or item.examine_description
                    or None,
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
            for detail_id, detail_def in location.details.items():
                details.append(
                    VisibleEntity(
                        id=detail_id,
                        name=detail_def.name,
                        description=detail_def.scene_description,
                        is_new=False,
                    )
                )

        return details

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
        """Get all exits with accessibility analysis.

        Analyzes each exit to determine if it's accessible and why.

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

            # Determine if destination is known
            destination_known = exit_def.destination_known
            if hasattr(state, "visited_locations"):
                if dest_id in state.visited_locations:
                    destination_known = True

            exits.append(
                LocationExitDebug(
                    direction=direction,
                    destination_id=dest_id,
                    destination_name=dest_name,
                    is_accessible=is_accessible,
                    access_reason=access_reason,
                    scene_description=exit_def.scene_description or None,
                    destination_known=destination_known,
                )
            )

        return exits

    def _get_items_debug(
        self,
        location: "Location",
        world: "WorldData",
        state: "GameStateProtocol",
    ) -> list[LocationItemDebug]:
        """Get all items at location with visibility analysis.

        Returns ALL items defined at the location, not just visible ones.
        Each item includes its visibility status and the reason.

        Visibility rules (in order of precedence):
        1. Item in inventory -> "taken"
        2. Item hidden with no condition -> "hidden"
        3. Item hidden with unmet condition -> "condition_not_met:{flag}"
        4. Item visible -> "visible"

        Args:
            location: The current location
            world: World data for item lookups
            state: Current game state

        Returns:
            List of LocationItemDebug with visibility status
        """
        items = []

        for item_id in location.items:
            item = world.get_item(item_id)
            if not item:
                continue

            # Determine visibility status
            is_in_inventory = item_id in state.inventory
            is_visible, visibility_reason = self.analyze_item_visibility(
                item, item_id, state
            )

            # Get placement from location if available
            placement = (
                location.item_placements.get(item_id)
                if location.item_placements
                else None
            )

            items.append(
                LocationItemDebug(
                    item_id=item_id,
                    name=item.name,
                    scene_description=item.scene_description or "",
                    is_visible=is_visible,
                    is_in_inventory=is_in_inventory,
                    visibility_reason=visibility_reason,
                    placement=placement,
                    portable=item.portable,
                    examine_description=item.examine_description or "",
                )
            )

        return items

    def analyze_item_visibility(
        self,
        item: "Item",
        item_id: str,
        state: "GameStateProtocol",
    ) -> tuple[bool, str]:
        """Analyze why an item is visible or hidden.

        This is the single source of truth for item visibility logic.
        Use this method instead of duplicating visibility checks.

        Visibility rules (in order of precedence):
        1. Item in inventory -> False, "taken"
        2. Item hidden with no condition -> False, "hidden"
        3. Item hidden with unmet condition -> False, "condition_not_met:{flag}"
        4. Item visible -> True, "visible"

        Args:
            item: The item definition
            item_id: The item's ID
            state: Current game state

        Returns:
            Tuple of (is_visible, reason_string)
        """
        # Check if in inventory first
        if item_id in state.inventory:
            return False, "taken"

        # Check hidden status
        if item.hidden:
            if not item.find_condition:
                return False, "hidden"

            required_flag = item.find_condition.get("requires_flag")
            if required_flag:
                if state.flags.get(required_flag, False):
                    return True, "visible"
                else:
                    return False, f"condition_not_met:{required_flag}"
            else:
                return False, "hidden"

        return True, "visible"

    def _get_npcs_debug(
        self,
        location: "Location",
        world: "WorldData",
        state: "GameStateProtocol",
    ) -> list[LocationNPCDebug]:
        """Get all NPCs that could be at location with visibility analysis.

        Returns NPCs that are defined for this location (via npc.location,
        npc.locations, or Location.npcs), along with their visibility status.

        Visibility rules:
        1. NPC removed via location_changes -> "removed"
        2. NPC moved to different location -> "wrong_location:{actual_loc}"
        3. NPC appears_when condition not met -> "condition_not_met:{condition}"
        4. NPC visible -> "visible"

        Args:
            location: The current location
            world: World data for NPC lookups
            state: Current game state

        Returns:
            List of LocationNPCDebug with visibility status
        """
        npcs = []
        location_id = state.current_location

        # Collect all NPCs that could be at this location
        for npc_id, npc in world.npcs.items():
            # Check if NPC is associated with this location
            is_base_location = npc.location == location_id
            is_roaming_location = location_id in npc.locations
            is_in_location_npcs = npc_id in location.npcs

            if not (is_base_location or is_roaming_location or is_in_location_npcs):
                continue

            # Analyze visibility
            is_visible, visibility_reason, current_location = (
                self._analyze_npc_visibility(npc, npc_id, location_id, state)
            )

            # Get placement from location if available
            placement = (
                location.npc_placements.get(npc_id) if location.npc_placements else None
            )

            npcs.append(
                LocationNPCDebug(
                    npc_id=npc_id,
                    name=npc.name,
                    role=npc.role or "",
                    appearance=npc.appearance or "",
                    is_visible=is_visible,
                    visibility_reason=visibility_reason,
                    placement=placement,
                    current_location=current_location,
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
                        reveals_exit=interaction.reveals_exit,
                        gives_item=interaction.gives_item,
                        removes_item=interaction.removes_item,
                    )
                )

        return interactions
