"""Integration tests for TwoPhaseProcessor.

Tests cover:
- Full movement flow with mocked LLM
- Rejected movement (locked door)
- Unsupported action response
- Opening narrative generation
- Turn counting
- Victory checking
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.engine.two_phase import TwoPhaseProcessor
from app.engine.two_phase_state import TwoPhaseStateManager
from app.models.two_phase_state import TwoPhaseGameState
from app.models.event import EventType


class TestTwoPhaseProcessorIntegration:
    """Integration tests for TwoPhaseProcessor."""

    @pytest.fixture
    def mock_llm_response(self):
        """Create a mock LLM response."""
        return '{"narrative": "You enter a new room."}'

    @pytest.fixture
    def mock_narrator(self, mock_llm_response):
        """Create a mock narrator that returns test narrative."""

        async def mock_narrate(events, snapshot):
            return "You enter a new room.", None

        narrator = MagicMock()
        narrator.narrate = AsyncMock(side_effect=mock_narrate)
        return narrator

    @pytest.fixture
    def processor_with_mock(self, sample_world_data, mock_narrator):
        """Create processor with mocked narrator."""
        # Create a mock state manager
        manager = MagicMock(spec=TwoPhaseStateManager)
        manager.session_id = "test-session"
        manager.world_id = "test-world"
        manager.world_data = sample_world_data

        # Setup state
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=["test_key"],
            flags={},
            visited_locations={"start_room"},
            turn_count=0,
        )
        manager.get_state.return_value = state
        manager.get_current_location.return_value = sample_world_data.get_location(
            "start_room"
        )
        manager.is_first_visit.return_value = True
        manager.move_to.return_value = True
        manager.check_victory.return_value = (False, "")
        manager.increment_turn.return_value = None

        processor = TwoPhaseProcessor(manager, debug=False)
        processor.narrator = mock_narrator

        return processor, manager

    # Movement tests

    @pytest.mark.asyncio
    async def test_successful_movement(self, processor_with_mock) -> None:
        """Successful movement returns narrative and updates state."""
        processor, manager = processor_with_mock
        manager._state = manager.get_state()
        manager._state.flags["door_unlocked"] = True

        # Update the manager to return state with flag
        state_with_flag = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            inventory=["test_key"],
            flags={"door_unlocked": True},
            visited_locations={"start_room"},
            turn_count=0,
        )
        manager.get_state.return_value = state_with_flag

        response = await processor.process("north")

        assert response.narrative is not None
        assert len(response.narrative) > 0
        manager.move_to.assert_called_once()
        manager.increment_turn.assert_called_once()

    @pytest.mark.asyncio
    async def test_movement_rejected_locked(self, processor_with_mock) -> None:
        """Movement to locked room is rejected."""
        processor, manager = processor_with_mock

        # No door_unlocked flag - movement should be rejected
        response = await processor.process("north")

        assert response.narrative is not None
        # Move should not be called for rejected movement
        manager.move_to.assert_not_called()
        # Turn should still increment
        manager.increment_turn.assert_called_once()

    @pytest.mark.asyncio
    async def test_movement_rejected_no_exit(self, processor_with_mock) -> None:
        """Movement to non-existent exit is rejected."""
        processor, manager = processor_with_mock

        response = await processor.process("west")

        assert response.narrative is not None
        manager.move_to.assert_not_called()

    # Unsupported action tests

    @pytest.mark.asyncio
    async def test_unsupported_action(self, processor_with_mock) -> None:
        """Non-movement actions return unsupported message."""
        processor, manager = processor_with_mock

        response = await processor.process("examine painting")

        assert "don't understand" in response.narrative.lower()
        assert response.events == []
        manager.move_to.assert_not_called()
        manager.increment_turn.assert_not_called()

    @pytest.mark.asyncio
    async def test_take_action_unsupported(self, processor_with_mock) -> None:
        """Take actions are not supported in Phase 1."""
        processor, manager = processor_with_mock

        response = await processor.process("take key")

        assert "don't understand" in response.narrative.lower()

    @pytest.mark.asyncio
    async def test_empty_action_unsupported(self, processor_with_mock) -> None:
        """Empty actions return unsupported message."""
        processor, manager = processor_with_mock

        response = await processor.process("")

        assert "don't understand" in response.narrative.lower()

    # Opening narrative tests

    @pytest.mark.asyncio
    async def test_opening_narrative(self, processor_with_mock) -> None:
        """Opening narrative is generated for game start."""
        processor, manager = processor_with_mock

        narrative, debug_info = await processor.get_initial_narrative()

        assert narrative is not None
        assert len(narrative) > 0
        # Narrator should be called with LOCATION_CHANGED event
        processor.narrator.narrate.assert_called_once()
        call_args = processor.narrator.narrate.call_args
        events = call_args[0][0]
        assert len(events) == 1
        assert events[0].type == EventType.LOCATION_CHANGED
        assert events[0].context.get("is_opening") is True

    # Game over tests

    @pytest.mark.asyncio
    async def test_game_over_response(self, processor_with_mock) -> None:
        """Game over state returns appropriate message."""
        processor, manager = processor_with_mock

        # Set game to won state
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="end_room",
            status="won",
        )
        manager.get_state.return_value = state

        response = await processor.process("north")

        assert "game has ended" in response.narrative.lower()
        assert response.game_complete is True

    # Victory tests

    @pytest.mark.asyncio
    async def test_victory_condition(self, processor_with_mock) -> None:
        """Victory condition triggers game complete."""
        processor, manager = processor_with_mock

        # Setup for successful movement that triggers victory
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            flags={"knows_secret": True},
            visited_locations={"start_room"},
            turn_count=0,
        )
        manager.get_state.return_value = state
        manager.check_victory.return_value = (True, "You win!")
        manager.move_to.return_value = True

        response = await processor.process("east")

        assert response.game_complete is True
        assert response.ending_narrative == "You win!"

    # Event structure tests

    @pytest.mark.asyncio
    async def test_events_in_response(self, processor_with_mock) -> None:
        """Response includes events list."""
        processor, manager = processor_with_mock

        # Setup for successful movement
        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            flags={"door_unlocked": True},
            visited_locations={"start_room"},
            turn_count=0,
        )
        manager.get_state.return_value = state

        response = await processor.process("north")

        assert response.events is not None
        assert len(response.events) > 0
        # Events should be serialized dicts
        assert isinstance(response.events[0], dict)


class TestTwoPhaseProcessorWithRealState:
    """Tests using real TwoPhaseStateManager (requires test world)."""

    @pytest.fixture
    def mock_narrator_for_real(self):
        """Create mock narrator for tests with real state manager."""

        async def mock_narrate(events, snapshot):
            return "Test narrative.", None

        narrator = MagicMock()
        narrator.narrate = AsyncMock(side_effect=mock_narrate)
        return narrator

    @pytest.mark.asyncio
    async def test_full_flow_with_real_state(
        self, sample_world_data, mock_narrator_for_real
    ) -> None:
        """Test full movement flow with real state manager (mocked world loading)."""
        # This test would require mocking WorldLoader
        # For now, just verify the processor can be created
        pass


class TestTwoPhaseProcessorDirectionParsing:
    """Tests for direction parsing through the full processor."""

    @pytest.fixture
    def processor_with_mock(self, sample_world_data):
        """Create processor with mocked narrator."""

        async def mock_narrate(events, snapshot):
            return "Test narrative.", None

        manager = MagicMock(spec=TwoPhaseStateManager)
        manager.session_id = "test-session"
        manager.world_id = "test-world"
        manager.world_data = sample_world_data

        state = TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
            flags={"door_unlocked": True},
            visited_locations={"start_room"},
        )
        manager.get_state.return_value = state
        manager.is_first_visit.return_value = True
        manager.move_to.return_value = True
        manager.check_victory.return_value = (False, "")
        manager.increment_turn.return_value = None

        processor = TwoPhaseProcessor(manager, debug=False)
        processor.narrator = MagicMock()
        processor.narrator.narrate = AsyncMock(side_effect=mock_narrate)

        return processor, manager

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "command",
        ["north", "n", "go north", "NORTH", "  north  "],
    )
    async def test_north_variations(self, command, processor_with_mock) -> None:
        """Various north commands are processed."""
        processor, manager = processor_with_mock

        response = await processor.process(command)

        # Should attempt movement (even if rejected due to requirements)
        # The important thing is it wasn't treated as unsupported
        assert "don't understand" not in response.narrative.lower()
