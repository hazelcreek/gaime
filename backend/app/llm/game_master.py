"""
Game Master - LLM-powered narrative generation and action processing
"""

from typing import TYPE_CHECKING

from app.llm.client import get_completion, parse_json_response
from app.models.game import LLMResponse, StateChanges, InventoryChange

if TYPE_CHECKING:
    from app.engine.state import GameStateManager


SYSTEM_PROMPT = '''You are the Game Master for a text adventure game called "{world_name}".
You create immersive, atmospheric narrative responses to player actions.

## World Setting
Theme: {theme}
Tone: {tone}

## Current Game State
- Location: {current_location} ({location_name})
- Inventory: {inventory}
- Health: {health}/100
- Sanity: {sanity}/100
- Discovered Areas: {discovered}
- Story Progress: {flags}

## Current Location Details
{location_atmosphere}

Available Exits: {exits}
Items Here: {items_here}
NPCs Present: {npcs_here}

## World Constraints (MUST follow these rules)
{constraints}

## NPCs Knowledge (for dialogue)
{npc_knowledge}

## Your Role
1. Narrate in second person ("You see...", "You feel...")
2. Be atmospheric and evocative, matching the tone
3. Respond appropriately to player actions
4. Only allow actions that make sense in context
5. Track and update game state through your response
6. Never break the fourth wall or mention game mechanics directly
7. If an action is impossible, explain why narratively

## Response Format
You MUST respond with valid JSON in this exact format:
{{
  "narrative": "Your narrative text here, describing what happens...",
  "state_changes": {{
    "inventory": {{ "add": [], "remove": [] }},
    "location": null,
    "stats": {{ "health": 0, "sanity": 0 }},
    "flags": {{}},
    "discovered_locations": []
  }},
  "hints": []
}}

Notes on state_changes:
- location: Set to new location ID if player moves, null otherwise
- stats: Use DELTAS (e.g., -5 for damage, +10 for healing)
- flags: Set flags that should be remembered (e.g., "found_key": true)
- hints: Optional subtle hints for the player
- Only include changes that actually happen
'''

OPENING_PROMPT = '''Generate the opening narrative for this adventure.
The player has just arrived at: {location_name}

Premise: {premise}

Create an atmospheric introduction that:
1. Sets the mood and scene
2. Establishes the player's situation
3. Hints at the mystery ahead
4. Ends with a sense of possibility

Remember to respond in the JSON format specified.'''


class GameMaster:
    """LLM-powered game master for narrative generation"""
    
    def __init__(self, state_manager: "GameStateManager"):
        self.state_manager = state_manager
        self.world_data = state_manager.world_data
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with current game context"""
        state = self.state_manager.get_state()
        world = self.world_data.world
        location = self.state_manager.get_current_location()
        
        # Get items at location
        items_here = []
        if location:
            for item_id in location.items:
                item = self.world_data.get_item(item_id)
                if item and not item.hidden:
                    items_here.append(item.name)
        
        # Get NPCs present
        npcs_here = []
        npc_knowledge = []
        for npc in self.state_manager.get_present_npcs():
            npcs_here.append(f"{npc.name} - {npc.role}")
            if npc.knowledge:
                npc_knowledge.append(f"{npc.name}: {', '.join(npc.knowledge[:3])}")
        
        # Format inventory
        inventory_names = []
        for item_id in state.inventory:
            item = self.world_data.get_item(item_id)
            inventory_names.append(item.name if item else item_id)
        
        return SYSTEM_PROMPT.format(
            world_name=world.name,
            theme=world.theme,
            tone=world.tone,
            current_location=state.current_location,
            location_name=location.name if location else "Unknown",
            location_atmosphere=location.atmosphere if location else "",
            exits=", ".join(location.exits.keys()) if location else "none",
            inventory=", ".join(inventory_names) if inventory_names else "nothing",
            health=state.stats.health,
            sanity=state.stats.sanity,
            discovered=", ".join(state.discovered_locations),
            flags=", ".join(f"{k}={v}" for k, v in state.flags.items()) if state.flags else "none",
            items_here=", ".join(items_here) if items_here else "nothing visible",
            npcs_here=", ".join(npcs_here) if npcs_here else "no one",
            constraints="\n".join(f"- {c}" for c in world.constraints),
            npc_knowledge="\n".join(npc_knowledge) if npc_knowledge else "No NPCs present"
        )
    
    async def generate_opening(self) -> str:
        """Generate the opening narrative for a new game"""
        world = self.world_data.world
        location = self.state_manager.get_current_location()
        
        system_prompt = self._build_system_prompt()
        user_prompt = OPENING_PROMPT.format(
            location_name=location.name if location else "the starting area",
            premise=world.premise
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await get_completion(messages)
        parsed = parse_json_response(response)
        
        # Apply any initial state changes
        if parsed.get("state_changes"):
            self._apply_changes(parsed["state_changes"])
        
        return parsed.get("narrative", "You find yourself in a mysterious place...")
    
    async def process_action(self, action: str) -> LLMResponse:
        """Process a player action and generate response"""
        system_prompt = self._build_system_prompt()
        
        # Add location details for context
        location = self.state_manager.get_current_location()
        details_context = ""
        if location and location.details:
            details_context = "\n\nExaminable details in this location:\n"
            for key, desc in location.details.items():
                details_context += f"- {key}: {desc}\n"
        
        # Add interaction hints
        interaction_context = ""
        if location and location.interactions:
            interaction_context = "\n\nPossible special interactions:\n"
            for int_id, interaction in location.interactions.items():
                interaction_context += f"- {int_id}: triggers on {interaction.triggers}, hint: {interaction.narrative_hint}\n"
        
        user_prompt = f'''The player action is: "{action}"

{details_context}
{interaction_context}

Process this action and respond with the narrative result and any state changes.'''
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await get_completion(messages)
        parsed = parse_json_response(response)
        
        # Check for interactions that should trigger
        if location and location.interactions:
            for int_id, interaction in location.interactions.items():
                if any(trigger.lower() in action.lower() for trigger in interaction.triggers):
                    # Set associated flags
                    if interaction.sets_flag:
                        if "flags" not in parsed.get("state_changes", {}):
                            parsed.setdefault("state_changes", {})["flags"] = {}
                        parsed["state_changes"]["flags"][interaction.sets_flag] = True
                    
                    # Reveal exits
                    if interaction.reveals_exit:
                        if "discovered_locations" not in parsed.get("state_changes", {}):
                            parsed.setdefault("state_changes", {})["discovered_locations"] = []
                        # The exit is now accessible
        
        # Parse into structured response
        state_changes = self._parse_state_changes(parsed.get("state_changes", {}))
        
        return LLMResponse(
            narrative=parsed.get("narrative", "Nothing happens."),
            state_changes=state_changes,
            hints=parsed.get("hints", [])
        )
    
    def _parse_state_changes(self, changes: dict) -> StateChanges:
        """Parse state changes from LLM response"""
        inventory = changes.get("inventory", {})
        
        return StateChanges(
            inventory=InventoryChange(
                add=inventory.get("add", []),
                remove=inventory.get("remove", [])
            ),
            location=changes.get("location"),
            stats=changes.get("stats", {}),
            flags=changes.get("flags", {}),
            discovered_locations=changes.get("discovered_locations", [])
        )
    
    def _apply_changes(self, changes: dict):
        """Apply state changes directly"""
        state = self.state_manager.get_state()
        
        inventory = changes.get("inventory", {})
        for item in inventory.get("add", []):
            if item not in state.inventory:
                state.inventory.append(item)
        for item in inventory.get("remove", []):
            if item in state.inventory:
                state.inventory.remove(item)
        
        if changes.get("location"):
            state.current_location = changes["location"]
        
        for stat, delta in changes.get("stats", {}).items():
            self.state_manager.modify_stat(stat, delta)
        
        for flag, value in changes.get("flags", {}).items():
            self.state_manager.set_flag(flag, value)

