"""
Image Generator - Uses Google Gemini's native image generation capabilities
for creating scene images for game locations.

Based on: https://ai.google.dev/gemini-api/docs/image-generation
Uses the google-genai SDK for native image generation.
"""

import os
import base64
import asyncio
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


# Image generation model - Gemini with image output capability
# See: https://ai.google.dev/gemini-api/docs/image-generation
# Options: "gemini-2.5-flash-image" (fast) or "gemini-3-pro-image-preview" (advanced)
IMAGE_MODEL = "gemini-3-pro-image-preview"


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
    
    Uses the google-genai SDK as per:
    https://ai.google.dev/gemini-api/docs/image-generation
    
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
    from google import genai
    
    # Configure the API
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required for image generation")
    
    # Create client with API key
    client = genai.Client(api_key=api_key)
    
    # Create the prompt
    prompt = get_image_prompt(location_name, atmosphere, theme, tone)
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Use the new google-genai SDK for image generation
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=IMAGE_MODEL,
            contents=[prompt]
        )
        
        # Extract image data from response parts
        for part in response.parts:
            if part.inline_data is not None:
                # Save the image using PIL if available, otherwise raw bytes
                image_path = output_dir / f"{location_id}.png"
                
                try:
                    # Try using the as_image() method (returns PIL Image)
                    image = part.as_image()
                    await asyncio.to_thread(image.save, str(image_path))
                except Exception:
                    # Fallback: save raw bytes
                    image_data = part.inline_data.data
                    if isinstance(image_data, str):
                        image_data = base64.b64decode(image_data)
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                
                return str(image_path)
        
        print(f"No image data in response for {location_id}")
        return None
        
    except Exception as e:
        print(f"Error generating image for {location_id}: {e}")
        # Try alternative model if primary fails
        return await _generate_with_alternative_model(
            location_id, prompt, output_dir, client
        )


async def _generate_with_alternative_model(
    location_id: str,
    prompt: str,
    output_dir: Path,
    client
) -> Optional[str]:
    """
    Fallback image generation using alternative Gemini image models.
    
    Uses the google-genai SDK.
    """
    # Alternative model names to try
    # See: https://ai.google.dev/gemini-api/docs/image-generation
    alternative_models = [
        "gemini-2.5-flash-image",  # Fast model
        "gemini-2.0-flash-exp",
    ]
    
    for alt_model in alternative_models:
        try:
            print(f"Trying alternative model: {alt_model}")
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=alt_model,
                contents=[prompt]
            )
            
            # Extract image data from response parts
            for part in response.parts:
                if part.inline_data is not None:
                    image_path = output_dir / f"{location_id}.png"
                    
                    try:
                        # Try using the as_image() method
                        image = part.as_image()
                        await asyncio.to_thread(image.save, str(image_path))
                    except Exception:
                        # Fallback: save raw bytes
                        image_data = part.inline_data.data
                        if isinstance(image_data, str):
                            image_data = base64.b64decode(image_data)
                        with open(image_path, 'wb') as f:
                            f.write(image_data)
                    
                    print(f"Successfully generated image with {alt_model}")
                    return str(image_path)
            
        except Exception as e:
            print(f"Alternative model {alt_model} failed for {location_id}: {e}")
            continue
    
    print(f"All image generation attempts failed for {location_id}")
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
