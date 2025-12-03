"""
Action processor - Handles player actions with LLM integration
"""

import json
import re
from typing import TYPE_CHECKING

from app.models.game import ActionResponse, StateChanges, LLMResponse
from app.llm.game_master import GameMaster

if TYPE_CHECKING:
    from app.engine.state import GameStateManager


class ActionProcessor:
    """Processes player actions and generates narrative responses"""
    
    def __init__(self, state_manager: "GameStateManager"):
        self.state_manager = state_manager
        self.game_master = GameMaster(state_manager)
    
    async def get_initial_narrative(self) -> str:
        """Generate the opening narrative for a new game"""
        return await self.game_master.generate_opening()
    
    async def process(self, action: str) -> ActionResponse:
        """Process a player action and return the response"""
        action = action.strip()
        
        # Check if game is already over
        state = self.state_manager.get_state()
        if state.status != "playing":
            return ActionResponse(
                narrative="The game has ended. Start a new game to play again.",
                state=state,
                hints=[],
                game_complete=True,
                ending_narrative=None
            )
        
        # Check for built-in commands first
        builtin_response = self._handle_builtin(action)
        if builtin_response:
            return builtin_response
        
        # Process with LLM
        llm_response = await self.game_master.process_action(action)
        
        # Apply state changes
        self._apply_state_changes(llm_response.state_changes)
        
        # Increment turn
        self.state_manager.increment_turn()
        
        # Check for victory conditions
        is_victory, ending_narrative = self.state_manager.check_victory()
        
        if is_victory:
            # Append victory narrative to the action response
            full_narrative = llm_response.narrative + "\n\n---\n\n" + ending_narrative
            return ActionResponse(
                narrative=full_narrative,
                state=self.state_manager.get_state(),
                hints=[],
                game_complete=True,
                ending_narrative=ending_narrative
            )
        
        return ActionResponse(
            narrative=llm_response.narrative,
            state=self.state_manager.get_state(),
            hints=llm_response.hints,
            game_complete=False,
            ending_narrative=None
        )
    
    def _handle_builtin(self, action: str) -> ActionResponse | None:
        """Handle built-in commands without LLM"""
        action_lower = action.lower().strip()
        
        # Help command
        if action_lower in ["help", "?"]:
            return self._help_response()
        
        # Inventory command
        if action_lower in ["inventory", "inv", "i"]:
            return self._inventory_response()
        
        # Look command (still use LLM for rich description)
        # But we could have a simple version here
        
        return None
    
    def _help_response(self) -> ActionResponse:
        """Generate help text"""
        world = self.state_manager.world_data.world
        commands = world.commands
        
        help_text = "Available commands:\n\n"
        for cmd, desc in commands.items():
            help_text += f"  {cmd} - {desc}\n"
        
        help_text += "\nYou can also try natural language commands like:\n"
        help_text += "  - 'examine the painting'\n"
        help_text += "  - 'talk to Jenkins'\n"
        help_text += "  - 'go north' or just 'north'\n"
        help_text += "  - 'pick up the key'\n"
        
        return ActionResponse(
            narrative=help_text,
            state=self.state_manager.get_state(),
            hints=[],
            game_complete=False,
            ending_narrative=None
        )
    
    def _inventory_response(self) -> ActionResponse:
        """Generate inventory listing"""
        state = self.state_manager.get_state()
        inventory = state.inventory
        
        if not inventory:
            narrative = "Your pockets are empty."
        else:
            narrative = "You are carrying:\n\n"
            for item_id in inventory:
                item = self.state_manager.world_data.get_item(item_id)
                if item:
                    narrative += f"  • {item.name}\n"
                else:
                    narrative += f"  • {item_id}\n"
        
        return ActionResponse(
            narrative=narrative,
            state=state,
            hints=[],
            game_complete=False,
            ending_narrative=None
        )
    
    def _apply_state_changes(self, changes: StateChanges):
        """Apply state changes from LLM response"""
        state = self.state_manager.get_state()
        
        # Inventory changes
        for item in changes.inventory.add:
            if item not in state.inventory:
                state.inventory.append(item)
        for item in changes.inventory.remove:
            if item in state.inventory:
                state.inventory.remove(item)
        
        # Location change
        if changes.location:
            can_access, _ = self.state_manager.can_access_location(changes.location)
            if can_access:
                state.current_location = changes.location
                if changes.location not in state.discovered_locations:
                    state.discovered_locations.append(changes.location)
        
        # Stat changes
        for stat, delta in changes.stats.items():
            self.state_manager.modify_stat(stat, delta)
        
        # Flag changes
        for flag, value in changes.flags.items():
            self.state_manager.set_flag(flag, value)
        
        # Discovered locations
        for loc in changes.discovered_locations:
            if loc not in state.discovered_locations:
                state.discovered_locations.append(loc)


def parse_movement(action: str) -> str | None:
    """Parse movement commands and return direction"""
    action_lower = action.lower().strip()
    
    # Direct directions
    directions = {
        'north': 'north', 'n': 'north',
        'south': 'south', 's': 'south',
        'east': 'east', 'e': 'east',
        'west': 'west', 'w': 'west',
        'up': 'up', 'u': 'up',
        'down': 'down', 'd': 'down',
        'back': 'back',
    }
    
    if action_lower in directions:
        return directions[action_lower]
    
    # "go north" style
    go_match = re.match(r'go\s+(\w+)', action_lower)
    if go_match:
        direction = go_match.group(1)
        return directions.get(direction)
    
    return None

