"""Unit tests for event models.

Tests cover:
- Event creation and validation
- RejectionEvent creation
- EventType enum values
- RejectionCode enum values
"""

from app.models.event import Event, EventType, RejectionCode, RejectionEvent


class TestEventType:
    """Tests for EventType enum."""

    def test_movement_events(self) -> None:
        """Movement event types are valid."""
        assert EventType.LOCATION_CHANGED == "location_changed"
        assert EventType.SCENE_BROWSED == "scene_browsed"

    def test_item_events(self) -> None:
        """Item event types are valid."""
        assert EventType.ITEM_TAKEN == "item_taken"
        assert EventType.ITEM_DROPPED == "item_dropped"
        assert EventType.ITEM_USED == "item_used"
        assert EventType.ITEM_REVEALED == "item_revealed"
        assert EventType.ITEM_CONSUMED == "item_consumed"

    def test_container_events(self) -> None:
        """Container event types are valid."""
        assert EventType.CONTAINER_OPENED == "container_opened"
        assert EventType.CONTAINER_CLOSED == "container_closed"

    def test_discovery_events(self) -> None:
        """Discovery event types are valid."""
        assert EventType.DETAIL_EXAMINED == "detail_examined"
        assert EventType.SECRET_DISCOVERED == "secret_discovered"
        assert EventType.EXIT_REVEALED == "exit_revealed"

    def test_npc_events(self) -> None:
        """NPC event types are valid."""
        assert EventType.NPC_GREETED == "npc_greeted"
        assert EventType.NPC_CONVERSATION == "npc_conversation"

    def test_meta_events(self) -> None:
        """Meta event types are valid."""
        assert EventType.ACTION_REJECTED == "action_rejected"
        assert EventType.NOTHING_HAPPENED == "nothing_happened"
        assert EventType.FLAVOR_ACTION == "flavor_action"


class TestRejectionCode:
    """Tests for RejectionCode enum."""

    def test_movement_rejections(self) -> None:
        """Movement rejection codes are valid."""
        assert RejectionCode.NO_EXIT == "no_exit"
        assert RejectionCode.EXIT_LOCKED == "exit_locked"
        assert RejectionCode.EXIT_BLOCKED == "exit_blocked"

    def test_item_rejections(self) -> None:
        """Item rejection codes are valid."""
        assert RejectionCode.ITEM_NOT_VISIBLE == "item_not_visible"
        assert RejectionCode.ITEM_NOT_PORTABLE == "item_not_portable"
        assert RejectionCode.ALREADY_HAVE == "already_have"

    def test_container_rejections(self) -> None:
        """Container rejection codes are valid."""
        assert RejectionCode.CONTAINER_LOCKED == "container_locked"
        assert RejectionCode.CONTAINER_ALREADY_OPEN == "container_already_open"

    def test_safety_rejection(self) -> None:
        """Safety guardrail rejection exists."""
        assert RejectionCode.SAFETY_GUARDRAIL == "safety_guardrail"


class TestEvent:
    """Tests for Event model."""

    def test_minimal_creation(self) -> None:
        """Event can be created with just type."""
        event = Event(type=EventType.LOCATION_CHANGED)

        assert event.type == EventType.LOCATION_CHANGED
        assert event.subject is None
        assert event.target is None
        assert event.state_changes == {}
        assert event.context == {}
        assert event.primary is True  # Default

    def test_scene_browsed_event(self) -> None:
        """SCENE_BROWSED event can include visible entities."""
        event = Event(
            type=EventType.SCENE_BROWSED,
            subject="main_hallway",
            context={
                "first_visit": True,
                "is_manual_browse": False,
                "visible_items": ["rusty_key", "old_letter"],
                "visible_npcs": ["butler_jenkins"],
                "visible_exits": [
                    {"direction": "north", "destination": "library"},
                    {"direction": "east", "destination": "kitchen"},
                ],
            },
        )

        assert event.type == EventType.SCENE_BROWSED
        assert event.subject == "main_hallway"
        assert event.context["first_visit"] is True
        assert len(event.context["visible_items"]) == 2
        assert len(event.context["visible_exits"]) == 2

    def test_with_subject(self) -> None:
        """Event can have a subject entity."""
        event = Event(
            type=EventType.ITEM_TAKEN,
            subject="brass_key",
        )

        assert event.subject == "brass_key"

    def test_with_target(self) -> None:
        """Event can have a target entity."""
        event = Event(
            type=EventType.ITEM_USED,
            subject="brass_key",
            target="front_door",
        )

        assert event.subject == "brass_key"
        assert event.target == "front_door"

    def test_with_state_changes(self) -> None:
        """Event can specify state changes."""
        event = Event(
            type=EventType.FLAG_SET,
            subject="door_unlocked",
            state_changes={"flags": {"door_unlocked": True}},
        )

        assert event.state_changes == {"flags": {"door_unlocked": True}}

    def test_with_context(self) -> None:
        """Event can have narration context."""
        event = Event(
            type=EventType.ITEM_REVEALED,
            subject="brass_key",
            context={"is_new": True, "container": "desk_drawer"},
        )

        assert event.context["is_new"] is True
        assert event.context["container"] == "desk_drawer"

    def test_primary_flag(self) -> None:
        """Event can be marked as secondary (side effect)."""
        primary = Event(type=EventType.CONTAINER_OPENED, subject="desk")
        secondary = Event(
            type=EventType.ITEM_REVEALED,
            subject="brass_key",
            primary=False,
        )

        assert primary.primary is True
        assert secondary.primary is False


class TestRejectionEvent:
    """Tests for RejectionEvent model."""

    def test_creation(self) -> None:
        """RejectionEvent can be created with required fields."""
        rejection = RejectionEvent(
            rejection_code=RejectionCode.EXIT_LOCKED,
            rejection_reason="The door is locked.",
        )

        assert rejection.type == EventType.ACTION_REJECTED
        assert rejection.rejection_code == RejectionCode.EXIT_LOCKED
        assert rejection.rejection_reason == "The door is locked."

    def test_with_subject(self) -> None:
        """RejectionEvent can have a subject entity."""
        rejection = RejectionEvent(
            rejection_code=RejectionCode.EXIT_LOCKED,
            rejection_reason="The basement door is locked.",
            subject="basement_door",
        )

        assert rejection.subject == "basement_door"

    def test_with_context(self) -> None:
        """RejectionEvent can have context for hints."""
        rejection = RejectionEvent(
            rejection_code=RejectionCode.EXIT_LOCKED,
            rejection_reason="The door is locked.",
            context={"requires_key": "iron_key"},
        )

        assert rejection.context["requires_key"] == "iron_key"

    def test_would_have_hint(self) -> None:
        """RejectionEvent can hint at what would have happened."""
        rejection = RejectionEvent(
            rejection_code=RejectionCode.ITEM_NOT_VISIBLE,
            rejection_reason="You don't see that here.",
            would_have="Pick up the hidden treasure",
        )

        assert rejection.would_have == "Pick up the hidden treasure"

    def test_type_is_action_rejected(self) -> None:
        """RejectionEvent always has ACTION_REJECTED type."""
        rejection = RejectionEvent(
            rejection_code=RejectionCode.NO_EXIT,
            rejection_reason="There's no way to go north.",
        )

        assert rejection.type == EventType.ACTION_REJECTED
