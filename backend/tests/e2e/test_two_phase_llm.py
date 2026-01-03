"""End-to-end tests for InteractorAI and NarratorAI with real LLM calls.

These tests verify that the LLM components work correctly with real API calls.
They are marked as slow and e2e, so they are skipped by default in CI.

Run these tests with:
    pytest tests/e2e/test_two_phase_llm.py -v --run-slow

Prerequisites:
    - Set LLM_API_KEY environment variable with valid API key
    - Have network access to the LLM provider
"""

from __future__ import annotations

import os
import pytest

from app.engine.two_phase.models.event import Event, EventType
from app.engine.two_phase.models.perception import (
    PerceptionSnapshot,
    VisibleEntity,
    VisibleExit,
)
from app.llm.two_phase.interactor import InteractorAI
from app.llm.two_phase.narrator import NarratorAI


# Skip all tests in this module if no API key is set
pytestmark = [
    pytest.mark.slow,
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get("LLM_API_KEY") is None
        and os.environ.get("GOOGLE_API_KEY") is None
        and os.environ.get("GEMINI_API_KEY") is None,
        reason="LLM API key not set (need LLM_API_KEY, GOOGLE_API_KEY, or GEMINI_API_KEY)",
    ),
]


@pytest.fixture
def sample_snapshot() -> PerceptionSnapshot:
    """Create a sample perception snapshot for testing."""
    return PerceptionSnapshot(
        location_id="library",
        location_name="The Library",
        location_atmosphere="Dusty shelves stretch to the ceiling. An old desk sits by the window.",
        visible_items=[
            VisibleEntity(
                id="old_letter",
                name="Old Letter",
                description="A yellowed envelope sealed with red wax.",
                is_new=False,
            ),
            VisibleEntity(
                id="brass_key",
                name="Brass Key",
                description="A small key with ornate engravings.",
                is_new=False,
            ),
        ],
        visible_details=[
            VisibleEntity(
                id="bookshelves",
                name="Bookshelves",
                description="Ancient tomes fill the shelves.",
                is_new=False,
            ),
        ],
        visible_exits=[
            VisibleExit(
                direction="north",
                destination_name="The Study",
                description="A doorway leads to the study.",
                is_locked=False,
                is_blocked=False,
            ),
            VisibleExit(
                direction="south",
                destination_name="Main Hall",
                description=None,
                is_locked=False,
                is_blocked=False,
            ),
        ],
        visible_npcs=[],
        inventory=[
            VisibleEntity(
                id="candle",
                name="Candle",
                description="A half-melted candle.",
                is_new=False,
            ),
        ],
        first_visit=True,
    )


class TestInteractorAIE2E:
    """End-to-end tests for InteractorAI."""

    @pytest.fixture
    def interactor(self, sample_world_data) -> InteractorAI:
        """Create an InteractorAI instance."""
        return InteractorAI(
            world_data=sample_world_data,
            session_id="test-e2e-session",
            debug=True,
        )

    async def test_parse_examine_command(self, interactor, sample_snapshot) -> None:
        """InteractorAI correctly parses 'examine the letter' to old_letter."""
        intent, debug = await interactor.parse("examine the letter", sample_snapshot)

        # Should be an ActionIntent
        from app.engine.two_phase.models.intent import ActionIntent, ActionType

        assert isinstance(intent, ActionIntent)
        assert intent.action_type == ActionType.EXAMINE
        # Should resolve "the letter" to "old_letter"
        assert intent.target_id == "old_letter"

        # Debug info should be present
        assert debug is not None
        assert debug.raw_response is not None

    async def test_parse_take_command(self, interactor, sample_snapshot) -> None:
        """InteractorAI correctly parses 'pick up the key' to brass_key."""
        intent, debug = await interactor.parse("pick up the key", sample_snapshot)

        from app.engine.two_phase.models.intent import ActionIntent, ActionType

        assert isinstance(intent, ActionIntent)
        assert intent.action_type == ActionType.TAKE
        assert intent.target_id == "brass_key"

    async def test_parse_unknown_target_returns_flavor(
        self, interactor, sample_snapshot
    ) -> None:
        """InteractorAI returns FlavorIntent for unknown targets."""
        intent, debug = await interactor.parse("examine the ceiling", sample_snapshot)

        from app.engine.two_phase.models.intent import FlavorIntent, ActionType

        assert isinstance(intent, FlavorIntent)
        # Should have action_hint set to EXAMINE
        assert intent.action_hint == ActionType.EXAMINE
        # Target should be the unresolved description
        assert "ceiling" in intent.target.lower() if intent.target else True

    async def test_parse_unknown_verb_returns_flavor(
        self, interactor, sample_snapshot
    ) -> None:
        """InteractorAI returns FlavorIntent for unknown verbs."""
        intent, debug = await interactor.parse("dance gracefully", sample_snapshot)

        from app.engine.two_phase.models.intent import FlavorIntent

        assert isinstance(intent, FlavorIntent)
        assert "dance" in intent.verb.lower()

    async def test_parse_ambiguous_input(self, interactor, sample_snapshot) -> None:
        """InteractorAI handles ambiguous input gracefully."""
        intent, debug = await interactor.parse("look at the thing", sample_snapshot)

        # Should return either ActionIntent or FlavorIntent, not crash
        from app.engine.two_phase.models.intent import ActionIntent, FlavorIntent

        assert isinstance(intent, (ActionIntent, FlavorIntent))

    async def test_debug_info_contains_tokens(
        self, interactor, sample_snapshot
    ) -> None:
        """Debug info contains token usage information."""
        _, debug = await interactor.parse("examine letter", sample_snapshot)

        assert debug is not None
        assert debug.tokens_total > 0


class TestNarratorAIE2E:
    """End-to-end tests for NarratorAI."""

    @pytest.fixture
    def narrator(self, sample_world_data) -> NarratorAI:
        """Create a NarratorAI instance."""
        return NarratorAI(
            world_data=sample_world_data,
            session_id="test-e2e-session",
            debug=True,
        )

    async def test_opening_narrative_quality(self, narrator, sample_snapshot) -> None:
        """Opening narrative includes atmosphere and visible items."""
        event = Event(
            type=EventType.SCENE_BROWSED,
            subject="library",
            context={
                "first_visit": True,
                "is_opening": True,
                "premise": "You are a detective investigating a mysterious manor.",
                "starting_situation": "The library doors creak open as you enter.",
                "visible_items": ["Old Letter", "Brass Key"],
                "visible_npcs": [],
                "visible_exits": [
                    {"direction": "north", "destination": "The Study"},
                ],
            },
        )

        narrative, debug = await narrator.narrate([event], sample_snapshot)

        # Narrative should be substantive
        assert len(narrative) > 50

        # Should mention the location name or atmosphere
        narrative_lower = narrative.lower()
        assert "library" in narrative_lower or "dusty" in narrative_lower

        # Debug info should be present
        assert debug is not None

    async def test_location_change_narrative(self, narrator, sample_snapshot) -> None:
        """Narrates movement to a new location."""
        event = Event(
            type=EventType.LOCATION_CHANGED,
            subject="library",
            context={
                "from_location": "main_hall",
                "direction": "north",
                "first_visit": True,
                "destination_name": "The Library",
                "visible_items": ["Old Letter", "Brass Key"],
                "visible_npcs": [],
                "visible_exits": [
                    {"direction": "north", "destination": "The Study"},
                    {"direction": "south", "destination": "Main Hall"},
                ],
            },
        )

        narrative, debug = await narrator.narrate([event], sample_snapshot)

        # Should have actual narrative content
        assert len(narrative) > 20

        # Should reference the library or movement
        narrative_lower = narrative.lower()
        assert (
            "library" in narrative_lower
            or "enter" in narrative_lower
            or "step" in narrative_lower
        )

    async def test_rejection_narrative_is_natural(
        self, narrator, sample_snapshot
    ) -> None:
        """Rejection narratives feel natural, not like error messages."""
        from app.engine.two_phase.models.event import RejectionEvent, RejectionCode

        event = RejectionEvent(
            rejection_code=RejectionCode.NO_EXIT,
            rejection_reason="There's no way to go west from here.",
            subject="west",
        )

        narrative, debug = await narrator.narrate([event], sample_snapshot)

        # Should not contain error-like language
        assert "error" not in narrative.lower()
        assert "invalid" not in narrative.lower()

        # Should explain why movement isn't possible
        assert len(narrative) > 10

    async def test_examine_item_narrative(self, narrator, sample_snapshot) -> None:
        """Examine action generates descriptive narrative."""
        event = Event(
            type=EventType.ITEM_EXAMINED,
            subject="old_letter",
            context={
                "entity_name": "Old Letter",
                "description": "A yellowed envelope sealed with red wax. The seal shows a raven crest.",
                "in_inventory": False,
            },
        )

        narrative, debug = await narrator.narrate([event], sample_snapshot)

        # Should describe the letter
        narrative_lower = narrative.lower()
        assert "letter" in narrative_lower or "envelope" in narrative_lower

    async def test_take_item_narrative(self, narrator, sample_snapshot) -> None:
        """Take action generates appropriate narrative."""
        event = Event(
            type=EventType.ITEM_TAKEN,
            subject="brass_key",
            context={
                "item_name": "Brass Key",
                "take_description": "The key feels cold in your hand.",
                "from_location": "library",
            },
        )

        narrative, debug = await narrator.narrate([event], sample_snapshot)

        # Should describe taking the key
        narrative_lower = narrative.lower()
        assert "key" in narrative_lower

    async def test_flavor_action_narrative(self, narrator, sample_snapshot) -> None:
        """Flavor actions get atmospheric responses."""
        event = Event(
            type=EventType.FLAVOR_ACTION,
            context={
                "verb": "dance",
                "action_hint": None,
                "target": None,
                "target_id": None,
                "topic": None,
                "manner": "gracefully",
            },
        )

        narrative, debug = await narrator.narrate([event], sample_snapshot)

        # Should have some narrative response
        assert len(narrative) > 10

    async def test_no_hidden_items_mentioned(self, narrator) -> None:
        """Narrator does not mention items not in the snapshot."""
        # Create a snapshot with only one visible item
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
            location_atmosphere="A quiet library.",
            visible_items=[
                VisibleEntity(
                    id="book",
                    name="Book",
                    description="An ordinary book.",
                    is_new=False,
                ),
            ],
            visible_details=[],
            visible_exits=[],
            visible_npcs=[],
            inventory=[],
            first_visit=False,
        )

        event = Event(
            type=EventType.SCENE_BROWSED,
            subject="library",
            context={
                "first_visit": False,
                "is_manual_browse": True,
                "visible_items": ["Book"],
                "visible_npcs": [],
                "visible_exits": [],
            },
        )

        narrative, debug = await narrator.narrate([event], snapshot)

        # The hidden items (not in snapshot) should NOT be mentioned
        narrative_lower = narrative.lower()
        # These are not in the snapshot so shouldn't appear
        assert "secret" not in narrative_lower
        assert "hidden" not in narrative_lower

    async def test_debug_info_contains_prompts(self, narrator, sample_snapshot) -> None:
        """Debug info contains the full prompts used."""
        event = Event(
            type=EventType.SCENE_BROWSED,
            subject="library",
            context={
                "first_visit": True,
                "visible_items": ["Old Letter"],
                "visible_npcs": [],
                "visible_exits": [],
            },
        )

        _, debug = await narrator.narrate([event], sample_snapshot)

        assert debug is not None
        assert debug.system_prompt is not None
        assert len(debug.system_prompt) > 100
        assert debug.user_prompt is not None
        assert "SCENE_BROWSED" in debug.user_prompt
