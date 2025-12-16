"""
Two-Phase Engine state models.

This module contains state models specific to the two-phase game engine.
These are completely separate from the classic engine's GameState to maintain
strict engine isolation.

See planning/two-phase-game-loop-spec.md for the full specification.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.game import LLMDebugInfo


class TwoPhaseGameState(BaseModel):
    """Game state for the two-phase engine.

    This model is completely separate from the classic engine's GameState.
    Key differences:
        - visited_locations is a set (not list) for efficient first-visit detection
        - container_states tracks open/closed state of containers
        - No narrative_memory (two-phase uses different context approach)

    Attributes:
        session_id: Unique identifier for this game session
        current_location: ID of the player's current location
        inventory: List of item IDs in player's possession
        flags: World-defined flags (set by interactions)
        visited_locations: Set of location IDs player has visited
        container_states: Mapping of container_id to is_open state
        turn_count: Number of turns taken
        status: Game status - "playing", "won", or "lost"
    """

    session_id: str
    current_location: str
    inventory: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
    visited_locations: set[str] = Field(default_factory=set)
    container_states: dict[str, bool] = Field(default_factory=dict)
    turn_count: int = 0
    status: str = "playing"

    model_config = {"validate_assignment": True}


class TwoPhaseActionResponse(BaseModel):
    """Response from two-phase action processing.

    Attributes:
        narrative: The narrative text to display to the player
        state: Current game state after the action
        events: List of events that occurred (serialized)
        game_complete: True if the game has ended
        ending_narrative: Final narrative if game completed
        llm_debug: Debug info when debug mode is enabled
    """

    narrative: str
    state: TwoPhaseGameState
    events: list[dict] = Field(default_factory=list)
    game_complete: bool = False
    ending_narrative: str | None = None
    llm_debug: LLMDebugInfo | None = None

