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
    flag: str | None = None      # Must have this flag set to win
    item: str | None = None      # Must have this item in inventory to win
    narrative: str = ""          # Ending narrative when player wins


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
    starting_situation: str = ""  # Initial narrative context explaining why player can act
    victory: VictoryCondition | None = None  # Win condition for the game


class InteractionEffect(BaseModel):
    """Effect of an interaction"""
    triggers: list[str] = Field(default_factory=list)
    narrative_hint: str = ""
    sets_flag: str | None = None
    reveals_exit: str | None = None
    gives_item: str | None = None
    removes_item: str | None = None


class LocationRequirement(BaseModel):
    """Requirements to access a location"""
    flag: str | None = None
    item: str | None = None


class Location(BaseModel):
    """Location/room definition from locations.yaml"""
    name: str
    atmosphere: str = ""
    exits: dict[str, str] = Field(default_factory=dict)
    items: list[str] = Field(default_factory=list)
    npcs: list[str] = Field(default_factory=list)
    details: dict[str, str] = Field(default_factory=dict)
    interactions: dict[str, InteractionEffect] = Field(default_factory=dict)
    requires: LocationRequirement | None = None
    item_placements: dict[str, str] = Field(default_factory=dict)  # Maps item_id to placement description
    npc_placements: dict[str, str] = Field(default_factory=dict)   # Maps npc_id to position description


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
    move_to: str | None = None  # New location ID, or None to remove NPC from game entirely


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
    location_changes: list[NPCLocationChange] = Field(default_factory=list)  # Trigger-based location changes


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
    """Item definition from items.yaml"""
    name: str
    portable: bool = True
    examine: str = ""
    found_description: str = ""
    take_description: str = ""
    unlocks: str | None = None
    location: str | None = None
    hidden: bool = False
    find_condition: dict | None = None
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
        """Get all visible items at a location"""
        location = self.get_location(location_id)
        if not location:
            return []
        
        result = []
        for item_id in location.items:
            item = self.get_item(item_id)
            if item and not item.hidden:
                result.append(item)
        return result

