"""
Image Generator - Uses Google Gemini's native image generation capabilities
for creating scene images for game locations.

Based on: https://ai.google.dev/gemini-api/docs/image-generation
Uses Gemini 2.0 Flash with native image generation (Imagen 3 backbone)
"""

import os
import base64
import asyncio
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


# Image generation model - Gemini 2.0 Flash with native image output
IMAGE_MODEL = "gemini-2.0-flash-exp"


def get_image_prompt(location_name: str, atmosphere: str, theme: str, tone: str) -> str:
    """
    Generate a prompt for creating a scene image.
    
    Args:
        location_name: Name of the location
        atmosphere: Atmospheric description from location YAML
        theme: World theme (e.g., "Victorian gothic horror")
        tone: World tone (e.g., "atmospheric, mysterious")
    
    Returns:
        A detailed prompt for image generation
    """
    # Clean up the atmosphere text
    atmosphere_clean = atmosphere.strip().replace('\n', ' ')
    
    prompt = f"""Create a dramatic, atmospheric scene illustration for a text adventure game.

Location: {location_name}
Theme: {theme}
Tone: {tone}

Scene Description:
{atmosphere_clean}

Style Requirements:
- Digital painting style with rich colors and dramatic lighting
- Painterly, evocative atmosphere suitable for a text adventure game
- First-person perspective as if the player is viewing the scene
- Moody, immersive lighting that matches the tone
- No text, UI elements, or characters in frame
- 16:9 widescreen composition
- Detailed environment with depth and atmospheric effects"""
    
    return prompt


async def generate_location_image(
    location_id: str,
    location_name: str,
    atmosphere: str,
    theme: str,
    tone: str,
    output_dir: Path
) -> Optional[str]:
    """
    Generate an image for a single location using Gemini's native image generation.
    
    Args:
        location_id: Unique ID of the location
        location_name: Display name of the location
        atmosphere: Atmospheric description
        theme: World theme
        tone: World tone
        output_dir: Directory to save the generated image
    
    Returns:
        Path to the generated image, or None if generation failed
    """
    import google.generativeai as genai
    
    # Configure the API
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required for image generation")
    
    genai.configure(api_key=api_key)
    
    # Create the prompt
    prompt = get_image_prompt(location_name, atmosphere, theme, tone)
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Use Gemini 2.0 Flash with image generation
        model = genai.GenerativeModel(IMAGE_MODEL)
        
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="image/png"
            )
        )
        
        # Extract image data from response
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    # Decode and save the image
                    image_data = part.inline_data.data
                    image_path = output_dir / f"{location_id}.png"
                    
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                    
                    return str(image_path)
        
        # Fallback: Try alternative response format
        if hasattr(response, 'result') and response.result:
            image_data = base64.b64decode(response.result)
            image_path = output_dir / f"{location_id}.png"
            
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            return str(image_path)
        
        print(f"No image data in response for {location_id}")
        return None
        
    except Exception as e:
        print(f"Error generating image for {location_id}: {e}")
        # Try with Imagen 3 if Flash fails
        return await _generate_with_imagen(
            location_id, prompt, output_dir
        )


async def _generate_with_imagen(
    location_id: str,
    prompt: str,
    output_dir: Path
) -> Optional[str]:
    """
    Fallback image generation using Imagen 3 model.
    """
    import google.generativeai as genai
    
    try:
        # Try Imagen 3 model
        imagen = genai.ImageGenerationModel("imagen-3.0-generate-002")
        
        result = await asyncio.to_thread(
            imagen.generate_images,
            prompt=prompt,
            number_of_images=1,
            aspect_ratio="16:9",
            safety_filter_level="block_only_high",
            person_generation="dont_allow"
        )
        
        if result.images:
            image_path = output_dir / f"{location_id}.png"
            
            # Save the image
            await asyncio.to_thread(
                result.images[0].save,
                str(image_path)
            )
            
            return str(image_path)
        
        return None
        
    except Exception as e:
        print(f"Imagen fallback failed for {location_id}: {e}")
        return None


async def generate_world_images(
    world_id: str,
    worlds_dir: Path,
    location_ids: Optional[list[str]] = None
) -> dict[str, Optional[str]]:
    """
    Generate images for all (or specified) locations in a world.
    
    Args:
        world_id: ID of the world
        worlds_dir: Base directory containing worlds
        location_ids: Optional list of specific location IDs to generate.
                     If None, generates for all locations.
    
    Returns:
        Dict mapping location_id to image path (or None if failed)
    """
    import yaml
    
    world_path = worlds_dir / world_id
    locations_yaml = world_path / "locations.yaml"
    world_yaml = world_path / "world.yaml"
    images_dir = world_path / "images"
    
    if not locations_yaml.exists():
        raise FileNotFoundError(f"Locations file not found: {locations_yaml}")
    
    # Load world metadata
    theme = "fantasy"
    tone = "atmospheric"
    
    if world_yaml.exists():
        with open(world_yaml) as f:
            world_data = yaml.safe_load(f)
            theme = world_data.get("theme", theme)
            tone = world_data.get("tone", tone)
    
    # Load locations
    with open(locations_yaml) as f:
        locations = yaml.safe_load(f) or {}
    
    # Filter to requested locations if specified
    if location_ids:
        locations = {k: v for k, v in locations.items() if k in location_ids}
    
    results = {}
    
    for loc_id, loc_data in locations.items():
        loc_name = loc_data.get("name", loc_id)
        atmosphere = loc_data.get("atmosphere", "")
        
        print(f"Generating image for: {loc_name}")
        
        image_path = await generate_location_image(
            location_id=loc_id,
            location_name=loc_name,
            atmosphere=atmosphere,
            theme=theme,
            tone=tone,
            output_dir=images_dir
        )
        
        results[loc_id] = image_path
        
        # Small delay between generations to avoid rate limiting
        await asyncio.sleep(0.5)
    
    return results


def get_location_image_path(world_id: str, location_id: str, worlds_dir: Path) -> Optional[str]:
    """
    Get the path to a location's image if it exists.
    
    Args:
        world_id: ID of the world
        location_id: ID of the location
        worlds_dir: Base directory containing worlds
    
    Returns:
        Relative path to the image, or None if not found
    """
    image_path = worlds_dir / world_id / "images" / f"{location_id}.png"
    
    if image_path.exists():
        return str(image_path)
    
    return None


def list_location_images(world_id: str, worlds_dir: Path) -> dict[str, str]:
    """
    List all existing location images for a world.
    
    Args:
        world_id: ID of the world
        worlds_dir: Base directory containing worlds
    
    Returns:
        Dict mapping location_id to image path
    """
    images_dir = worlds_dir / world_id / "images"
    
    if not images_dir.exists():
        return {}
    
    images = {}
    for image_file in images_dir.glob("*.png"):
        location_id = image_file.stem
        images[location_id] = str(image_file)
    
    return images
