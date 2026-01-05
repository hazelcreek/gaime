"""Unit tests for NarratorAI prompt building.

Tests cover:
- Exit formatting respects destination_known
- NPC formatting in system prompt
- narrative_hint handling in event descriptions
"""

import pytest

from app.engine.two_phase.models.perception import (
    PerceptionSnapshot,
    VisibleEntity,
    VisibleExit,
)
from app.engine.two_phase.models.event import Event, EventType
from app.llm.two_phase.narrator import NarratorAI


class TestNarratorPromptBuilding:
    """Tests for NarratorAI prompt building."""

    @pytest.fixture
    def narrator(self, sample_world_data) -> NarratorAI:
        """Create NarratorAI instance."""
        return NarratorAI(
            world_data=sample_world_data,
            session_id="test-session",
            debug=True,
        )

    # =========================================================================
    # Exit destination visibility tests
    # =========================================================================

    def test_known_destination_in_prompt(self, narrator) -> None:
        """Exits with destination_known=True show destination name in prompt."""
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
            visible_exits=[
                VisibleExit(
                    direction="north",
                    destination_name="The Study",
                    destination_known=True,
                    description="An archway leads north",
                ),
            ],
        )

        prompt = narrator._build_system_prompt(snapshot)

        # Should contain the destination name
        assert "The Study" in prompt
        assert "north" in prompt

    def test_unknown_destination_hidden_in_prompt(self, narrator) -> None:
        """Exits with destination_known=False do NOT show destination name in prompt."""
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
            visible_exits=[
                VisibleExit(
                    direction="north",
                    destination_name="Secret Chamber",  # Should NOT appear
                    destination_known=False,
                    description="A heavy iron door",
                ),
            ],
        )

        prompt = narrator._build_system_prompt(snapshot)

        # Should NOT contain the destination name
        assert "Secret Chamber" not in prompt
        # Should indicate unknown
        assert "unknown" in prompt.lower()
        # Should still show the direction
        assert "north" in prompt

    def test_mixed_destinations_in_prompt(self, narrator) -> None:
        """Prompt correctly handles mix of known and unknown destinations."""
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
            visible_exits=[
                VisibleExit(
                    direction="north",
                    destination_name="The Study",
                    destination_known=True,
                ),
                VisibleExit(
                    direction="east",
                    destination_name="Hidden Room",  # Should NOT appear
                    destination_known=False,
                ),
            ],
        )

        prompt = narrator._build_system_prompt(snapshot)

        # Known destination should appear
        assert "The Study" in prompt
        # Unknown destination should NOT appear
        assert "Hidden Room" not in prompt

    # =========================================================================
    # NPC formatting tests
    # =========================================================================

    def test_visible_npcs_in_prompt(self, narrator) -> None:
        """Visible NPCs appear in system prompt."""
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
            visible_npcs=[
                VisibleEntity(
                    id="butler",
                    name="The Butler",
                    description="A stern man in formal attire",
                ),
            ],
        )

        prompt = narrator._build_system_prompt(snapshot)

        # Should contain NPC info
        assert "The Butler" in prompt
        assert "stern man" in prompt

    def test_no_npcs_shows_no_one(self, narrator) -> None:
        """Empty visible_npcs shows 'No one else here'."""
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
            visible_npcs=[],
        )

        prompt = narrator._build_system_prompt(snapshot)

        # Should indicate no NPCs
        assert "No one else here" in prompt

    # =========================================================================
    # Event description tests
    # =========================================================================

    def test_exit_examined_event_description(self, narrator) -> None:
        """EXIT_EXAMINED event is described correctly."""
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
        )

        event = Event(
            type=EventType.EXIT_EXAMINED,
            subject="north_door",
            context={
                "entity_name": "the iron door",
                "description": "The door is heavily reinforced",
                "destination_known": False,
            },
        )

        description = narrator._describe_event(event, snapshot)

        # Should use the exit examined handler
        assert "EXIT_EXAMINED" in description
        assert "iron door" in description
        assert "unknown" in description.lower() or "DO NOT reveal" in description

    def test_exit_examined_with_destination_reveal(self, narrator) -> None:
        """EXIT_EXAMINED with destination_revealed is dramatized."""
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
        )

        event = Event(
            type=EventType.EXIT_EXAMINED,
            subject="north_door",
            context={
                "entity_name": "the iron door",
                "description": "Examining the markings reveals...",
                "destination_revealed": True,
                "destination_name": "The Secret Chamber",
            },
        )

        description = narrator._describe_event(event, snapshot)

        # Should mention revelation
        assert "REVEALED" in description or "discovered" in description.lower()
        assert "Secret Chamber" in description

    def test_narrative_hint_in_item_examined(self, narrator) -> None:
        """narrative_hint is included in ITEM_EXAMINED event description."""
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
        )

        event = Event(
            type=EventType.ITEM_EXAMINED,
            subject="old_letter",
            context={
                "entity_name": "Old Letter",
                "description": "A yellowed envelope",
                "narrative_hint": "The wax seal bears an unfamiliar crest!",
            },
        )

        description = narrator._describe_event(event, snapshot)

        # Should include the hint
        assert "wax seal" in description or "Narrative Hint" in description

    def test_narrative_hint_in_detail_examined(self, narrator) -> None:
        """narrative_hint is included in DETAIL_EXAMINED event description."""
        snapshot = PerceptionSnapshot(
            location_id="library",
            location_name="The Library",
        )

        event = Event(
            type=EventType.DETAIL_EXAMINED,
            subject="portrait",
            context={
                "entity_name": "Portrait",
                "description": "A painting of the former owner",
                "narrative_hint": "The eyes seem to follow you!",
            },
        )

        description = narrator._describe_event(event, snapshot)

        # Should include the hint
        assert "eyes" in description or "Narrative Hint" in description
