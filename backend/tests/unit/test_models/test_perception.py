"""Unit tests for perception models.

Tests cover:
- VisibleEntity creation
- VisibleExit creation
- PerceptionSnapshot creation and structure
"""

from app.models.perception import (
    PerceptionSnapshot,
    VisibleEntity,
    VisibleExit,
)


class TestVisibleEntity:
    """Tests for VisibleEntity model."""

    def test_minimal_creation(self) -> None:
        """VisibleEntity can be created with required fields."""
        entity = VisibleEntity(
            id="brass_key",
            name="Small Brass Key",
        )

        assert entity.id == "brass_key"
        assert entity.name == "Small Brass Key"
        assert entity.description is None  # Optional
        assert entity.is_new is False  # Default

    def test_with_description(self) -> None:
        """VisibleEntity can have a description."""
        entity = VisibleEntity(
            id="brass_key",
            name="Small Brass Key",
            description="A tarnished key lies in the drawer.",
        )

        assert entity.description == "A tarnished key lies in the drawer."

    def test_is_new_flag(self) -> None:
        """VisibleEntity can be marked as newly discovered."""
        entity = VisibleEntity(
            id="brass_key",
            name="Small Brass Key",
            is_new=True,
        )

        assert entity.is_new is True


class TestVisibleExit:
    """Tests for VisibleExit model."""

    def test_minimal_creation(self) -> None:
        """VisibleExit can be created with required fields."""
        exit_ = VisibleExit(
            direction="north",
            destination_name="The Library",
        )

        assert exit_.direction == "north"
        assert exit_.destination_name == "The Library"
        assert exit_.description is None
        assert exit_.is_locked is False
        assert exit_.is_blocked is False

    def test_with_description(self) -> None:
        """VisibleExit can have a description."""
        exit_ = VisibleExit(
            direction="north",
            destination_name="The Library",
            description="An archway leads north into shadows.",
        )

        assert exit_.description == "An archway leads north into shadows."

    def test_locked_exit(self) -> None:
        """VisibleExit can be marked as locked."""
        exit_ = VisibleExit(
            direction="down",
            destination_name="The Basement",
            is_locked=True,
        )

        assert exit_.is_locked is True

    def test_blocked_exit(self) -> None:
        """VisibleExit can be marked as blocked."""
        exit_ = VisibleExit(
            direction="east",
            destination_name="The Burning Wing",
            is_blocked=True,
        )

        assert exit_.is_blocked is True


class TestPerceptionSnapshot:
    """Tests for PerceptionSnapshot model."""

    def test_minimal_creation(self) -> None:
        """PerceptionSnapshot can be created with required fields."""
        snapshot = PerceptionSnapshot(
            location_id="entrance_hall",
            location_name="Entrance Hall",
        )

        assert snapshot.location_id == "entrance_hall"
        assert snapshot.location_name == "Entrance Hall"
        assert snapshot.location_atmosphere is None
        assert snapshot.visible_items == []
        assert snapshot.visible_details == []
        assert snapshot.visible_exits == []
        assert snapshot.visible_npcs == []
        assert snapshot.inventory == []
        assert snapshot.affordances == {}
        assert snapshot.known_facts == []
        assert snapshot.first_visit is False

    def test_with_visible_items(self) -> None:
        """PerceptionSnapshot can include visible items."""
        snapshot = PerceptionSnapshot(
            location_id="study",
            location_name="The Study",
            visible_items=[
                VisibleEntity(id="brass_key", name="Brass Key", is_new=True),
                VisibleEntity(id="old_letter", name="Yellowed Letter"),
            ],
        )

        assert len(snapshot.visible_items) == 2
        assert snapshot.visible_items[0].id == "brass_key"
        assert snapshot.visible_items[0].is_new is True

    def test_with_visible_exits(self) -> None:
        """PerceptionSnapshot can include visible exits."""
        snapshot = PerceptionSnapshot(
            location_id="entrance_hall",
            location_name="Entrance Hall",
            visible_exits=[
                VisibleExit(direction="north", destination_name="Library"),
                VisibleExit(direction="east", destination_name="Dining Room"),
            ],
        )

        assert len(snapshot.visible_exits) == 2
        assert snapshot.visible_exits[0].direction == "north"

    def test_with_inventory(self) -> None:
        """PerceptionSnapshot can include player inventory."""
        snapshot = PerceptionSnapshot(
            location_id="study",
            location_name="The Study",
            inventory=[
                VisibleEntity(id="brass_key", name="Brass Key"),
            ],
        )

        assert len(snapshot.inventory) == 1
        assert snapshot.inventory[0].id == "brass_key"

    def test_with_affordances(self) -> None:
        """PerceptionSnapshot can include affordances."""
        snapshot = PerceptionSnapshot(
            location_id="study",
            location_name="The Study",
            affordances={
                "openable_containers": ["desk_drawer"],
                "usable_tools": ["matches"],
            },
        )

        assert "openable_containers" in snapshot.affordances
        assert "desk_drawer" in snapshot.affordances["openable_containers"]

    def test_first_visit_flag(self) -> None:
        """PerceptionSnapshot can indicate first visit."""
        snapshot = PerceptionSnapshot(
            location_id="secret_chamber",
            location_name="Secret Chamber",
            first_visit=True,
        )

        assert snapshot.first_visit is True

    def test_hidden_items_not_included(self) -> None:
        """Ensure hidden items would not appear in snapshot.

        Note: This is a documentation test - the actual filtering
        happens in the VisibilityResolver, not in the model.
        """
        # When building a snapshot, hidden items should NOT be included
        snapshot = PerceptionSnapshot(
            location_id="study",
            location_name="The Study",
            visible_items=[],  # No hidden items here!
        )

        # The snapshot correctly excludes hidden items
        assert len(snapshot.visible_items) == 0
