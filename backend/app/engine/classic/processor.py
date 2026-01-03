"""
Action processor - Handles player actions with LLM integration

This is the classic engine's action processor, which uses a single LLM call
to process actions and generate narrative.
"""

import re
from typing import TYPE_CHECKING

from app.engine.classic.models import ActionResponse, StateChanges, LLMDebugInfo
from app.llm.classic.game_master import GameMaster

if TYPE_CHECKING:
    from app.engine.classic.state import GameStateManager


class ActionProcessor:
    """Processes player actions and generates narrative responses"""

    def __init__(self, state_manager: "GameStateManager", debug: bool = False):
        self.state_manager = state_manager
        self.debug = debug
        self.game_master = GameMaster(state_manager, debug=debug)
        self.last_debug_info: LLMDebugInfo | None = None

    async def get_initial_narrative(self) -> tuple[str, LLMDebugInfo | None]:
        """Generate the opening narrative for a new game

        Returns:
            Tuple of (narrative, debug_info) where debug_info is populated if debug mode is on
        """
        narrative, debug_info = await self.game_master.generate_opening()
        self.last_debug_info = debug_info
        return narrative, debug_info

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
                ending_narrative=None,
            )

        # Check for built-in commands first
        builtin_response = self._handle_builtin(action)
        if builtin_response:
            return builtin_response

        # Process with LLM
        llm_response = await self.game_master.process_action(action)

        # Store debug info
        self.last_debug_info = llm_response.debug_info

        # Apply state changes (including memory updates and exchange recording)
        self._apply_state_changes(
            llm_response.state_changes,
            player_action=action,
            narrative=llm_response.narrative,
        )

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
                ending_narrative=ending_narrative,
                llm_debug=llm_response.debug_info,
            )

        return ActionResponse(
            narrative=llm_response.narrative,
            state=self.state_manager.get_state(),
            hints=llm_response.hints,
            game_complete=False,
            ending_narrative=None,
            llm_debug=llm_response.debug_info,
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

        # Debug command
        if action_lower == "debug":
            return self._debug_response()

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
            ending_narrative=None,
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
            ending_narrative=None,
        )

    def _debug_response(self) -> ActionResponse:
        """Generate debug info showing game state, flags, narrative memory, and NPC visibility"""
        state = self.state_manager.get_state()
        world_data = self.state_manager.world_data
        current_location = self.state_manager.get_current_location()
        memory = state.narrative_memory

        lines = ["=== DEBUG INFO ===\n"]

        # Current location and turn
        lines.append(f"Location: {state.current_location}")
        lines.append(f"Turn: {state.turn_count}")
        lines.append(f"Status: {state.status}\n")

        # Flags
        lines.append("--- FLAGS ---")
        if state.flags:
            for flag, value in sorted(state.flags.items()):
                lines.append(f"  {flag}: {value}")
        else:
            lines.append("  (no flags set)")
        lines.append("")

        # Narrative Memory
        lines.append("--- NARRATIVE MEMORY ---")

        # Recent exchanges
        lines.append("  Recent Exchanges:")
        if memory.recent_exchanges:
            for exchange in memory.recent_exchanges:
                action_short = (
                    exchange.player_action[:40] + "..."
                    if len(exchange.player_action) > 40
                    else exchange.player_action
                )
                lines.append(f'    [Turn {exchange.turn}] "{action_short}"')
        else:
            lines.append("    (none)")

        # NPC memory
        lines.append("  NPC Memory:")
        if memory.npc_memory:
            for npc_id, npc_mem in memory.npc_memory.items():
                lines.append(f"    {npc_id}:")
                lines.append(
                    f"      Encounters: {npc_mem.encounter_count}, First met: {npc_mem.first_met_location}"
                )
                if npc_mem.topics_discussed:
                    lines.append(
                        f"      Topics: {', '.join(npc_mem.topics_discussed[-3:])}"
                    )
                lines.append(
                    f"      Player: {npc_mem.player_disposition}, NPC: {npc_mem.npc_disposition}"
                )
                if npc_mem.notable_moments:
                    lines.append(f'      Notable: "{npc_mem.notable_moments[-1]}"')
        else:
            lines.append("    (no NPC interactions)")

        # Discoveries
        lines.append("  Discoveries:")
        if memory.discoveries:
            for discovery in memory.discoveries:
                lines.append(f"    - {discovery}")
        else:
            lines.append("    (none)")
        lines.append("")

        # NPC Trust
        lines.append("--- NPC TRUST ---")
        if state.npc_trust:
            for npc_id, trust in state.npc_trust.items():
                npc = world_data.get_npc(npc_id)
                name = npc.name if npc else npc_id
                lines.append(f"  {name}: {trust}")
        else:
            lines.append("  (no trust levels)")
        lines.append("")

        # NPC Visibility Analysis
        lines.append("--- NPC VISIBILITY ---")
        for npc_id, npc in world_data.npcs.items():
            npc_current_loc = self.state_manager.get_npc_current_location(npc_id)
            was_removed = self.state_manager._was_removed_from_game(npc)

            # Check conditions
            conditions_met = True
            condition_details = []

            if npc.appears_when:
                for condition in npc.appears_when:
                    if condition.condition == "has_flag":
                        flag_name = str(condition.value)
                        flag_value = state.flags.get(flag_name, False)
                        status = "OK" if flag_value else "MISSING"
                        condition_details.append(
                            f"    has_flag '{flag_name}': {status}"
                        )
                        if not flag_value:
                            conditions_met = False
                    elif condition.condition == "trust_above":
                        npc_trust = state.npc_trust.get(npc_id, 0)
                        required = condition.value
                        status = "OK" if npc_trust >= required else f"NEED {required}"
                        condition_details.append(
                            f"    trust_above {required}: {npc_trust} ({status})"
                        )
                        if npc_trust < required:
                            conditions_met = False

            # Check location
            if was_removed:
                is_here = False
            else:
                has_location_override = self.state_manager._has_active_location_change(
                    npc
                )
                if has_location_override:
                    is_here = npc_current_loc == state.current_location
                else:
                    is_here = (
                        npc_current_loc == state.current_location
                        or state.current_location in npc.locations
                    )

            visible = conditions_met and is_here and not was_removed
            visibility_icon = "[VISIBLE]" if visible else "[HIDDEN]"
            if was_removed:
                visibility_icon = "[REMOVED]"

            lines.append(f"  {npc.name} ({npc_id}) {visibility_icon}")
            lines.append(
                f"    Location: {npc_current_loc or 'roaming'} (roams: {npc.locations})"
            )
            lines.append(f"    At player location: {'YES' if is_here else 'NO'}")

            if condition_details:
                lines.append("    Conditions:")
                lines.extend(condition_details)
            else:
                lines.append("    Conditions: (none - always visible)")
        lines.append("")

        # Interactions at current location
        lines.append("--- INTERACTIONS AT LOCATION ---")
        if current_location and current_location.interactions:
            for int_id, interaction in current_location.interactions.items():
                lines.append(f"  {int_id}:")
                lines.append(f"    Triggers: {', '.join(interaction.triggers)}")
                if interaction.sets_flag:
                    lines.append(f"    Sets flag: {interaction.sets_flag}")
                if interaction.reveals_exit:
                    lines.append(f"    Reveals exit: {interaction.reveals_exit}")
        else:
            lines.append("  (no interactions)")

        narrative = "\n".join(lines)

        return ActionResponse(
            narrative=narrative,
            state=state,
            hints=["Use the API endpoint /api/game/debug/{session_id} for JSON format"],
            game_complete=False,
            ending_narrative=None,
        )

    def _apply_state_changes(
        self, changes: StateChanges, player_action: str = "", narrative: str = ""
    ):
        """Apply state changes from LLM response"""
        state = self.state_manager._state  # Get direct reference to internal state

        # Inventory changes
        for item in changes.inventory.add:
            if item not in state.inventory:
                state.inventory.append(item)
        for item in changes.inventory.remove:
            if item in state.inventory:
                state.inventory.remove(item)

        # Location change
        if changes.location:
            can_access, access_reason = self.state_manager.can_access_location(
                changes.location
            )
            if can_access:
                # Update location directly on the state manager's internal state
                self.state_manager._state.current_location = changes.location
                if changes.location not in state.discovered_locations:
                    state.discovered_locations.append(changes.location)

        # Flag changes
        for flag, value in changes.flags.items():
            self.state_manager.set_flag(flag, value)

        # Discovered locations
        for loc in changes.discovered_locations:
            if loc not in state.discovered_locations:
                state.discovered_locations.append(loc)

        # Apply memory updates
        if changes.memory_updates:
            self.state_manager.apply_memory_updates(changes.memory_updates)

        # Add this exchange to recent memory (if we have action and narrative)
        if player_action and narrative:
            self.state_manager.add_exchange(player_action, narrative)


def parse_movement(action: str) -> str | None:
    """Parse movement commands and return direction"""
    action_lower = action.lower().strip()

    # Direct directions
    directions = {
        "north": "north",
        "n": "north",
        "south": "south",
        "s": "south",
        "east": "east",
        "e": "east",
        "west": "west",
        "w": "west",
        "up": "up",
        "u": "up",
        "down": "down",
        "d": "down",
        "back": "back",
    }

    if action_lower in directions:
        return directions[action_lower]

    # "go north" style
    go_match = re.match(r"go\s+(\w+)", action_lower)
    if go_match:
        direction = go_match.group(1)
        return directions.get(direction)

    return None
