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

from app.engine.two_phase.visibility import DefaultVisibilityResolver
from app.engine.two_phase.models.state import TwoPhaseGameState


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

    def test_build_snapshot_exits(self, resolver, state, sample_world_data) -> None:
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

    def test_hidden_items_excluded(self, resolver, state, sample_world_data) -> None:
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

    def test_inventory_in_snapshot(self, resolver, state, sample_world_data) -> None:
        """Snapshot includes inventory items."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        inventory_ids = [i.id for i in snapshot.inventory]
        assert "test_key" in inventory_ids

    def test_inventory_item_details(self, resolver, state, sample_world_data) -> None:
        """Inventory items have name and description."""
        snapshot = resolver.build_snapshot(state, sample_world_data)

        key_item = next((i for i in snapshot.inventory if i.id == "test_key"), None)
        assert key_item is not None
        assert key_item.name == "Test Key"

    # First visit detection

    def test_first_visit_true(self, resolver, sample_world_data) -> None:
        """first_visit is True for unvisited location."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="locked_room",
            visited_locations=set(),  # Haven't visited anywhere
        )

        snapshot = resolver.build_snapshot(state, sample_world_data)
        assert snapshot.first_visit is True

    def test_first_visit_false(self, resolver, state, sample_world_data) -> None:
        """first_visit is False for visited location."""
        # state.visited_locations already includes start_room
        snapshot = resolver.build_snapshot(state, sample_world_data)
        assert snapshot.first_visit is False

    # Details / scenery

    def test_details_in_snapshot(self, resolver, state, sample_world_data) -> None:
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
        assert not resolver.is_item_visible(
            "nonexistent_item", state, sample_world_data
        )

    # Edge cases

    def test_snapshot_missing_location(self, resolver, sample_world_data) -> None:
        """Handles missing location gracefully."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="nonexistent_room",
        )

        snapshot = resolver.build_snapshot(state, sample_world_data)

        assert snapshot.location_id == "nonexistent_room"
        assert snapshot.location_name == "Unknown Location"

    def test_empty_inventory(self, resolver, sample_world_data) -> None:
        """Handles empty inventory."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=[],
        )

        snapshot = resolver.build_snapshot(state, sample_world_data)
        assert snapshot.inventory == []

    # ==========================================================================
    # build_debug_snapshot tests
    # ==========================================================================

    def test_debug_snapshot_includes_location_info(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot includes correct location info."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        assert debug.location_id == "start_room"
        assert debug.name == "Starting Room"
        assert debug.atmosphere is not None

    def test_debug_snapshot_includes_all_items(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot includes ALL items, not just visible ones."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        # Should include container_box (at location)
        item_ids = [i.item_id for i in debug.items]
        assert "container_box" in item_ids

    def test_debug_snapshot_shows_taken_item_status(
        self, resolver, sample_world_data
    ) -> None:
        """Debug snapshot shows items in inventory with 'taken' status."""
        # Put container_box in inventory to test taken status
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=["container_box"],
            flags={},
            visited_locations={"start_room"},
        )

        debug = resolver.build_debug_snapshot(state, sample_world_data)

        box_item = next((i for i in debug.items if i.item_id == "container_box"), None)
        assert box_item is not None
        assert box_item.is_in_inventory is True
        assert box_item.visibility_reason == "taken"

    def test_debug_snapshot_shows_visible_item_status(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot shows visible items with correct status."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        box_item = next((i for i in debug.items if i.item_id == "container_box"), None)
        assert box_item is not None
        assert box_item.is_visible is True
        assert box_item.visibility_reason == "visible"

    def test_debug_snapshot_includes_all_exits(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot includes all exits with accessibility info."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        # start_room has north and east exits
        assert len(debug.exits) == 2
        directions = [e.direction for e in debug.exits]
        assert "north" in directions
        assert "east" in directions

    def test_debug_snapshot_shows_exit_accessibility(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot shows exit accessibility status."""
        # north exit requires door_unlocked flag
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        north_exit = next((e for e in debug.exits if e.direction == "north"), None)
        assert north_exit is not None
        assert north_exit.is_accessible is False
        assert "requires_flag" in north_exit.access_reason

    def test_debug_snapshot_exit_accessible_with_flag(
        self, resolver, sample_world_data
    ) -> None:
        """Exit becomes accessible when flag is set."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=[],
            flags={"door_unlocked": True},
            visited_locations={"start_room"},
        )

        debug = resolver.build_debug_snapshot(state, sample_world_data)

        north_exit = next((e for e in debug.exits if e.direction == "north"), None)
        assert north_exit is not None
        assert north_exit.is_accessible is True
        assert north_exit.access_reason == "accessible"

    def test_debug_snapshot_includes_details(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot includes location details."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        # start_room has floor, walls, box details
        assert debug.details is not None
        assert "floor" in debug.details or "walls" in debug.details

    def test_debug_snapshot_excludes_exit_directions_from_details(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot filters exit directions out of details."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        # Exit directions should not appear in details
        assert "north" not in debug.details
        assert "south" not in debug.details
        assert "east" not in debug.details
        assert "west" not in debug.details

    def test_debug_snapshot_includes_npcs(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot includes NPC info."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        # test_npc should be in npcs list (location=start_room in fixture)
        npc_ids = [n.npc_id for n in debug.npcs]
        assert "test_npc" in npc_ids

    def test_debug_snapshot_npc_visibility_status(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot shows NPC visibility status."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        test_npc = next((n for n in debug.npcs if n.npc_id == "test_npc"), None)
        assert test_npc is not None
        assert test_npc.is_visible is True
        assert test_npc.visibility_reason == "visible"

    def test_debug_snapshot_missing_location(self, resolver, sample_world_data) -> None:
        """Debug snapshot handles missing location gracefully."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="nonexistent_room",
        )

        debug = resolver.build_debug_snapshot(state, sample_world_data)

        assert debug.location_id == "nonexistent_room"
        assert debug.name == "Unknown Location"
        assert debug.exits == []
        assert debug.items == []

    def test_debug_snapshot_includes_item_placement(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot includes item placement info if available."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        box_item = next((i for i in debug.items if i.item_id == "container_box"), None)
        assert box_item is not None
        # Placement comes from location.item_placements
        if box_item.placement:
            assert "corner" in box_item.placement

    def test_debug_snapshot_includes_npc_placement(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot includes NPC placement info if available."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        test_npc = next((n for n in debug.npcs if n.npc_id == "test_npc"), None)
        assert test_npc is not None
        # Placement comes from location.npc_placements
        if test_npc.placement:
            assert "east" in test_npc.placement

    def test_debug_snapshot_includes_interactions(
        self, resolver, sample_world_data
    ) -> None:
        """Debug snapshot includes location interactions when present."""
        from app.models.world import Location, InteractionEffect, WorldData

        # Create a location with an interaction
        loc_with_interaction = Location(
            name="Test Room",
            atmosphere="A test room",
            exits={},
            interactions={
                "test_interaction": InteractionEffect(
                    triggers=["test", "examine thing"],
                    sets_flag="test_flag",
                )
            },
        )

        custom_world = WorldData(
            world=sample_world_data.world,
            locations={"test_room": loc_with_interaction},
            items={},
            npcs={},
        )

        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="test_room",
            inventory=[],
            flags={},
        )

        debug = resolver.build_debug_snapshot(state, custom_world)

        interaction_ids = [i.interaction_id for i in debug.interactions]
        assert "test_interaction" in interaction_ids

    def test_debug_snapshot_interaction_details(
        self, resolver, sample_world_data
    ) -> None:
        """Debug snapshot includes interaction triggers and effects."""
        from app.models.world import Location, InteractionEffect, WorldData

        # Create a location with a detailed interaction
        loc_with_interaction = Location(
            name="Test Room",
            atmosphere="A test room",
            exits={},
            interactions={
                "examine_box": InteractionEffect(
                    triggers=["examine box", "look at box", "open box"],
                    sets_flag="box_opened",
                    gives_item="hidden_gem",
                )
            },
        )

        custom_world = WorldData(
            world=sample_world_data.world,
            locations={"test_room": loc_with_interaction},
            items={},
            npcs={},
        )

        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="test_room",
            inventory=[],
            flags={},
        )

        debug = resolver.build_debug_snapshot(state, custom_world)

        examine_box = next(
            (i for i in debug.interactions if i.interaction_id == "examine_box"),
            None,
        )
        assert examine_box is not None
        assert examine_box.triggers is not None
        assert len(examine_box.triggers) == 3
        assert examine_box.sets_flag == "box_opened"
        assert examine_box.gives_item == "hidden_gem"

    def test_debug_snapshot_no_interactions(
        self, resolver, state, sample_world_data
    ) -> None:
        """Debug snapshot handles locations without interactions."""
        debug = resolver.build_debug_snapshot(state, sample_world_data)

        # The sample_world_data fixture locations don't have interactions
        # in the programmatic fixture (they're in the YAML fixtures)
        assert debug.interactions == []

    # ==========================================================================
    # analyze_item_visibility tests (public method)
    # ==========================================================================

    def test_analyze_visibility_visible_item(
        self, resolver, state, sample_world_data
    ) -> None:
        """analyze_item_visibility returns visible for non-hidden items."""
        item = sample_world_data.get_item("container_box")
        is_visible, reason = resolver.analyze_item_visibility(
            item, "container_box", state
        )
        assert is_visible is True
        assert reason == "visible"

    def test_analyze_visibility_taken_item(self, resolver, sample_world_data) -> None:
        """analyze_item_visibility returns 'taken' for inventory items."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=["container_box"],
            flags={},
        )
        item = sample_world_data.get_item("container_box")
        is_visible, reason = resolver.analyze_item_visibility(
            item, "container_box", state
        )
        assert is_visible is False
        assert reason == "taken"

    def test_analyze_visibility_hidden_no_condition(
        self, resolver, state, sample_world_data
    ) -> None:
        """analyze_item_visibility returns 'hidden' for items with no condition."""
        # Create a hidden item with no find_condition
        from app.models.world import Item

        hidden_item = Item(
            name="Secret Item",
            portable=True,
            examine="A secret item.",
            hidden=True,
        )
        is_visible, reason = resolver.analyze_item_visibility(
            hidden_item, "secret_item", state
        )
        assert is_visible is False
        assert reason == "hidden"

    def test_analyze_visibility_hidden_condition_not_met(
        self, resolver, state, sample_world_data
    ) -> None:
        """analyze_item_visibility returns condition_not_met for unmet conditions."""
        item = sample_world_data.get_item("hidden_gem")
        is_visible, reason = resolver.analyze_item_visibility(item, "hidden_gem", state)
        assert is_visible is False
        assert "condition_not_met" in reason
        assert "box_opened" in reason

    def test_analyze_visibility_hidden_condition_met(
        self, resolver, sample_world_data
    ) -> None:
        """analyze_item_visibility returns visible when condition met."""
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=[],
            flags={"box_opened": True},
        )
        item = sample_world_data.get_item("hidden_gem")
        is_visible, reason = resolver.analyze_item_visibility(item, "hidden_gem", state)
        assert is_visible is True
        assert reason == "visible"
