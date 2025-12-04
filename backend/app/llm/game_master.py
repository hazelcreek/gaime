"""
Game Master - LLM-powered narrative generation and action processing
"""

import re
from typing import TYPE_CHECKING

from datetime import datetime

from app.llm.client import get_completion, parse_json_response, get_model_string
from app.llm.session_logger import log_llm_interaction
from app.models.game import (
    LLMResponse, StateChanges, InventoryChange, LLMDebugInfo,
    MemoryUpdates, NPCInteractionUpdate
)

if TYPE_CHECKING:
    from app.engine.state import GameStateManager


def _normalize_action(text: str) -> str:
    """
    Normalize action text for more robust matching.
    Handles common preposition variants and synonyms.
    """
    text = text.lower().strip()
    
    # Normalize preposition variants
    text = re.sub(r'\binto\b', 'in', text)
    text = re.sub(r'\bonto\b', 'on', text)
    text = re.sub(r'\btoward[s]?\b', 'to', text)
    text = re.sub(r'\binside\b', 'in', text)
    
    # Normalize verb synonyms for common actions
    text = re.sub(r'\b(inspect|study|check|view|observe)\b', 'examine', text)
    text = re.sub(r'\b(grab|pick up|take|get)\b', 'take', text)
    text = re.sub(r'\b(speak|chat|converse)\b', 'talk', text)
    
    return text


def _matches_interaction(action: str, triggers: list[str]) -> bool:
    """
    Check if an action matches any of the interaction triggers.
    Uses normalized matching for robustness.
    """
    normalized_action = _normalize_action(action)
    
    for trigger in triggers:
        normalized_trigger = _normalize_action(trigger)
        
        # Check if trigger is a substring of the action (original behavior)
        if normalized_trigger in normalized_action:
            return True
        
        # Also check if action is a substring of trigger (handles short commands)
        if normalized_action in normalized_trigger:
            return True
        
        # Check word-level overlap for flexibility
        # (e.g., "mirror examine" should match "examine mirror")
        trigger_words = set(normalized_trigger.split())
        action_words = set(normalized_action.split())
        
        # If all significant trigger words (2+ chars) are in the action, it's a match
        significant_trigger_words = {w for w in trigger_words if len(w) >= 3}
        if significant_trigger_words and significant_trigger_words.issubset(action_words):
            return True
    
    return False


SYSTEM_PROMPT = '''You are the Game Master for a text adventure game called "{world_name}".
You create immersive, atmospheric narrative responses to player actions.

## World Setting
Theme: {theme}
Tone: {tone}
{starting_situation}

## Current Game State
- Location: {current_location} ({location_name})
- Inventory: {inventory}
- Health: {health}/100
- Discovered Areas: {discovered}
- Story Progress: {flags}

## Narrative Memory (use this to maintain continuity)
### Recent Context
{recent_context}

### NPC Relationships
{npc_relationships}

### Already Discovered (mention briefly, do NOT describe in detail again)
{discoveries}

IMPORTANT: For items/features in "Already Discovered", only reference them briefly (e.g., "the crumpled letter on the table") - do NOT re-describe their full appearance. Focus narrative detail on things NOT yet discovered.

## Current Location Details
{location_atmosphere}

Exits (with narrative context): {exits}
NPCs Present: {npcs_here}

## Visible Items at Location
{items_here_detailed}

## Item Details (USE THESE EXACT DESCRIPTIONS when player examines items)
{item_details}

## Location Details (examinable features)
{location_details}

## World Constraints (MUST follow these rules)
{constraints}

## NPCs Knowledge (for dialogue)
{npc_knowledge}

## Factual Accuracy (CRITICAL)
- NEVER invent locations for items - only mention locations from the world data above
- NEVER make up where items are hidden - use ONLY the knowledge provided in "NPCs Knowledge"
- If you don't know where something is, the NPC should say they don't know - don't guess
- All item locations MUST match what's defined in the world - check "Visible Items at Location" and item details

## Your Role
1. Narrate in second person ("You see...", "You feel...")
2. Be atmospheric and evocative, matching the tone
3. Respond appropriately to player actions
4. Only allow actions that make sense in context
5. Track and update game state through your response
6. Never break the fourth wall or mention game mechanics directly
7. If an action is impossible, explain why narratively
8. When player examines an item, use the EXACT text from Item Details above
9. When player moves, set location to the destination location_id (e.g., "dining_room", not the direction)
10. NEVER use any special formatting in the narrative - no HTML/XML tags, no markdown (no **bold**, *italic*, etc.), no special syntax. Write plain prose only

## Narrative Continuity Rules (CRITICAL)
11. Check "Already Discovered" - items/features listed there should only be mentioned briefly, NOT described in full detail again
12. Check "NPC Relationships" - reference previous conversations naturally, don't re-introduce NPCs you've met
13. Check "Recent Context" - maintain emotional tone and acknowledge what just happened
14. When an NPC is met for the first time, describe them fully; on subsequent meetings, acknowledge familiarity

## Scene Description Rules (CRITICAL)
15. When describing a scene for the FIRST TIME (nothing in "Already Discovered"):
    - State the location name and physical context clearly
    - Describe ALL NPCs present fully using their appearance from "NPCs Present"
    - Describe ALL visible items using their found_description text
    - Describe exits narratively with context
16. When RE-DESCRIBING a scene (player says "look around" again, things in "Already Discovered"):
    - Give a BRIEF atmospheric summary, not a full repeat
    - Only MENTION already-discovered items/features in passing (e.g., "the letter still sits on the table")
    - Focus detail on anything NEW or CHANGED since last time
    - Vary your language - don't repeat the same descriptions verbatim
17. If an exit seems implausible for the setting, explain WHY it's accessible in the narrative
18. Only mention items that are listed in "Visible Items at Location" - never invent items
19. NPCs listed in "NPCs Present" MUST be described when looking around - they are physically there!
20. Maintain physical reality constraints consistent with the world's theme

## Response Format
You MUST respond with valid JSON in this exact format:
{{
  "narrative": "Your narrative text here, describing what happens...",
  "state_changes": {{
    "inventory": {{ "add": ["item_id_1"], "remove": ["item_id_2"] }},
    "location": null,
    "stats": {{ "health": 0 }},
    "discovered_locations": []
  }},
  "memory_updates": {{
    "npc_interactions": {{
      "npc_id": {{
        "topic_discussed": "optional - key topic from this exchange",
        "player_disposition": "optional - how player is acting toward NPC",
        "npc_disposition": "optional - how NPC now feels toward player",
        "notable_moment": "optional - 1 sentence memorable exchange"
      }}
    }},
    "new_discoveries": ["type:id", "type:id"]
  }},
  "hints": []
}}

Notes on state_changes:
- location: Set to new location ID if player moves, null otherwise
- inventory: Use item IDs (not names) for add/remove lists. Only add items that are visible/present.
- stats: Use DELTAS (e.g., -5 for damage, +10 for healing)
- hints: Optional subtle hints for the player
- Only include changes that actually happen

Notes on memory_updates:
- npc_interactions: Track meaningful NPC exchanges. Use npc_id as key. Only include fields that changed.
  - topic_discussed: Key topic (e.g., "the dagger", "her death")
  - player_disposition: Freeform (e.g., "sympathetic", "aggressive", "curious")
  - npc_disposition: How NPC feels (e.g., "warming up", "suspicious", "trusting")
  - notable_moment: Brief memorable quote or event
- new_discoveries: Items/features/NPCs first described. Use typed format:
  - "item:rusty_key" - first time examining/finding an item
  - "npc:ghost_child" - first time meeting an NPC
  - "feature:slash_marks" - first time noticing a location feature
'''

OPENING_PROMPT = '''Generate the opening narrative for this adventure.
The player is at: {location_name}

Premise: {premise}

Starting Situation: {starting_situation}

Create an atmospheric introduction that:
1. Sets the mood and scene, clearly establishing WHERE the player is
2. Establishes the player's situation and WHY they can act now (use the starting situation)
3. Describes ALL visible items naturally using their found_description
4. Describes exits with narrative context (not just directions)
5. Hints at the goal ahead
6. Ends with a sense of possibility and urgency

Remember to respond in the JSON format specified.'''


class GameMaster:
    """LLM-powered game master for narrative generation"""
    
    def __init__(self, state_manager: "GameStateManager", debug: bool = False):
        self.state_manager = state_manager
        self.world_data = state_manager.world_data
        self.debug = debug
        self.last_debug_info: LLMDebugInfo | None = None
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with current game context"""
        state = self.state_manager.get_state()
        world = self.world_data.world
        location = self.state_manager.get_current_location()
        
        # Get items at location with their placement descriptions
        items_here_detailed = []
        location_item_ids = []
        if location:
            for item_id in location.items:
                # Skip items already in player's inventory
                if item_id in state.inventory:
                    continue
                item = self.world_data.get_item(item_id)
                if item and not item.hidden:
                    location_item_ids.append(item_id)
                    # Use location-specific placement if available, otherwise fall back to found_description
                    placement = location.item_placements.get(item_id)
                    if placement:
                        items_here_detailed.append(f"- {item.name} ({item_id}): {placement}")
                    else:
                        found_desc = item.found_description or f"A {item.name} is here."
                        items_here_detailed.append(f"- {item.name} ({item_id}): {found_desc}")
        
        # Get NPCs present with their appearance and placement descriptions
        npcs_here = []
        npc_knowledge = []
        for npc in self.state_manager.get_present_npcs():
            # Find the NPC ID by matching name
            npc_id = None
            for nid, n in self.world_data.npcs.items():
                if n.name == npc.name:
                    npc_id = nid
                    break
            
            # Build NPC description with appearance
            npc_desc = f"{npc.name} - {npc.role}"
            
            # Use location-specific placement if available
            placement = location.npc_placements.get(npc_id) if location and npc_id else None
            if placement:
                npc_desc += f" ({placement})"
            
            # Include appearance description for narrative use
            if npc.appearance:
                appearance_short = npc.appearance.strip().replace('\n', ' ')
                npc_desc += f"\n    Appearance: {appearance_short}"
            
            npcs_here.append(npc_desc)
            
            if npc.knowledge:
                npc_knowledge.append(f"{npc.name}: {', '.join(npc.knowledge[:3])}")
        
        # Format inventory
        inventory_names = []
        for item_id in state.inventory:
            item = self.world_data.get_item(item_id)
            inventory_names.append(item.name if item else item_id)
        
        # Build item details with examine content for items in inventory and at location
        item_details = []
        all_item_ids = list(set(state.inventory + location_item_ids))
        for item_id in all_item_ids:
            item = self.world_data.get_item(item_id)
            if item and item.examine:
                item_details.append(f"- {item.name} ({item_id}):\n{item.examine.strip()}")
        
        # Format exits with destination location IDs and narrative context
        exits_formatted = []
        if location:
            for direction, dest_id in location.exits.items():
                dest_loc = self.world_data.get_location(dest_id)
                dest_name = dest_loc.name if dest_loc else dest_id
                # Check if there's a detail about this exit
                exit_detail = location.details.get(direction, "") if location.details else ""
                if exit_detail:
                    exits_formatted.append(f"{direction} -> {dest_id} ({dest_name}): {exit_detail}")
                else:
                    exits_formatted.append(f"{direction} -> {dest_id} ({dest_name})")
        
        # Format location details (examinable features)
        location_details = []
        if location and location.details:
            for key, desc in location.details.items():
                location_details.append(f"- {key}: {desc}")
        
        # Get starting situation if defined
        starting_situation = ""
        if hasattr(world, 'starting_situation') and world.starting_situation:
            starting_situation = f"Starting Situation: {world.starting_situation}"
        
        # Get narrative memory context
        memory_context = self.state_manager.get_memory_context()
        
        # Format discoveries list
        discoveries_list = memory_context["discoveries"]
        discoveries_formatted = ", ".join(discoveries_list) if discoveries_list else "(nothing yet)"
        
        return SYSTEM_PROMPT.format(
            world_name=world.name,
            theme=world.theme,
            tone=world.tone,
            starting_situation=starting_situation,
            current_location=state.current_location,
            location_name=location.name if location else "Unknown",
            location_atmosphere=location.atmosphere if location else "",
            exits="\n".join(exits_formatted) if exits_formatted else "none",
            inventory=", ".join(inventory_names) if inventory_names else "nothing",
            health=state.stats.health,
            discovered=", ".join(state.discovered_locations),
            flags=", ".join(f"{k}={v}" for k, v in state.flags.items()) if state.flags else "none",
            items_here_detailed="\n".join(items_here_detailed) if items_here_detailed else "Nothing visible",
            npcs_here=", ".join(npcs_here) if npcs_here else "no one",
            item_details="\n\n".join(item_details) if item_details else "No items available to examine",
            location_details="\n".join(location_details) if location_details else "No special features",
            constraints="\n".join(f"- {c}" for c in world.constraints),
            npc_knowledge="\n".join(npc_knowledge) if npc_knowledge else "No NPCs present",
            recent_context=memory_context["recent_context"],
            npc_relationships=memory_context["npc_relationships"],
            discoveries=discoveries_formatted
        )
    
    async def generate_opening(self) -> tuple[str, LLMDebugInfo | None]:
        """Generate the opening narrative for a new game
        
        Returns:
            Tuple of (narrative, debug_info) where debug_info is populated if debug mode is on
        """
        world = self.world_data.world
        location = self.state_manager.get_current_location()
        
        # Get starting situation if defined
        starting_situation = ""
        if hasattr(world, 'starting_situation') and world.starting_situation:
            starting_situation = world.starting_situation
        else:
            starting_situation = "The adventure begins now."
        
        system_prompt = self._build_system_prompt()
        user_prompt = OPENING_PROMPT.format(
            location_name=location.name if location else "the starting area",
            premise=world.premise,
            starting_situation=starting_situation
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await get_completion(messages, response_format={"type": "json_object"})
        parsed = parse_json_response(response)
        
        model = get_model_string()
        
        # Always log to session file
        log_llm_interaction(
            session_id=self.state_manager.session_id,
            world_id=self.state_manager.world_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=response or "",
            parsed_response=parsed,
            model=model
        )
        
        # Capture debug info if enabled (for API response)
        debug_info = None
        if self.debug:
            debug_info = LLMDebugInfo(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                raw_response=response or "",
                parsed_response=parsed,
                model=model,
                timestamp=datetime.now().isoformat()
            )
            self.last_debug_info = debug_info
        
        # Apply any initial state changes
        if parsed.get("state_changes"):
            self._apply_changes(parsed["state_changes"], parsed.get("memory_updates"))
        
        return parsed.get("narrative", "You find yourself in a mysterious place..."), debug_info
    
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

Process this action and respond with the narrative result and any state changes.
Ensure you respond with a valid JSON object as specified in the system instructions.'''
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await get_completion(messages, response_format={"type": "json_object"})
        parsed = parse_json_response(response)
        
        # Check for interactions that should trigger
        if location and location.interactions:
            for int_id, interaction in location.interactions.items():
                if _matches_interaction(action, interaction.triggers):
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
        
        # Validate state changes for consistency
        state_changes_dict = parsed.get("state_changes", {})
        
        # Validate location change is a valid exit
        new_location = state_changes_dict.get("location")
        if new_location and location:
            valid_destinations = list(location.exits.values())
            if new_location not in valid_destinations:
                # LLM tried to move to invalid location - reject the move
                state_changes_dict["location"] = None
                parsed["narrative"] = parsed.get("narrative", "") + " (You can't go that way.)"
        
        # Validate inventory additions exist
        inventory_changes = state_changes_dict.get("inventory", {})
        items_to_add = inventory_changes.get("add", [])
        valid_items = []
        for item_id in items_to_add:
            item = self.world_data.get_item(item_id)
            # Item must exist and either be at location or already validated by game logic
            if item and (item_id in (location.items if location else []) or item.location == self.state_manager.get_state().current_location):
                valid_items.append(item_id)
        if items_to_add:
            inventory_changes["add"] = valid_items
        
        # Get memory updates from parsed response
        memory_updates_raw = parsed.get("memory_updates", {})
        
        # Parse into structured response
        state_changes = self._parse_state_changes(state_changes_dict, memory_updates_raw)
        
        model = get_model_string()
        
        # Always log to session file
        log_llm_interaction(
            session_id=self.state_manager.session_id,
            world_id=self.state_manager.world_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=response or "",
            parsed_response=parsed,
            model=model
        )
        
        # Capture debug info if enabled (for API response)
        debug_info = None
        if self.debug:
            debug_info = LLMDebugInfo(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                raw_response=response or "",
                parsed_response=parsed,
                model=model,
                timestamp=datetime.now().isoformat()
            )
            self.last_debug_info = debug_info
        
        return LLMResponse(
            narrative=parsed.get("narrative", "Nothing happens."),
            state_changes=state_changes,
            hints=parsed.get("hints", []),
            debug_info=debug_info
        )
    
    def _parse_state_changes(self, changes: dict, memory_updates_raw: dict | None = None) -> StateChanges:
        """Parse state changes from LLM response"""
        inventory = changes.get("inventory", {})
        
        # Parse world-defined flags (set by interactions)
        raw_flags = changes.get("flags", {})
        sanitized_flags = {k: bool(v) for k, v in raw_flags.items()}
        
        # Parse memory updates
        memory_updates = MemoryUpdates()
        if memory_updates_raw:
            # Parse NPC interactions
            npc_interactions = {}
            for npc_id, update_data in memory_updates_raw.get("npc_interactions", {}).items():
                if isinstance(update_data, dict):
                    npc_interactions[npc_id] = NPCInteractionUpdate(
                        topic_discussed=update_data.get("topic_discussed"),
                        player_disposition=update_data.get("player_disposition"),
                        npc_disposition=update_data.get("npc_disposition"),
                        notable_moment=update_data.get("notable_moment")
                    )
            memory_updates = MemoryUpdates(
                npc_interactions=npc_interactions,
                new_discoveries=memory_updates_raw.get("new_discoveries", [])
            )
        
        return StateChanges(
            inventory=InventoryChange(
                add=inventory.get("add", []),
                remove=inventory.get("remove", [])
            ),
            location=changes.get("location"),
            stats=changes.get("stats", {}),
            flags=sanitized_flags,
            discovered_locations=changes.get("discovered_locations", []),
            memory_updates=memory_updates
        )
    
    def _apply_changes(self, changes: dict, memory_updates_raw: dict | None = None):
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
        
        # Apply memory updates if provided
        if memory_updates_raw:
            memory_updates = MemoryUpdates(
                npc_interactions={
                    npc_id: NPCInteractionUpdate(**update_data)
                    for npc_id, update_data in memory_updates_raw.get("npc_interactions", {}).items()
                    if isinstance(update_data, dict)
                },
                new_discoveries=memory_updates_raw.get("new_discoveries", [])
            )
            self.state_manager.apply_memory_updates(memory_updates)

