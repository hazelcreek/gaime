"""Unit tests for ExamineValidator.

Tests cover:
- Valid examination of items at location
- Valid examination of location details
- Valid examination of inventory items
- Valid examination of exits (Phase 4)
- on_examine effects in validation context (Phase 4)
- Rejection for hidden items
- Rejection for non-existent targets
- Rejection for items at wrong location
"""

import pytest

from app.engine.two_phase.validators.examine import ExamineValidator
from app.engine.two_phase.visibility import DefaultVisibilityResolver
from app.engine.two_phase.models.intent import ActionIntent, ActionType
from app.engine.two_phase.models.event import RejectionCode
from app.engine.two_phase.models.state import TwoPhaseGameState


class TestExamineValidator:
    """Tests for ExamineValidator."""

    @pytest.fixture
    def visibility_resolver(self) -> DefaultVisibilityResolver:
        """Create visibility resolver instance."""
        return DefaultVisibilityResolver()

    @pytest.fixture
    def validator(self, visibility_resolver) -> ExamineValidator:
        """Create validator instance with visibility resolver."""
        return ExamineValidator(visibility_resolver)

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

    def test_scene_description_in_context(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Scene description is included for items with it."""
        state.flags["box_opened"] = True
        intent = examine_intent("hidden_gem")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context.get("scene_description") is not None
        assert "glints" in result.context["scene_description"]

    # Exit examination tests (Phase 4)

    def test_examine_exit(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining a visible exit succeeds."""
        intent = examine_intent("north")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["entity_type"] == "exit"
        assert result.context["entity_id"] == "north"
        assert "description" in result.context
        assert "destination_id" in result.context
        assert result.context["destination_id"] == "locked_room"

    def test_examine_exit_with_reveal_destination_on_examine(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining exit with reveal_destination_on_examine includes reveal effect."""
        intent = examine_intent("north")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        # Should have on_examine with reveal_destination_on_examine
        assert result.context.get("on_examine") is not None
        assert result.context["on_examine"].get("reveal_destination_on_examine") is True
        assert result.context["on_examine"].get("direction") == "north"

    def test_examine_hidden_exit_fails(self, validator, examine_intent) -> None:
        """Examining a hidden exit fails with TARGET_NOT_FOUND."""
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

        intent = examine_intent("down")
        result = validator.validate(intent, state, world)

        # Hidden exit should be treated as not found
        assert result.valid is False
        assert result.rejection_code == RejectionCode.TARGET_NOT_FOUND

    def test_examine_hidden_exit_visible_with_flag(
        self, validator, examine_intent
    ) -> None:
        """Examining a hidden exit succeeds when condition is met."""
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
                            scene_description="A trapdoor leading down",
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

        intent = examine_intent("down")
        result = validator.validate(intent, state, world)

        # Hidden exit should now be examinable
        assert result.valid is True
        assert result.context["entity_type"] == "exit"
        assert result.context["entity_id"] == "down"

    # on_examine effects tests (Phase 4)

    def test_examine_detail_with_on_examine_effects(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining detail with on_examine includes effects in context."""
        intent = examine_intent("box")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["entity_type"] == "detail"
        # Should have on_examine effects
        assert result.context.get("on_examine") is not None
        assert result.context["on_examine"].get("sets_flag") == "box_opened"
        assert result.context["on_examine"].get("narrative_hint") is not None

    def test_examine_item_with_on_examine_effects(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining item with on_examine includes effects in context."""
        intent = examine_intent("test_key")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["entity_type"] == "item"
        # The test_key should have on_examine effects
        assert result.context.get("on_examine") is not None
        assert result.context["on_examine"].get("sets_flag") == "key_examined"

    # Hidden NPC tests

    def test_examine_hidden_npc_fails(self, validator, examine_intent) -> None:
        """Examining a hidden NPC fails with TARGET_NOT_FOUND."""
        from app.models.world import (
            WorldData,
            World,
            Location,
            NPC,
            NPCPlacement,
            PlayerSetup,
        )

        # Create a world with a hidden NPC
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
                    npc_placements={
                        "spy": NPCPlacement(
                            placement="lurking behind the curtain",
                            hidden=True,
                            find_condition={"requires_flag": "pulled_curtain"},
                        ),
                    },
                ),
            },
            items={},
            npcs={
                "spy": NPC(name="Shadowy Figure", location="room"),
            },
        )

        state = TwoPhaseGameState(
            session_id="test",
            current_location="room",
            flags={},  # Flag NOT set
        )

        intent = examine_intent("spy")
        result = validator.validate(intent, state, world)

        # Hidden NPC should be treated as not found
        assert result.valid is False
        assert result.rejection_code == RejectionCode.TARGET_NOT_FOUND

    def test_examine_hidden_npc_visible_with_flag(
        self, validator, examine_intent
    ) -> None:
        """Examining a hidden NPC succeeds when condition is met."""
        from app.models.world import (
            WorldData,
            World,
            Location,
            NPC,
            NPCPlacement,
            PlayerSetup,
        )

        # Create a world with a hidden NPC
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
                    npc_placements={
                        "spy": NPCPlacement(
                            placement="lurking behind the curtain",
                            hidden=True,
                            find_condition={"requires_flag": "pulled_curtain"},
                        ),
                    },
                ),
            },
            items={},
            npcs={
                "spy": NPC(
                    name="Shadowy Figure",
                    location="room",
                    appearance="A cloaked figure with piercing eyes",
                ),
            },
        )

        state = TwoPhaseGameState(
            session_id="test",
            current_location="room",
            flags={"pulled_curtain": True},  # Flag IS set
        )

        intent = examine_intent("spy")
        result = validator.validate(intent, state, world)

        # Hidden NPC should now be examinable
        assert result.valid is True
        assert result.context["entity_type"] == "npc"
        assert result.context["entity_id"] == "spy"
        assert result.context["entity_name"] == "Shadowy Figure"

    def test_examine_visible_npc(
        self, validator, state, sample_world_data, examine_intent
    ) -> None:
        """Examining a visible NPC at location succeeds."""
        # test_npc is in npc_placements at start_room and not hidden
        intent = examine_intent("test_npc")

        result = validator.validate(intent, state, sample_world_data)

        assert result.valid is True
        assert result.context["entity_type"] == "npc"
        assert result.context["entity_id"] == "test_npc"
