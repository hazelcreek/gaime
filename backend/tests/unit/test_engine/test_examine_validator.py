"""Unit tests for ExamineValidator.

Tests cover:
- Valid examination of items at location
- Valid examination of location details
- Valid examination of inventory items
- Rejection for hidden items
- Rejection for non-existent targets
- Rejection for items at wrong location
"""

import pytest

from app.engine.two_phase.validators.examine import ExamineValidator
from app.engine.two_phase.models.intent import ActionIntent, ActionType
from app.engine.two_phase.models.event import RejectionCode
from app.engine.two_phase.models.state import TwoPhaseGameState


class TestExamineValidator:
    """Tests for ExamineValidator."""

    @pytest.fixture
    def validator(self) -> ExamineValidator:
        """Create validator instance."""
        return ExamineValidator()

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

    # Valid examination tests

    def test_examine_item_at_location(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining visible item at location succeeds."""
        intent = examine_intent("container_box")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["entity_type"] == "item"
        assert result.context["entity_id"] == "container_box"
        assert result.context["entity_name"] == "Wooden Box"
        assert "description" in result.context

    def test_examine_inventory_item(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining item in inventory succeeds."""
        intent = examine_intent("test_key")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["entity_type"] == "item"
        assert result.context["entity_id"] == "test_key"
        assert result.context["in_inventory"] is True

    def test_examine_location_detail(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining location detail (scenery) succeeds."""
        intent = examine_intent("floor")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["entity_type"] == "detail"
        assert result.context["entity_id"] == "floor"
        assert "floorboards" in result.context["description"].lower()

    def test_examine_walls_detail(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining walls detail succeeds."""
        intent = examine_intent("walls")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["entity_type"] == "detail"
        assert "stone" in result.context["description"].lower()

    # Rejection tests

    def test_hidden_item_not_visible(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Hidden item without condition met is not visible."""
        intent = examine_intent("hidden_gem")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.ITEM_NOT_VISIBLE

    def test_hidden_item_visible_with_flag(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Hidden item is visible when condition flag is set."""
        state.flags["box_opened"] = True
        intent = examine_intent("hidden_gem")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["entity_id"] == "hidden_gem"

    def test_nonexistent_target(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining non-existent target fails."""
        intent = examine_intent("banana")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.TARGET_NOT_FOUND

    def test_item_at_wrong_location(
        self, validator, sample_world_data, examine_intent
    ) -> None:
        """Examining item at different location fails."""
        # Move player to locked_room where container_box is not
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="locked_room",
            inventory=[],
            flags={"door_unlocked": True},
            visited_locations={"start_room", "locked_room"},
        )
        intent = examine_intent("container_box")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.ITEM_NOT_HERE

    # Non-EXAMINE intent rejection

    def test_non_examine_intent_rejected(
        self, validator, state, sample_world_data
    ) -> None:
        """Non-EXAMINE intents are rejected."""
        intent = ActionIntent(
            action_type=ActionType.TAKE,
            raw_input="take box",
            verb="take",
            target_id="container_box",
        )

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.TARGET_NOT_FOUND

    # Context fields

    def test_found_description_in_context(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Found description is included for items with it."""
        state.flags["box_opened"] = True
        intent = examine_intent("hidden_gem")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context.get("found_description") is not None
        assert "glints" in result.context["found_description"]
