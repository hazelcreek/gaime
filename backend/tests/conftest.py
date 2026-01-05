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
    ExitDefinition,
    DetailDefinition,
    ItemPlacement,
    NPCPlacement,
    ExaminationEffect,
)

if TYPE_CHECKING:
    from tests.mocks.llm import MockLLMClient


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command line options."""
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests (including E2E tests with real LLM calls)",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests requiring real LLM"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip slow/e2e tests unless --run-slow is provided."""
    if config.getoption("--run-slow"):
        # --run-slow given: don't skip slow tests
        return

    skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
    for item in items:
        if "slow" in item.keywords or "e2e" in item.keywords:
            item.add_marker(skip_slow)


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
    """Create a minimal 3-room layout for testing (V3 schema + Phase 4 features).

    Layout:
        [locked_room] (north, requires door_unlocked flag)
              |
        [start_room] --- [secret_room] (east, requires knows_secret flag)

    V3: Uses item_placements and npc_placements instead of items/npcs lists.
    Phase 4: Uses on_examine effects and destination reveal features.
    """
    return {
        "start_room": Location(
            name="Starting Room",
            atmosphere="A simple room with exits in multiple directions.",
            exits={
                "north": ExitDefinition(
                    destination="locked_room",
                    scene_description="A heavy wooden door to the north",
                    examine_description="The iron lock mechanism is old but functional.",
                    destination_known=False,
                    reveal_destination_on_examine=True,  # Phase 4
                ),
                "east": ExitDefinition(
                    destination="secret_room",
                    scene_description="A concealed passage to the east",
                    destination_known=False,
                    reveal_destination_on_flag="found_secret_door",  # Phase 4
                ),
            },
            # V3: item_placements defines which items are here and their visibility
            item_placements={
                "test_key": ItemPlacement(
                    placement="catches the light on the floor",
                ),
                "container_box": ItemPlacement(
                    placement="sits in the corner",
                ),
                "hidden_gem": ItemPlacement(
                    placement="glints from inside the box",
                    hidden=True,
                    find_condition={"requires_flag": "box_opened"},
                ),
            },
            # V3: npc_placements defines which NPCs are here
            npc_placements={
                "test_npc": NPCPlacement(
                    placement="stands near the east wall",
                ),
            },
            details={
                "floor": DetailDefinition(
                    name="Floor",
                    scene_description="Plain wooden floorboards.",
                ),
                "walls": DetailDefinition(
                    name="Walls",
                    scene_description="Bare stone walls.",
                ),
                "box": DetailDefinition(  # Phase 4: detail with on_examine
                    name="Wooden Box",
                    scene_description="A small wooden box with a brass clasp.",
                    examine_description="You open the brass clasp and peer inside the box.",
                    on_examine=ExaminationEffect(
                        sets_flag="box_opened",
                        narrative_hint="The box opens to reveal its contents",
                    ),
                ),
            },
        ),
        "locked_room": Location(
            name="Locked Room",
            atmosphere="A room that was previously locked.",
            exits={
                "south": ExitDefinition(
                    destination="start_room",
                    scene_description="The doorway back to the starting room",
                    destination_known=True,
                ),
            },
            requires=LocationRequirement(flag="door_unlocked"),
        ),
        "secret_room": Location(
            name="Secret Room",
            atmosphere="A hidden chamber with ancient secrets.",
            exits={
                "west": ExitDefinition(
                    destination="start_room",
                    scene_description="The passage back to the starting room",
                    destination_known=True,
                ),
            },
            requires=LocationRequirement(flag="knows_secret"),
        ),
    }


@pytest.fixture
def sample_items() -> dict[str, Item]:
    """Create sample items (V3 schema + Phase 4 features).

    V3: Removed location, hidden, find_condition - these are now in ItemPlacement.
    Phase 4: Adds on_examine effects to items.
    """
    return {
        "test_key": Item(
            name="Test Key",
            portable=True,
            examine_description="A simple brass key for testing.",
            scene_description="A brass key catches the light.",
            unlocks="locked_room",
            on_examine=ExaminationEffect(  # Phase 4
                sets_flag="key_examined",
                narrative_hint="The key has strange markings.",
            ),
        ),
        "container_box": Item(
            name="Wooden Box",
            portable=False,
            examine_description="A small wooden box with a lid.",
            scene_description="A wooden box sits here.",
        ),
        "hidden_gem": Item(
            name="Hidden Gem",
            portable=True,
            examine_description="A sparkling gem hidden in the box.",
            scene_description="A beautiful gem glints from inside the box.",
            # V3: hidden and find_condition moved to ItemPlacement in locations
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
