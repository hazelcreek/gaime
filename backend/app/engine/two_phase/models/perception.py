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
        destination_known: Whether player knows where this exit leads
        description: Optional description of the exit (scene_description)
        is_locked: Whether the exit is currently locked
        is_blocked: Whether the exit is blocked (rubble, etc.)

    Example:
        >>> exit = VisibleExit(
        ...     direction="north",
        ...     destination_name="The Library",
        ...     destination_known=True,
        ...     description="An archway leads north into shadows.",
        ... )
    """

    direction: str
    destination_name: str
    destination_known: bool = True
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


# =============================================================================
# Debug Snapshot Models
# =============================================================================
#
# These models provide a complete view of location state for debugging.
# Unlike PerceptionSnapshot (which filters to what player can see), these
# show EVERYTHING with visibility status flags.
#
# EXTENSIBILITY: When adding fields to world models (models/world.py),
# update the corresponding debug model here and the build_debug_snapshot()
# method in visibility.py. See docs/DEBUG_SNAPSHOT.md for the full pattern.
# =============================================================================


class LocationItemDebug(BaseModel):
    """Item at location with full visibility analysis.

    Shows all items defined at a location with their current visibility
    status and the reason for that status.

    Source fields from models/world.py Item:
        - name, scene_description, examine_description, hidden, find_condition, portable

    Attributes:
        item_id: The item's unique identifier
        name: Display name from world definition
        scene_description: How item appears in scene (from Item.scene_description)
        is_visible: Whether player can currently see this item
        is_in_inventory: Whether player has already taken this item
        visibility_reason: Why the item is visible/hidden
        placement: Where item is placed in location (from Location.item_placements)
        portable: Whether item can be taken
        examine_description: Full examination text

    Example:
        >>> item = LocationItemDebug(
        ...     item_id="brass_key",
        ...     name="Brass Key",
        ...     scene_description="A small brass key glints in the drawer.",
        ...     is_visible=False,
        ...     is_in_inventory=False,
        ...     visibility_reason="hidden:requires_flag:drawer_opened",
        ...     placement="inside the desk drawer",
        ...     portable=True,
        ... )
    """

    item_id: str
    name: str
    scene_description: str = ""
    is_visible: bool
    is_in_inventory: bool
    visibility_reason: str  # "visible", "hidden", "taken", "condition_not_met:flag_x"
    placement: str | None = None  # from Location.item_placements
    portable: bool = True
    examine_description: str = ""


class LocationNPCDebug(BaseModel):
    """NPC at location with full visibility analysis.

    Shows all NPCs that could be at a location with their current
    visibility status and the reason for that status.

    Source fields from models/world.py NPC:
        - name, role, appearance, location, locations, appears_when, location_changes

    Attributes:
        npc_id: The NPC's unique identifier
        name: Display name from world definition
        role: NPC's role/occupation
        appearance: Physical description
        is_visible: Whether NPC is currently visible to player
        visibility_reason: Why the NPC is visible/hidden
        placement: Where NPC is positioned (from Location.npc_placements)
        current_location: NPC's current location (may differ from base due to triggers)

    Example:
        >>> npc = LocationNPCDebug(
        ...     npc_id="ghost_child",
        ...     name="Spectral Child",
        ...     role="haunting spirit",
        ...     appearance="A translucent figure of a young girl",
        ...     is_visible=False,
        ...     visibility_reason="condition_not_met:has_flag:lantern_lit",
        ...     placement="hovering near the window",
        ...     current_location="nursery",
        ... )
    """

    npc_id: str
    name: str
    role: str = ""
    appearance: str = ""
    is_visible: bool
    visibility_reason: (
        str  # "visible", "condition_not_met:flag_x", "removed", "wrong_location"
    )
    placement: str | None = None  # from Location.npc_placements
    current_location: str | None = None  # NPC's actual current location


class LocationExitDebug(BaseModel):
    """Exit with accessibility and visibility analysis.

    Shows all exits from a location with their accessibility status,
    visibility status (V3), and any requirements that must be met.

    Source fields from models/world.py ExitDefinition:
        - destination, scene_description, destination_known, locked, blocked
        - hidden, find_condition (V3)

    Attributes:
        direction: The exit direction (north, south, etc.)
        destination_id: ID of the destination location
        destination_name: Display name of destination
        is_accessible: Whether player can currently use this exit
        access_reason: Why the exit is accessible/blocked
        scene_description: Visual description of the exit
        destination_known: Whether player knows where this exit leads
        is_hidden: Whether this exit is hidden (V3)
        visibility_reason: Why the exit is visible/hidden (V3)

    Example:
        >>> exit = LocationExitDebug(
        ...     direction="north",
        ...     destination_id="secret_chamber",
        ...     destination_name="Secret Chamber",
        ...     is_accessible=False,
        ...     access_reason="requires_flag:bookcase_moved",
        ...     scene_description="A concealed passage behind the bookcase",
        ...     destination_known=False,
        ...     is_hidden=True,
        ...     visibility_reason="condition_not_met:bookcase_moved",
        ... )
    """

    direction: str
    destination_id: str
    destination_name: str
    is_accessible: bool
    access_reason: str  # "accessible", "requires_flag:x", "requires_item:y", "locked:x", "blocked:x"
    scene_description: str | None = None
    destination_known: bool = True
    # V3: Hidden exit support
    is_hidden: bool = False
    visibility_reason: str = (
        "visible"  # "visible", "hidden", "revealed", "condition_not_met:x"
    )


class LocationInteractionDebug(BaseModel):
    """Interaction available at location.

    Source fields from models/world.py InteractionEffect:
        - triggers, narrative_hint, sets_flag, gives_item, removes_item
        - V3: reveals_exit removed (use hidden exits instead)

    Attributes:
        interaction_id: The interaction's unique identifier
        triggers: List of trigger words/phrases
        sets_flag: Flag that gets set when triggered
        gives_item: Item given to player
        removes_item: Item removed from player
    """

    interaction_id: str
    triggers: list[str] = Field(default_factory=list)
    sets_flag: str | None = None
    gives_item: str | None = None
    removes_item: str | None = None


class LocationDebugSnapshot(BaseModel):
    """Full location state for debug view - shows everything with status.

    Unlike PerceptionSnapshot which filters to what the player can see,
    this snapshot shows ALL entities at a location with their visibility
    status flags. Used for the state inspection debug view.

    EXTENSIBILITY: This model mirrors the Location model from models/world.py.
    When new fields are added to Location, they should be added here too.
    See docs/DEBUG_SNAPSHOT.md for the extension pattern.

    Source: models/world.py Location
        - name, atmosphere, exits, items, npcs, details, interactions,
          requires, item_placements, npc_placements

    Attributes:
        location_id: Current location ID
        name: Display name of location
        atmosphere: Atmosphere description for the location
        exits: All exits with accessibility status
        items: All items with visibility status
        npcs: All NPCs with visibility status
        details: Examinable scenery elements (key -> description)
        interactions: Available interactions at this location
        requires: Access requirements for this location (if any)

    Example:
        >>> snapshot = LocationDebugSnapshot(
        ...     location_id="study",
        ...     name="The Study",
        ...     atmosphere="Dust motes dance in shafts of pale light",
        ...     exits=[LocationExitDebug(...)],
        ...     items=[LocationItemDebug(...)],
        ...     npcs=[LocationNPCDebug(...)],
        ...     details={"desk": "A heavy oak writing desk"},
        ...     interactions=[LocationInteractionDebug(...)],
        ... )
    """

    location_id: str
    name: str
    atmosphere: str = ""
    exits: list[LocationExitDebug] = Field(default_factory=list)
    items: list[LocationItemDebug] = Field(default_factory=list)
    npcs: list[LocationNPCDebug] = Field(default_factory=list)
    details: dict[str, str] = Field(default_factory=dict)
    interactions: list[LocationInteractionDebug] = Field(default_factory=list)
    requires: dict[str, str] | None = None  # {"flag": "x"} or {"item": "y"}
