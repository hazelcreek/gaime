"""
Game state management for the classic engine.

Handles game sessions and state transitions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from app.engine.classic.models import (
    GameState,
    NarrativeExchange,
    NPCInteractionMemory,
    MemoryUpdates,
)
from app.models.world import WorldData
from app.engine.world import WorldLoader

if TYPE_CHECKING:
    from app.models.world import NPC

# Constants for memory limits
MAX_RECENT_EXCHANGES = 3
MAX_NPC_TOPICS = 10
MAX_NPC_NOTABLE_MOMENTS = 3
NARRATIVE_WORD_LIMIT = 100


class GameStateManager:
    """Manages game state for a single session"""

    def __init__(self, world_id: str):
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
            current_location=world.player.starting_location,
            inventory=list(world.player.starting_inventory),
            discovered_locations=[world.player.starting_location],
            flags={},
            turn_count=0,
            npc_trust={},
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
            # Returns None if NPC has no base location or was removed from the game
            npc_current_loc = self.get_npc_current_location(npc_id)

            # Check if NPC was explicitly removed from game via location_changes
            # (not just lacking a base location)
            if npc_current_loc is None and self._was_removed_from_game(npc):
                continue

            # Check if NPC is at current location
            # Either via dynamic single location or via multi-location (roaming NPCs)
            # Note: roaming NPCs (with locations list) only roam if they haven't been
            # moved by location_changes - once moved, they're at the specific location
            has_location_override = self._has_active_location_change(npc)

            if has_location_override:
                # NPC was moved by a trigger - they're only at that specific location
                is_here = npc_current_loc == current_location
            else:
                # Normal behavior - check both single location and roaming locations
                is_here = (
                    npc_current_loc == current_location
                    or current_location in npc.locations
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

    def _was_removed_from_game(self, npc) -> bool:
        """
        Check if NPC was explicitly removed from game via location_changes with move_to: null.

        An NPC with npc.location = None is NOT removed if they:
        - Have roaming locations (locations list)
        - Simply don't have a base location defined

        They ARE removed only if a location_change with move_to: null was triggered.
        """
        for change in npc.location_changes:
            if change.move_to is None and self._state.flags.get(
                change.when_flag, False
            ):
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
            if not any(
                self._state.flags.get(c.when_flag, False) for c in npc.location_changes
            ):
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

        visible = []

        for npc_id, npc in self.world_data.npcs.items():
            npc_current_loc = self.get_npc_current_location(npc_id)

            # Check if NPC was explicitly removed from game via location_changes
            if npc_current_loc is None and self._was_removed_from_game(npc):
                continue

            # Check if NPC has an active location override
            has_location_override = self._has_active_location_change(npc)

            if has_location_override:
                # NPC was moved by a trigger - they're only at that specific location
                is_here = npc_current_loc == location_id
            else:
                # Normal behavior - check both single location and roaming locations
                is_here = npc_current_loc == location_id or location_id in npc.locations

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
                return False, "You haven't discovered how to access this area yet"

        # Check item requirement
        if location.requires.item:
            if location.requires.item not in self._state.inventory:
                return False, "You need something to access this area"

        return True, ""

    def move_to(self, location_id: str) -> tuple[bool, str]:
        """Attempt to move to a new location"""
        current = self.get_current_location()

        # Check if exit exists
        if location_id not in current.exits.values():
            # Check if it's a valid direction
            direction_map = {
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
        if (
            item_id not in location.items
            and item.location != self._state.current_location
        ):
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
            return (
                False,
                f"You need a {required_item.name if required_item else action.requires_item}",
            )

        # Apply effects
        if action.sets_flag:
            self._state.flags[action.sets_flag] = True

        return True, action.description

    def set_flag(self, flag: str, value: bool = True):
        """Set a world-defined game flag"""
        self._state.flags[flag] = value

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
        return (
            True,
            victory.narrative or "Congratulations! You have completed the adventure.",
        )

    # =========================================================================
    # Narrative Memory Management
    # =========================================================================

    def add_exchange(self, player_action: str, narrative: str) -> None:
        """
        Add a narrative exchange to recent memory.

        Truncates narrative to ~100 words and maintains a rolling window of
        MAX_RECENT_EXCHANGES turns.
        """
        memory = self._state.narrative_memory

        # Truncate narrative to word limit
        words = narrative.split()
        if len(words) > NARRATIVE_WORD_LIMIT:
            truncated = " ".join(words[:NARRATIVE_WORD_LIMIT]) + "..."
        else:
            truncated = narrative

        # Create exchange
        exchange = NarrativeExchange(
            turn=self._state.turn_count,
            player_action=player_action,
            narrative_summary=truncated,
        )

        # Add to recent exchanges, maintaining limit
        memory.recent_exchanges.append(exchange)
        if len(memory.recent_exchanges) > MAX_RECENT_EXCHANGES:
            memory.recent_exchanges = memory.recent_exchanges[-MAX_RECENT_EXCHANGES:]

    def update_npc_memory(
        self,
        npc_id: str,
        topic: str | None = None,
        player_disposition: str | None = None,
        npc_disposition: str | None = None,
        notable_moment: str | None = None,
    ) -> None:
        """
        Update interaction memory for an NPC.

        Creates the memory entry if this is the first encounter.
        Maintains limits on topics (10) and notable moments (3).
        """
        memory = self._state.narrative_memory

        # Get or create NPC memory
        if npc_id not in memory.npc_memory:
            memory.npc_memory[npc_id] = NPCInteractionMemory(
                encounter_count=1,
                first_met_location=self._state.current_location,
                first_met_turn=self._state.turn_count,
                last_interaction_turn=self._state.turn_count,
            )
        else:
            npc_mem = memory.npc_memory[npc_id]
            npc_mem.encounter_count += 1
            npc_mem.last_interaction_turn = self._state.turn_count

        npc_mem = memory.npc_memory[npc_id]

        # Update topic
        if topic and topic not in npc_mem.topics_discussed:
            npc_mem.topics_discussed.append(topic)
            if len(npc_mem.topics_discussed) > MAX_NPC_TOPICS:
                npc_mem.topics_discussed = npc_mem.topics_discussed[-MAX_NPC_TOPICS:]

        # Update dispositions (freeform strings)
        if player_disposition:
            npc_mem.player_disposition = player_disposition
        if npc_disposition:
            npc_mem.npc_disposition = npc_disposition

        # Add notable moment
        if notable_moment and notable_moment not in npc_mem.notable_moments:
            npc_mem.notable_moments.append(notable_moment)
            if len(npc_mem.notable_moments) > MAX_NPC_NOTABLE_MOMENTS:
                npc_mem.notable_moments = npc_mem.notable_moments[
                    -MAX_NPC_NOTABLE_MOMENTS:
                ]

    def mark_discovered(self, entity_type: str, entity_id: str) -> None:
        """
        Mark an entity as discovered (described to player).

        Uses typed format: "item:rusty_key", "npc:ghost_child", "feature:slash_marks"
        """
        typed_id = f"{entity_type}:{entity_id}"
        if typed_id not in self._state.narrative_memory.discoveries:
            self._state.narrative_memory.discoveries.append(typed_id)

    def has_discovered(self, entity_type: str, entity_id: str) -> bool:
        """Check if an entity has already been described to the player."""
        typed_id = f"{entity_type}:{entity_id}"
        return typed_id in self._state.narrative_memory.discoveries

    def apply_memory_updates(self, updates: MemoryUpdates) -> None:
        """
        Apply memory updates from LLM response.

        Processes NPC interaction updates and new discoveries.
        """
        # Apply NPC interaction updates
        for npc_id, update in updates.npc_interactions.items():
            self.update_npc_memory(
                npc_id=npc_id,
                topic=update.topic_discussed,
                player_disposition=update.player_disposition,
                npc_disposition=update.npc_disposition,
                notable_moment=update.notable_moment,
            )

        # Apply discoveries (parse typed format)
        for typed_id in updates.new_discoveries:
            if ":" in typed_id:
                entity_type, entity_id = typed_id.split(":", 1)
                self.mark_discovered(entity_type, entity_id)
            else:
                # Fallback for untyped IDs - assume "feature"
                self.mark_discovered("feature", typed_id)

    def get_memory_context(self) -> dict:
        """
        Get narrative memory formatted for system prompt inclusion.

        Returns a dict with formatted strings for:
        - recent_context: Last 2-3 turns
        - npc_relationships: Per-NPC summaries
        - discoveries: List of already-described entities
        """
        memory = self._state.narrative_memory

        # Format recent exchanges
        recent_lines = []
        for exchange in memory.recent_exchanges:
            # Truncate action if too long
            action = (
                exchange.player_action[:50] + "..."
                if len(exchange.player_action) > 50
                else exchange.player_action
            )
            summary = (
                exchange.narrative_summary[:150] + "..."
                if len(exchange.narrative_summary) > 150
                else exchange.narrative_summary
            )
            recent_lines.append(
                f'[Turn {exchange.turn}] Player: "{action}" -> {summary}'
            )

        # Format NPC relationships
        npc_lines = []
        for npc_id, npc_mem in memory.npc_memory.items():
            parts = [f"{npc_id}: Met {npc_mem.encounter_count}x"]
            if npc_mem.topics_discussed:
                topics = ", ".join(npc_mem.topics_discussed[-3:])  # Last 3 topics
                parts.append(f"discussed: {topics}")
            if npc_mem.player_disposition != "neutral":
                parts.append(f"player is {npc_mem.player_disposition}")
            if npc_mem.npc_disposition != "neutral":
                parts.append(f"NPC is {npc_mem.npc_disposition}")
            if npc_mem.notable_moments:
                parts.append(f'notable: "{npc_mem.notable_moments[-1]}"')
            npc_lines.append(". ".join(parts))

        return {
            "recent_context": (
                "\n".join(recent_lines) if recent_lines else "(no recent interactions)"
            ),
            "npc_relationships": (
                "\n".join(npc_lines) if npc_lines else "(no NPC interactions yet)"
            ),
            "discoveries": memory.discoveries,
        }
