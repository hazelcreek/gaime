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
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


# Image generation model - Gemini with image output capability
# See: https://ai.google.dev/gemini-api/docs/image-generation
# Options: "gemini-2.5-flash-image" (fast) or "gemini-3-pro-image-preview" (advanced)
IMAGE_MODEL = "gemini-3-pro-image-preview"


@dataclass
class ExitInfo:
    """Information about an exit for visual representation"""
    direction: str
    destination_name: str
    is_secret: bool = False  # Revealed exits that were hidden
    requires_key: bool = False  # Locked exits


@dataclass
class ItemInfo:
    """Information about an item for visual representation"""
    name: str
    description: str = ""
    is_hidden: bool = False
    is_artifact: bool = False


@dataclass
class NPCInfo:
    """Information about an NPC for visual representation"""
    name: str
    appearance: str = ""
    role: str = ""


@dataclass
class LocationContext:
    """Full context for a location to generate appropriate imagery"""
    exits: list[ExitInfo] = field(default_factory=list)
    items: list[ItemInfo] = field(default_factory=list)
    npcs: list[NPCInfo] = field(default_factory=list)


def _build_exits_description(exits: list[ExitInfo]) -> str:
    """Build a description of exits for the image prompt."""
    if not exits:
        return ""
    
    direction_mappings = {
        "north": "a doorway or passage visible ahead in the distance",
        "south": "an opening or exit behind, perhaps suggested by light or shadows",
        "east": "a passage or doorway visible to the right side of the scene",
        "west": "a passage or doorway visible to the left side of the scene",
        "up": "stairs leading upward, or a visible upper level or balcony",
        "down": "stairs descending, a trapdoor, or a passage leading below",
        "back": "the way you came, perhaps a doorway with light streaming through",
    }
    
    exit_descriptions = []
    secret_hints = []
    
    for exit in exits:
        direction = exit.direction.lower()
        
        if exit.is_secret:
            # Secret exits should be very subtle - barely noticeable
            if direction in ["north", "south", "east", "west"]:
                secret_hints.append(f"a faint draft or subtle irregularity in the wall suggesting something hidden")
            elif direction == "up":
                secret_hints.append("shadows on the ceiling that hint at an unseen passage")
            elif direction == "down":
                secret_hints.append("a barely visible crack in the floor or subtle depression")
        elif exit.requires_key:
            # Locked exits should be visible but clearly blocked
            if direction in direction_mappings:
                exit_descriptions.append(f"{direction_mappings[direction]}, but secured with a heavy lock or barrier")
        else:
            # Normal exits - clearly visible
            if direction in direction_mappings:
                exit_descriptions.append(direction_mappings[direction])
            else:
                # Custom direction names
                exit_descriptions.append(f"a passage or path leading toward {exit.destination_name}")
    
    parts = []
    if exit_descriptions:
        parts.append("Visible pathways: " + "; ".join(exit_descriptions))
    if secret_hints:
        parts.append("Subtle environmental details: " + "; ".join(secret_hints))
    
    return "\n".join(parts)


def _build_items_description(items: list[ItemInfo]) -> str:
    """Build a description of items for the image prompt."""
    if not items:
        return ""
    
    visible_items = []
    hidden_hints = []
    artifact_items = []
    
    for item in items:
        if item.is_hidden:
            # Hidden items should be barely visible - a glint, shadow, or suggestion
            hidden_hints.append(
                f"something barely visible that could be {item.name.lower()}, "
                "perhaps catching a sliver of light or partially obscured"
            )
        elif item.is_artifact:
            # Artifacts should be present but mysterious
            artifact_items.append(
                f"a notable object ({item.name}) that draws the eye with subtle presence, "
                "perhaps glowing faintly or positioned prominently"
            )
        else:
            # Regular items - naturally placed in the scene
            visible_items.append(f"{item.name} placed naturally within the scene")
    
    parts = []
    if visible_items:
        parts.append("Objects in the scene: " + "; ".join(visible_items))
    if artifact_items:
        parts.append("Significant objects: " + "; ".join(artifact_items))
    if hidden_hints:
        parts.append("Barely perceptible elements: " + "; ".join(hidden_hints[:2]))  # Limit hints
    
    return "\n".join(parts)


def _build_npcs_description(npcs: list[NPCInfo]) -> str:
    """Build a description of NPCs for the image prompt."""
    if not npcs:
        return ""
    
    npc_descriptions = []
    
    for npc in npcs:
        if npc.appearance:
            # Clean up the appearance text
            appearance_clean = npc.appearance.strip().replace('\n', ' ')[:200]
            npc_descriptions.append(
                f"A figure - {npc.name} ({npc.role}): {appearance_clean}"
            )
        else:
            npc_descriptions.append(
                f"A figure present in the scene - {npc.name}, {npc.role}"
            )
    
    if npc_descriptions:
        return "Characters visible in the scene: " + "; ".join(npc_descriptions)
    return ""


def get_image_prompt(
    location_name: str,
    atmosphere: str,
    theme: str,
    tone: str,
    context: Optional[LocationContext] = None
) -> str:
    """
    Generate a prompt for creating a scene image.
    
    Args:
        location_name: Name of the location
        atmosphere: Atmospheric description from location YAML
        theme: World theme (e.g., "Victorian gothic horror")
        tone: World tone (e.g., "atmospheric, mysterious")
        context: Optional LocationContext with exits, items, and NPCs
    
    Returns:
        A detailed prompt for image generation
    """
    # Clean up the atmosphere text
    atmosphere_clean = atmosphere.strip().replace('\n', ' ')
    
    # Build interactive elements descriptions
    exits_desc = ""
    items_desc = ""
    npcs_desc = ""
    
    if context:
        exits_desc = _build_exits_description(context.exits)
        items_desc = _build_items_description(context.items)
        npcs_desc = _build_npcs_description(context.npcs)
    
    # Build the interactive elements section
    interactive_elements = []
    if exits_desc:
        interactive_elements.append(exits_desc)
    if items_desc:
        interactive_elements.append(items_desc)
    if npcs_desc:
        interactive_elements.append(npcs_desc)
    
    interactive_section = ""
    if interactive_elements:
        interactive_section = f"""

Interactive Elements to Include:
{chr(10).join(interactive_elements)}

Important: These elements should be integrated naturally into the scene, not highlighted 
or labelled. They should reward careful observation - exits should look like real 
architectural features, items should be placed where they would naturally be found, 
and any characters should be positioned authentically within the space."""
    
    prompt = f"""Create a dramatic, atmospheric scene illustration for a text adventure game.

Location: {location_name}
Theme: {theme}
Tone: {tone}

Scene Description:
{atmosphere_clean}{interactive_section}

Style Requirements:
- Digital painting style with rich colors and dramatic lighting
- Painterly, evocative atmosphere suitable for a text adventure game
- First-person perspective as if the player is viewing the scene
- Moody, immersive lighting that matches the tone
- 16:9 widescreen composition
- Detailed environment with depth and atmospheric effects
- Natural integration of doorways, passages, and architectural features that suggest movement possibilities
- Subtle visual storytelling through object placement and environmental details"""
    
    return prompt


async def generate_location_image(
    location_id: str,
    location_name: str,
    atmosphere: str,
    theme: str,
    tone: str,
    output_dir: Path,
    context: Optional[LocationContext] = None
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
        context: Optional LocationContext with exits, items, and NPCs for visual hints
    
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
    
    # Create the prompt with context
    prompt = get_image_prompt(location_name, atmosphere, theme, tone, context)
    
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


def _build_location_context(
    location_id: str,
    loc_data: dict,
    locations: dict,
    npcs_data: dict,
    items_data: dict
) -> LocationContext:
    """
    Build a LocationContext from world data for image generation.
    
    Args:
        location_id: ID of the current location
        loc_data: Location data from locations.yaml
        locations: All locations data for looking up destination names
        npcs_data: All NPCs data from npcs.yaml
        items_data: All items data from items.yaml
    
    Returns:
        LocationContext with exits, items, and NPCs
    """
    context = LocationContext()
    
    # Build exits info
    exits_data = loc_data.get("exits", {})
    requires = loc_data.get("requires", {})
    
    for direction, destination_id in exits_data.items():
        destination_data = locations.get(destination_id, {})
        destination_name = destination_data.get("name", destination_id)
        dest_requires = destination_data.get("requires", {})
        
        # Check if destination requires a key/item (locked)
        requires_key = bool(dest_requires.get("item") if dest_requires else False)
        
        # Check if this exit was a revealed secret (requires flag means it was hidden)
        is_secret = bool(dest_requires.get("flag") if dest_requires else False)
        
        context.exits.append(ExitInfo(
            direction=direction,
            destination_name=destination_name,
            is_secret=is_secret,
            requires_key=requires_key
        ))
    
    # Build items info - items listed in the location
    location_items = loc_data.get("items", [])
    for item_id in location_items:
        item_data = items_data.get(item_id, {})
        if item_data:
            context.items.append(ItemInfo(
                name=item_data.get("name", item_id),
                description=item_data.get("found_description", ""),
                is_hidden=item_data.get("hidden", False),
                is_artifact=item_data.get("properties", {}).get("artifact", False)
            ))
    
    # Also check for items that have this location set
    for item_id, item_data in items_data.items():
        if item_data.get("location") == location_id and item_id not in location_items:
            context.items.append(ItemInfo(
                name=item_data.get("name", item_id),
                description=item_data.get("found_description", ""),
                is_hidden=item_data.get("hidden", False),
                is_artifact=item_data.get("properties", {}).get("artifact", False)
            ))
    
    # Build NPCs info - NPCs at this location
    location_npcs = loc_data.get("npcs", [])
    for npc_id in location_npcs:
        npc_data = npcs_data.get(npc_id, {})
        if npc_data:
            context.npcs.append(NPCInfo(
                name=npc_data.get("name", npc_id),
                appearance=npc_data.get("appearance", ""),
                role=npc_data.get("role", "")
            ))
    
    # Also check for NPCs that have this location set or in their locations list
    for npc_id, npc_data in npcs_data.items():
        npc_location = npc_data.get("location")
        npc_locations = npc_data.get("locations", [])
        
        if npc_id not in location_npcs:
            if npc_location == location_id or location_id in npc_locations:
                # Check if NPC has appearance conditions (make them more subtle/ghostly)
                appears_when = npc_data.get("appears_when", [])
                
                context.npcs.append(NPCInfo(
                    name=npc_data.get("name", npc_id),
                    appearance=npc_data.get("appearance", ""),
                    role=npc_data.get("role", "")
                ))
    
    return context


async def generate_world_images(
    world_id: str,
    worlds_dir: Path,
    location_ids: Optional[list[str]] = None
) -> dict[str, Optional[str]]:
    """
    Generate images for all (or specified) locations in a world.
    
    Images include visual hints for exits, items, and NPCs present
    at each location to give players indication for interaction.
    
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
    npcs_yaml = world_path / "npcs.yaml"
    items_yaml = world_path / "items.yaml"
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
    
    # Filter to requested locations if specified
    target_locations = locations
    if location_ids:
        target_locations = {k: v for k, v in locations.items() if k in location_ids}
    
    results = {}
    
    for loc_id, loc_data in target_locations.items():
        loc_name = loc_data.get("name", loc_id)
        atmosphere = loc_data.get("atmosphere", "")
        
        # Build context with exits, items, and NPCs
        context = _build_location_context(
            location_id=loc_id,
            loc_data=loc_data,
            locations=locations,
            npcs_data=npcs_data,
            items_data=items_data
        )
        
        print(f"Generating image for: {loc_name}")
        print(f"  - Exits: {[e.direction for e in context.exits]}")
        print(f"  - Items: {[i.name for i in context.items]}")
        print(f"  - NPCs: {[n.name for n in context.npcs]}")
        
        image_path = await generate_location_image(
            location_id=loc_id,
            location_name=loc_name,
            atmosphere=atmosphere,
            theme=theme,
            tone=tone,
            output_dir=images_dir,
            context=context
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
