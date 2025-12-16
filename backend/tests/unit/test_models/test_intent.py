"""Unit tests for intent models.

Tests cover:
- ActionIntent creation and validation
- FlavorIntent creation and validation
- ActionType enum values
- Field constraints and defaults
"""

import pytest
from pydantic import ValidationError

from app.models.intent import ActionIntent, ActionType, FlavorIntent, Intent


class TestActionType:
    """Tests for ActionType enum."""

    def test_movement_action(self) -> None:
        """MOVE is a valid action type."""
        assert ActionType.MOVE == "move"

    def test_object_actions(self) -> None:
        """Object interaction actions are valid."""
        assert ActionType.EXAMINE == "examine"
        assert ActionType.TAKE == "take"
        assert ActionType.DROP == "drop"
        assert ActionType.USE == "use"
        assert ActionType.OPEN == "open"
        assert ActionType.CLOSE == "close"

    def test_communication_actions(self) -> None:
        """Communication actions are valid."""
        assert ActionType.TALK == "talk"
        assert ActionType.ASK == "ask"
        assert ActionType.GIVE == "give"
        assert ActionType.SHOW == "show"

    def test_meta_actions(self) -> None:
        """Meta actions are valid."""
        assert ActionType.WAIT == "wait"
        assert ActionType.INVENTORY == "inventory"
        assert ActionType.HELP == "help"


class TestActionIntent:
    """Tests for ActionIntent model."""

    def test_minimal_creation(self) -> None:
        """ActionIntent can be created with required fields only."""
        intent = ActionIntent(
            action_type=ActionType.MOVE,
            raw_input="go north",
            verb="go",
            target_id="north",
        )

        assert intent.type == "action_intent"
        assert intent.action_type == ActionType.MOVE
        assert intent.raw_input == "go north"
        assert intent.verb == "go"
        assert intent.target_id == "north"
        assert intent.confidence == 1.0  # Default
        assert intent.alternatives == []  # Default

    def test_use_with_instrument(self) -> None:
        """ActionIntent supports instrument_id for USE actions."""
        intent = ActionIntent(
            action_type=ActionType.USE,
            raw_input="use key on door",
            verb="use",
            target_id="front_door",
            instrument_id="brass_key",
        )

        assert intent.target_id == "front_door"
        assert intent.instrument_id == "brass_key"

    def test_ask_with_topic(self) -> None:
        """ActionIntent supports topic_id for ASK actions."""
        intent = ActionIntent(
            action_type=ActionType.ASK,
            raw_input="ask Jenkins about the curse",
            verb="ask",
            target_id="butler_jenkins",
            topic_id="family_curse",
        )

        assert intent.target_id == "butler_jenkins"
        assert intent.topic_id == "family_curse"

    def test_give_with_recipient(self) -> None:
        """ActionIntent supports recipient_id for GIVE actions."""
        intent = ActionIntent(
            action_type=ActionType.GIVE,
            raw_input="give apple to Jenkins",
            verb="give",
            target_id="red_apple",
            recipient_id="butler_jenkins",
        )

        assert intent.target_id == "red_apple"
        assert intent.recipient_id == "butler_jenkins"

    def test_confidence_score(self) -> None:
        """ActionIntent can have custom confidence scores."""
        intent = ActionIntent(
            action_type=ActionType.EXAMINE,
            raw_input="look at the thing",
            verb="look at",
            target_id="mysterious_object",
            confidence=0.75,
        )

        assert intent.confidence == 0.75

    def test_alternatives_list(self) -> None:
        """ActionIntent can have alternative interpretations."""
        primary = ActionIntent(
            action_type=ActionType.TAKE,
            raw_input="get the key",
            verb="get",
            target_id="brass_key",
            confidence=0.9,
        )

        alternative = ActionIntent(
            action_type=ActionType.TAKE,
            raw_input="get the key",
            verb="get",
            target_id="iron_key",
            confidence=0.6,
        )

        primary.alternatives = [alternative]

        assert len(primary.alternatives) == 1
        assert primary.alternatives[0].target_id == "iron_key"

    def test_missing_required_field(self) -> None:
        """ActionIntent requires all mandatory fields."""
        with pytest.raises(ValidationError):
            ActionIntent(
                action_type=ActionType.MOVE,
                raw_input="go north",
                # Missing: verb, target_id
            )

    def test_type_discriminator(self) -> None:
        """ActionIntent has correct type discriminator."""
        intent = ActionIntent(
            action_type=ActionType.MOVE,
            raw_input="north",
            verb="go",
            target_id="north",
        )

        assert intent.type == "action_intent"


class TestFlavorIntent:
    """Tests for FlavorIntent model."""

    def test_minimal_creation(self) -> None:
        """FlavorIntent can be created with required fields only."""
        flavor = FlavorIntent(
            verb="dance",
            raw_input="dance around",
        )

        assert flavor.type == "flavor_intent"
        assert flavor.verb == "dance"
        assert flavor.raw_input == "dance around"
        assert flavor.target is None  # Optional
        assert flavor.topic is None  # Optional
        assert flavor.manner is None  # Optional

    def test_with_manner(self) -> None:
        """FlavorIntent supports manner/adverb."""
        flavor = FlavorIntent(
            verb="dance",
            raw_input="dance gracefully",
            manner="gracefully",
        )

        assert flavor.manner == "gracefully"

    def test_with_target(self) -> None:
        """FlavorIntent supports target entity."""
        flavor = FlavorIntent(
            verb="wave",
            raw_input="wave at the painting",
            target="family_portrait",
        )

        assert flavor.target == "family_portrait"

    def test_improvised_dialogue(self) -> None:
        """FlavorIntent supports improvised dialogue topics."""
        flavor = FlavorIntent(
            verb="ask",
            raw_input="ask Jenkins about football",
            target="butler_jenkins",
            topic="football",
        )

        assert flavor.target == "butler_jenkins"
        assert flavor.topic == "football"

    def test_type_discriminator(self) -> None:
        """FlavorIntent has correct type discriminator."""
        flavor = FlavorIntent(
            verb="jump",
            raw_input="jump around",
        )

        assert flavor.type == "flavor_intent"


class TestIntentUnion:
    """Tests for Intent type union."""

    def test_action_intent_is_intent(self) -> None:
        """ActionIntent is a valid Intent."""
        intent: Intent = ActionIntent(
            action_type=ActionType.MOVE,
            raw_input="north",
            verb="go",
            target_id="north",
        )

        assert isinstance(intent, ActionIntent)

    def test_flavor_intent_is_intent(self) -> None:
        """FlavorIntent is a valid Intent."""
        intent: Intent = FlavorIntent(
            verb="dance",
            raw_input="dance",
        )

        assert isinstance(intent, FlavorIntent)

    def test_discriminator_distinguishes(self) -> None:
        """Type discriminator can distinguish intent types."""
        action = ActionIntent(
            action_type=ActionType.TAKE,
            raw_input="take key",
            verb="take",
            target_id="key",
        )

        flavor = FlavorIntent(
            verb="jump",
            raw_input="jump",
        )

        assert action.type == "action_intent"
        assert flavor.type == "flavor_intent"
