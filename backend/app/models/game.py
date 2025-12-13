"""
Game state models - Pydantic models for game session state
"""

from pydantic import BaseModel, Field


# =============================================================================
# Narrative Memory Models
# =============================================================================

class NarrativeExchange(BaseModel):
    """Single turn exchange for short-term memory"""
    turn: int
    player_action: str
    narrative_summary: str  # Truncated to ~100 words


class NPCInteractionMemory(BaseModel):
    """Memory of interactions with a specific NPC"""
    encounter_count: int = 0
    first_met_location: str | None = None
    first_met_turn: int | None = None
    topics_discussed: list[str] = Field(default_factory=list)  # Max 10 topics
    player_disposition: str = "neutral"  # Freeform: "friendly", "suspicious", etc.
    npc_disposition: str = "neutral"  # How NPC feels toward player
    notable_moments: list[str] = Field(default_factory=list)  # Max 3 moments
    last_interaction_turn: int = 0


class NarrativeMemory(BaseModel):
    """Session narrative memory - tracks context for immersive storytelling"""
    recent_exchanges: list[NarrativeExchange] = Field(default_factory=list)  # Max 3
    npc_memory: dict[str, NPCInteractionMemory] = Field(default_factory=dict)
    discoveries: list[str] = Field(default_factory=list)  # Typed IDs: "item:key", "npc:ghost", "feature:marks"


class NPCInteractionUpdate(BaseModel):
    """Update to NPC interaction from LLM response"""
    topic_discussed: str | None = None
    player_disposition: str | None = None
    npc_disposition: str | None = None
    notable_moment: str | None = None


class MemoryUpdates(BaseModel):
    """Memory updates from LLM response"""
    npc_interactions: dict[str, NPCInteractionUpdate] = Field(default_factory=dict)
    new_discoveries: list[str] = Field(default_factory=list)


# =============================================================================
# Game State Models
# =============================================================================

class InventoryChange(BaseModel):
    """Changes to inventory"""
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


class StateChanges(BaseModel):
    """State changes from an action"""
    inventory: InventoryChange = Field(default_factory=InventoryChange)
    location: str | None = None
    flags: dict[str, bool] = Field(default_factory=dict)  # World-defined flags (set by interactions)
    discovered_locations: list[str] = Field(default_factory=list)
    memory_updates: MemoryUpdates = Field(default_factory=MemoryUpdates)  # Narrative memory updates


class GameState(BaseModel):
    """Current game session state"""
    session_id: str
    current_location: str
    inventory: list[str] = Field(default_factory=list)
    discovered_locations: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)  # World-defined flags (set by interactions)
    turn_count: int = 0
    npc_trust: dict[str, int] = Field(default_factory=dict)
    npc_locations: dict[str, str] = Field(default_factory=dict)  # Current NPC locations (npc_id -> location_id)
    status: str = "playing"  # "playing", "won", "lost"
    narrative_memory: NarrativeMemory = Field(default_factory=NarrativeMemory)  # Narrative context tracking
    
    def apply_changes(self, changes: StateChanges) -> None:
        """Apply state changes from an action"""
        # Update inventory
        for item in changes.inventory.add:
            if item not in self.inventory:
                self.inventory.append(item)
        for item in changes.inventory.remove:
            if item in self.inventory:
                self.inventory.remove(item)
        
        # Update location
        if changes.location:
            self.current_location = changes.location
            if changes.location not in self.discovered_locations:
                self.discovered_locations.append(changes.location)
        
        # Update world-defined flags
        self.flags.update(changes.flags)
        
        # Update discovered locations
        for loc in changes.discovered_locations:
            if loc not in self.discovered_locations:
                self.discovered_locations.append(loc)
        
        # Increment turn
        self.turn_count += 1


class ActionRequest(BaseModel):
    """Request to process a player action"""
    session_id: str
    action: str
    debug: bool = False  # Enable LLM debug info in response


class LLMDebugInfo(BaseModel):
    """Debug info for LLM interactions"""
    system_prompt: str
    user_prompt: str
    raw_response: str
    parsed_response: dict
    model: str
    timestamp: str


class ActionResponse(BaseModel):
    """Response from processing an action"""
    narrative: str
    state: GameState
    hints: list[str] = Field(default_factory=list)
    game_complete: bool = False  # True if game has ended (won or lost)
    ending_narrative: str | None = None  # Final narrative if game completed
    llm_debug: LLMDebugInfo | None = None  # Debug info when debug mode enabled


class LLMResponse(BaseModel):
    """Parsed response from LLM"""
    narrative: str
    state_changes: StateChanges = Field(default_factory=StateChanges)
    hints: list[str] = Field(default_factory=list)
    debug_info: LLMDebugInfo | None = None  # Debug info when debug mode enabled

