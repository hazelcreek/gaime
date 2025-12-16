"""
Intent models for the two-phase game engine.

This module defines the structured representations of player intent
after parsing but before validation.

Key concepts:
    - ActionIntent: State-changing actions (move, take, use, etc.)
    - FlavorIntent: Atmospheric actions that don't change state (dance, wave)
    - ActionType: Enumeration of supported action categories

Naming Convention:
    - Fields ending in `_id` contain resolved entity IDs from the world model
    - Fields without `_id` may contain raw player descriptions

See planning/two-phase-game-loop-spec.md Section: Core Data Models

Example:
    >>> intent = ActionIntent(
    ...     action_type=ActionType.TAKE,
    ...     raw_input="pick up the key",
    ...     verb="pick up",
    ...     target_id="brass_key",
    ... )
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Primary categories of player actions.

    These represent the mechanical action types that can change game state.

    Categories:
        Movement: MOVE
        Object Interaction: EXAMINE, TAKE, DROP, USE, OPEN, CLOSE
        Communication: TALK, ASK, GIVE, SHOW
        Environment: LISTEN, SEARCH
        Meta: WAIT, INVENTORY, HELP

    Note: "look around" / bare "look" is treated as re-narration of the
    current location, not as a separate ActionType. "look at X" is EXAMINE.
    """

    # Movement
    MOVE = "move"  # Navigate between locations

    # Object Interaction
    EXAMINE = "examine"  # Look at something closely (includes "look at X")
    TAKE = "take"  # Pick up an item
    DROP = "drop"  # Put down an item
    USE = "use"  # Use item (standalone or on target)
    OPEN = "open"  # Open container/door
    CLOSE = "close"  # Close container/door

    # Communication
    TALK = "talk"  # Speak to NPC
    ASK = "ask"  # Ask NPC about topic
    GIVE = "give"  # Give item to NPC
    SHOW = "show"  # Show item to NPC

    # Environment
    LISTEN = "listen"  # Listen for sounds
    SEARCH = "search"  # Search area/container

    # Meta
    WAIT = "wait"  # Pass time
    INVENTORY = "inventory"  # Check inventory
    HELP = "help"  # Show help


class ActionIntent(BaseModel):
    """Structured representation of a state-changing player action.

    ActionIntent represents what the player is trying to do AFTER parsing
    but BEFORE validation. All entity references use resolved IDs from
    the world model.

    Attributes:
        type: Discriminator literal for union typing
        action_type: The category of action being attempted
        raw_input: The original player input string
        verb: The verb used (preserved for rich narration)
        target_id: Primary target (resolved entity ID or direction)
        instrument_id: For USE: the tool being used on the target
        topic_id: For ASK: resolved conversation topic ID
        recipient_id: For GIVE/SHOW: who receives the item
        confidence: Parsing confidence (1.0 for rule-based, 0-1 for AI)
        alternatives: Other possible interpretations (for disambiguation)

    Example:
        >>> # "use key on door"
        >>> intent = ActionIntent(
        ...     action_type=ActionType.USE,
        ...     raw_input="use key on door",
        ...     verb="use",
        ...     target_id="front_door",
        ...     instrument_id="brass_key",
        ... )

        >>> # "go north"
        >>> intent = ActionIntent(
        ...     action_type=ActionType.MOVE,
        ...     raw_input="go north",
        ...     verb="go",
        ...     target_id="north",
        ... )
    """

    type: Literal["action_intent"] = "action_intent"
    action_type: ActionType

    # Original player input
    raw_input: str

    # Original verb used (for rich narration)
    verb: str

    # Primary target (resolved entity ID: item_id, npc_id, detail_id, or direction)
    target_id: str

    # Action-specific secondary fields (all resolved IDs, mutually exclusive):
    instrument_id: str | None = None  # USE: "use INSTRUMENT on target"
    topic_id: str | None = None  # ASK: resolved conversation topic
    recipient_id: str | None = None  # GIVE/SHOW: "give item to RECIPIENT"

    # Confidence score (0.0-1.0) when AI-parsed
    confidence: float = 1.0

    # Alternative interpretations (for disambiguation)
    alternatives: list["ActionIntent"] = Field(default_factory=list)


class FlavorIntent(BaseModel):
    """Atmospheric actions that add flavor but don't change game state.

    FlavorIntent is used for:
        - Physical expressions: "jump around", "dance", "sing", "wave"
        - Improvised dialogue: "ask Jenkins about football" (undefined topic)

    FlavorIntents undergo lightweight validation (target presence check)
    before being sent to the narrator for prose generation.

    Attributes:
        type: Discriminator literal for union typing
        verb: The action verb ("dance", "wave", "ask")
        raw_input: The original player input string
        target: Optional entity reference (may be ID or raw description)
        topic: For ASK: unresolved dialogue topic
        manner: Adverbial modifier ("gracefully", "loudly")

    Example:
        >>> # "dance gracefully"
        >>> flavor = FlavorIntent(
        ...     verb="dance",
        ...     raw_input="dance gracefully",
        ...     manner="gracefully",
        ... )

        >>> # "ask Jenkins about football" (undefined topic)
        >>> flavor = FlavorIntent(
        ...     verb="ask",
        ...     raw_input="ask Jenkins about football",
        ...     target="butler_jenkins",
        ...     topic="football",
        ... )
    """

    type: Literal["flavor_intent"] = "flavor_intent"
    verb: str
    raw_input: str

    # Optional context (may be entity ID or raw description)
    target: str | None = None  # Entity reference or description
    topic: str | None = None  # Unresolved dialogue topic
    manner: str | None = None  # Adverbial modifier ("dance GRACEFULLY")


# Type alias for either intent type
Intent = ActionIntent | FlavorIntent
