"""
World Builder API endpoints - AI-assisted world generation and image generation
"""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.llm.world_builder import WorldBuilder
from app.llm.image_generator import (
    generate_location_image,
    generate_world_images,
    generate_location_variants,
    get_location_image_path,
    list_location_images,
    load_variant_manifest,
    LocationContext,
    ExitInfo,
    ItemInfo,
    NPCInfo,
    _build_location_context,
    _get_conditional_npcs_at_location,
    ImageGenerationError,
)
from app.llm.style_loader import resolve_style

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
                # Add timestamp to force cache refresh
                try:
                    mtime = int(os.path.getmtime(image_path))
                    image_url = f"/api/builder/{world_id}/images/{loc_id}?t={mtime}"
                except OSError:
                    image_url = f"/api/builder/{world_id}/images/{loc_id}"
                
                response_results.append(ImageGenerationResult(
                    location_id=loc_id,
                    success=True,
                    image_url=image_url
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
async def generate_single_image(world_id: str, location_id: str, model: str | None = None):
    """Generate or regenerate image for a single location.
    
    The generated image includes visual hints for exits, items, and NPCs
    present at the location to give players indication for interaction.
    
    Args:
        model: Optional model override. If not provided, uses the default model.
    """
    import yaml
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting image generation for {world_id}/{location_id} with model={model or 'default'}")
    
    try:
        world_path = WORLDS_DIR / world_id
        locations_yaml = world_path / "locations.yaml"
        world_yaml = world_path / "world.yaml"
        npcs_yaml = world_path / "npcs.yaml"
        items_yaml = world_path / "items.yaml"
        images_dir = world_path / "images"
        
        if not locations_yaml.exists():
            raise HTTPException(status_code=404, detail=f"World '{world_id}' not found")
        
        # Load world metadata
        theme = "fantasy"
        tone = "atmospheric"
        style_config = None
        
        if world_yaml.exists():
            with open(world_yaml) as f:
                world_data = yaml.safe_load(f) or {}
                theme = world_data.get("theme", theme)
                tone = world_data.get("tone", tone)
                style_config = world_data.get("style") or world_data.get("style_block")
        
        # Resolve style configuration
        style_block = resolve_style(style_config)
        logger.info(f"Using style: {style_block.name or 'default'}")
        
        # Load location data
        with open(locations_yaml) as f:
            locations = yaml.safe_load(f) or {}
        
        if location_id not in locations:
            raise HTTPException(
                status_code=404, 
                detail=f"Location '{location_id}' not found in world '{world_id}'"
            )
        
        # Load NPCs (optional)
        npcs_data = {}
        if npcs_yaml.exists():
            with open(npcs_yaml) as f:
                npcs_data = yaml.safe_load(f) or {}
        
        # Load items (optional)
        items_data = {}
        if items_yaml.exists():
            with open(items_yaml) as f:
                items_data = yaml.safe_load(f) or {}
        
        loc_data = locations[location_id]
        loc_name = loc_data.get("name", location_id)
        atmosphere = loc_data.get("atmosphere", "")
        
        # Build context with exits, items, and NPCs for visual hints
        context = _build_location_context(
            location_id=location_id,
            loc_data=loc_data,
            locations=locations,
            npcs_data=npcs_data,
            items_data=items_data
        )
        
        logger.info(f"Calling generate_location_image for {loc_name} with model={model or 'default'}")
        
        image_path = await generate_location_image(
            location_id=location_id,
            location_name=loc_name,
            atmosphere=atmosphere,
            theme=theme,
            tone=tone,
            output_dir=images_dir,
            context=context,
            model_override=model,
            style_block=style_block
        )
        
        logger.info(f"Image generation completed for {loc_name}: {image_path}")
        
        if image_path:
            # Add timestamp to force cache refresh
            try:
                mtime = int(os.path.getmtime(image_path))
                image_url = f"/api/builder/{world_id}/images/{location_id}?t={mtime}"
            except OSError:
                image_url = f"/api/builder/{world_id}/images/{location_id}"
                
            return {
                "success": True,
                "location_id": location_id,
                "image_url": image_url,
                "message": f"Image generated for {loc_name}"
            }
        else:
            # This shouldn't happen anymore since we raise exceptions now
            raise HTTPException(
                status_code=500,
                detail="Image generation failed - no image data returned"
            )
    
    except HTTPException:
        raise
    except ImageGenerationError as e:
        # Handle our custom image generation errors with appropriate status codes
        logger.warning(f"Image generation failed for {location_id}: {e.message} (retryable: {e.is_retryable})")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        )
    except Exception as e:
        logger.error(f"Unexpected error generating image for {location_id}: {e}", exc_info=True)
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
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@router.post("/{world_id}/images/{location_id}/generate-variants")
async def generate_location_image_variants(world_id: str, location_id: str):
    """
    Generate all image variants for a location with conditional NPCs.
    
    This creates:
    - Base image (no conditional NPCs visible)
    - Variant images for each conditional NPC
    - A manifest JSON file mapping conditions to images
    
    Use this for locations where NPCs appear conditionally (with appears_when).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Generating variants for {world_id}/{location_id}")
    
    try:
        manifest = await generate_location_variants(
            world_id=world_id,
            worlds_dir=WORLDS_DIR,
            location_id=location_id
        )
        
        if manifest:
            # Build response with image URLs
            images_generated = [manifest.base] + [v["image"] for v in manifest.variants]
            
            return {
                "success": True,
                "location_id": location_id,
                "base_image": f"/api/builder/{world_id}/images/{location_id}",
                "variants": [
                    {
                        "npcs": v["npcs"],
                        "image_url": f"/api/builder/{world_id}/images/{v['image'].replace('.png', '')}"
                    }
                    for v in manifest.variants
                ],
                "manifest_path": f"{location_id}_variants.json",
                "images_generated": len(images_generated),
                "message": f"Generated {len(images_generated)} image variants"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Variant generation failed"
            )
    
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImageGenerationError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{world_id}/images/{location_id}/variants")
async def get_location_variants_info(world_id: str, location_id: str):
    """
    Get information about available image variants for a location.
    
    Returns the variant manifest if it exists, showing which NPCs
    have variant images and what conditions trigger them.
    """
    import yaml
    
    images_dir = WORLDS_DIR / world_id / "images"
    manifest = load_variant_manifest(location_id, images_dir)
    
    # Also check for conditional NPCs at this location
    locations_yaml = WORLDS_DIR / world_id / "locations.yaml"
    npcs_yaml = WORLDS_DIR / world_id / "npcs.yaml"
    
    conditional_npcs = []
    if locations_yaml.exists() and npcs_yaml.exists():
        with open(locations_yaml) as f:
            locations = yaml.safe_load(f) or {}
        with open(npcs_yaml) as f:
            npcs_data = yaml.safe_load(f) or {}
        
        if location_id in locations:
            conditional_npcs = _get_conditional_npcs_at_location(
                location_id, locations[location_id], npcs_data
            )
    
    if manifest:
        return {
            "has_variants": True,
            "location_id": location_id,
            "base_image": manifest.base,
            "variants": manifest.variants,
            "conditional_npcs": conditional_npcs,
            "variant_count": len(manifest.variants)
        }
    else:
        return {
            "has_variants": False,
            "location_id": location_id,
            "conditional_npcs": conditional_npcs,
            "message": "No variants generated yet. Use POST /generate-variants to create them."
        }


@router.get("/{world_id}/images")
async def list_images(world_id: str):
    """List all available images for a world"""
    try:
        images_map = list_location_images(world_id, WORLDS_DIR)
        
        result_images = {}
        for loc_id, path in images_map.items():
            try:
                mtime = int(os.path.getmtime(path))
                result_images[loc_id] = f"/api/builder/{world_id}/images/{loc_id}?t={mtime}"
            except OSError:
                result_images[loc_id] = f"/api/builder/{world_id}/images/{loc_id}"
        
        return {
            "world_id": world_id,
            "images": result_images,
            "count": len(result_images)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list images: {str(e)}"
        )


@router.get("/debug/image-api")
async def debug_image_api():
    """
    Debug endpoint to test the Google image generation API.
    Returns detailed information about API connectivity and configuration.
    """
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    result = {
        "api_key_configured": False,
        "api_key_length": 0,
        "models_to_try": [],
        "test_results": [],
        "notes": []
    }
    
    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        result["api_key_configured"] = True
        result["api_key_length"] = len(api_key)
    else:
        return result
    
    # List models we'll try
    from app.llm.image_generator import IMAGE_MODEL
    result["models_to_try"] = [
        IMAGE_MODEL,
        "gemini-2.5-flash-image-preview",
        "gemini-3-pro-image-preview",
    ]
    
    # Try a simple API call to check connectivity
    try:
        from google import genai
        import asyncio
        
        client = genai.Client(api_key=api_key)
        
        # Test with a simple text prompt first (faster)
        simple_prompt = "Generate a test image of a blue square"
        
        for model in result["models_to_try"]:
            test_result = {
                "model": model,
                "status": "unknown",
                "error": None,
                "error_details": None,
                "response_info": None
            }
            
            try:
                logger.info(f"[Debug] Testing model: {model}")
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=model,
                        contents=[simple_prompt]
                    ),
                    timeout=60.0  # 60 second timeout for pro model
                )
                
                test_result["status"] = "responded"
                
                # Check response content
                if response.parts:
                    has_image = any(p.inline_data is not None for p in response.parts)
                    has_text = any(p.text is not None for p in response.parts if hasattr(p, 'text'))
                    test_result["response_info"] = {
                        "has_parts": True,
                        "num_parts": len(response.parts),
                        "has_image_data": has_image,
                        "has_text": has_text
                    }
                else:
                    test_result["response_info"] = {"has_parts": False}
                
                # Check for blocks
                if hasattr(response, 'prompt_feedback'):
                    feedback = response.prompt_feedback
                    if hasattr(feedback, 'block_reason') and feedback.block_reason:
                        test_result["status"] = "blocked"
                        test_result["error"] = str(feedback.block_reason)
                
            except asyncio.TimeoutError:
                test_result["status"] = "timeout"
                test_result["error"] = "API call timed out after 60 seconds"
                if "3-pro" in model:
                    test_result["error_details"] = "Gemini 3 Pro may have rate limits (2 images/day for free tier). Check: https://ai.google.dev/pricing"
            except Exception as e:
                test_result["status"] = "error"
                error_str = str(e)
                test_result["error"] = f"{type(e).__name__}: {error_str}"
                
                # Parse common errors
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    test_result["error_details"] = "RATE LIMITED - You've hit your quota. Check usage at: https://aistudio.google.com/app/plan"
                elif "403" in error_str or "PERMISSION_DENIED" in error_str:
                    test_result["error_details"] = "PERMISSION DENIED - API key may not have access to this model"
                elif "404" in error_str:
                    test_result["error_details"] = "MODEL NOT FOUND - This model may not be available in your region or plan"
            
            result["test_results"].append(test_result)
            logger.info(f"[Debug] Model {model}: {test_result['status']}")
    
    except Exception as e:
        result["test_results"].append({
            "model": "initialization",
            "status": "error",
            "error": f"Failed to initialize API client: {type(e).__name__}: {str(e)}"
        })
    
    # Add helpful notes
    result["notes"] = [
        "Check your quota: https://aistudio.google.com/app/plan",
        "API pricing: https://ai.google.dev/pricing",
        "Gemini 3 Pro may have stricter rate limits than Flash models",
        "If timeout persists, the model may be overloaded - try again later"
    ]
    
    return result


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

