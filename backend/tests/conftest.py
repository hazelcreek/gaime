"""
Shared pytest fixtures for GAIME backend tests.

This module provides:
- sample_world_data: Minimal WorldData for fast unit tests
- sample_game_state: GameState with predictable values
- mock_llm_client: Mock LLM client for deterministic testing
- Custom markers for test categorization
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.models.game import GameState, NarrativeMemory  # noqa: E402
from app.models.world import (  # noqa: E402
    WorldData,
    World,
    Location,
    Item,
    NPC,
    PlayerSetup,
    VictoryCondition,
    LocationRequirement,
    NPCTrust,
    NPCPersonality,
)

if TYPE_CHECKING:
    from tests.mocks.llm import MockLLMClient


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests requiring real LLM"
    )


# =============================================================================
# World Data Fixtures
# =============================================================================


@pytest.fixture
def sample_world() -> World:
    """Create a minimal World configuration for testing."""
    return World(
        name="Test World",
        theme="A simple test world for unit testing",
        premise="You are testing the game engine.",
        tone="neutral",
        constraints=["Keep responses brief for testing"],
        commands={
            "look": "Examine your surroundings",
            "inventory": "Check what you're carrying",
            "help": "Show available commands",
        },
        player=PlayerSetup(
            starting_location="start_room",
            starting_inventory=["test_key"],
        ),
        victory=VictoryCondition(
            location="secret_room",
            flag="puzzle_solved",
            narrative="You have completed the test!",
        ),
    )


@pytest.fixture
def sample_locations() -> dict[str, Location]:
    """Create a minimal 3-room layout for testing.

    Layout:
        [locked_room] (north, requires door_unlocked flag)
              |
        [start_room] --- [secret_room] (east, requires knows_secret flag)
    """
    return {
        "start_room": Location(
            name="Starting Room",
            atmosphere="A simple room with exits in multiple directions.",
            exits={"north": "locked_room", "east": "secret_room"},
            items=["container_box"],
            details={
                "floor": "Plain wooden floorboards.",
                "walls": "Bare stone walls.",
            },
        ),
        "locked_room": Location(
            name="Locked Room",
            atmosphere="A room that was previously locked.",
            exits={"south": "start_room"},
            requires=LocationRequirement(flag="door_unlocked"),
        ),
        "secret_room": Location(
            name="Secret Room",
            atmosphere="A hidden chamber with ancient secrets.",
            exits={"west": "start_room"},
            requires=LocationRequirement(flag="knows_secret"),
        ),
    }


@pytest.fixture
def sample_items() -> dict[str, Item]:
    """Create sample items including a container with hidden contents."""
    return {
        "test_key": Item(
            name="Test Key",
            portable=True,
            examine="A simple brass key for testing.",
            location="start_room",
            unlocks="locked_room",
        ),
        "container_box": Item(
            name="Wooden Box",
            portable=False,
            examine="A small wooden box with a lid.",
            location="start_room",
        ),
        "hidden_gem": Item(
            name="Hidden Gem",
            portable=True,
            examine="A sparkling gem hidden in the box.",
            location="start_room",
            hidden=True,
            find_condition={"requires_flag": "box_opened"},
            found_description="A beautiful gem glints from inside the box.",
        ),
    }


@pytest.fixture
def sample_npcs() -> dict[str, NPC]:
    """Create a sample NPC for testing."""
    return {
        "test_npc": NPC(
            name="Test Guide",
            role="A helpful guide for testing",
            location="start_room",
            appearance="A friendly figure ready to help.",
            personality=NPCPersonality(
                traits=["helpful", "patient"],
                speech_style="Clear and concise",
            ),
            knowledge=["Knows about the secret room", "Knows about the puzzle"],
            trust=NPCTrust(initial=0, threshold=2),
        ),
    }


@pytest.fixture
def sample_world_data(
    sample_world: World,
    sample_locations: dict[str, Location],
    sample_items: dict[str, Item],
    sample_npcs: dict[str, NPC],
) -> WorldData:
    """Create complete WorldData for testing."""
    return WorldData(
        world=sample_world,
        locations=sample_locations,
        items=sample_items,
        npcs=sample_npcs,
    )


# =============================================================================
# Game State Fixtures
# =============================================================================


@pytest.fixture
def sample_game_state() -> GameState:
    """Create a GameState with predictable initial values."""
    return GameState(
        session_id="test-session-001",
        current_location="start_room",
        inventory=["test_key"],
        discovered_locations=["start_room"],
        flags={},
        turn_count=0,
        npc_trust={"test_npc": 0},
        npc_locations={},
        status="playing",
        narrative_memory=NarrativeMemory(),
    )


@pytest.fixture
def game_state_with_progress() -> GameState:
    """Create a GameState with some progress made."""
    return GameState(
        session_id="test-session-002",
        current_location="start_room",
        inventory=["test_key", "hidden_gem"],
        discovered_locations=["start_room", "locked_room"],
        flags={
            "door_unlocked": True,
            "box_opened": True,
        },
        turn_count=5,
        npc_trust={"test_npc": 2},
        npc_locations={},
        status="playing",
        narrative_memory=NarrativeMemory(),
    )


# =============================================================================
# LLM Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_client() -> "MockLLMClient":
    """Create a mock LLM client with default responses."""
    from tests.mocks.llm import MockLLMClient

    return MockLLMClient(
        responses={
            "default": '{"narrative": "Test response", "state_changes": {}}',
        }
    )


@pytest.fixture
def mock_llm_with_responses() -> callable:
    """Factory fixture to create mock LLM with custom responses.

    Usage:
        def test_something(mock_llm_with_responses):
            llm = mock_llm_with_responses({
                "examine": '{"narrative": "You see a key"}',
                "take": '{"narrative": "You pick up the key"}',
            })
    """
    from tests.mocks.llm import MockLLMClient

    def _factory(responses: dict[str, str]) -> MockLLMClient:
        return MockLLMClient(responses=responses)

    return _factory
