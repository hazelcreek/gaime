"""
World schema models - Pydantic models for YAML world definitions
"""

from pydantic import BaseModel, Field


class PlayerSetup(BaseModel):
    """Initial player configuration"""

    starting_location: str
    starting_inventory: list[str] = Field(default_factory=list)


class VictoryCondition(BaseModel):
    """Win condition for the game"""

    location: str | None = None  # Must be at this location to win
    flag: str | None = None  # Must have this flag set to win
    item: str | None = None  # Must have this item in inventory to win
    narrative: str = ""  # Ending narrative when player wins


class World(BaseModel):
    """Main world definition from world.yaml"""

    name: str
    theme: str
    tone: str = "atmospheric"
    premise: str
    hero_name: str = "the hero"  # Protagonist name that NPCs will use in dialogue
    player: PlayerSetup
    constraints: list[str] = Field(default_factory=list)
    commands: dict[str, str] = Field(default_factory=dict)
    starting_situation: str = (
        ""  # Initial narrative context explaining why player can act
    )
    victory: VictoryCondition | None = None  # Win condition for the game
    style: str | None = None  # Visual style preset for image generation
    visual_setting: str = (
        ""  # World-level visual language for image generation (5-10 sentences)
    )


class InteractionEffect(BaseModel):
    """Effect of an interaction (V3).

    V3 removes reveals_exit - use hidden exits with find_condition instead.

    Attributes:
        triggers: Phrases that trigger this interaction
        narrative_hint: Hint for narrator about what happens
        sets_flag: Flag to set when triggered
        gives_item: Item given to player
        removes_item: Item removed from player
    """

    triggers: list[str] = Field(default_factory=list)
    narrative_hint: str = ""
    sets_flag: str | None = None
    # V3: Removed reveals_exit - use hidden exits with find_condition instead
    gives_item: str | None = None
    removes_item: str | None = None


# =============================================================================
# V3 Schema Models - Unified visibility with location-bound placement
# These models are used by Location for the V3 world schema.
# =============================================================================


class ItemPlacement(BaseModel):
    """Item placement with visibility control (V3).

    Visibility is a property of WHERE an item is placed, not WHAT the item is.
    The same key could be visible on a table in one room but hidden in a
    drawer in another.

    Attributes:
        placement: How item appears in scene (e.g., "lies on the dusty table")
        hidden: Not visible until revealed by find_condition
        find_condition: Condition to reveal (e.g., {requires_flag: "searched_drawer"})
    """

    placement: str  # How item appears in scene
    hidden: bool = False  # Not visible until revealed
    find_condition: dict | None = None  # e.g., {requires_flag: "searched_drawer"}


class NPCPlacement(BaseModel):
    """NPC placement with visibility control (V3).

    Visibility is a property of WHERE an NPC is placed, not WHO the NPC is.
    An NPC can be present but hidden (e.g., spy behind curtain).

    Attributes:
        placement: Where NPC is positioned (e.g., "lurking behind the curtain")
        hidden: Not visible until revealed by find_condition
        find_condition: Condition to reveal (e.g., {requires_flag: "searched_curtain"})
    """

    placement: str  # Where NPC is positioned
    hidden: bool = False  # Not visible until revealed
    find_condition: dict | None = None  # e.g., {requires_flag: "pulled_curtain"}


class ExaminationEffect(BaseModel):
    """Effects triggered when examining a detail, item, or exit.

    Note: To reveal hidden items, use sets_flag here and hidden+find_condition
    on the ItemPlacement. This avoids the confusing 'reveals_item' pattern.

    Attributes:
        sets_flag: Flag to set when examined
        reveals_exit_destination: Exit direction whose destination becomes known
        narrative_hint: Hint for narrator about what the examination reveals
    """

    sets_flag: str | None = None
    reveals_exit_destination: str | None = None  # Exit direction to reveal destination
    narrative_hint: str | None = None


class ExitDefinition(BaseModel):
    """Structured exit with visual descriptions and destination visibility (V3).

    Supports both destination visibility (whether player knows WHERE it leads)
    and exit visibility (whether the exit itself is shown at all).

    Attributes:
        destination: Location ID this exit leads to
        scene_description: How exit appears in scene
        examine_description: Detailed view on examination
        destination_known: Whether player initially knows the destination
        reveal_destination_on_flag: Reveal destination when this flag is set
        reveal_destination_on_examine: Reveal destination when player examines the exit
        hidden: Exit not visible until revealed (V3)
        find_condition: Condition to reveal exit (V3)
        locked: Whether exit requires a key
        requires_key: Item ID needed to unlock
        blocked: Whether exit is blocked
        blocked_reason: Why the exit is blocked
    """

    destination: str

    # Visual descriptions (for narration and image generation)
    scene_description: str = ""
    examine_description: str | None = None

    # Destination visibility (whether player knows WHERE it leads)
    destination_known: bool = True
    reveal_destination_on_flag: str | None = None
    reveal_destination_on_examine: bool = False
    # Note: Visiting the destination ALWAYS reveals it (automatic, not configurable)

    # Exit visibility (whether exit is shown at all) - V3
    hidden: bool = False  # Exit not visible until revealed
    find_condition: dict | None = None  # e.g., {requires_flag: "found_secret_lever"}

    # Accessibility
    locked: bool = False
    requires_key: str | None = None
    blocked: bool = False
    blocked_reason: str | None = None


class DetailDefinition(BaseModel):
    """Structured detail with examination support (V3).

    Details are scenery elements that can be examined but not taken.
    Supports visibility control for hidden details (e.g., secret clues).

    Attributes:
        name: Display name for the detail
        scene_description: How detail appears in scene
        examine_description: Detailed view on examination
        on_examine: Effects triggered by examination
        hidden: Detail not visible until revealed (V3)
        find_condition: Condition to reveal detail (V3)
    """

    name: str
    scene_description: str
    examine_description: str | None = None
    on_examine: ExaminationEffect | None = None

    # Detail visibility - V3
    hidden: bool = False  # Detail not visible until revealed
    find_condition: dict | None = None  # e.g., {requires_flag: "used_magnifying_glass"}


class LocationRequirement(BaseModel):
    """Requirements to access a location"""

    flag: str | None = None
    item: str | None = None


class Location(BaseModel):
    """Location/room definition from locations.yaml (V3 schema).

    V3 uses item_placements/npc_placements as the source of truth for which
    entities are present. The keys of these dicts define which items/NPCs
    are at this location, replacing the old items/npcs lists.

    Attributes:
        name: Display name for the location
        atmosphere: Atmosphere hints for AI narrative generation
        visual_description: Pure visual scene description for image generation (3-5 sentences)
        exits: Direction -> ExitDefinition mapping
        details: Examinable scenery elements
        interactions: Special interactions at this location
        requires: Access requirements (flag or item needed)
        item_placements: Items at this location with visibility control
        npc_placements: NPCs at this location with visibility control
    """

    name: str
    atmosphere: str = ""
    visual_description: str = (
        ""  # Pure visual scene for image generation (3-5 sentences)
    )
    exits: dict[str, ExitDefinition] = Field(default_factory=dict)
    details: dict[str, DetailDefinition] = Field(default_factory=dict)
    interactions: dict[str, InteractionEffect] = Field(default_factory=dict)
    requires: LocationRequirement | None = None

    # V3: Item and NPC placements with visibility control
    # The KEYS define which items/NPCs are present at this location
    item_placements: dict[str, ItemPlacement] = Field(default_factory=dict)
    npc_placements: dict[str, NPCPlacement] = Field(default_factory=dict)


class NPCPersonality(BaseModel):
    """NPC personality traits"""

    traits: list[str] = Field(default_factory=list)
    speech_style: str = ""
    quirks: list[str] = Field(default_factory=list)


class NPCTrust(BaseModel):
    """NPC trust/relationship mechanics"""

    initial: int = 0
    threshold: int = 3
    build_actions: list[str] = Field(default_factory=list)


class AppearanceCondition(BaseModel):
    """Condition for NPC appearance"""

    condition: str
    value: int | str | bool


class NPCLocationChange(BaseModel):
    """Trigger-based NPC location change"""

    when_flag: str  # Flag that triggers this move
    move_to: str | None = (
        None  # New location ID, or None to remove NPC from game entirely
    )


class NPC(BaseModel):
    """NPC definition from npcs.yaml"""

    name: str
    role: str = ""
    location: str | None = None
    locations: list[str] = Field(default_factory=list)
    appearance: str = ""
    personality: NPCPersonality = Field(default_factory=NPCPersonality)
    knowledge: list[str] = Field(default_factory=list)
    dialogue_rules: list[str] = Field(default_factory=list)
    trust: NPCTrust | None = None
    appears_when: list[AppearanceCondition] = Field(default_factory=list)
    behavior: str = ""
    location_changes: list[NPCLocationChange] = Field(
        default_factory=list
    )  # Trigger-based location changes


class ItemProperty(BaseModel):
    """Special item properties"""

    artifact: bool = False
    effect: dict | None = None


class ItemUseAction(BaseModel):
    """Item use action definition"""

    description: str = ""
    requires_item: str | None = None
    sets_flag: str | None = None


class ItemClue(BaseModel):
    """Item clue information"""

    hint_for: str | None = None
    reveals: str | None = None


class Item(BaseModel):
    """Item definition from items.yaml (V3 schema).

    V3 separates WHAT an item IS (defined here) from WHERE it is placed
    and HOW VISIBLE it is (defined in Location.item_placements).

    Attributes:
        name: Display name for the item
        portable: Whether item can be taken
        scene_description: How item appears in scene
        examine_description: Detailed examination text
        on_examine: Effects triggered by examination (Phase 4)
        take_description: Narration when item is taken
        unlocks: Location or container this item unlocks
        properties: Special item properties
        use_actions: Actions that can be performed with this item
        clues: Hints this item provides
    """

    name: str
    portable: bool = True

    # Visual descriptions
    scene_description: str = ""  # How item appears in scene
    examine_description: str = ""  # Detailed examination text

    # Examination effects (Phase 4)
    on_examine: ExaminationEffect | None = None

    take_description: str = ""
    unlocks: str | None = None

    # V3: Removed location, hidden, find_condition - now in ItemPlacement

    properties: ItemProperty = Field(default_factory=ItemProperty)
    use_actions: dict[str, ItemUseAction] = Field(default_factory=dict)
    clues: list[ItemClue] = Field(default_factory=list)


class WorldData(BaseModel):
    """Complete loaded world data"""

    world: World
    locations: dict[str, Location]
    npcs: dict[str, NPC]
    items: dict[str, Item]

    def get_location(self, location_id: str) -> Location | None:
        """Get a location by ID"""
        return self.locations.get(location_id)

    def get_npc(self, npc_id: str) -> NPC | None:
        """Get an NPC by ID"""
        return self.npcs.get(npc_id)

    def get_item(self, item_id: str) -> Item | None:
        """Get an item by ID"""
        return self.items.get(item_id)

    def get_npcs_at_location(self, location_id: str) -> list[NPC]:
        """Get all NPCs at a location"""
        result = []
        for npc_id, npc in self.npcs.items():
            if npc.location == location_id or location_id in npc.locations:
                result.append(npc)
        return result

    def get_items_at_location(self, location_id: str) -> list[Item]:
        """Get all items defined at a location (V3).

        Returns items whose IDs are keys in location.item_placements.
        Does NOT filter by visibility - use VisibilityResolver for that.

        Args:
            location_id: The location ID to check

        Returns:
            List of Item objects at this location
        """
        location = self.get_location(location_id)
        if not location:
            return []

        result = []
        for item_id in location.item_placements.keys():
            item = self.get_item(item_id)
            if item:
                result.append(item)
        return result
