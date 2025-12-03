"""
Game state models - Pydantic models for game session state
"""

from pydantic import BaseModel, Field


class GameStats(BaseModel):
    """Player statistics"""
    health: int = 100
    
    class Config:
        extra = "allow"  # Allow additional stats


class InventoryChange(BaseModel):
    """Changes to inventory"""
    add: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)


class StateChanges(BaseModel):
    """State changes from an action"""
    inventory: InventoryChange = Field(default_factory=InventoryChange)
    location: str | None = None
    stats: dict[str, int] = Field(default_factory=dict)
    flags: dict[str, bool] = Field(default_factory=dict)
    discovered_locations: list[str] = Field(default_factory=list)


class GameState(BaseModel):
    """Current game session state"""
    session_id: str
    player_name: str = "Traveler"
    current_location: str
    inventory: list[str] = Field(default_factory=list)
    stats: GameStats = Field(default_factory=GameStats)
    discovered_locations: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
    turn_count: int = 0
    npc_trust: dict[str, int] = Field(default_factory=dict)
    status: str = "playing"  # "playing", "won", "lost"
    
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
        
        # Update stats
        for stat, delta in changes.stats.items():
            current = getattr(self.stats, stat, 0)
            setattr(self.stats, stat, max(0, current + delta))
        
        # Update flags
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


class ActionResponse(BaseModel):
    """Response from processing an action"""
    narrative: str
    state: GameState
    hints: list[str] = Field(default_factory=list)
    game_complete: bool = False  # True if game has ended (won or lost)
    ending_narrative: str | None = None  # Final narrative if game completed


class LLMResponse(BaseModel):
    """Parsed response from LLM"""
    narrative: str
    state_changes: StateChanges = Field(default_factory=StateChanges)
    hints: list[str] = Field(default_factory=list)

