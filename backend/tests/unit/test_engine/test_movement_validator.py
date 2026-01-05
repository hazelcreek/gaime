"""Unit tests for MovementValidator.

Tests cover:
- Valid movement (exit exists, no requirements)
- NO_EXIT rejection (direction not available)
- PRECONDITION_FAILED rejection (flag/item required)
- First visit detection in context
- Back direction handling
"""

import pytest

from app.engine.two_phase.validators.movement import MovementValidator
from app.engine.two_phase.models.intent import ActionIntent, ActionType
from app.engine.two_phase.models.event import RejectionCode
from app.engine.two_phase.models.state import TwoPhaseGameState


class TestMovementValidator:
    """Tests for MovementValidator."""

    @pytest.fixture
    def validator(self) -> MovementValidator:
        """Create validator instance."""
        return MovementValidator()

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
    def move_intent(self) -> callable:
        """Factory for creating MOVE intents."""

        def _create(direction: str) -> ActionIntent:
            return ActionIntent(
                action_type=ActionType.MOVE,
                raw_input=f"go {direction}",
                verb="go",
                target_id=direction,
            )

        return _create

    # Valid movement tests

    def test_valid_movement_north(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """Movement to existing exit succeeds when requirements met."""
        # locked_room requires door_unlocked flag
        state.flags["door_unlocked"] = True
        intent = move_intent("north")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["destination"] == "locked_room"
        assert result.context["direction"] == "north"

    def test_valid_movement_east(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """Movement east succeeds."""
        intent = move_intent("east")

        result = validator.validate(intent, state, sample_world_data)

        # east exit requires knows_secret flag
        # Since flag isn't set, this should fail
        assert result.valid is False
        assert result.rejection_code == RejectionCode.PRECONDITION_FAILED

    def test_first_visit_in_context(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """First visit to location is indicated in context."""
        # Set flag so we can access locked_room
        state.flags["door_unlocked"] = True
        intent = move_intent("north")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["first_visit"] is True

    def test_revisit_in_context(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """Revisit to location is indicated in context."""
        state.flags["door_unlocked"] = True
        state.visited_locations.add("locked_room")
        intent = move_intent("north")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["first_visit"] is False

    # NO_EXIT rejection tests

    def test_no_exit_rejection(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """Movement to non-existent direction fails with NO_EXIT."""
        intent = move_intent("west")  # No west exit from start_room

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.NO_EXIT
        assert "west" in result.rejection_reason.lower()

    def test_no_exit_south(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """No south exit from start_room."""
        intent = move_intent("south")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.NO_EXIT

    # PRECONDITION_FAILED rejection tests

    def test_flag_requirement_not_met(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """Movement to location requiring flag fails without flag."""
        intent = move_intent("north")  # locked_room requires door_unlocked

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.PRECONDITION_FAILED

    def test_flag_requirement_met(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """Movement succeeds when required flag is set."""
        state.flags["door_unlocked"] = True
        intent = move_intent("north")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True

    def test_secret_room_requires_flag(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """Secret room requires knows_secret flag."""
        intent = move_intent("east")  # secret_room requires knows_secret

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.PRECONDITION_FAILED

    def test_secret_room_accessible_with_flag(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """Secret room accessible when flag set."""
        state.flags["knows_secret"] = True
        intent = move_intent("east")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["destination"] == "secret_room"

    # Back direction tests

    def test_back_from_locked_room(
        self, validator, sample_world_data, move_intent
    ) -> None:
        """Back from locked_room returns to start_room."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="locked_room",
            visited_locations={"start_room", "locked_room"},
        )
        intent = move_intent("back")

        result = validator.validate(intent, state, sample_world_data)

        # locked_room has only one exit (south to start_room)
        assert result.valid is True
        assert result.context["destination"] == "start_room"

    def test_back_with_multiple_exits(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """Back with multiple exits uses south if available."""
        # start_room has north and east exits, no south
        intent = move_intent("back")

        result = validator.validate(intent, state, sample_world_data)

        # No south exit and multiple exits - should fail
        assert result.valid is False
        assert result.rejection_code == RejectionCode.NO_EXIT

    # from_location in context

    def test_from_location_in_context(
        self, validator, state, sample_world_data, move_intent
    ) -> None:
        """from_location is included in validation context."""
        state.flags["door_unlocked"] = True
        intent = move_intent("north")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["from_location"] == "start_room"

    # Non-MOVE intent rejection

    def test_non_move_intent_rejected(
        self, validator, state, sample_world_data
    ) -> None:
        """Non-MOVE intents are rejected."""
        intent = ActionIntent(
            action_type=ActionType.EXAMINE,
            raw_input="examine door",
            verb="examine",
            target_id="door",
        )

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is False
        assert result.rejection_code == RejectionCode.TARGET_NOT_FOUND

    # Hidden exit tests

    def test_hidden_exit_not_visible_fails(self, validator, move_intent) -> None:
        """Movement to hidden exit fails with NO_EXIT when condition not met."""
        from app.models.world import (
            WorldData,
            World,
            Location,
            ExitDefinition,
            PlayerSetup,
        )

        # Create a world with a hidden exit
        world = WorldData(
            world=World(
                name="Test",
                theme="test",
                premise="test",
                player=PlayerSetup(starting_location="room"),
            ),
            locations={
                "room": Location(
                    name="Room",
                    exits={
                        "north": ExitDefinition(destination="hall"),  # Visible
                        "down": ExitDefinition(
                            destination="secret",
                            hidden=True,
                            find_condition={"requires_flag": "found_trapdoor"},
                        ),
                    },
                ),
                "hall": Location(name="Hall"),
                "secret": Location(name="Secret Basement"),
            },
            items={},
            npcs={},
        )

        state = TwoPhaseGameState(
            session_id="test",
            current_location="room",
            flags={},  # Flag NOT set
        )

        intent = move_intent("down")
        result = validator.validate(intent, state, world)

        # Hidden exit should be treated as nonexistent
        assert result.valid is False
        assert result.rejection_code == RejectionCode.NO_EXIT
        assert "down" in result.rejection_reason.lower()

    def test_hidden_exit_visible_with_flag_succeeds(
        self, validator, move_intent
    ) -> None:
        """Movement to hidden exit succeeds when condition is met."""
        from app.models.world import (
            WorldData,
            World,
            Location,
            ExitDefinition,
            PlayerSetup,
        )

        # Create a world with a hidden exit
        world = WorldData(
            world=World(
                name="Test",
                theme="test",
                premise="test",
                player=PlayerSetup(starting_location="room"),
            ),
            locations={
                "room": Location(
                    name="Room",
                    exits={
                        "down": ExitDefinition(
                            destination="secret",
                            hidden=True,
                            find_condition={"requires_flag": "found_trapdoor"},
                        ),
                    },
                ),
                "secret": Location(name="Secret Basement"),
            },
            items={},
            npcs={},
        )

        state = TwoPhaseGameState(
            session_id="test",
            current_location="room",
            flags={"found_trapdoor": True},  # Flag IS set
        )

        intent = move_intent("down")
        result = validator.validate(intent, state, world)

        # Hidden exit should now be accessible
        assert result.valid is True
        assert result.context["destination"] == "secret"

    def test_back_ignores_hidden_exits(self, validator, move_intent) -> None:
        """Back navigation does not consider hidden exits."""
        from app.models.world import (
            WorldData,
            World,
            Location,
            ExitDefinition,
            PlayerSetup,
        )

        # Create a room with one visible exit and one hidden exit
        world = WorldData(
            world=World(
                name="Test",
                theme="test",
                premise="test",
                player=PlayerSetup(starting_location="room"),
            ),
            locations={
                "room": Location(
                    name="Room",
                    exits={
                        "north": ExitDefinition(destination="hall"),  # Visible
                        "down": ExitDefinition(
                            destination="secret",
                            hidden=True,
                            find_condition={"requires_flag": "found_trapdoor"},
                        ),
                    },
                ),
                "hall": Location(name="Hall"),
                "secret": Location(name="Secret Basement"),
            },
            items={},
            npcs={},
        )

        state = TwoPhaseGameState(
            session_id="test",
            current_location="room",
            flags={},  # Hidden exit not revealed
        )

        intent = move_intent("back")
        result = validator.validate(intent, state, world)

        # Only "north" is visible, so back should succeed and go north
        assert result.valid is True
        assert result.context["destination"] == "hall"
        assert result.context["direction"] == "north"

    def test_back_fails_when_only_hidden_exits(self, validator, move_intent) -> None:
        """Back fails when only hidden exits are available."""
        from app.models.world import (
            WorldData,
            World,
            Location,
            ExitDefinition,
            PlayerSetup,
        )

        # Create a room with ONLY hidden exits
        world = WorldData(
            world=World(
                name="Test",
                theme="test",
                premise="test",
                player=PlayerSetup(starting_location="room"),
            ),
            locations={
                "room": Location(
                    name="Room",
                    exits={
                        "down": ExitDefinition(
                            destination="secret",
                            hidden=True,
                            find_condition={"requires_flag": "found_trapdoor"},
                        ),
                    },
                ),
                "secret": Location(name="Secret Basement"),
            },
            items={},
            npcs={},
        )

        state = TwoPhaseGameState(
            session_id="test",
            current_location="room",
            flags={},  # Hidden exit not revealed
        )

        intent = move_intent("back")
        result = validator.validate(intent, state, world)

        # No visible exits, so back should fail
        assert result.valid is False
        assert result.rejection_code == RejectionCode.NO_EXIT
