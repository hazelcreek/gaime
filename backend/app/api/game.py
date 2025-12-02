"""
Game API endpoints - Handle player actions and game state
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.engine.state import GameStateManager
from app.engine.actions import ActionProcessor
from app.models.game import GameState, ActionRequest, ActionResponse

router = APIRouter()

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

