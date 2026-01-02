"""Unit tests for RuleBasedParser.

Tests cover:
- Cardinal direction patterns (north, n, go north)
- Vertical directions (up, down)
- Back/leave/exit patterns
- Non-movement returns None
- Confidence scores
"""

import pytest

from app.engine.parser import RuleBasedParser
from app.models.intent import ActionType
from app.models.two_phase_state import TwoPhaseGameState


class TestRuleBasedParser:
    """Tests for RuleBasedParser movement parsing."""

    @pytest.fixture
    def parser(self) -> RuleBasedParser:
        """Create parser instance."""
        return RuleBasedParser()

    @pytest.fixture
    def state(self) -> TwoPhaseGameState:
        """Create minimal test state."""
        return TwoPhaseGameState(
            session_id="test-session",
            current_location="start_room",
        )

    @pytest.fixture
    def world(self, sample_world_data):
        """Use sample world data fixture."""
        return sample_world_data

    # Cardinal direction tests

    def test_parse_north(self, parser, state, world) -> None:
        """'north' parses to MOVE intent."""
        intent = parser.parse("north", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.MOVE
        assert intent.target_id == "north"
        assert intent.verb == "go"
        assert intent.confidence == 1.0

    def test_parse_n(self, parser, state, world) -> None:
        """'n' parses to MOVE north."""
        intent = parser.parse("n", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.MOVE
        assert intent.target_id == "north"

    def test_parse_go_north(self, parser, state, world) -> None:
        """'go north' parses to MOVE intent."""
        intent = parser.parse("go north", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.MOVE
        assert intent.target_id == "north"
        assert intent.verb == "go"

    def test_parse_south(self, parser, state, world) -> None:
        """'south' and 's' parse correctly."""
        for cmd in ("south", "s", "go south"):
            intent = parser.parse(cmd, state, world)
            assert intent is not None
            assert intent.target_id == "south"

    def test_parse_east(self, parser, state, world) -> None:
        """'east' and 'e' parse correctly."""
        for cmd in ("east", "e", "go east"):
            intent = parser.parse(cmd, state, world)
            assert intent is not None
            assert intent.target_id == "east"

    def test_parse_west(self, parser, state, world) -> None:
        """'west' and 'w' parse correctly."""
        for cmd in ("west", "w", "go west"):
            intent = parser.parse(cmd, state, world)
            assert intent is not None
            assert intent.target_id == "west"

    # Vertical directions

    def test_parse_up(self, parser, state, world) -> None:
        """'up' and 'u' parse correctly."""
        for cmd in ("up", "u", "go up"):
            intent = parser.parse(cmd, state, world)
            assert intent is not None
            assert intent.target_id == "up"

    def test_parse_down(self, parser, state, world) -> None:
        """'down' and 'd' parse correctly."""
        for cmd in ("down", "d", "go down"):
            intent = parser.parse(cmd, state, world)
            assert intent is not None
            assert intent.target_id == "down"

    # Back/leave/exit

    def test_parse_back(self, parser, state, world) -> None:
        """'back' parses to MOVE with 'back' target."""
        intent = parser.parse("back", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.MOVE
        assert intent.target_id == "back"

    def test_parse_go_back(self, parser, state, world) -> None:
        """'go back' parses to MOVE with 'back' target."""
        intent = parser.parse("go back", state, world)

        assert intent is not None
        assert intent.target_id == "back"

    def test_parse_leave(self, parser, state, world) -> None:
        """'leave' parses to MOVE back."""
        intent = parser.parse("leave", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.MOVE
        assert intent.target_id == "back"
        assert intent.verb == "leave"

    def test_parse_exit(self, parser, state, world) -> None:
        """'exit' parses to MOVE back."""
        intent = parser.parse("exit", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.MOVE
        assert intent.target_id == "back"
        assert intent.verb == "exit"

    # Browse patterns

    def test_parse_look(self, parser, state, world) -> None:
        """'look' parses to BROWSE intent."""
        intent = parser.parse("look", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.BROWSE
        assert intent.target_id == ""
        assert intent.verb == "look"
        assert intent.confidence == 1.0

    def test_parse_look_around(self, parser, state, world) -> None:
        """'look around' parses to BROWSE intent."""
        intent = parser.parse("look around", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.BROWSE
        assert intent.target_id == ""
        assert intent.verb == "look"

    def test_parse_l(self, parser, state, world) -> None:
        """'l' parses to BROWSE intent."""
        intent = parser.parse("l", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.BROWSE
        assert intent.target_id == ""

    def test_parse_survey(self, parser, state, world) -> None:
        """'survey' parses to BROWSE intent."""
        intent = parser.parse("survey", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.BROWSE
        assert intent.verb == "look"

    def test_parse_scan(self, parser, state, world) -> None:
        """'scan' parses to BROWSE intent."""
        intent = parser.parse("scan", state, world)

        assert intent is not None
        assert intent.action_type == ActionType.BROWSE

    def test_look_at_not_browse(self, parser, state, world) -> None:
        """'look at X' should NOT match BROWSE (should return None for Interactor)."""
        intent = parser.parse("look at the desk", state, world)

        # This should NOT be parsed as BROWSE - Interactor handles it as EXAMINE
        assert intent is None

    # Non-movement commands return None

    def test_examine_returns_none(self, parser, state, world) -> None:
        """'examine' returns None (not supported in Phase 1)."""
        intent = parser.parse("examine painting", state, world)
        assert intent is None

    def test_take_returns_none(self, parser, state, world) -> None:
        """'take' returns None (not supported in Phase 1)."""
        intent = parser.parse("take key", state, world)
        assert intent is None

    def test_talk_returns_none(self, parser, state, world) -> None:
        """'talk' returns None (not supported in Phase 1)."""
        intent = parser.parse("talk to guard", state, world)
        assert intent is None

    def test_gibberish_returns_none(self, parser, state, world) -> None:
        """Unrecognized input returns None."""
        intent = parser.parse("xyzzy plugh", state, world)
        assert intent is None

    def test_empty_returns_none(self, parser, state, world) -> None:
        """Empty input returns None."""
        intent = parser.parse("", state, world)
        assert intent is None

    # Case insensitivity

    def test_case_insensitive(self, parser, state, world) -> None:
        """Parser is case insensitive."""
        for cmd in ("NORTH", "North", "NoRtH"):
            intent = parser.parse(cmd, state, world)
            assert intent is not None
            assert intent.target_id == "north"

    # Whitespace handling

    def test_whitespace_trimmed(self, parser, state, world) -> None:
        """Parser trims whitespace."""
        intent = parser.parse("  north  ", state, world)
        assert intent is not None
        assert intent.target_id == "north"

    # Raw input preserved

    def test_raw_input_preserved(self, parser, state, world) -> None:
        """raw_input preserves original input."""
        intent = parser.parse("GO NORTH", state, world)
        assert intent is not None
        assert intent.raw_input == "GO NORTH"

    # Confidence score

    def test_confidence_is_one(self, parser, state, world) -> None:
        """Rule-based parsing has confidence 1.0."""
        intent = parser.parse("north", state, world)
        assert intent is not None
        assert intent.confidence == 1.0
