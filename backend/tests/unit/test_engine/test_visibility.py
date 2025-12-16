"""Unit tests for DefaultVisibilityResolver.

Tests cover:
- build_snapshot() returns correct location info
- Visible exits populated correctly
- Visible items filtering
- Inventory entities
- Hidden item filtering
- First visit detection
"""

import pytest

from app.engine.visibility import DefaultVisibilityResolver
from app.models.two_phase_state import TwoPhaseGameState
from app.models.perception import PerceptionSnapshot, VisibleExit, VisibleEntity


class TestDefaultVisibilityResolver:
    """Tests for DefaultVisibilityResolver."""

    @pytest.fixture
    def resolver(self) -> DefaultVisibilityResolver:
        """Create resolver instance."""
        return DefaultVisibilityResolver()

    @pytest.fixture
    def state(self) -> TwoPhaseGameState:
        """Create test state."""
        return TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=["test_key"],
            flags={},
            visited_locations={"start_room"},
        )

    # build_snapshot tests

    def test_build_snapshot_location_info(
        self, resolver, state, sample_world_data
    ) -> None:
        """Snapshot includes correct location info."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        assert snapshot.location_id == "start_room"
        assert snapshot.location_name == "Starting Room"
        assert snapshot.location_atmosphere is not None

    def test_build_snapshot_exits(
        self, resolver, state, sample_world_data
    ) -> None:
        """Snapshot includes visible exits."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        assert len(snapshot.visible_exits) == 2  # north and east
        directions = [e.direction for e in snapshot.visible_exits]
        assert "north" in directions
        assert "east" in directions

    def test_exit_has_destination_name(
        self, resolver, state, sample_world_data
    ) -> None:
        """Exits include destination names."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        north_exit = next(
            (e for e in snapshot.visible_exits if e.direction == "north"), None
        )
        assert north_exit is not None
        assert north_exit.destination_name == "Locked Room"

    def test_build_snapshot_visible_items(
        self, resolver, state, sample_world_data
    ) -> None:
        """Snapshot includes visible items at location."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        # container_box is at start_room and not hidden
        item_ids = [i.id for i in snapshot.visible_items]
        assert "container_box" in item_ids

    def test_hidden_items_excluded(
        self, resolver, state, sample_world_data
    ) -> None:
        """Hidden items are not in visible_items."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        # hidden_gem is hidden until box_opened flag is set
        item_ids = [i.id for i in snapshot.visible_items]
        assert "hidden_gem" not in item_ids

    def test_hidden_item_visible_with_flag(
        self, resolver, state, sample_world_data
    ) -> None:
        """Hidden items become visible when condition met.
        
        Note: This test verifies the is_item_visible() logic, not build_snapshot().
        The hidden_gem in the fixture has location="start_room" but is NOT in
        the location.items list, so it won't appear in visible_items.
        
        For items to appear in build_snapshot(), they must be in location.items.
        """
        state.flags["box_opened"] = True
        
        # Verify the item IS visible via is_item_visible()
        assert resolver.is_item_visible("hidden_gem", state, sample_world_data)

    def test_inventory_items_not_in_visible(
        self, resolver, state, sample_world_data
    ) -> None:
        """Items in inventory are not in visible_items."""
        # test_key is in inventory
        snapshot = resolver.build_snapshot(state, sample_world_data)

        visible_ids = [i.id for i in snapshot.visible_items]
        assert "test_key" not in visible_ids

    def test_inventory_in_snapshot(
        self, resolver, state, sample_world_data
    ) -> None:
        """Snapshot includes inventory items."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        inventory_ids = [i.id for i in snapshot.inventory]
        assert "test_key" in inventory_ids

    def test_inventory_item_details(
        self, resolver, state, sample_world_data
    ) -> None:
        """Inventory items have name and description."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        key_item = next((i for i in snapshot.inventory if i.id == "test_key"), None)
        assert key_item is not None
        assert key_item.name == "Test Key"

    # First visit detection

    def test_first_visit_true(
        self, resolver, sample_world_data
    ) -> None:
        """first_visit is True for unvisited location."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="locked_room",
            visited_locations=set(),  # Haven't visited anywhere
        )

        snapshot = resolver.build_snapshot(state, sample_world_data)
        assert snapshot.first_visit is True

    def test_first_visit_false(
        self, resolver, state, sample_world_data
    ) -> None:
        """first_visit is False for visited location."""
        # state.visited_locations already includes start_room
        snapshot = resolver.build_snapshot(state, sample_world_data)
        assert snapshot.first_visit is False

    # Details / scenery

    def test_details_in_snapshot(
        self, resolver, state, sample_world_data
    ) -> None:
        """Snapshot includes location details."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        # start_room has floor, walls, box details
        detail_ids = [d.id for d in snapshot.visible_details]
        assert "floor" in detail_ids or "walls" in detail_ids

    # is_item_visible tests

    def test_is_item_visible_in_inventory(
        self, resolver, state, sample_world_data
    ) -> None:
        """Items in inventory are visible."""
        assert resolver.is_item_visible("test_key", state, sample_world_data)

    def test_is_item_visible_at_location(
        self, resolver, state, sample_world_data
    ) -> None:
        """Non-hidden items at location are visible."""
        assert resolver.is_item_visible("container_box", state, sample_world_data)

    def test_is_item_visible_hidden_without_flag(
        self, resolver, state, sample_world_data
    ) -> None:
        """Hidden items without condition met are not visible."""
        assert not resolver.is_item_visible("hidden_gem", state, sample_world_data)

    def test_is_item_visible_hidden_with_flag(
        self, resolver, state, sample_world_data
    ) -> None:
        """Hidden items are visible when condition met."""
        state.flags["box_opened"] = True
        assert resolver.is_item_visible("hidden_gem", state, sample_world_data)

    def test_is_item_visible_wrong_location(
        self, resolver, state, sample_world_data
    ) -> None:
        """Items at different location are not visible."""
        # No items are defined at locked_room in test world
        # Let's check that container_box (at start_room) isn't visible from locked_room
        state.current_location = "locked_room"
        assert not resolver.is_item_visible("container_box", state, sample_world_data)

    def test_is_item_visible_nonexistent(
        self, resolver, state, sample_world_data
    ) -> None:
        """Non-existent items are not visible."""
        assert not resolver.is_item_visible("nonexistent_item", state, sample_world_data)

    # Edge cases

    def test_snapshot_missing_location(
        self, resolver, sample_world_data
    ) -> None:
        """Handles missing location gracefully."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="nonexistent_room",
        )

        snapshot = resolver.build_snapshot(state, sample_world_data)

        assert snapshot.location_id == "nonexistent_room"
        assert snapshot.location_name == "Unknown Location"

    def test_empty_inventory(
        self, resolver, sample_world_data
    ) -> None:
        """Handles empty inventory."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=[],
        )

        snapshot = resolver.build_snapshot(state, sample_world_data)
        assert snapshot.inventory == []

