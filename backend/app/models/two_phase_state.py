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


class NarrationEntry(BaseModel):
    """A single narration with context for style variation.

    Used to track recent narrations so the Narrator can avoid
    repetitive phrasing and adapt tone based on history.

    Attributes:
        text: The full narration text
        location_id: Where the narration occurred
        turn: The turn number when this was generated
        event_type: Type of event that triggered the narration
    """

    text: str
    location_id: str
    turn: int
    event_type: str  # "scene_browsed", "location_changed", etc.


class TwoPhaseDebugInfo(BaseModel):
    """Debug info capturing the full two-phase pipeline.

    This model captures debug information at each stage of the two-phase
    action processing pipeline: Parser -> Validator -> Narrator.

    Attributes:
        raw_input: The original player input string
        parser_type: Which parser handled the input ("rule_based" or "interactor_ai")
        parsed_intent: The ActionIntent produced by parsing (or None if not recognized)
        interactor_debug: LLM debug info if InteractorAI was used (future)
        validation_result: The ValidationResult from the validator
        events: List of events generated (serialized dicts)
        narrator_debug: LLM debug info from the Narrator call
    """

    raw_input: str

    # Parser stage
    parser_type: str  # "rule_based" or "interactor_ai"
    parsed_intent: dict | None = None  # ActionIntent.model_dump() or None

    # InteractorAI (future - will be None for rule-based)
    interactor_debug: LLMDebugInfo | None = None

    # Validation stage
    validation_result: dict | None = None  # ValidationResult data

    # Events generated
    events: list[dict] = Field(default_factory=list)

    # Narrator stage
    narrator_debug: LLMDebugInfo | None = None


class TwoPhaseGameState(BaseModel):
    """Game state for the two-phase engine.

    This model is completely separate from the classic engine's GameState.
    Key differences:
        - visited_locations is a set (not list) for efficient first-visit detection
        - container_states tracks open/closed state of containers
        - narration_history tracks recent narrations for style variation

    Attributes:
        session_id: Unique identifier for this game session
        current_location: ID of the player's current location
        inventory: List of item IDs in player's possession
        flags: World-defined flags (set by interactions)
        visited_locations: Set of location IDs player has visited
        container_states: Mapping of container_id to is_open state
        turn_count: Number of turns taken
        status: Game status - "playing", "won", or "lost"
        narration_history: Last 5 narrations for style variation (rolling window)
    """

    session_id: str
    current_location: str
    inventory: list[str] = Field(default_factory=list)
    flags: dict[str, bool] = Field(default_factory=dict)
    visited_locations: set[str] = Field(default_factory=set)
    container_states: dict[str, bool] = Field(default_factory=dict)
    turn_count: int = 0
    status: str = "playing"
    narration_history: list[NarrationEntry] = Field(default_factory=list)

    model_config = {"validate_assignment": True}


class TwoPhaseActionResponse(BaseModel):
    """Response from two-phase action processing.

    Attributes:
        narrative: The narrative text to display to the player
        state: Current game state after the action
        events: List of events that occurred (serialized)
        game_complete: True if the game has ended
        ending_narrative: Final narrative if game completed
        pipeline_debug: Full pipeline debug info when debug mode is enabled
    """

    narrative: str
    state: TwoPhaseGameState
    events: list[dict] = Field(default_factory=list)
    game_complete: bool = False
    ending_narrative: str | None = None
    pipeline_debug: TwoPhaseDebugInfo | None = None
