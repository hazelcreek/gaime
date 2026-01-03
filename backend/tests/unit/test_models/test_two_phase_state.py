"""Unit tests for TwoPhaseGameState model.

Tests cover:
- Model creation with defaults
- visited_locations set behavior
- container_states tracking
- Field validation
- NarrationEntry model
- narration_history tracking
"""

from app.engine.two_phase.models.state import (
    NarrationEntry,
    TwoPhaseGameState,
    TwoPhaseActionResponse,
    TwoPhaseDebugInfo,
)


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
        assert state.narration_history == []

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


class TestNarrationEntry:
    """Tests for NarrationEntry model."""

    def test_create_narration_entry(self) -> None:
        """NarrationEntry can be created with all fields."""
        entry = NarrationEntry(
            text="You stand in a dimly lit hallway.",
            location_id="main_hallway",
            turn=3,
            event_type="scene_browsed",
        )

        assert entry.text == "You stand in a dimly lit hallway."
        assert entry.location_id == "main_hallway"
        assert entry.turn == 3
        assert entry.event_type == "scene_browsed"

    def test_narration_entry_serialization(self) -> None:
        """NarrationEntry can be serialized to dict."""
        entry = NarrationEntry(
            text="The lockers line the walls.",
            location_id="locker_room",
            turn=5,
            event_type="location_changed",
        )

        data = entry.model_dump()
        assert data["text"] == "The lockers line the walls."
        assert data["location_id"] == "locker_room"
        assert data["turn"] == 5
        assert data["event_type"] == "location_changed"


class TestNarrationHistory:
    """Tests for narration_history in TwoPhaseGameState."""

    def test_narration_history_empty_by_default(self) -> None:
        """narration_history is empty by default."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
        )

        assert state.narration_history == []
        assert isinstance(state.narration_history, list)

    def test_narration_history_with_entries(self) -> None:
        """narration_history can contain NarrationEntry objects."""
        entries = [
            NarrationEntry(
                text="Opening scene...",
                location_id="main_hallway",
                turn=0,
                event_type="scene_browsed",
            ),
            NarrationEntry(
                text="You examine the lockers.",
                location_id="main_hallway",
                turn=1,
                event_type="item_examined",
            ),
        ]

        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="main_hallway",
            narration_history=entries,
        )

        assert len(state.narration_history) == 2
        assert state.narration_history[0].event_type == "scene_browsed"
        assert state.narration_history[1].turn == 1

    def test_narration_history_preserves_order(self) -> None:
        """narration_history preserves insertion order."""
        entries = [
            NarrationEntry(
                text=f"Turn {i}", location_id="room", turn=i, event_type="test"
            )
            for i in range(5)
        ]

        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="room",
            narration_history=entries,
        )

        for i, entry in enumerate(state.narration_history):
            assert entry.turn == i


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
        assert response.pipeline_debug is None

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
        """Response can include pipeline debug info."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
        )

        debug_info = TwoPhaseDebugInfo(
            raw_input="go north",
            parser_type="rule_based",
            parsed_intent={"action_type": "move", "direction": "north"},
            validation_result={"valid": True},
            events=[{"type": "location_changed", "subject": "library"}],
        )

        response = TwoPhaseActionResponse(
            narrative="A dark room.",
            state=state,
            pipeline_debug=debug_info,
        )

        assert response.pipeline_debug is not None
        assert response.pipeline_debug.parser_type == "rule_based"
