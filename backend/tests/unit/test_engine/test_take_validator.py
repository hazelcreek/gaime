"""Unit tests for TakeValidator.

Tests cover:
- Valid taking of portable items
- Rejection for non-portable items
- Rejection for items already in inventory
- Rejection for hidden items
- Rejection for items at wrong location
- Rejection for non-existent targets
"""

import pytest

from app.engine.two_phase.validators.take import TakeValidator
from app.engine.two_phase.models.intent import ActionIntent, ActionType
from app.engine.two_phase.models.event import RejectionCode
from app.engine.two_phase.models.state import TwoPhaseGameState


class TestTakeValidator:
    """Tests for TakeValidator."""

    @pytest.fixture
    def validator(self) -> TakeValidator:
        """Create validator instance."""
        return TakeValidator()

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
    def take_intent(self) -> callable:
        """Factory for creating TAKE intents."""

        def _create(target_id: str) -> ActionIntent:
            return ActionIntent(
                action_type=ActionType.TAKE,
                raw_input=f"take {target_id}",
                verb="take",
                target_id=target_id,
            )

        return _create

    # Valid take tests

    def test_take_portable_item(
        self, validator, state, sample_world_data, take_intent
    ) -> None:
        """Taking a portable item succeeds."""
        # Remove test_key from inventory so we can take it from location
        state.inventory = []
        intent = take_intent("test_key")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["item_id"] == "test_key"
        assert result.context["item_name"] == "Test Key"

    def test_take_revealed_hidden_item(
        self, validator, state, sample_world_data, take_intent
    ) -> None:
        """Taking a revealed hidden item succeeds."""
        state.flags["box_opened"] = True
        intent = take_intent("hidden_gem")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["item_id"] == "hidden_gem"
        assert result.context["item_name"] == "Hidden Gem"

    # Rejection tests

    def test_take_non_portable_item(
        self, validator, state, sample_world_data, take_intent
    ) -> None:
        """Taking a non-portable item fails."""
        intent = take_intent("container_box")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.ITEM_NOT_PORTABLE
        assert "can't take" in result.rejection_reason.lower()

    def test_take_already_have(
        self, validator, state, sample_world_data, take_intent
    ) -> None:
        """Taking an item already in inventory fails."""
        intent = take_intent("test_key")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.ALREADY_HAVE
        assert "already have" in result.rejection_reason.lower()

    def test_take_hidden_item_not_visible(
        self, validator, state, sample_world_data, take_intent
    ) -> None:
        """Taking a hidden item without condition met fails."""
        intent = take_intent("hidden_gem")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.ITEM_NOT_VISIBLE

    def test_take_nonexistent_item(
        self, validator, state, sample_world_data, take_intent
    ) -> None:
        """Taking a non-existent item fails."""
        intent = take_intent("banana")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.TARGET_NOT_FOUND

    def test_take_item_at_wrong_location(
        self, validator, sample_world_data, take_intent
    ) -> None:
        """Taking an item at a different location fails."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="locked_room",
            inventory=[],
            flags={"door_unlocked": True},
            visited_locations={"start_room", "locked_room"},
        )
        intent = take_intent("container_box")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        # container_box is not portable anyway, but location check happens first
        # Actually the item check happens first, then location, then portable
        # Let's use test_key which is portable
        intent2 = take_intent("test_key")
        result2 = validator.validate(intent2, state, sample_world_data)

        assert result2.valid is False
        assert result2.rejection_code == RejectionCode.ITEM_NOT_HERE

    # Non-TAKE intent rejection

    def test_non_take_intent_rejected(
        self, validator, state, sample_world_data
    ) -> None:
        """Non-TAKE intents are rejected."""
        intent = ActionIntent(
            action_type=ActionType.EXAMINE,
            raw_input="examine box",
            verb="examine",
            target_id="container_box",
        )

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.TARGET_NOT_FOUND

    # Context fields

    def test_take_description_in_context(
        self, validator, state, sample_world_data, take_intent
    ) -> None:
        """Take description is included in context."""
        state.flags["box_opened"] = True
        intent = take_intent("hidden_gem")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert "from_location" in result.context
        assert result.context["from_location"] == "start_room"
