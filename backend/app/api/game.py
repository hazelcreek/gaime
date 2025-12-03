"""
Game API endpoints - Handle player actions and game state
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.engine.state import GameStateManager
from app.engine.actions import ActionProcessor
from app.models.game import GameState, ActionRequest, ActionResponse
from app.llm.image_generator import get_location_image_path, load_variant_manifest

router = APIRouter()

# Get worlds directory path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
WORLDS_DIR = PROJECT_ROOT / "worlds"

# In-memory game sessions (for prototype - would use Redis/DB in production)
game_sessions: dict[str, GameStateManager] = {}


class NewGameRequest(BaseModel):
    """Request to start a new game"""
    world_id: str = "cursed-manor"
    player_name: str = "Traveler"


class NewGameResponse(BaseModel):
    """Response after starting a new game"""
    session_id: str
    narrative: str
    state: GameState


@router.post("/new", response_model=NewGameResponse)
async def new_game(request: NewGameRequest):
    """Start a new game session"""
    try:
        manager = GameStateManager(request.world_id, request.player_name)
        session_id = manager.session_id
        game_sessions[session_id] = manager
        
        # Generate initial narrative
        processor = ActionProcessor(manager)
        initial_narrative = await processor.get_initial_narrative()
        
        return NewGameResponse(
            session_id=session_id,
            narrative=initial_narrative,
            state=manager.get_state()
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"World '{request.world_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/action", response_model=ActionResponse)
async def process_action(request: ActionRequest):
    """Process a player action and return narrative response"""
    if request.session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    manager = game_sessions[request.session_id]
    processor = ActionProcessor(manager)
    
    try:
        response = await processor.process(request.action)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{session_id}")
async def get_state(session_id: str):
    """Get current game state"""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    manager = game_sessions[session_id]
    return {"state": manager.get_state()}


@router.get("/image/{session_id}/{location_id}")
async def get_location_image_for_session(session_id: str, location_id: str):
    """
    Get the appropriate location image for a game session.
    
    This endpoint returns the correct image variant based on which NPCs
    are currently visible at the location in the game state.
    
    For locations with conditional NPCs (e.g., ghost_child with appears_when),
    this will return:
    - Base image if the NPC hasn't appeared yet
    - Variant image with the NPC if conditions are met
    """
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    manager = game_sessions[session_id]
    world_id = manager.world_id
    
    # Get visible NPCs at this location
    visible_npcs = manager.get_visible_npcs_at_location(location_id)
    visible_npc_ids = [npc_id for npc_id, npc in visible_npcs]
    
    # Get the appropriate image path
    image_path = get_location_image_path(
        world_id=world_id,
        location_id=location_id,
        worlds_dir=WORLDS_DIR,
        visible_npc_ids=visible_npc_ids
    )
    
    if not image_path:
        # Fallback to base image without variants
        image_path = WORLDS_DIR / world_id / "images" / f"{location_id}.png"
        if not image_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Image not found for location '{location_id}'"
            )
        image_path = str(image_path)
    
    return FileResponse(
        image_path,
        media_type="image/png",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@router.get("/image/{session_id}")
async def get_current_location_image(session_id: str):
    """
    Get the image for the player's current location in a game session.
    
    Convenience endpoint that uses the session's current location.
    """
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    manager = game_sessions[session_id]
    current_location = manager.get_state().current_location
    
    return await get_location_image_for_session(session_id, current_location)

