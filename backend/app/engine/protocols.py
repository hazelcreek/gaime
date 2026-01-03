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
                             IntentHandler.validate() -> ValidationResult
                                          |
                                          v (if valid)
                             IntentHandler.execute() -> State Changes
                                          |
                                          v
                             IntentHandler.create_event() -> Event
                                          |
                                          v
                                   NarratorAI -> Narrative Text
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.engine.two_phase.models.intent import ActionIntent, Intent
    from app.engine.two_phase.models.event import Event
    from app.engine.two_phase.models.perception import PerceptionSnapshot
    from app.engine.two_phase.models.validation import ValidationResult
    from app.engine.two_phase.models.state import (
        TwoPhaseGameState,
        TwoPhaseActionResponse,
    )
    from app.engine.two_phase.state import TwoPhaseStateManager
    from app.models.world import WorldData


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
        state: "TwoPhaseGameState",
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
class IntentValidator(Protocol):
    """Protocol for validating intents against world rules.

    Validators check if an action is allowed given the current
    game state and world rules. They do not modify state.

    Example validators:
        - MovementValidator: Checks if exit exists and is accessible
        - TakeValidator: Checks if item is visible and portable
        - ExamineValidator: Checks if target is visible
    """

    def validate(
        self,
        intent: "ActionIntent",
        state: "TwoPhaseGameState",
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
class IntentHandler(Protocol):
    """Protocol for handling any intent type (ActionIntent or FlavorIntent).

    IntentHandler is the core abstraction for the two-phase engine's
    action processing. Each handler encapsulates the complete logic
    for one type of action:

    1. validate() - Check if the action is allowed
    2. execute() - Apply state changes (called only if validation passes)
    3. create_event() - Create the event for narration

    Attributes:
        checks_victory: Whether to check victory conditions after this action

    Example implementations:
        - MovementHandler: Handles MOVE actions, checks_victory=True
        - ExamineHandler: Handles EXAMINE actions, checks_victory=False
        - FlavorHandler: Handles FlavorIntent, always valid, no state changes
    """

    checks_victory: bool

    def validate(
        self,
        intent: "Intent",
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> "ValidationResult":
        """Validate the intent against game rules.

        For FlavorHandler, this always returns a valid result.
        For ActionHandlers, this delegates to the appropriate validator.

        Args:
            intent: The parsed intent (ActionIntent or FlavorIntent)
            state: Current game state
            world: World data with rules and entity definitions

        Returns:
            ValidationResult indicating success or failure with reason
        """
        ...

    def execute(
        self,
        intent: "Intent",
        result: "ValidationResult",
        state_manager: "TwoPhaseStateManager",
    ) -> None:
        """Execute state changes (called only if validation passes).

        For FlavorHandler, this is a no-op.
        For ActionHandlers, this applies the appropriate state mutations.

        Args:
            intent: The validated intent
            result: The validation result (contains context like destination)
            state_manager: The state manager to mutate
        """
        ...

    def create_event(
        self,
        intent: "Intent",
        result: "ValidationResult",
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> "Event":
        """Create the event for narration.

        Args:
            intent: The processed intent
            result: The validation result
            state: Current game state (may reflect executed changes)
            world: World data for entity lookups

        Returns:
            Event for the narrator to describe
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
        state: "TwoPhaseGameState",
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
        state: "TwoPhaseGameState",
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
        state: "TwoPhaseGameState",
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
        action: str,
    ) -> "TwoPhaseActionResponse":
        """Process a player action through the two-phase pipeline.

        Args:
            action: The raw player input

        Returns:
            TwoPhaseActionResponse with narrative and updated state
        """
        ...

    async def get_initial_narrative(
        self,
    ) -> tuple[str, object | None]:
        """Generate the opening narrative for a new game.

        Returns:
            Tuple of (narrative text, debug info if enabled)
        """
        ...
