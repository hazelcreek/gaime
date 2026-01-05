"""
Two-Phase Engine state management.

This module provides state management specific to the two-phase game engine.
It is completely separate from the classic engine's GameStateManager.

See planning/two-phase-game-loop-spec.md for the full specification.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from app.engine.two_phase.models.state import NarrationEntry, TwoPhaseGameState
from app.models.world import WorldData, Location
from app.engine.world import WorldLoader


class TwoPhaseStateManager:
    """Manages game state for two-phase engine sessions.

    This class handles all state operations for the two-phase engine,
    including world loading, location tracking, and state mutations.

    Attributes:
        session_id: Unique identifier for this session
        world_id: ID of the loaded world
        created_at: When the session was created
        world_data: Loaded world data (shared with classic engine)

    Example:
        >>> manager = TwoPhaseStateManager("cursed-manor")
        >>> state = manager.get_state()
        >>> manager.move_to("library")
    """

    def __init__(self, world_id: str):
        """Initialize a new two-phase game session.

        Args:
            world_id: The ID of the world to load
        """
        self.session_id = str(uuid.uuid4())
        self.world_id = world_id
        self.created_at = datetime.now()

        # Load world data (shared WorldLoader)
        loader = WorldLoader()
        self.world_data: WorldData = loader.load_world(world_id)

        # Initialize game state
        world = self.world_data.world
        starting_location = world.player.starting_location

        self._state = TwoPhaseGameState(
            session_id=self.session_id,
            current_location=starting_location,
            inventory=list(world.player.starting_inventory),
            flags={},
            visited_locations={starting_location},
            container_states={},
            turn_count=0,
            status="playing",
        )

    def get_state(self) -> TwoPhaseGameState:
        """Get the current game state.

        Returns:
            The current TwoPhaseGameState
        """
        return self._state

    def get_world_data(self) -> WorldData:
        """Get the loaded world data.

        Returns:
            The WorldData for this session
        """
        return self.world_data

    def get_current_location(self) -> Location | None:
        """Get the current location object.

        Returns:
            The Location object for the current location, or None if not found
        """
        return self.world_data.get_location(self._state.current_location)

    def is_first_visit(self, location_id: str) -> bool:
        """Check if a location has never been visited.

        Args:
            location_id: The location to check

        Returns:
            True if the player has never visited this location
        """
        return location_id not in self._state.visited_locations

    def move_to(self, location_id: str) -> bool:
        """Move the player to a new location.

        Updates current_location and adds to visited_locations if first visit.

        Args:
            location_id: The destination location ID

        Returns:
            True if this was a first visit, False otherwise
        """
        first_visit = self.is_first_visit(location_id)

        self._state.current_location = location_id
        self._state.visited_locations.add(location_id)

        return first_visit

    def set_flag(self, flag: str, value: bool = True) -> None:
        """Set a world-defined game flag.

        Args:
            flag: The flag name
            value: The flag value (default True)
        """
        self._state.flags[flag] = value

    def get_flag(self, flag: str) -> bool:
        """Get a flag value.

        Args:
            flag: The flag name

        Returns:
            The flag value, or False if not set
        """
        return self._state.flags.get(flag, False)

    def has_item(self, item_id: str) -> bool:
        """Check if player has an item in inventory.

        Args:
            item_id: The item ID to check

        Returns:
            True if the item is in inventory
        """
        return item_id in self._state.inventory

    def add_item(self, item_id: str) -> bool:
        """Add an item to inventory.

        Args:
            item_id: The item ID to add

        Returns:
            True if the item was added, False if already present
        """
        if item_id in self._state.inventory:
            return False
        self._state.inventory.append(item_id)
        return True

    def remove_item(self, item_id: str) -> bool:
        """Remove an item from inventory.

        Args:
            item_id: The item ID to remove

        Returns:
            True if the item was removed, False if not present
        """
        if item_id not in self._state.inventory:
            return False
        self._state.inventory.remove(item_id)
        return True

    def is_container_open(self, container_id: str) -> bool:
        """Check if a container is currently open.

        Args:
            container_id: The container item ID

        Returns:
            True if the container is open, False if closed or unknown
        """
        return self._state.container_states.get(container_id, False)

    def set_container_state(self, container_id: str, is_open: bool) -> None:
        """Set the open/closed state of a container.

        Args:
            container_id: The container item ID
            is_open: True to open, False to close
        """
        self._state.container_states[container_id] = is_open

    def reveal_exit_destination(self, location_id: str, direction: str) -> None:
        """Mark an exit's destination as revealed.

        This is used by on_examine effects and reveal_destination_on_flag to track
        which exit destinations the player has learned about.

        Args:
            location_id: The location where the exit is
            direction: The exit direction (e.g., "north")
        """
        if location_id not in self._state.revealed_exits:
            self._state.revealed_exits[location_id] = set()
        self._state.revealed_exits[location_id].add(direction)

    def is_exit_destination_revealed(self, location_id: str, direction: str) -> bool:
        """Check if an exit's destination has been revealed.

        Args:
            location_id: The location where the exit is
            direction: The exit direction

        Returns:
            True if the destination has been dynamically revealed
        """
        return direction in self._state.revealed_exits.get(location_id, set())

    def increment_turn(self) -> None:
        """Increment the turn counter."""
        self._state.turn_count += 1

    def set_status(self, status: str) -> None:
        """Set the game status.

        Args:
            status: The new status ("playing", "won", "lost")
        """
        if status not in ("playing", "won", "lost"):
            raise ValueError(f"Invalid status: {status}")
        self._state.status = status

    def check_victory(self) -> tuple[bool, str]:
        """Check if victory conditions are met.

        Returns:
            Tuple of (is_victory, ending_narrative)
        """
        world = self.world_data.world

        if not world.victory:
            return False, ""

        victory = world.victory

        # Check location requirement
        if victory.location and self._state.current_location != victory.location:
            return False, ""

        # Check flag requirement
        if victory.flag and not self._state.flags.get(victory.flag, False):
            return False, ""

        # Check item requirement
        if victory.item and victory.item not in self._state.inventory:
            return False, ""

        # All conditions met
        self._state.status = "won"
        return (
            True,
            victory.narrative or "Congratulations! You have completed the adventure.",
        )

    def update_narration_history(self, history: list[NarrationEntry]) -> None:
        """Update the narration history.

        Args:
            history: The new narration history list
        """
        self._state.narration_history = history
