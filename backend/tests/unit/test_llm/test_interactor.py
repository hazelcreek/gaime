"""Unit tests for InteractorAI.

Tests cover:
- Building system prompt with entities
- Parsing ActionIntent from LLM response
- Parsing FlavorIntent from LLM response
- Handling action hints in FlavorIntent
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.llm.interactor import InteractorAI
from app.models.intent import ActionIntent, ActionType, FlavorIntent
from app.models.perception import PerceptionSnapshot, VisibleEntity, VisibleExit


class TestInteractorAI:
    """Tests for InteractorAI."""

    @pytest.fixture
    def snapshot(self) -> PerceptionSnapshot:
        """Create a test perception snapshot."""
        return PerceptionSnapshot(
            location_id="start_room",
            location_name="Starting Room",
            location_atmosphere="A simple room with exits.",
            visible_items=[
                VisibleEntity(
                    id="old_letter",
                    name="Crumpled Letter",
                    description="A yellowed letter",
                ),
                VisibleEntity(
                    id="candlestick",
                    name="Silver Candlestick",
                    description="A tarnished candlestick",
                ),
            ],
            visible_details=[
                VisibleEntity(
                    id="portraits",
                    name="Portraits",
                    description="Family portraits on the walls",
                ),
            ],
            visible_exits=[
                VisibleExit(
                    direction="north",
                    destination_name="Library",
                ),
            ],
            visible_npcs=[
                VisibleEntity(
                    id="butler_jenkins",
                    name="Jenkins",
                    description="The butler",
                ),
            ],
            inventory=[
                VisibleEntity(
                    id="pocket_watch",
                    name="Pocket Watch",
                    description="Your father's watch",
                ),
            ],
            first_visit=True,
        )

    @pytest.fixture
    def interactor(self, sample_world_data) -> InteractorAI:
        """Create InteractorAI instance."""
        return InteractorAI(
            world_data=sample_world_data,
            session_id="test-session",
            debug=True,
        )

    def test_build_system_prompt_includes_items(self, interactor, snapshot) -> None:
        """System prompt includes visible items."""
        prompt = interactor._build_system_prompt(snapshot)

        assert "old_letter" in prompt
        assert "Crumpled Letter" in prompt
        assert "candlestick" in prompt

    def test_build_system_prompt_includes_details(self, interactor, snapshot) -> None:
        """System prompt includes location details."""
        prompt = interactor._build_system_prompt(snapshot)

        assert "portraits" in prompt
        assert "Portraits" in prompt

    def test_build_system_prompt_includes_npcs(self, interactor, snapshot) -> None:
        """System prompt includes NPCs."""
        prompt = interactor._build_system_prompt(snapshot)

        assert "butler_jenkins" in prompt
        assert "Jenkins" in prompt

    def test_build_system_prompt_includes_inventory(self, interactor, snapshot) -> None:
        """System prompt includes inventory."""
        prompt = interactor._build_system_prompt(snapshot)

        assert "pocket_watch" in prompt
        assert "Pocket Watch" in prompt

    def test_build_system_prompt_includes_exits(self, interactor, snapshot) -> None:
        """System prompt includes exits."""
        prompt = interactor._build_system_prompt(snapshot)

        assert "north" in prompt
        assert "Library" in prompt

    # Parse response tests

    def test_parse_action_intent_examine(self, interactor) -> None:
        """Parses EXAMINE action intent correctly."""
        parsed = {
            "type": "action_intent",
            "action_type": "EXAMINE",
            "target_id": "old_letter",
            "verb": "examine",
            "confidence": 0.95,
        }

        intent = interactor._parse_response(parsed, "examine the letter")

        assert isinstance(intent, ActionIntent)
        assert intent.action_type == ActionType.EXAMINE
        assert intent.target_id == "old_letter"
        assert intent.verb == "examine"
        assert intent.confidence == 0.95

    def test_parse_action_intent_take(self, interactor) -> None:
        """Parses TAKE action intent correctly."""
        parsed = {
            "type": "action_intent",
            "action_type": "TAKE",
            "target_id": "candlestick",
            "verb": "pick up",
            "confidence": 1.0,
        }

        intent = interactor._parse_response(parsed, "pick up the candlestick")

        assert isinstance(intent, ActionIntent)
        assert intent.action_type == ActionType.TAKE
        assert intent.target_id == "candlestick"
        assert intent.verb == "pick up"

    def test_parse_flavor_intent_generic(self, interactor) -> None:
        """Parses generic flavor intent correctly."""
        parsed = {
            "type": "flavor_intent",
            "verb": "dance",
            "manner": "gracefully",
        }

        intent = interactor._parse_response(parsed, "dance gracefully")

        assert isinstance(intent, FlavorIntent)
        assert intent.verb == "dance"
        assert intent.manner == "gracefully"
        assert intent.action_hint is None

    def test_parse_flavor_intent_with_action_hint(self, interactor) -> None:
        """Parses flavor intent with action hint correctly."""
        parsed = {
            "type": "flavor_intent",
            "verb": "examine",
            "action_hint": "EXAMINE",
            "target": "the ceiling",
        }

        intent = interactor._parse_response(parsed, "examine the ceiling")

        assert isinstance(intent, FlavorIntent)
        assert intent.verb == "examine"
        assert intent.action_hint == ActionType.EXAMINE
        assert intent.target == "the ceiling"

    def test_parse_flavor_intent_with_target_id(self, interactor) -> None:
        """Parses flavor intent with resolved target_id correctly."""
        parsed = {
            "type": "flavor_intent",
            "verb": "ask",
            "action_hint": "ASK",
            "target_id": "butler_jenkins",
            "topic": "football",
        }

        intent = interactor._parse_response(parsed, "ask jenkins about football")

        assert isinstance(intent, FlavorIntent)
        assert intent.verb == "ask"
        assert intent.action_hint == ActionType.ASK
        assert intent.target_id == "butler_jenkins"
        assert intent.topic == "football"

    def test_parse_unknown_action_type_defaults_to_examine(self, interactor) -> None:
        """Unknown action type defaults to EXAMINE."""
        parsed = {
            "type": "action_intent",
            "action_type": "UNKNOWN_ACTION",
            "target_id": "something",
            "verb": "do",
        }

        intent = interactor._parse_response(parsed, "do something")

        assert isinstance(intent, ActionIntent)
        assert intent.action_type == ActionType.EXAMINE

    def test_parse_missing_type_defaults_to_flavor(self, interactor) -> None:
        """Missing type field defaults to flavor intent."""
        parsed = {
            "verb": "wave",
        }

        intent = interactor._parse_response(parsed, "wave")

        assert isinstance(intent, FlavorIntent)
        assert intent.verb == "wave"

    # Integration test with mocked LLM

    @pytest.mark.asyncio
    async def test_parse_calls_llm(self, interactor, snapshot) -> None:
        """Parse method calls LLM and processes response."""
        mock_response = '{"type": "action_intent", "action_type": "EXAMINE", "target_id": "old_letter", "verb": "examine", "confidence": 1.0}'

        with patch(
            "app.llm.interactor.get_completion", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = mock_response

            intent, debug_info = await interactor.parse("examine the letter", snapshot)

        assert isinstance(intent, ActionIntent)
        assert intent.action_type == ActionType.EXAMINE
        assert intent.target_id == "old_letter"
        mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_returns_debug_info(self, interactor, snapshot) -> None:
        """Parse returns debug info when enabled."""
        mock_response = '{"type": "flavor_intent", "verb": "dance"}'

        with patch(
            "app.llm.interactor.get_completion", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = mock_response

            intent, debug_info = await interactor.parse("dance", snapshot)

        assert debug_info is not None
        assert debug_info.raw_response == mock_response
        assert "start_room" in debug_info.system_prompt
