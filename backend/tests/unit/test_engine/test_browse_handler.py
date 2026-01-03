"""Unit tests for BrowseHandler.

Tests cover:
- validate() always returns valid
- execute() is a no-op (doesn't change state)
- create_event() returns SCENE_BROWSED event
- create_event() includes visible entities when snapshot provided
- checks_victory is False
"""

import pytest

from app.engine.two_phase.handlers.browse import BrowseHandler
from app.engine.two_phase.visibility import DefaultVisibilityResolver
from app.engine.two_phase.models.intent import ActionIntent, ActionType
from app.engine.two_phase.models.event import EventType
from app.engine.two_phase.models.state import TwoPhaseGameState
from app.engine.two_phase.models.perception import (
    PerceptionSnapshot,
    VisibleEntity,
    VisibleExit,
)


class TestBrowseHandler:
    """Tests for BrowseHandler."""

    @pytest.fixture
    def visibility_resolver(self) -> DefaultVisibilityResolver:
        """Create visibility resolver instance."""
        return DefaultVisibilityResolver()

    @pytest.fixture
    def handler(self, visibility_resolver) -> BrowseHandler:
        """Create handler instance."""
        return BrowseHandler(visibility_resolver)

    @pytest.fixture
    def state(self) -> TwoPhaseGameState:
        """Create test state at start_room."""
        return TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=["test_key"],
            flags={},
            visited_locations={"start_room"},
        )

    @pytest.fixture
    def browse_intent(self) -> ActionIntent:
        """Create a BROWSE intent."""
        return ActionIntent(
            action_type=ActionType.BROWSE,
            raw_input="look around",
            verb="look",
            target_id="",
        )

    @pytest.fixture
    def sample_snapshot(self) -> PerceptionSnapshot:
        """Create a sample perception snapshot."""
        return PerceptionSnapshot(
            location_id="start_room",
            location_name="Starting Room",
            location_atmosphere="A simple room.",
            visible_items=[
                VisibleEntity(id="container_box", name="Wooden Box"),
            ],
            visible_npcs=[
                VisibleEntity(id="test_npc", name="Test Guide"),
            ],
            visible_exits=[
                VisibleExit(direction="north", destination_name="Locked Room"),
                VisibleExit(direction="east", destination_name="Secret Room"),
            ],
        )

    # Attribute tests

    def test_checks_victory_is_false(self, handler) -> None:
        """BrowseHandler.checks_victory should be False."""
        assert handler.checks_victory is False

    # Validate tests

    def test_validate_always_returns_valid(
        self, handler, browse_intent, state, sample_world_data
    ) -> None:
        """validate() always returns a valid result for BROWSE."""
        result = handler.validate(browse_intent, state, sample_world_data)

        assert result.valid is True

    def test_validate_valid_regardless_of_location(
        self, handler, browse_intent, sample_world_data
    ) -> None:
        """validate() returns valid even at unknown location."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="nonexistent_room",
        )

        result = handler.validate(browse_intent, state, sample_world_data)

        assert result.valid is True

    # Execute tests

    def test_execute_does_not_change_state(
        self, handler, browse_intent, state, sample_world_data
    ) -> None:
        """execute() is a no-op - doesn't change state."""
        from unittest.mock import MagicMock

        result = handler.validate(browse_intent, state, sample_world_data)

        # Create a mock state manager
        mock_state_manager = MagicMock()

        # Execute should not call any state methods
        handler.execute(browse_intent, result, mock_state_manager)

        # Verify no state-changing methods were called
        mock_state_manager.move_to.assert_not_called()
        mock_state_manager.add_item.assert_not_called()
        mock_state_manager.set_flag.assert_not_called()

    # Create event tests

    def test_create_event_returns_scene_browsed(
        self, handler, browse_intent, state, sample_world_data
    ) -> None:
        """create_event() returns SCENE_BROWSED event."""
        result = handler.validate(browse_intent, state, sample_world_data)

        event = handler.create_event(browse_intent, result, state, sample_world_data)

        assert event.type == EventType.SCENE_BROWSED

    def test_create_event_subject_is_current_location(
        self, handler, browse_intent, state, sample_world_data
    ) -> None:
        """create_event() subject is the current location."""
        result = handler.validate(browse_intent, state, sample_world_data)

        event = handler.create_event(browse_intent, result, state, sample_world_data)

        assert event.subject == "start_room"

    def test_create_event_first_visit_is_false(
        self, handler, browse_intent, state, sample_world_data
    ) -> None:
        """create_event() sets first_visit=False (manual browse is never first visit)."""
        result = handler.validate(browse_intent, state, sample_world_data)

        event = handler.create_event(browse_intent, result, state, sample_world_data)

        assert event.context["first_visit"] is False

    def test_create_event_is_manual_browse(
        self, handler, browse_intent, state, sample_world_data
    ) -> None:
        """create_event() sets is_manual_browse=True."""
        result = handler.validate(browse_intent, state, sample_world_data)

        event = handler.create_event(browse_intent, result, state, sample_world_data)

        assert event.context["is_manual_browse"] is True

    def test_create_event_with_snapshot_includes_items(
        self, handler, browse_intent, state, sample_world_data, sample_snapshot
    ) -> None:
        """create_event() includes visible_items when snapshot provided."""
        result = handler.validate(browse_intent, state, sample_world_data)

        event = handler.create_event(
            browse_intent, result, state, sample_world_data, snapshot=sample_snapshot
        )

        assert "visible_items" in event.context
        assert "Wooden Box" in event.context["visible_items"]

    def test_create_event_with_snapshot_includes_npcs(
        self, handler, browse_intent, state, sample_world_data, sample_snapshot
    ) -> None:
        """create_event() includes visible_npcs when snapshot provided."""
        result = handler.validate(browse_intent, state, sample_world_data)

        event = handler.create_event(
            browse_intent, result, state, sample_world_data, snapshot=sample_snapshot
        )

        assert "visible_npcs" in event.context
        assert "Test Guide" in event.context["visible_npcs"]

    def test_create_event_with_snapshot_includes_exits(
        self, handler, browse_intent, state, sample_world_data, sample_snapshot
    ) -> None:
        """create_event() includes visible_exits when snapshot provided."""
        result = handler.validate(browse_intent, state, sample_world_data)

        event = handler.create_event(
            browse_intent, result, state, sample_world_data, snapshot=sample_snapshot
        )

        assert "visible_exits" in event.context
        exit_directions = [e["direction"] for e in event.context["visible_exits"]]
        assert "north" in exit_directions
        assert "east" in exit_directions

    def test_create_event_without_snapshot_no_visible_entities(
        self, handler, browse_intent, state, sample_world_data
    ) -> None:
        """create_event() without snapshot doesn't include entity lists."""
        result = handler.validate(browse_intent, state, sample_world_data)

        event = handler.create_event(browse_intent, result, state, sample_world_data)

        assert "visible_items" not in event.context
        assert "visible_npcs" not in event.context
        assert "visible_exits" not in event.context
