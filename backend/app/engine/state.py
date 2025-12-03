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
        
        # Initialize NPC trust levels and default locations
        for npc_id, npc in self.world_data.npcs.items():
            if npc.trust:
                self._state.npc_trust[npc_id] = npc.trust.initial
            # Store initial NPC location (single location takes precedence over locations list)
            if npc.location:
                self._state.npc_locations[npc_id] = npc.location
    
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
        """Get NPCs present in current location, considering dynamic location changes"""
        current_location = self._state.current_location
        visible_npcs = []
        
        for npc_id, npc in self.world_data.npcs.items():
            # Get the NPC's current location (may have changed due to triggers)
            # Returns None if NPC has been removed from the game
            npc_current_loc = self.get_npc_current_location(npc_id)
            
            # If NPC location is None, they've left the game entirely
            if npc_current_loc is None:
                continue
            
            # Check if NPC is at current location
            # Either via dynamic single location or via multi-location (roaming NPCs)
            # Note: roaming NPCs (with locations list) only roam if they haven't been
            # moved by location_changes - once moved, they're at the specific location
            has_location_override = self._has_active_location_change(npc)
            
            if has_location_override:
                # NPC was moved by a trigger - they're only at that specific location
                is_here = (npc_current_loc == current_location)
            else:
                # Normal behavior - check both single location and roaming locations
                is_here = (
                    npc_current_loc == current_location or
                    current_location in npc.locations
                )
            
            if is_here and self._check_npc_appears(npc):
                visible_npcs.append(npc)
        
        return visible_npcs
    
    def _has_active_location_change(self, npc) -> bool:
        """Check if any location_change trigger is currently active for this NPC."""
        for change in npc.location_changes:
            if self._state.flags.get(change.when_flag, False):
                return True
        return False
    
    def get_npc_current_location(self, npc_id: str) -> str | None:
        """
        Get the current location of an NPC, considering location_changes triggers.
        
        Location changes are checked in order; the last matching trigger wins.
        """
        npc = self.world_data.get_npc(npc_id)
        if not npc:
            return None
        
        # Start with the base location
        current_loc = npc.location
        
        # Check location_changes triggers (in order, last match wins)
        for change in npc.location_changes:
            if self._state.flags.get(change.when_flag, False):
                current_loc = change.move_to
        
        # Also check if there's an override in npc_locations state
        if npc_id in self._state.npc_locations:
            # State override only applies if no location_changes triggered
            if not any(self._state.flags.get(c.when_flag, False) for c in npc.location_changes):
                current_loc = self._state.npc_locations[npc_id]
        
        return current_loc
    
    def get_visible_npcs_at_location(self, location_id: str) -> list[tuple[str, "NPC"]]:
        """
        Get visible NPCs at a specific location with their IDs.
        
        Returns list of (npc_id, NPC) tuples for NPCs that are:
        1. Currently at the location (via location or locations field, considering triggers)
        2. Have their appears_when conditions met
        3. Haven't been removed from the game (location_changes with move_to: null)
        
        Used for image variant selection.
        """
        from app.models.world import NPC
        visible = []
        
        for npc_id, npc in self.world_data.npcs.items():
            npc_current_loc = self.get_npc_current_location(npc_id)
            
            # NPC has left the game entirely
            if npc_current_loc is None:
                continue
            
            # Check if NPC has an active location override
            has_location_override = self._has_active_location_change(npc)
            
            if has_location_override:
                # NPC was moved by a trigger - they're only at that specific location
                is_here = (npc_current_loc == location_id)
            else:
                # Normal behavior - check both single location and roaming locations
                is_here = (
                    npc_current_loc == location_id or
                    location_id in npc.locations
                )
            
            if is_here and self._check_npc_appears(npc):
                visible.append((npc_id, npc))
        
        return visible
    
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
    
    def check_victory(self) -> tuple[bool, str]:
        """
        Check if victory conditions are met.
        
        Returns:
            tuple[bool, str]: (is_victory, ending_narrative)
        """
        world = self.world_data.world
        
        # No victory conditions defined
        if not world.victory:
            return False, ""
        
        victory = world.victory
        
        # Check location requirement
        if victory.location:
            if self._state.current_location != victory.location:
                return False, ""
        
        # Check flag requirement
        if victory.flag:
            if not self._state.flags.get(victory.flag, False):
                return False, ""
        
        # Check item requirement
        if victory.item:
            if victory.item not in self._state.inventory:
                return False, ""
        
        # All conditions met - player wins!
        self._state.status = "won"
        return True, victory.narrative or "Congratulations! You have completed the adventure."

