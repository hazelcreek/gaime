"""Unit tests for exit destination reveal mechanics.

Tests cover:
- reveal_destination_on_flag reveals destination when flag is set
- reveal_destination_on_examine reveals destination when exit is examined
- revealed_exits state persists and is used in visibility checks
- Visiting a location automatically reveals destination from that location
"""

import pytest

from app.engine.two_phase.visibility import DefaultVisibilityResolver
from app.engine.two_phase.models.state import TwoPhaseGameState
from app.engine.two_phase.state import TwoPhaseStateManager


class TestDestinationRevealMechanics:
    """Tests for destination reveal mechanics."""

    @pytest.fixture
    def resolver(self) -> DefaultVisibilityResolver:
        """Create visibility resolver instance."""
        return DefaultVisibilityResolver()

    @pytest.fixture
    def state(self) -> TwoPhaseGameState:
        """Create test state at start_room."""
        return TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=[],
            flags={},
            visited_locations={"start_room"},
            revealed_exits={},
        )

    # reveal_destination_on_flag tests

    def test_reveal_destination_on_flag_destination_unknown_without_flag(
        self, resolver, state, sample_world_data
    ) -> None:
        """Exit destination is unknown when reveal_destination_on_flag is not set."""
        # East exit has reveal_destination_on_flag: found_secret_door
        state.flags = {}

        snapshot = resolver.build_snapshot(state, sample_world_data)

        east_exit = next(
            (e for e in snapshot.visible_exits if e.direction == "east"), None
        )
        assert east_exit is not None
        assert east_exit.destination_known is False

    def test_reveal_destination_on_flag_destination_known_with_flag(
        self, resolver, state, sample_world_data
    ) -> None:
        """Exit destination is known when reveal_destination_on_flag is set."""
        # East exit has reveal_destination_on_flag: found_secret_door
        state.flags = {"found_secret_door": True}

        snapshot = resolver.build_snapshot(state, sample_world_data)

        east_exit = next(
            (e for e in snapshot.visible_exits if e.direction == "east"), None
        )
        assert east_exit is not None
        assert east_exit.destination_known is True

    # revealed_exits state tests

    def test_revealed_exits_makes_destination_known(
        self, resolver, state, sample_world_data
    ) -> None:
        """Exit destination is known when in revealed_exits."""
        # North exit has destination_known: false but we reveal it
        state.revealed_exits = {"start_room": {"north"}}

        snapshot = resolver.build_snapshot(state, sample_world_data)

        north_exit = next(
            (e for e in snapshot.visible_exits if e.direction == "north"), None
        )
        assert north_exit is not None
        assert north_exit.destination_known is True

    def test_revealed_exits_location_specific(
        self, resolver, state, sample_world_data
    ) -> None:
        """revealed_exits only applies to the specific location."""
        # Reveal north exit in a different location
        state.revealed_exits = {"other_room": {"north"}}

        snapshot = resolver.build_snapshot(state, sample_world_data)

        north_exit = next(
            (e for e in snapshot.visible_exits if e.direction == "north"), None
        )
        assert north_exit is not None
        # Should NOT be known since we only revealed it in other_room
        assert north_exit.destination_known is False

    # visited_locations auto-reveal tests

    def test_visited_location_reveals_destination(
        self, resolver, state, sample_world_data
    ) -> None:
        """Visiting a location reveals exit destination to that location."""
        # North exit leads to locked_room
        state.visited_locations = {"start_room", "locked_room"}

        snapshot = resolver.build_snapshot(state, sample_world_data)

        north_exit = next(
            (e for e in snapshot.visible_exits if e.direction == "north"), None
        )
        assert north_exit is not None
        assert north_exit.destination_known is True

    def test_unvisited_location_destination_unknown(
        self, resolver, state, sample_world_data
    ) -> None:
        """Destination is unknown if player hasn't visited it."""
        # Only start_room visited
        state.visited_locations = {"start_room"}

        snapshot = resolver.build_snapshot(state, sample_world_data)

        north_exit = next(
            (e for e in snapshot.visible_exits if e.direction == "north"), None
        )
        assert north_exit is not None
        # destination_known is False and we haven't visited locked_room
        assert north_exit.destination_known is False

    # StateManager reveal methods tests

    def test_state_manager_reveal_exit_destination(self, sample_world_data) -> None:
        """StateManager.reveal_exit_destination() adds to revealed_exits."""
        state_manager = TwoPhaseStateManager.__new__(TwoPhaseStateManager)
        state_manager._state = TwoPhaseGameState(
            session_id="test",
            current_location="start_room",
            inventory=[],
            flags={},
            visited_locations={"start_room"},
            revealed_exits={},
        )
        state_manager.world_data = sample_world_data

        state_manager.reveal_exit_destination("start_room", "north")

        assert "start_room" in state_manager._state.revealed_exits
        assert "north" in state_manager._state.revealed_exits["start_room"]

    def test_state_manager_is_exit_destination_revealed(
        self, sample_world_data
    ) -> None:
        """StateManager.is_exit_destination_revealed() checks revealed_exits."""
        state_manager = TwoPhaseStateManager.__new__(TwoPhaseStateManager)
        state_manager._state = TwoPhaseGameState(
            session_id="test",
            current_location="start_room",
            inventory=[],
            flags={},
            visited_locations={"start_room"},
            revealed_exits={"start_room": {"north"}},
        )
        state_manager.world_data = sample_world_data

        assert state_manager.is_exit_destination_revealed("start_room", "north") is True
        assert state_manager.is_exit_destination_revealed("start_room", "east") is False
        assert (
            state_manager.is_exit_destination_revealed("other_room", "north") is False
        )

    # Debug snapshot tests

    def test_debug_snapshot_uses_destination_known_logic(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot uses same destination_known logic as build_snapshot."""
        # Set flag to reveal east exit destination
        state.flags = {"found_secret_door": True}

        debug = resolver.build_debug_snapshot(state, sample_world_data)

        east_exit = next((e for e in debug.exits if e.direction == "east"), None)
        assert east_exit is not None
        assert east_exit.destination_known is True
