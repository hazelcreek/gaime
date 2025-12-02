"""
Game state management - Handles game sessions and state transitions
"""

import uuid
from datetime import datetime

from app.models.game import GameState, GameStats
from app.models.world import WorldData
from app.engine.world import WorldLoader


class GameStateManager:
    """Manages game state for a single session"""
    
    def __init__(self, world_id: str, player_name: str = "Traveler"):
        """Initialize a new game session"""
        self.session_id = str(uuid.uuid4())
        self.world_id = world_id
        self.created_at = datetime.now()
        
        # Load world data
        loader = WorldLoader()
        self.world_data: WorldData = loader.load_world(world_id)
        
        # Initialize game state from world configuration
        world = self.world_data.world
        self._state = GameState(
            session_id=self.session_id,
            player_name=player_name,
            current_location=world.player.starting_location,
            inventory=list(world.player.starting_inventory),
            stats=GameStats(**world.player.stats),
            discovered_locations=[world.player.starting_location],
            flags={},
            turn_count=0,
            npc_trust={}
        )
        
        # Initialize NPC trust levels
        for npc_id, npc in self.world_data.npcs.items():
            if npc.trust:
                self._state.npc_trust[npc_id] = npc.trust.initial
    
    def get_state(self) -> GameState:
        """Get current game state"""
        return self._state
    
    def get_world_data(self) -> WorldData:
        """Get world data"""
        return self.world_data
    
    def get_current_location(self):
        """Get current location data"""
        return self.world_data.get_location(self._state.current_location)
    
    def get_visible_items(self) -> list:
        """Get items visible in current location"""
        return self.world_data.get_items_at_location(self._state.current_location)
    
    def get_present_npcs(self) -> list:
        """Get NPCs present in current location"""
        npcs = self.world_data.get_npcs_at_location(self._state.current_location)
        
        # Filter by appearance conditions
        visible_npcs = []
        for npc in npcs:
            if self._check_npc_appears(npc):
                visible_npcs.append(npc)
        
        return visible_npcs
    
    def _check_npc_appears(self, npc) -> bool:
        """Check if NPC appearance conditions are met"""
        if not npc.appears_when:
            return True
        
        for condition in npc.appears_when:
            if condition.condition == "has_flag":
                if not self._state.flags.get(str(condition.value), False):
                    return False
            elif condition.condition == "trust_above":
                npc_trust = self._state.npc_trust.get(npc.name, 0)
                if npc_trust < condition.value:
                    return False
        
        return True
    
    def can_access_location(self, location_id: str) -> tuple[bool, str]:
        """Check if player can access a location"""
        location = self.world_data.get_location(location_id)
        
        if not location:
            return False, f"Unknown location: {location_id}"
        
        if not location.requires:
            return True, ""
        
        # Check flag requirement
        if location.requires.flag:
            if not self._state.flags.get(location.requires.flag, False):
                return False, f"You haven't discovered how to access this area yet"
        
        # Check item requirement
        if location.requires.item:
            if location.requires.item not in self._state.inventory:
                return False, f"You need something to access this area"
        
        return True, ""
    
    def move_to(self, location_id: str) -> tuple[bool, str]:
        """Attempt to move to a new location"""
        current = self.get_current_location()
        
        # Check if exit exists
        if location_id not in current.exits.values():
            # Check if it's a valid direction
            direction_map = {
                'north': 'north', 'n': 'north',
                'south': 'south', 's': 'south',
                'east': 'east', 'e': 'east',
                'west': 'west', 'w': 'west',
                'up': 'up', 'u': 'up',
                'down': 'down', 'd': 'down',
                'back': 'back'
            }
            direction = direction_map.get(location_id.lower())
            if direction and direction in current.exits:
                location_id = current.exits[direction]
            else:
                return False, "You can't go that way"
        
        # Check access
        can_access, reason = self.can_access_location(location_id)
        if not can_access:
            return False, reason
        
        # Move
        self._state.current_location = location_id
        if location_id not in self._state.discovered_locations:
            self._state.discovered_locations.append(location_id)
        
        return True, ""
    
    def take_item(self, item_id: str) -> tuple[bool, str]:
        """Attempt to take an item"""
        item = self.world_data.get_item(item_id)
        
        if not item:
            return False, f"There's no {item_id} here"
        
        if not item.portable:
            return False, "You can't take that"
        
        # Check if item is in current location
        location = self.get_current_location()
        if item_id not in location.items and item.location != self._state.current_location:
            return False, f"There's no {item.name} here"
        
        # Check if item is hidden and conditions not met
        if item.hidden and item.find_condition:
            required_flag = item.find_condition.get("requires_flag")
            if required_flag and not self._state.flags.get(required_flag, False):
                return False, f"You don't see any {item.name}"
        
        # Already have it?
        if item_id in self._state.inventory:
            return False, f"You already have the {item.name}"
        
        # Take it
        self._state.inventory.append(item_id)
        return True, item.take_description or f"You take the {item.name}"
    
    def use_item(self, item_id: str, target: str | None = None) -> tuple[bool, str]:
        """Attempt to use an item"""
        if item_id not in self._state.inventory:
            return False, f"You don't have a {item_id}"
        
        item = self.world_data.get_item(item_id)
        if not item:
            return False, f"Unknown item: {item_id}"
        
        # Check if item has use actions
        if not item.use_actions:
            return False, f"You're not sure how to use the {item.name}"
        
        # Find applicable action
        action = None
        if target and target in item.use_actions:
            action = item.use_actions[target]
        elif len(item.use_actions) == 1:
            action = list(item.use_actions.values())[0]
        
        if not action:
            return False, f"You're not sure how to use the {item.name} that way"
        
        # Check requirements
        if action.requires_item and action.requires_item not in self._state.inventory:
            required_item = self.world_data.get_item(action.requires_item)
            return False, f"You need a {required_item.name if required_item else action.requires_item}"
        
        # Apply effects
        if action.sets_flag:
            self._state.flags[action.sets_flag] = True
        
        return True, action.description
    
    def set_flag(self, flag: str, value: bool = True):
        """Set a game flag"""
        self._state.flags[flag] = value
    
    def modify_stat(self, stat: str, delta: int):
        """Modify a player stat"""
        current = getattr(self._state.stats, stat, 0)
        setattr(self._state.stats, stat, max(0, min(100, current + delta)))
    
    def build_trust(self, npc_id: str, amount: int = 1):
        """Build trust with an NPC"""
        if npc_id in self._state.npc_trust:
            self._state.npc_trust[npc_id] += amount
    
    def increment_turn(self):
        """Increment the turn counter"""
        self._state.turn_count += 1

