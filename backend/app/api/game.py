"""
Game API endpoints - Handle player actions and game state

This module provides the game API using the two-phase engine architecture.
"""

from pathlib import Path
from typing import NamedTuple

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.engine.two_phase.state import TwoPhaseStateManager
from app.engine.two_phase.processor import TwoPhaseProcessor
from app.engine.two_phase.models.state import (
    TwoPhaseGameState,
    TwoPhaseActionResponse,
    TwoPhaseDebugInfo,
)
from app.engine.two_phase.visibility import DefaultVisibilityResolver
from app.llm.image_generator import get_location_image_path

router = APIRouter()

# Get worlds directory path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
WORLDS_DIR = PROJECT_ROOT / "worlds"


# =============================================================================
# Session Types
# =============================================================================


class GameSession(NamedTuple):
    """Session data for the game engine."""

    manager: TwoPhaseStateManager


# In-memory game sessions (for prototype - would use Redis/DB in production)
game_sessions: dict[str, GameSession] = {}


# =============================================================================
# Request/Response Models
# =============================================================================


class NewGameRequest(BaseModel):
    """Request to start a new game"""

    world_id: str = "cursed-manor"
    debug: bool = False  # Enable LLM debug info in responses


class NewGameResponse(BaseModel):
    """Response after starting a new game"""

    session_id: str
    narrative: str
    state: TwoPhaseGameState
    pipeline_debug: TwoPhaseDebugInfo | None = None


class ActionRequest(BaseModel):
    """Request to process a player action"""

    session_id: str
    action: str
    debug: bool = False


# =============================================================================
# Game Start Endpoints
# =============================================================================


@router.post("/new")
async def new_game(request: NewGameRequest) -> NewGameResponse:
    """Start a new game session."""
    try:
        manager = TwoPhaseStateManager(request.world_id)
        session_id = manager.session_id

        # Store session
        game_sessions[session_id] = GameSession(manager=manager)

        # Generate initial narrative using two-phase processor
        processor = TwoPhaseProcessor(manager, debug=request.debug)
        initial_narrative, debug_info = await processor.get_initial_narrative()

        return NewGameResponse(
            session_id=session_id,
            narrative=initial_narrative,
            state=manager.get_state(),
            pipeline_debug=debug_info,
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"World '{request.world_id}' not found"
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Action Processing Endpoints
# =============================================================================


@router.post("/action")
async def process_action(request: ActionRequest) -> TwoPhaseActionResponse:
    """Process a player action and return narrative response."""
    if request.session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = game_sessions[request.session_id]

    try:
        processor = TwoPhaseProcessor(session.manager, debug=request.debug)
        return await processor.process(request.action)

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# State Query Endpoints
# =============================================================================


@router.get("/state/{session_id}")
async def get_state(session_id: str):
    """Get current game state with location debug information.

    Returns:
        - state: Current game state
        - location_debug: Full location details merged with game state visibility
    """
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = game_sessions[session_id]
    state = session.manager.get_state()
    world = session.manager.get_world_data()

    # Build location debug snapshot using the shared VisibilityResolver
    # This provides a unified view of world data merged with game state
    resolver = DefaultVisibilityResolver()
    location_debug = resolver.build_debug_snapshot(state, world)

    return {
        "state": state,
        "location_debug": location_debug.model_dump(),
    }


@router.get("/debug/{session_id}")
async def debug_state(session_id: str):
    """Get detailed debug info about game state."""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = game_sessions[session_id]
    manager = session.manager
    state = manager.get_state()

    return {
        "session_id": manager.session_id,
        "current_location": state.current_location,
        "turn_count": state.turn_count,
        "status": state.status,
        "flags": state.flags,
        "inventory": state.inventory,
        "visited_locations": list(state.visited_locations),
        "container_states": state.container_states,
    }


# =============================================================================
# Image Endpoints
# =============================================================================


@router.get("/image/{session_id}/{location_id}")
async def get_location_image_for_session(session_id: str, location_id: str):
    """
    Get the appropriate location image for a game session.

    This endpoint returns the correct image variant based on which NPCs
    are currently visible at the location in the game state.
    """
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = game_sessions[session_id]
    world_id = session.manager.world_id

    # Get the appropriate image path
    image_path = get_location_image_path(
        world_id=world_id,
        location_id=location_id,
        worlds_dir=WORLDS_DIR,
        visible_npc_ids=[],  # NPC variants not yet implemented in two-phase
    )

    if not image_path:
        image_path = WORLDS_DIR / world_id / "images" / f"{location_id}.png"
        if not image_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Image not found for location '{location_id}'"
            )
        image_path = str(image_path)

    return FileResponse(
        image_path,
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/image/{session_id}")
async def get_current_location_image(session_id: str):
    """
    Get the image for the player's current location in a game session.
    """
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = game_sessions[session_id]
    current_location = session.manager.get_state().current_location

    return await get_location_image_for_session(session_id, current_location)
