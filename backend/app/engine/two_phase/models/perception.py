"""
Perception models for the two-phase game engine.

The PerceptionSnapshot defines exactly what information the Narrator
is allowed to see. This prevents spoilers and ensures hidden items
are never mentioned in narration.

Key principle: HIDDEN ITEMS MUST NEVER APPEAR IN A SNAPSHOT.

See planning/two-phase-game-loop-spec.md Section: Visibility & Discovery Model

Example:
    >>> # After opening a drawer
    >>> snapshot = PerceptionSnapshot(
    ...     location_id="study",
    ...     location_name="The Study",
    ...     visible_items=[
    ...         VisibleEntity(id="brass_key", name="Small Brass Key", is_new=True),
    ...     ],
    ... )
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class VisibleEntity(BaseModel):
    """An entity visible to the player.

    Represents any entity that the player can currently perceive,
    whether it's an item, detail, NPC, or exit.

    Attributes:
        id: Entity ID from the world model
        name: Display name
        description: Optional description for context
        is_new: True if just revealed this turn (emphasize in narration)

    Example:
        >>> entity = VisibleEntity(
        ...     id="brass_key",
        ...     name="Small Brass Key",
        ...     description="A tarnished key lies in the drawer.",
        ...     is_new=True,  # Just discovered!
        ... )
    """

    id: str
    name: str
    description: str | None = None
    is_new: bool = False  # Just revealed this turn


class VisibleExit(BaseModel):
    """An exit visible to the player.

    Exits have additional properties compared to other entities,
    including direction and destination.

    Attributes:
        direction: The direction (north, south, etc.)
        destination_name: Name of the destination location
        description: Optional description of the exit
        is_locked: Whether the exit is currently locked
        is_blocked: Whether the exit is blocked (rubble, etc.)

    Example:
        >>> exit = VisibleExit(
        ...     direction="north",
        ...     destination_name="The Library",
        ...     description="An archway leads north into shadows.",
        ... )
    """

    direction: str
    destination_name: str
    description: str | None = None
    is_locked: bool = False
    is_blocked: bool = False


class PerceptionSnapshot(BaseModel):
    """What the Narrator is allowed to know about the current state.

    CRITICAL: Hidden items must NEVER appear in this snapshot.

    The PerceptionSnapshot is built by the VisibilityResolver after
    events are processed. It contains only what the player can
    currently perceive, filtered by visibility rules.

    Attributes:
        location_id: Current location ID
        location_name: Display name of location
        location_atmosphere: Atmosphere description for the Narrator
        visible_items: Items the player can see (filtered by visibility)
        visible_details: Examinable scenery elements
        visible_exits: Exits with their descriptions
        visible_npcs: NPCs present at the location
        inventory: Player's inventory items
        affordances: Contextual hints (e.g., openable containers)
        known_facts: Facts the player has learned (from flags/discoveries)

    Example:
        >>> # BEFORE opening drawer
        >>> snapshot_before = PerceptionSnapshot(
        ...     location_id="study",
        ...     location_name="The Study",
        ...     visible_items=[],  # Key is NOT visible (in closed container)
        ...     visible_details=[
        ...         VisibleEntity(id="desk", name="Writing Desk"),
        ...     ],
        ...     affordances={"openable_containers": ["desk"]},
        ... )

        >>> # AFTER opening drawer
        >>> snapshot_after = PerceptionSnapshot(
        ...     location_id="study",
        ...     location_name="The Study",
        ...     visible_items=[
        ...         VisibleEntity(id="brass_key", name="Brass Key", is_new=True),
        ...     ],
        ... )
    """

    # Current location
    location_id: str
    location_name: str
    location_atmosphere: str | None = None

    # Visible entities (filtered by visibility rules)
    visible_items: list[VisibleEntity] = Field(default_factory=list)
    visible_details: list[VisibleEntity] = Field(default_factory=list)
    visible_exits: list[VisibleExit] = Field(default_factory=list)
    visible_npcs: list[VisibleEntity] = Field(default_factory=list)

    # Player state
    inventory: list[VisibleEntity] = Field(default_factory=list)

    # Contextual hints (spoiler-safe)
    affordances: dict[str, list[str]] = Field(default_factory=dict)
    # Example: {"openable_containers": ["desk_drawer"], "usable_tools": ["matches"]}

    # Known facts from flags/discoveries (not spoilers)
    known_facts: list[str] = Field(default_factory=list)

    # Is this the first visit to this location?
    first_visit: bool = False


class ItemVisibility(str):
    """How an item starts in terms of visibility.

    Used in world definitions to specify initial visibility state:
        - VISIBLE: Always visible (default)
        - CONCEALED: Inside a closed container
        - HIDDEN: Secret, requires discovery flag
    """

    VISIBLE = "visible"  # Always visible (default)
    CONCEALED = "concealed"  # In a closed container
    HIDDEN = "hidden"  # Secret, needs discovery
