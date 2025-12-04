"""
World loader - Load and validate YAML world files
"""

import os
from pathlib import Path

import yaml

from app.models.world import (
    World,
    Location,
    NPC,
    Item,
    WorldData,
    InteractionEffect,
    NPCPersonality,
    NPCTrust,
    ItemProperty,
    ItemUseAction,
    ItemClue,
    LocationRequirement,
    PlayerSetup,
    AppearanceCondition,
    VictoryCondition,
)


class WorldLoader:
    """Loads game worlds from YAML files"""
    
    def __init__(self, worlds_dir: str | None = None):
        """Initialize with worlds directory path"""
        if worlds_dir is None:
            # Default to worlds/ relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            worlds_dir = project_root / "worlds"
        self.worlds_dir = Path(worlds_dir)
    
    def list_worlds(self) -> list[dict]:
        """List available worlds with metadata"""
        worlds = []
        
        if not self.worlds_dir.exists():
            return worlds
        
        for world_path in self.worlds_dir.iterdir():
            if world_path.is_dir():
                world_yaml = world_path / "world.yaml"
                if world_yaml.exists():
                    try:
                        with open(world_yaml) as f:
                            data = yaml.safe_load(f)
                        worlds.append({
                            "id": world_path.name,
                            "name": data.get("name", world_path.name),
                            "theme": data.get("theme", ""),
                            "description": data.get("premise", "")[:200] + "..." if len(data.get("premise", "")) > 200 else data.get("premise", "")
                        })
                    except Exception:
                        pass
        
        return worlds
    
    def load_world(self, world_id: str, validate: bool = True) -> WorldData:
        """
        Load a complete world from YAML files.
        
        Args:
            world_id: The world identifier (folder name in worlds/)
            validate: Whether to validate the world on load (default True)
        
        Returns:
            WorldData with all world content
        
        Raises:
            FileNotFoundError: If world doesn't exist
            ValueError: If validation fails and validate=True
        """
        world_path = self.worlds_dir / world_id
        
        if not world_path.exists():
            raise FileNotFoundError(f"World '{world_id}' not found at {world_path}")
        
        # Load each YAML file
        world = self._load_world_yaml(world_path / "world.yaml")
        locations = self._load_locations_yaml(world_path / "locations.yaml")
        npcs = self._load_npcs_yaml(world_path / "npcs.yaml")
        items = self._load_items_yaml(world_path / "items.yaml")
        
        world_data = WorldData(
            world=world,
            locations=locations,
            npcs=npcs,
            items=items
        )
        
        # Validate world if requested
        if validate:
            from app.engine.validator import WorldValidator
            validator = WorldValidator(world_data, world_id)
            result = validator.validate()
            
            if not result.is_valid:
                error_list = "\n  - ".join(result.errors)
                raise ValueError(
                    f"World '{world_id}' validation failed with {len(result.errors)} error(s):\n  - {error_list}"
                )
        
        return world_data
    
    def _load_world_yaml(self, path: Path) -> World:
        """Load world.yaml"""
        with open(path) as f:
            data = yaml.safe_load(f)
        
        # Parse player setup
        player_data = data.get("player", {})
        player = PlayerSetup(
            starting_location=player_data.get("starting_location", "start"),
            starting_inventory=player_data.get("starting_inventory", []),
            stats=player_data.get("stats", {"health": 100})
        )
        
        # Parse victory condition
        victory = None
        victory_data = data.get("victory")
        if victory_data and isinstance(victory_data, dict):
            victory = VictoryCondition(
                location=victory_data.get("location"),
                flag=victory_data.get("flag"),
                item=victory_data.get("item"),
                narrative=victory_data.get("narrative", "")
            )
        
        return World(
            name=data.get("name", "Unnamed World"),
            theme=data.get("theme", ""),
            tone=data.get("tone", "atmospheric"),
            premise=data.get("premise", ""),
            player=player,
            constraints=data.get("constraints", []),
            commands=data.get("commands", {}),
            starting_situation=data.get("starting_situation", ""),
            victory=victory
        )
    
    def _load_locations_yaml(self, path: Path) -> dict[str, Location]:
        """Load locations.yaml"""
        if not path.exists():
            return {}
        
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        locations = {}
        for loc_id, loc_data in data.items():
            # Parse interactions
            interactions = {}
            for int_id, int_data in loc_data.get("interactions", {}).items():
                if isinstance(int_data, dict):
                    interactions[int_id] = InteractionEffect(
                        triggers=int_data.get("triggers", []),
                        narrative_hint=int_data.get("narrative_hint", ""),
                        sets_flag=int_data.get("sets_flag"),
                        reveals_exit=int_data.get("reveals_exit"),
                        gives_item=int_data.get("gives_item"),
                        removes_item=int_data.get("removes_item")
                    )
            
            # Parse requirements
            requires = None
            req_data = loc_data.get("requires")
            if req_data and isinstance(req_data, dict):
                requires = LocationRequirement(
                    flag=req_data.get("flag"),
                    item=req_data.get("item")
                )
            
            locations[loc_id] = Location(
                name=loc_data.get("name", loc_id),
                atmosphere=loc_data.get("atmosphere", ""),
                exits=loc_data.get("exits", {}),
                items=loc_data.get("items", []),
                npcs=loc_data.get("npcs", []),
                details=loc_data.get("details", {}),
                interactions=interactions,
                requires=requires
            )
        
        return locations
    
    def _load_npcs_yaml(self, path: Path) -> dict[str, NPC]:
        """Load npcs.yaml"""
        if not path.exists():
            return {}
        
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        npcs = {}
        for npc_id, npc_data in data.items():
            # Parse personality - handle both string and dict formats
            pers_data = npc_data.get("personality", {})
            if isinstance(pers_data, str):
                # Simple string format - use as traits description
                personality = NPCPersonality(
                    traits=[pers_data],
                    speech_style="",
                    quirks=[]
                )
            else:
                personality = NPCPersonality(
                    traits=pers_data.get("traits", []),
                    speech_style=pers_data.get("speech_style", ""),
                    quirks=pers_data.get("quirks", [])
                )
            
            # Parse trust
            trust = None
            trust_data = npc_data.get("trust")
            if trust_data:
                trust = NPCTrust(
                    initial=trust_data.get("initial", 0),
                    threshold=trust_data.get("threshold", 3),
                    build_actions=trust_data.get("build_actions", [])
                )
            
            # Parse appearance conditions
            appears_when = []
            for cond in npc_data.get("appears_when", []):
                if isinstance(cond, dict):
                    appears_when.append(AppearanceCondition(
                        condition=cond.get("condition", ""),
                        value=cond.get("value", True)
                    ))
            
            npcs[npc_id] = NPC(
                name=npc_data.get("name", npc_id),
                role=npc_data.get("role", ""),
                location=npc_data.get("location"),
                locations=npc_data.get("locations", []),
                appearance=npc_data.get("appearance", ""),
                personality=personality,
                knowledge=npc_data.get("knowledge", []),
                dialogue_rules=npc_data.get("dialogue_rules", []),
                trust=trust,
                appears_when=appears_when,
                behavior=npc_data.get("behavior", "")
            )
        
        return npcs
    
    def _load_items_yaml(self, path: Path) -> dict[str, Item]:
        """Load items.yaml"""
        if not path.exists():
            return {}
        
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        
        items = {}
        for item_id, item_data in data.items():
            # Parse properties
            props_data = item_data.get("properties", {})
            properties = ItemProperty(
                artifact=props_data.get("artifact", False),
                effect=props_data.get("effect")
            )
            
            # Parse use actions
            use_actions = {}
            for action_id, action_data in item_data.get("use_actions", {}).items():
                if isinstance(action_data, dict):
                    use_actions[action_id] = ItemUseAction(
                        description=action_data.get("description", ""),
                        requires_item=action_data.get("requires_item"),
                        sets_flag=action_data.get("sets_flag")
                    )
            
            # Parse clues
            clues = []
            for clue_data in item_data.get("clues", []):
                if isinstance(clue_data, dict):
                    clues.append(ItemClue(
                        hint_for=clue_data.get("hint_for"),
                        reveals=clue_data.get("reveals")
                    ))
            
            items[item_id] = Item(
                name=item_data.get("name", item_id),
                portable=item_data.get("portable", True),
                examine=item_data.get("examine", ""),
                found_description=item_data.get("found_description", ""),
                take_description=item_data.get("take_description", ""),
                unlocks=item_data.get("unlocks"),
                location=item_data.get("location"),
                hidden=item_data.get("hidden", False),
                find_condition=item_data.get("find_condition"),
                properties=properties,
                use_actions=use_actions,
                clues=clues
            )
        
        return items

