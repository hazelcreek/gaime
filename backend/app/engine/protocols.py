"""
Protocol definitions for the two-phase game engine.

This module defines abstract interfaces (Protocols) for the key components
of the two-phase action processing loop. Using protocols enables:

- Dependency injection for testing
- Clear component boundaries
- Swappable implementations
- Type-safe duck typing

See planning/two-phase-game-loop-spec.md for the full specification.

Component Flow:
    Player Input -> ActionParser -> ActionIntent/FlavorIntent
                                          |
                                          v
                                  IntentValidator -> ValidationResult
                                          |
                                          v (if valid)
                                  EventExecutor -> List[Event]
                                          |
                                          v
                                   NarratorAI -> Narrative Text
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.models.game import GameState
    from app.models.world import WorldData
    from app.models.intent import ActionIntent, FlavorIntent
    from app.models.event import Event
    from app.models.perception import PerceptionSnapshot
    from app.models.validation import ValidationResult


@runtime_checkable
class ActionParser(Protocol):
    """Protocol for parsing player input into structured intents.

    Implementations should attempt to parse the raw input and return
    an ActionIntent if successful, or None if parsing fails (e.g.,
    the input requires AI interpretation).

    Example implementations:
        - RuleBasedParser: Fast regex-based parsing for common patterns
        - InteractorAI: LLM-based parsing for complex/ambiguous inputs
    """

    def parse(
        self,
        raw_input: str,
        state: "GameState",
        world: "WorldData",
    ) -> "ActionIntent | None":
        """Parse player input into a structured ActionIntent.

        Args:
            raw_input: The raw player input string
            state: Current game state for context
            world: World data for entity resolution

        Returns:
            ActionIntent if parsing succeeds, None if input needs AI
        """
        ...


@runtime_checkable
class FlavorParser(Protocol):
    """Protocol for detecting flavor/atmospheric actions.

    Flavor actions don't change game state but add atmosphere
    (e.g., "dance", "jump", "wave at the painting").
    """

    def parse(
        self,
        raw_input: str,
        state: "GameState",
        world: "WorldData",
    ) -> "FlavorIntent | None":
        """Parse player input as a flavor action.

        Args:
            raw_input: The raw player input string
            state: Current game state for context
            world: World data for entity resolution

        Returns:
            FlavorIntent if this is a flavor action, None otherwise
        """
        ...


@runtime_checkable
class IntentValidator(Protocol):
    """Protocol for validating intents against world rules.

    Validators check if an action is allowed given the current
    game state and world rules. They do not modify state.

    Example validators:
        - MoveValidator: Checks if exit exists and is accessible
        - TakeValidator: Checks if item is visible and portable
        - UseValidator: Checks if item combination is valid
    """

    def validate(
        self,
        intent: "ActionIntent",
        state: "GameState",
        world: "WorldData",
    ) -> "ValidationResult":
        """Validate an action intent against game rules.

        Args:
            intent: The parsed action intent to validate
            state: Current game state
            world: World data with rules and entity definitions

        Returns:
            ValidationResult indicating success or failure with reason
        """
        ...


@runtime_checkable
class EventExecutor(Protocol):
    """Protocol for executing validated intents and producing events.

    Executors take a validated intent and produce a list of events
    that represent what happened. They may also apply state changes.

    Events are the source of truth for what happened and are passed
    to the narrator for prose generation.
    """

    def execute(
        self,
        intent: "ActionIntent",
        state: "GameState",
        world: "WorldData",
    ) -> list["Event"]:
        """Execute a validated intent and produce events.

        Args:
            intent: The validated action intent
            state: Current game state (may be modified)
            world: World data for entity lookups

        Returns:
            List of events representing what happened
        """
        ...


@runtime_checkable
class NarratorProtocol(Protocol):
    """Protocol for generating narrative from events.

    The narrator takes confirmed events and a perception snapshot
    (what the player can see) and generates rich prose.

    Narrators should:
        - Match the world's tone and style
        - Never mention hidden items
        - Make rejections feel natural, not like errors
        - Emphasize discovery moments (is_new=True items)
    """

    async def narrate(
        self,
        events: list["Event"],
        snapshot: "PerceptionSnapshot",
    ) -> str:
        """Generate narrative prose from events.

        Args:
            events: List of events to narrate
            snapshot: What the player can currently perceive

        Returns:
            Rich narrative text for display to the player
        """
        ...


@runtime_checkable
class VisibilityResolver(Protocol):
    """Protocol for computing what the player can see.

    Visibility is derived from game state, not stored. This protocol
    defines how to compute visibility for items, NPCs, and exits.

    Key rules:
        - Items in closed containers are NOT visible
        - Hidden items require their reveal condition to be met
        - Inventory items are always "visible" (accessible)
    """

    def is_item_visible(
        self,
        item_id: str,
        state: "GameState",
        world: "WorldData",
    ) -> bool:
        """Check if an item is visible to the player.

        Args:
            item_id: The item to check
            state: Current game state
            world: World data for item definitions

        Returns:
            True if the item is visible, False otherwise
        """
        ...

    def get_visible_items(
        self,
        location_id: str,
        state: "GameState",
        world: "WorldData",
    ) -> list[str]:
        """Get all visible item IDs at a location.

        Args:
            location_id: The location to check
            state: Current game state
            world: World data for item definitions

        Returns:
            List of visible item IDs
        """
        ...

    def build_snapshot(
        self,
        state: "GameState",
        world: "WorldData",
    ) -> "PerceptionSnapshot":
        """Build a complete perception snapshot for the narrator.

        The snapshot includes all visible entities at the current
        location, the player's inventory, and relevant context.

        Args:
            state: Current game state
            world: World data for entity definitions

        Returns:
            PerceptionSnapshot with all visible entities
        """
        ...


@runtime_checkable
class TwoPhaseProcessor(Protocol):
    """Protocol for the complete two-phase action processor.

    This is the main entry point for processing player actions.
    It coordinates the parsing, validation, execution, and narration phases.
    """

    async def process(
        self,
        raw_input: str,
        state: "GameState",
        world: "WorldData",
    ) -> tuple[str, list["Event"]]:
        """Process a player action through the two-phase pipeline.

        Args:
            raw_input: The raw player input
            state: Current game state (may be modified)
            world: World data

        Returns:
            Tuple of (narrative text, list of events that occurred)
        """
        ...
