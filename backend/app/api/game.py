"""
Game API endpoints - Handle player actions and game state

This module supports both the classic engine and the two-phase engine.
Engine selection is done at game start via the `engine` parameter.
"""

from pathlib import Path
from typing import NamedTuple, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.engine.classic.state import GameStateManager
from app.engine.classic.processor import ActionProcessor
from app.engine.classic.models import (
    GameState,
    ActionRequest,
    ActionResponse,
)
from app.models.game import LLMDebugInfo
from app.engine.two_phase.state import TwoPhaseStateManager
from app.engine.two_phase.processor import TwoPhaseProcessor
from app.engine.two_phase.models.state import TwoPhaseGameState, TwoPhaseActionResponse
from app.llm.image_generator import get_location_image_path
from app.api.engine import EngineVersion, ENGINE_INFO, DEFAULT_ENGINE

router = APIRouter()

# Get worlds directory path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
WORLDS_DIR = PROJECT_ROOT / "worlds"


# =============================================================================
# Session Types
# =============================================================================


class ClassicGameSession(NamedTuple):
    """Session data for classic engine."""

    manager: GameStateManager
    engine: EngineVersion


class TwoPhaseGameSession(NamedTuple):
    """Session data for two-phase engine."""

    manager: TwoPhaseStateManager
    engine: EngineVersion


# Union type for all session types
GameSession = Union[ClassicGameSession, TwoPhaseGameSession]


# In-memory game sessions (for prototype - would use Redis/DB in production)
game_sessions: dict[str, GameSession] = {}


# =============================================================================
# Request/Response Models
# =============================================================================


class NewGameRequest(BaseModel):
    """Request to start a new game"""

    world_id: str = "cursed-manor"
    debug: bool = False  # Enable LLM debug info in responses
    engine: EngineVersion = DEFAULT_ENGINE  # Engine version selection


class NewGameResponse(BaseModel):
    """Response after starting a new game (classic engine)"""

    session_id: str
    narrative: str
    state: GameState
    engine_version: EngineVersion
    llm_debug: LLMDebugInfo | None = None


class TwoPhaseNewGameResponse(BaseModel):
    """Response after starting a new game (two-phase engine)"""

    session_id: str
    narrative: str
    state: TwoPhaseGameState
    engine_version: EngineVersion
    llm_debug: LLMDebugInfo | None = None


class TwoPhaseActionRequest(BaseModel):
    """Request to process an action in two-phase engine"""

    session_id: str
    action: str
    debug: bool = False


# =============================================================================
# Game Start Endpoints
# =============================================================================


@router.post("/new")
async def new_game(request: NewGameRequest):
    """Start a new game session.

    The engine parameter determines which engine is used:
    - classic: Single LLM call for action processing (default)
    - two_phase: Separated parsing and narration

    Returns different response types based on engine selection.
    """
    try:
        if request.engine == EngineVersion.TWO_PHASE:
            return await _start_two_phase_game(request)
        else:
            return await _start_classic_game(request)

    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"World '{request.world_id}' not found"
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def _start_classic_game(request: NewGameRequest) -> NewGameResponse:
    """Start a game with the classic engine."""
    manager = GameStateManager(request.world_id)
    session_id = manager.session_id

    # Store session
    game_sessions[session_id] = ClassicGameSession(
        manager=manager,
        engine=EngineVersion.CLASSIC,
    )

    # Generate initial narrative
    processor = ActionProcessor(manager, debug=request.debug)
    initial_narrative, debug_info = await processor.get_initial_narrative()

    return NewGameResponse(
        session_id=session_id,
        narrative=initial_narrative,
        state=manager.get_state(),
        engine_version=EngineVersion.CLASSIC,
        llm_debug=debug_info,
    )


async def _start_two_phase_game(request: NewGameRequest) -> TwoPhaseNewGameResponse:
    """Start a game with the two-phase engine."""
    manager = TwoPhaseStateManager(request.world_id)
    session_id = manager.session_id

    # Store session
    game_sessions[session_id] = TwoPhaseGameSession(
        manager=manager,
        engine=EngineVersion.TWO_PHASE,
    )

    # Generate initial narrative using two-phase processor
    processor = TwoPhaseProcessor(manager, debug=request.debug)
    initial_narrative, debug_info = await processor.get_initial_narrative()

    return TwoPhaseNewGameResponse(
        session_id=session_id,
        narrative=initial_narrative,
        state=manager.get_state(),
        engine_version=EngineVersion.TWO_PHASE,
        llm_debug=debug_info,
    )


# =============================================================================
# Action Processing Endpoints
# =============================================================================


@router.post("/action")
async def process_action(request: ActionRequest):
    """Process a player action and return narrative response.

    Routes to the appropriate engine based on session type.
    """
    if request.session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = game_sessions[request.session_id]

    try:
        if isinstance(session, TwoPhaseGameSession):
            return await _process_two_phase_action(session, request)
        else:
            return await _process_classic_action(session, request)

    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def _process_classic_action(
    session: ClassicGameSession, request: ActionRequest
) -> ActionResponse:
    """Process action with classic engine."""
    processor = ActionProcessor(session.manager, debug=request.debug)
    return await processor.process(request.action)


async def _process_two_phase_action(
    session: TwoPhaseGameSession, request: ActionRequest
) -> TwoPhaseActionResponse:
    """Process action with two-phase engine."""
    processor = TwoPhaseProcessor(session.manager, debug=request.debug)
    return await processor.process(request.action)


# =============================================================================
# State Query Endpoints
# =============================================================================


@router.get("/state/{session_id}")
async def get_state(session_id: str):
    """Get current game state."""
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = game_sessions[session_id]
    return {
        "state": session.manager.get_state(),
        "engine": session.engine.value,
    }


@router.get("/debug/{session_id}")
async def debug_state(session_id: str):
    """
    Get detailed debug info about game state and NPC visibility.

    Note: Full debug info is only available for classic engine sessions.
    Two-phase engine returns simplified debug info.
    """
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = game_sessions[session_id]

    if isinstance(session, TwoPhaseGameSession):
        return _debug_two_phase_state(session)
    else:
        return _debug_classic_state(session)


def _debug_two_phase_state(session: TwoPhaseGameSession) -> dict:
    """Get debug info for two-phase engine session."""
    manager = session.manager
    state = manager.get_state()

    return {
        "session_id": manager.session_id,
        "engine": "two_phase",
        "current_location": state.current_location,
        "turn_count": state.turn_count,
        "status": state.status,
        "flags": state.flags,
        "inventory": state.inventory,
        "visited_locations": list(state.visited_locations),
        "container_states": state.container_states,
    }


def _debug_classic_state(session: ClassicGameSession) -> dict:
    """Get debug info for classic engine session."""
    manager = session.manager
    state = manager.get_state()
    world_data = manager.get_world_data()

    # Build NPC visibility analysis
    npc_analysis = []
    for npc_id, npc in world_data.npcs.items():
        npc_current_loc = manager.get_npc_current_location(npc_id)

        conditions_analysis = []
        all_conditions_met = True

        if npc.appears_when:
            for condition in npc.appears_when:
                if condition.condition == "has_flag":
                    flag_name = str(condition.value)
                    flag_value = state.flags.get(flag_name, False)
                    is_met = flag_value
                    conditions_analysis.append(
                        {
                            "type": "has_flag",
                            "flag": flag_name,
                            "required": True,
                            "current_value": flag_value,
                            "met": is_met,
                        }
                    )
                    if not is_met:
                        all_conditions_met = False
                elif condition.condition == "trust_above":
                    npc_trust = state.npc_trust.get(npc_id, 0)
                    required = condition.value
                    is_met = npc_trust >= required
                    conditions_analysis.append(
                        {
                            "type": "trust_above",
                            "required": required,
                            "current_value": npc_trust,
                            "met": is_met,
                        }
                    )
                    if not is_met:
                        all_conditions_met = False

        was_removed = manager._was_removed_from_game(npc)
        has_location_override = manager._has_active_location_change(npc)

        if was_removed:
            is_at_current_location = False
        elif has_location_override:
            is_at_current_location = npc_current_loc == state.current_location
        else:
            is_at_current_location = (
                npc_current_loc == state.current_location
                or state.current_location in npc.locations
            )

        would_be_visible = (
            all_conditions_met and is_at_current_location and not was_removed
        )

        npc_analysis.append(
            {
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
                "would_be_visible": would_be_visible,
            }
        )

    current_location = manager.get_current_location()
    interactions_available = []
    if current_location and current_location.interactions:
        for int_id, interaction in current_location.interactions.items():
            interactions_available.append(
                {
                    "id": int_id,
                    "triggers": interaction.triggers,
                    "sets_flag": interaction.sets_flag,
                    "reveals_exit": interaction.reveals_exit,
                }
            )

    memory = state.narrative_memory
    narrative_memory_summary = {
        "recent_exchanges": [
            {
                "turn": ex.turn,
                "player_action": ex.player_action,
                "narrative_summary": (
                    ex.narrative_summary[:100] + "..."
                    if len(ex.narrative_summary) > 100
                    else ex.narrative_summary
                ),
            }
            for ex in memory.recent_exchanges
        ],
        "npc_memory": {
            npc_id: {
                "encounter_count": npc_mem.encounter_count,
                "first_met_location": npc_mem.first_met_location,
                "first_met_turn": npc_mem.first_met_turn,
                "topics_discussed": npc_mem.topics_discussed,
                "player_disposition": npc_mem.player_disposition,
                "npc_disposition": npc_mem.npc_disposition,
                "notable_moments": npc_mem.notable_moments,
                "last_interaction_turn": npc_mem.last_interaction_turn,
            }
            for npc_id, npc_mem in memory.npc_memory.items()
        },
        "discoveries": list(memory.discoveries),
    }

    return {
        "session_id": manager.session_id,
        "engine": "classic",
        "current_location": state.current_location,
        "turn_count": state.turn_count,
        "status": state.status,
        "flags": state.flags,
        "narrative_memory": narrative_memory_summary,
        "inventory": state.inventory,
        "discovered_locations": state.discovered_locations,
        "npc_trust": state.npc_trust,
        "npc_analysis": npc_analysis,
        "interactions_at_location": interactions_available,
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

    Note: NPC-based image variants only work with classic engine.
    Two-phase engine returns the base image.
    """
    if session_id not in game_sessions:
        raise HTTPException(status_code=404, detail="Game session not found")

    session = game_sessions[session_id]
    world_id = session.manager.world_id

    # Get visible NPCs (classic engine only)
    visible_npc_ids = []
    if isinstance(session, ClassicGameSession):
        visible_npcs = session.manager.get_visible_npcs_at_location(location_id)
        visible_npc_ids = [npc_id for npc_id, npc in visible_npcs]

    # Get the appropriate image path
    image_path = get_location_image_path(
        world_id=world_id,
        location_id=location_id,
        worlds_dir=WORLDS_DIR,
        visible_npc_ids=visible_npc_ids,
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


# =============================================================================
# Engine Discovery Endpoint
# =============================================================================


@router.get("/engines")
async def list_engines():
    """
    List available game engine versions.

    Returns the available engines for frontend discovery:
    - classic: Single LLM call for action processing (default)
    - two_phase: Separated parsing (Phase 1: movement only)
    """
    return {
        "engines": ENGINE_INFO,
        "default": DEFAULT_ENGINE.value,
    }
