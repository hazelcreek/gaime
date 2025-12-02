"""
World Builder API endpoints - AI-assisted world generation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.llm.world_builder import WorldBuilder

router = APIRouter()


class GenerateWorldRequest(BaseModel):
    """Request to generate a new world"""
    prompt: str
    theme: str | None = None
    num_locations: int = 6
    num_npcs: int = 3


class GenerateWorldResponse(BaseModel):
    """Response with generated world content"""
    world_id: str
    world_yaml: str
    locations_yaml: str
    npcs_yaml: str
    items_yaml: str
    message: str


@router.post("/generate", response_model=GenerateWorldResponse)
async def generate_world(request: GenerateWorldRequest):
    """Generate a new world from a prompt using AI"""
    try:
        builder = WorldBuilder()
        result = await builder.generate(
            prompt=request.prompt,
            theme=request.theme,
            num_locations=request.num_locations,
            num_npcs=request.num_npcs
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save/{world_id}")
async def save_world(world_id: str, content: dict):
    """Save generated world content to files"""
    try:
        builder = WorldBuilder()
        builder.save_world(world_id, content)
        return {"message": f"World '{world_id}' saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

