"""
Event models for the two-phase game engine.

Events represent what happened as a result of a validated action.
They are the source of truth for state changes and are passed to
the narrator for prose generation.

Key concepts:
    - Event: Base representation of something that happened
    - RejectionEvent: Special event for failed/blocked actions
    - EventType: Enumeration of event categories

See planning/two-phase-game-loop-spec.md Section: Event System

Example:
    >>> event = Event(
    ...     type=EventType.ITEM_TAKEN,
    ...     subject="brass_key",
    ...     context={"from_container": "desk_drawer"},
    ... )
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events that can occur in the game.

    Categories:
        Movement: LOCATION_CHANGED, SCENE_BROWSED
        Items: ITEM_EXAMINED, ITEM_TAKEN, ITEM_DROPPED, ITEM_USED, ITEM_REVEALED, ITEM_CONSUMED
        Containers: CONTAINER_OPENED, CONTAINER_CLOSED
        Discovery: DETAIL_EXAMINED, SECRET_DISCOVERED, EXIT_REVEALED
        NPCs: NPC_GREETED, NPC_CONVERSATION, NPC_ITEM_GIVEN, NPC_ITEM_RECEIVED
        Game State: FLAG_SET, INTERACTION_TRIGGERED, VICTORY_ACHIEVED
        Meta: ACTION_REJECTED, NOTHING_HAPPENED, FLAVOR_ACTION
    """

    # Movement
    LOCATION_CHANGED = "location_changed"
    SCENE_BROWSED = "scene_browsed"  # Player surveyed the location

    # Items
    ITEM_EXAMINED = "item_examined"
    ITEM_TAKEN = "item_taken"
    ITEM_DROPPED = "item_dropped"
    ITEM_USED = "item_used"
    ITEM_REVEALED = "item_revealed"
    ITEM_CONSUMED = "item_consumed"

    # Containers
    CONTAINER_OPENED = "container_opened"
    CONTAINER_CLOSED = "container_closed"

    # Discovery
    DETAIL_EXAMINED = "detail_examined"
    EXIT_EXAMINED = "exit_examined"  # Player examined an exit
    SECRET_DISCOVERED = "secret_discovered"
    EXIT_REVEALED = "exit_revealed"

    # NPCs
    NPC_GREETED = "npc_greeted"
    NPC_CONVERSATION = "npc_conversation"
    NPC_ITEM_GIVEN = "npc_item_given"
    NPC_ITEM_RECEIVED = "npc_item_received"

    # Game State
    FLAG_SET = "flag_set"
    INTERACTION_TRIGGERED = "interaction_triggered"
    VICTORY_ACHIEVED = "victory_achieved"

    # Meta
    ACTION_REJECTED = "action_rejected"
    NOTHING_HAPPENED = "nothing_happened"
    FLAVOR_ACTION = "flavor_action"


class Event(BaseModel):
    """Represents something that happened in the game world.

    Events are created by the EventExecutor after validation succeeds.
    They capture both what happened and any context needed for narration.

    Attributes:
        type: The type of event that occurred
        subject: Primary entity involved (item_id, npc_id, location_id)
        target: Secondary entity (if applicable)
        state_changes: Dict of state changes to apply
        context: Additional context for narration
        primary: Whether this is the main event or a side effect

    Example:
        >>> # Player opened a drawer and found a key
        >>> events = [
        ...     Event(
        ...         type=EventType.CONTAINER_OPENED,
        ...         subject="desk_drawer",
        ...         primary=True,
        ...     ),
        ...     Event(
        ...         type=EventType.ITEM_REVEALED,
        ...         subject="brass_key",
        ...         context={"is_new": True, "container": "desk_drawer"},
        ...         primary=False,
        ...     ),
        ... ]
    """

    type: EventType

    # What was involved
    subject: str | None = None  # Primary entity (item_id, npc_id, location_id)
    target: str | None = None  # Secondary entity

    # State changes to apply
    state_changes: dict[str, object] = Field(default_factory=dict)

    # Context for narration
    context: dict[str, object] = Field(default_factory=dict)

    # Was this the primary outcome or a side effect?
    primary: bool = True


class RejectionCode(str, Enum):
    """Rejection codes for validation failures.

    These codes help identify why an action failed and enable
    appropriate narrator responses and potential hints.
    """

    # Movement
    NO_EXIT = "no_exit"  # Direction not available
    EXIT_NOT_VISIBLE = "exit_not_visible"  # Exit exists but undiscovered
    EXIT_LOCKED = "exit_locked"  # Exit is locked
    EXIT_BLOCKED = "exit_blocked"  # Exit blocked (rubble, fire, etc.)

    # Requirements
    PRECONDITION_FAILED = "precondition_failed"  # Missing flag/item/light/etc.

    # Items
    ITEM_NOT_VISIBLE = "item_not_visible"  # Can't interact with hidden item
    ITEM_NOT_HERE = "item_not_here"  # Item at different location
    ITEM_NOT_PORTABLE = "item_not_portable"  # Fixed in place
    ITEM_TOO_HEAVY = "item_too_heavy"  # Portable but too heavy
    ALREADY_HAVE = "already_have"  # Item already in inventory

    # Containers
    CONTAINER_LOCKED = "container_locked"  # Container is locked
    CONTAINER_ALREADY_OPEN = "container_already_open"  # Already open
    CONTAINER_ALREADY_CLOSED = "container_already_closed"  # Already closed

    # NPCs
    NPC_NOT_PRESENT = "npc_not_present"  # NPC not at this location
    NPC_HOSTILE = "npc_hostile"  # NPC won't interact
    NPC_BUSY = "npc_busy"  # NPC is occupied

    # Combinations
    TOOL_INSUFFICIENT = "tool_insufficient"  # Tool not suitable

    # Parsing
    AMBIGUOUS_TARGET = "ambiguous_target"  # Multiple matches for target
    TARGET_NOT_FOUND = "target_not_found"  # Target doesn't exist

    # Logic
    ALREADY_DONE = "already_done"  # One-time interaction already used

    # Safety
    SAFETY_GUARDRAIL = "safety_guardrail"  # Would create unwinnable state


class RejectionEvent(Event):
    """Event for rejected/failed actions with in-world explanation.

    RejectionEvents are created when validation fails. They include
    information to help the narrator generate a natural, in-world
    explanation for why the action didn't succeed.

    Attributes:
        rejection_code: Machine-readable rejection category
        rejection_reason: Human-readable reason (seed for Narrator)
        would_have: What would have happened if successful (for hints)

    Example:
        >>> rejection = RejectionEvent(
        ...     rejection_code=RejectionCode.EXIT_LOCKED,
        ...     rejection_reason="The heavy iron door to the basement is locked.",
        ...     subject="basement_door",
        ...     context={"requires_key": "iron_key"},
        ...     would_have="Access the basement",
        ... )

    The narrator should turn this into natural prose, not an error message:
        BAD: "Error: Cannot move north. Door is locked."
        GOOD: "You try the handle, but the heavy oak door is locked tight."
    """

    type: EventType = EventType.ACTION_REJECTED

    # Machine-readable rejection code
    rejection_code: RejectionCode

    # Human-readable reason (seed for Narrator)
    rejection_reason: str

    # What would have happened if successful (for hints)
    would_have: str | None = None
