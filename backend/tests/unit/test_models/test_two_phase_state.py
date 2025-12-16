"""Unit tests for TwoPhaseGameState model.

Tests cover:
- Model creation with defaults
- visited_locations set behavior
- container_states tracking
- Field validation
"""

import pytest
from pydantic import ValidationError

from app.models.two_phase_state import TwoPhaseGameState, TwoPhaseActionResponse
from app.models.game import LLMDebugInfo


class TestTwoPhaseGameState:
    """Tests for TwoPhaseGameState model."""

    def test_create_with_required_fields(self) -> None:
        """State can be created with just required fields."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
        )

        assert state.session_id == "test-session"
        assert state.current_location == "start_room"

    def test_default_values(self) -> None:
        """State has correct default values."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
        )

        assert state.inventory == []
        assert state.flags == {}
        assert state.visited_locations == set()
        assert state.container_states == {}
        assert state.turn_count == 0
        assert state.status == "playing"

    def test_visited_locations_is_set(self) -> None:
        """visited_locations is a set for efficient membership checking."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            visited_locations={"start_room", "library"},
        )

        assert isinstance(state.visited_locations, set)
        assert "start_room" in state.visited_locations
        assert "library" in state.visited_locations
        assert "kitchen" not in state.visited_locations

    def test_visited_locations_deduplication(self) -> None:
        """visited_locations automatically deduplicates entries."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            visited_locations={"start_room", "start_room", "library"},
        )

        assert len(state.visited_locations) == 2

    def test_container_states_tracking(self) -> None:
        """container_states tracks open/closed state of containers."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            container_states={"desk_drawer": True, "chest": False},
        )

        assert state.container_states["desk_drawer"] is True
        assert state.container_states["chest"] is False

    def test_flags_are_boolean(self) -> None:
        """flags dict stores boolean values."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            flags={"door_unlocked": True, "talked_to_npc": False},
        )

        assert state.flags["door_unlocked"] is True
        assert state.flags["talked_to_npc"] is False

    def test_inventory_is_list(self) -> None:
        """inventory is a list of item IDs."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=["key", "torch", "map"],
        )

        assert len(state.inventory) == 3
        assert "key" in state.inventory

    def test_status_values(self) -> None:
        """status can be playing, won, or lost."""
        for status in ("playing", "won", "lost"):
            state = TwoPhaseGameState(
                session_id="test-session",
                current_location="start_room",
                status=status,
            )
            assert state.status == status


class TestTwoPhaseActionResponse:
    """Tests for TwoPhaseActionResponse model."""

    def test_create_minimal_response(self) -> None:
        """Response can be created with minimal fields."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
        )

        response = TwoPhaseActionResponse(
            narrative="You stand in a dark room.",
            state=state,
        )

        assert response.narrative == "You stand in a dark room."
        assert response.state == state
        assert response.events == []
        assert response.game_complete is False
        assert response.ending_narrative is None
        assert response.llm_debug is None

    def test_response_with_events(self) -> None:
        """Response can include events list."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="library",
        )

        events = [
            {"type": "location_changed", "subject": "library"},
        ]

        response = TwoPhaseActionResponse(
            narrative="You enter the library.",
            state=state,
            events=events,
        )

        assert len(response.events) == 1
        assert response.events[0]["type"] == "location_changed"

    def test_response_game_complete(self) -> None:
        """Response can indicate game completion."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="end_room",
            status="won",
        )

        response = TwoPhaseActionResponse(
            narrative="You found the treasure!",
            state=state,
            game_complete=True,
            ending_narrative="Congratulations, adventurer!",
        )

        assert response.game_complete is True
        assert response.ending_narrative == "Congratulations, adventurer!"

    def test_response_with_debug_info(self) -> None:
        """Response can include LLM debug info."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
        )

        debug_info = LLMDebugInfo(
            system_prompt="You are a narrator.",
            user_prompt="Describe the room.",
            raw_response='{"narrative": "A dark room."}',
            parsed_response={"narrative": "A dark room."},
            model="gemini-1.5-flash",
            timestamp="2024-01-01T00:00:00",
        )

        response = TwoPhaseActionResponse(
            narrative="A dark room.",
            state=state,
            llm_debug=debug_info,
        )

        assert response.llm_debug is not None
        assert response.llm_debug.model == "gemini-1.5-flash"

