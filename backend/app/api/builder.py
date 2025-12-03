"""
World Builder API endpoints - AI-assisted world generation and image generation
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.llm.world_builder import WorldBuilder
from app.llm.image_generator import (
    generate_location_image,
    generate_world_images,
    get_location_image_path,
    list_location_images,
)

router = APIRouter()

# Get worlds directory path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
WORLDS_DIR = PROJECT_ROOT / "worlds"


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


class GenerateImageRequest(BaseModel):
    """Request to generate image for a single location"""
    location_id: str


class GenerateImagesRequest(BaseModel):
    """Request to generate images for multiple locations"""
    location_ids: list[str] | None = None  # None means all locations


class ImageGenerationResult(BaseModel):
    """Result of image generation"""
    location_id: str
    success: bool
    image_url: str | None = None
    error: str | None = None


class GenerateImagesResponse(BaseModel):
    """Response with image generation results"""
    world_id: str
    results: list[ImageGenerationResult]
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
    except ValueError as e:
        # Validation errors from world builder
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail=f"World generation failed: {str(e)}. Please try again.")


@router.post("/save/{world_id}")
async def save_world(world_id: str, content: dict):
    """Save generated world content to files"""
    try:
        builder = WorldBuilder()
        builder.save_world(world_id, content)
        return {"message": f"World '{world_id}' saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{world_id}/images/generate", response_model=GenerateImagesResponse)
async def generate_images(world_id: str, request: GenerateImagesRequest):
    """
    Generate scene images for locations in a world.
    If location_ids is provided, generates only for those locations.
    Otherwise, generates for all locations.
    """
    try:
        results = await generate_world_images(
            world_id=world_id,
            worlds_dir=WORLDS_DIR,
            location_ids=request.location_ids
        )
        
        response_results = []
        for loc_id, image_path in results.items():
            if image_path:
                response_results.append(ImageGenerationResult(
                    location_id=loc_id,
                    success=True,
                    image_url=f"/api/builder/{world_id}/images/{loc_id}"
                ))
            else:
                response_results.append(ImageGenerationResult(
                    location_id=loc_id,
                    success=False,
                    error="Image generation failed"
                ))
        
        successful = sum(1 for r in response_results if r.success)
        total = len(response_results)
        
        return GenerateImagesResponse(
            world_id=world_id,
            results=response_results,
            message=f"Generated {successful}/{total} images successfully"
        )
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Image generation failed: {str(e)}"
        )


@router.post("/{world_id}/images/{location_id}/generate")
async def generate_single_image(world_id: str, location_id: str):
    """Generate or regenerate image for a single location"""
    import yaml
    
    try:
        world_path = WORLDS_DIR / world_id
        locations_yaml = world_path / "locations.yaml"
        world_yaml = world_path / "world.yaml"
        images_dir = world_path / "images"
        
        if not locations_yaml.exists():
            raise HTTPException(status_code=404, detail=f"World '{world_id}' not found")
        
        # Load world metadata
        theme = "fantasy"
        tone = "atmospheric"
        
        if world_yaml.exists():
            with open(world_yaml) as f:
                world_data = yaml.safe_load(f)
                theme = world_data.get("theme", theme)
                tone = world_data.get("tone", tone)
        
        # Load location data
        with open(locations_yaml) as f:
            locations = yaml.safe_load(f) or {}
        
        if location_id not in locations:
            raise HTTPException(
                status_code=404, 
                detail=f"Location '{location_id}' not found in world '{world_id}'"
            )
        
        loc_data = locations[location_id]
        loc_name = loc_data.get("name", location_id)
        atmosphere = loc_data.get("atmosphere", "")
        
        image_path = await generate_location_image(
            location_id=location_id,
            location_name=loc_name,
            atmosphere=atmosphere,
            theme=theme,
            tone=tone,
            output_dir=images_dir
        )
        
        if image_path:
            return {
                "success": True,
                "location_id": location_id,
                "image_url": f"/api/builder/{world_id}/images/{location_id}",
                "message": f"Image generated for {loc_name}"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Image generation failed - no image data returned"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Image generation failed: {str(e)}"
        )


@router.get("/{world_id}/images/{location_id}")
async def get_location_image(world_id: str, location_id: str):
    """Get the image for a specific location"""
    image_path = WORLDS_DIR / world_id / "images" / f"{location_id}.png"
    
    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Image not found for location '{location_id}' in world '{world_id}'"
        )
    
    return FileResponse(
        image_path,
        media_type="image/png",
        headers={"Cache-Control": "max-age=3600"}
    )


@router.get("/{world_id}/images")
async def list_images(world_id: str):
    """List all available images for a world"""
    try:
        images = list_location_images(world_id, WORLDS_DIR)
        
        return {
            "world_id": world_id,
            "images": {
                loc_id: f"/api/builder/{world_id}/images/{loc_id}"
                for loc_id in images.keys()
            },
            "count": len(images)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list images: {str(e)}"
        )


@router.get("/{world_id}/locations")
async def list_locations(world_id: str):
    """List all locations in a world with their metadata"""
    import yaml
    
    locations_yaml = WORLDS_DIR / world_id / "locations.yaml"
    
    if not locations_yaml.exists():
        raise HTTPException(
            status_code=404,
            detail=f"World '{world_id}' not found"
        )
    
    try:
        with open(locations_yaml) as f:
            locations_data = yaml.safe_load(f) or {}
        
        # Get existing images
        images = list_location_images(world_id, WORLDS_DIR)
        
        locations = []
        for loc_id, loc_data in locations_data.items():
            locations.append({
                "id": loc_id,
                "name": loc_data.get("name", loc_id),
                "has_image": loc_id in images,
                "atmosphere": loc_data.get("atmosphere", "")[:200] + "..." if len(loc_data.get("atmosphere", "")) > 200 else loc_data.get("atmosphere", "")
            })
        
        return {
            "world_id": world_id,
            "locations": locations,
            "count": len(locations)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list locations: {str(e)}"
        )

