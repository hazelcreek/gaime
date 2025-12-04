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


@router.get("/debug/{session_id}")
async def debug_state(session_id: str):
    """
    Get detailed debug info about game state and NPC visibility.
    
    Useful for understanding why NPCs aren't appearing or what flags are set.
    """
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    manager = game_sessions[session_id]
    state = manager.get_state()
    world_data = manager.get_world_data()
    
    # Build NPC visibility analysis
    npc_analysis = []
    for npc_id, npc in world_data.npcs.items():
        # Get NPC's current location (considering location_changes)
        npc_current_loc = manager.get_npc_current_location(npc_id)
        
        # Check each appears_when condition
        conditions_analysis = []
        all_conditions_met = True
        
        if npc.appears_when:
            for condition in npc.appears_when:
                if condition.condition == "has_flag":
                    flag_name = str(condition.value)
                    flag_value = state.flags.get(flag_name, False)
                    is_met = flag_value
                    conditions_analysis.append({
                        "type": "has_flag",
                        "flag": flag_name,
                        "required": True,
                        "current_value": flag_value,
                        "met": is_met
                    })
                    if not is_met:
                        all_conditions_met = False
                elif condition.condition == "trust_above":
                    npc_trust = state.npc_trust.get(npc_id, 0)
                    required = condition.value
                    is_met = npc_trust >= required
                    conditions_analysis.append({
                        "type": "trust_above",
                        "required": required,
                        "current_value": npc_trust,
                        "met": is_met
                    })
                    if not is_met:
                        all_conditions_met = False
        
        # Check if NPC was removed from game
        was_removed = manager._was_removed_from_game(npc)
        
        # Check if NPC is at player's current location
        has_location_override = manager._has_active_location_change(npc)
        if was_removed:
            is_at_current_location = False
        elif has_location_override:
            is_at_current_location = (npc_current_loc == state.current_location)
        else:
            # Normal behavior - check both single location and roaming locations
            is_at_current_location = (
                npc_current_loc == state.current_location or
                state.current_location in npc.locations
            )
        
        # Determine visibility
        would_be_visible = all_conditions_met and is_at_current_location and not was_removed
        
        npc_analysis.append({
            "npc_id": npc_id,
            "name": npc.name,
            "role": npc.role,
            "base_location": npc.location,
            "roaming_locations": npc.locations,
            "current_location": npc_current_loc,
            "player_location": state.current_location,
            "is_at_player_location": is_at_current_location,
            "was_removed_from_game": was_removed,
            "has_appears_when": bool(npc.appears_when),
            "conditions": conditions_analysis,
            "all_conditions_met": all_conditions_met if npc.appears_when else True,
            "would_be_visible": would_be_visible
        })
    
    # Get available interactions at current location
    current_location = manager.get_current_location()
    interactions_available = []
    if current_location and current_location.interactions:
        for int_id, interaction in current_location.interactions.items():
            interactions_available.append({
                "id": int_id,
                "triggers": interaction.triggers,
                "sets_flag": interaction.sets_flag,
                "reveals_exit": interaction.reveals_exit
            })
    
    return {
        "session_id": session_id,
        "current_location": state.current_location,
        "turn_count": state.turn_count,
        "status": state.status,
        "flags": state.flags,  # World-defined flags (set by interactions)
        "llm_flags": state.llm_flags,  # AI-generated contextual flags
        "inventory": state.inventory,
        "discovered_locations": state.discovered_locations,
        "npc_trust": state.npc_trust,
        "npc_analysis": npc_analysis,
        "interactions_at_location": interactions_available
    }


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

