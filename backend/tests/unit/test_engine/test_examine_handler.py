"""Unit tests for ExamineHandler.

Tests cover:
- on_examine effect processing (sets_flag, reveals_exit_destination)
- Event creation with effect details
- Exit examination with destination reveal
"""

import pytest

from app.engine.two_phase.handlers.examine import ExamineHandler
from app.engine.two_phase.visibility import DefaultVisibilityResolver
from app.engine.two_phase.models.intent import ActionIntent, ActionType
from app.engine.two_phase.models.event import EventType
from app.engine.two_phase.models.state import TwoPhaseGameState
from app.engine.two_phase.models.validation import valid_result
from app.engine.two_phase.state import TwoPhaseStateManager


class TestExamineHandler:
    """Tests for ExamineHandler."""

    @pytest.fixture
    def visibility_resolver(self) -> DefaultVisibilityResolver:
        """Create visibility resolver instance."""
        return DefaultVisibilityResolver()

    @pytest.fixture
    def handler(self, visibility_resolver) -> ExamineHandler:
        """Create handler instance with visibility resolver."""
        return ExamineHandler(visibility_resolver)

    @pytest.fixture
    def state(self) -> TwoPhaseGameState:
        """Create test state at start_room."""
        return TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=["test_key"],
            flags={},
            visited_locations={"start_room"},
            revealed_exits={},
        )

    @pytest.fixture
    def examine_intent(self) -> callable:
        """Factory for creating EXAMINE intents."""

        def _create(target_id: str) -> ActionIntent:
            return ActionIntent(
                action_type=ActionType.EXAMINE,
                raw_input=f"examine {target_id}",
                verb="examine",
                target_id=target_id,
            )

        return _create

    # on_examine effect processing tests

    def test_execute_sets_flag(
        self, handler, examine_intent, sample_world_data
    ) -> None:
        """execute() sets flag from on_examine effect."""
        # Create a mock state manager
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

        # Create validation result with on_examine sets_flag
        result = valid_result(
            entity_type="detail",
            entity_id="box",
            entity_name="Wooden Box",
            description="A wooden box",
            on_examine={"sets_flag": "box_opened", "narrative_hint": "The box opens"},
        )

        intent = examine_intent("box")
        handler.execute(intent, result, state_manager)

        # Flag should be set
        assert state_manager.get_flag("box_opened") is True

    def test_execute_reveals_exit_destination(
        self, handler, examine_intent, sample_world_data
    ) -> None:
        """execute() reveals exit destination from on_examine effect."""
        # Create a mock state manager
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

        # Create validation result with reveal_destination_on_examine
        result = valid_result(
            entity_type="exit",
            entity_id="north",
            entity_name="Exit to north",
            description="A door",
            on_examine={
                "reveal_destination_on_examine": True,
                "direction": "north",
            },
        )

        intent = examine_intent("north")
        handler.execute(intent, result, state_manager)

        # Exit destination should be revealed
        assert state_manager.is_exit_destination_revealed("start_room", "north")

    def test_execute_no_effect_when_no_on_examine(
        self, handler, examine_intent, sample_world_data
    ) -> None:
        """execute() does nothing when no on_examine effects."""
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

        result = valid_result(
            entity_type="item",
            entity_id="container_box",
            entity_name="Wooden Box",
            description="A box",
        )

        intent = examine_intent("container_box")
        handler.execute(intent, result, state_manager)

        # No flags should be set
        assert len(state_manager._state.flags) == 0

    # Event creation tests

    def test_create_event_detail_examined(
        self, handler, state, sample_world_data, examine_intent
    ) -> None:
        """create_event() returns DETAIL_EXAMINED event for details."""
        result = valid_result(
            entity_type="detail",
            entity_id="box",
            entity_name="Wooden Box",
            description="A wooden box",
            on_examine={"sets_flag": "box_opened", "narrative_hint": "The box opens"},
        )

        intent = examine_intent("box")
        event = handler.create_event(intent, result, state, sample_world_data)

        assert event.type == EventType.DETAIL_EXAMINED
        assert event.subject == "box"
        assert event.context["entity_name"] == "Wooden Box"
        assert event.context.get("narrative_hint") == "The box opens"

    def test_create_event_exit_examined(
        self, handler, state, sample_world_data, examine_intent
    ) -> None:
        """create_event() returns EXIT_EXAMINED event for exits."""
        result = valid_result(
            entity_type="exit",
            entity_id="north",
            entity_name="Exit to north",
            description="A door",
            destination_id="locked_room",
            destination_name="Locked Room",
            destination_known=False,
            on_examine={"reveal_destination_on_examine": True, "direction": "north"},
        )

        intent = examine_intent("north")
        event = handler.create_event(intent, result, state, sample_world_data)

        assert event.type == EventType.EXIT_EXAMINED
        assert event.subject == "north"
        assert event.context["destination_id"] == "locked_room"
        assert event.context["destination_name"] == "Locked Room"
        assert event.context["destination_revealed"] is True

    def test_create_event_item_examined(
        self, handler, state, sample_world_data, examine_intent
    ) -> None:
        """create_event() returns ITEM_EXAMINED event for items."""
        result = valid_result(
            entity_type="item",
            entity_id="test_key",
            entity_name="Test Key",
            description="A brass key",
            in_inventory=True,
        )

        intent = examine_intent("test_key")
        event = handler.create_event(intent, result, state, sample_world_data)

        assert event.type == EventType.ITEM_EXAMINED
        assert event.subject == "test_key"
        assert event.context["entity_name"] == "Test Key"
        assert event.context["in_inventory"] is True

    # Handler attributes

    def test_checks_victory_is_true(self, handler) -> None:
        """Handler checks_victory should be True since on_examine can set flags."""
        assert handler.checks_victory is True
