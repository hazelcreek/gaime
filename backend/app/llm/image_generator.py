"""
Image Generator - Uses Google Gemini's native image generation capabilities
for creating scene images for game locations.

Based on: https://ai.google.dev/gemini-api/docs/image-generation
Uses the google-genai SDK for native image generation.

Supports variant-based images for conditional NPCs:
- Base image: {location_id}.png (no conditional NPCs)
- Variant: {location_id}__with__{npc_id}.png
- Manifest: {location_id}_variants.json
"""

import os
import base64
import asyncio
import random
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from dotenv import load_dotenv
from app.llm.prompt_loader import get_loader

load_dotenv()


# Image generation model - Gemini with image output capability
# See: https://ai.google.dev/gemini-api/docs/image-generation
# We exclusively use Gemini 3 Pro Image Preview for high quality 16:9 4K images
IMAGE_MODEL = "gemini-3-pro-image-preview"

# Retry configuration for transient errors
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 2.0  # seconds
MAX_RETRY_DELAY = 30.0  # seconds


class ImageGenerationError(Exception):
    """Custom exception for image generation failures with detailed info"""
    def __init__(self, message: str, is_retryable: bool = False, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.is_retryable = is_retryable
        self.status_code = status_code


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
    placement: str = ""  # Where the item is positioned in this specific location


@dataclass
class NPCInfo:
    """Information about an NPC for visual representation"""
    name: str
    appearance: str = ""
    role: str = ""
    placement: str = ""  # Where the NPC is positioned in this specific location


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
        # Use specific placement if available, otherwise use generic description
        placement_desc = item.placement if item.placement else f"placed naturally within the scene"
        
        if item.is_hidden:
            # Hidden items should be barely visible - a glint, shadow, or suggestion
            hidden_hints.append(
                f"something barely visible that could be {item.name.lower()}, "
                "perhaps catching a sliver of light or partially obscured"
            )
        elif item.is_artifact:
            # Artifacts should be present but mysterious, with specific placement if available
            if item.placement:
                artifact_items.append(
                    f"a notable object ({item.name}) {item.placement}, drawing the eye with subtle presence"
                )
            else:
                artifact_items.append(
                    f"a notable object ({item.name}) that draws the eye with subtle presence, "
                    "perhaps glowing faintly or positioned prominently"
                )
        else:
            # Regular items - use specific placement description
            visible_items.append(f"{item.name} {placement_desc}")
    
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
        # Build description with placement if available
        placement_part = f", {npc.placement}" if npc.placement else ""
        
        if npc.appearance:
            # Clean up the appearance text
            appearance_clean = npc.appearance.strip().replace('\n', ' ')[:200]
            npc_descriptions.append(
                f"A figure - {npc.name} ({npc.role}){placement_part}: {appearance_clean}"
            )
        elif npc.placement:
            # Has placement but no detailed appearance
            npc_descriptions.append(
                f"A figure - {npc.name}, {npc.role}, {npc.placement}"
            )
        else:
            npc_descriptions.append(
                f"A figure present in the scene - {npc.name}, {npc.role}"
            )
    
    if npc_descriptions:
        return "Characters visible in the scene: " + "; ".join(npc_descriptions)
    return ""


def get_edit_prompt(
    location_name: str,
    npcs: list[NPCInfo],
    theme: str,
    tone: str
) -> str:
    """
    Generate a prompt for adding NPCs to an existing image via image editing.
    
    This is used for NPC variant generation where we want to add characters
    to a base scene image while preserving the scene's style, lighting, and perspective.
    
    Args:
        location_name: Name of the location
        npcs: List of NPCInfo objects describing the NPCs to add
        theme: World theme (e.g., "Victorian gothic horror")
        tone: World tone (e.g., "atmospheric, mysterious")
    
    Returns:
        An edit-style prompt for image modification
    """
    if not npcs:
        return "Keep this image exactly as it is."
    
    # Build detailed NPC descriptions
    npc_descriptions = []
    for npc in npcs:
        placement_part = f" {npc.placement}" if npc.placement else " positioned naturally in the scene"
        
        if npc.appearance:
            appearance_clean = npc.appearance.strip().replace('\n', ' ')[:300]
            npc_descriptions.append(
                f"- {npc.name} ({npc.role}){placement_part}: {appearance_clean}"
            )
        else:
            npc_descriptions.append(
                f"- {npc.name}, {npc.role},{placement_part}"
            )
    
    npcs_text = "\n".join(npc_descriptions)
    
    template = get_loader().get_prompt("image_generator", "edit_prompt_template.txt")
    prompt = template.format(
        location_name=location_name,
        theme=theme,
        tone=tone,
        npcs_text=npcs_text
    )
    
    return prompt


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
        interactive_template = get_loader().get_prompt("image_generator", "interactive_elements_section.txt")
        interactive_section = interactive_template.format(
            interactive_elements="\n".join(interactive_elements)
        )
    
    image_template = get_loader().get_prompt("image_generator", "image_prompt_template.txt")
    prompt = image_template.format(
        location_name=location_name,
        theme=theme,
        tone=tone,
        atmosphere=atmosphere_clean,
        interactive_section=interactive_section
    )
    
    return prompt


def _save_prompt_markdown(
    output_dir: Path,
    location_id: str,
    location_name: str,
    prompt: str
) -> None:
    """
    Save the image generation prompt as a markdown file for debugging.
    
    Args:
        output_dir: Directory to save the markdown file
        location_id: ID of the location (used for filename)
        location_name: Display name of the location (used in header)
        prompt: The full prompt text that was sent to the model
    """
    prompt_path = output_dir / f"{location_id}_prompt.md"
    prompt_content = f"# Image Prompt: {location_name}\n\n{prompt}"
    with open(prompt_path, 'w') as f:
        f.write(prompt_content)


async def generate_location_image(
    location_id: str,
    location_name: str,
    atmosphere: str,
    theme: str,
    tone: str,
    output_dir: Path,
    context: Optional[LocationContext] = None,
    model_override: Optional[str] = None
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
        model_override: Optional model name to use instead of the default
    
    Returns:
        Path to the generated image, or None if generation failed
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from google import genai
    from google.genai import types
    
    # Use override model if provided, otherwise use default
    model_to_use = model_override or IMAGE_MODEL
    
    logger.info(f"[ImageGen] Starting generation for: {location_name} ({location_id}) using {model_to_use}")
    
    # Configure the API
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("[ImageGen] GEMINI_API_KEY not set!")
        raise ValueError("GEMINI_API_KEY environment variable is required for image generation")
    
    logger.info(f"[ImageGen] API key configured (length: {len(api_key)})")
    
    # Create client with API key
    client = genai.Client(api_key=api_key)
    
    # Create the prompt with context
    prompt = get_image_prompt(location_name, atmosphere, theme, tone, context)
    logger.info(f"[ImageGen] Prompt created (length: {len(prompt)} chars)")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        logger.info(f"[ImageGen] Calling {model_to_use}...")
        
        # Configure for Gemini 3 Pro Image Preview via generate_content
        # This model uses generate_content but supports image_config for resolution control
        config = types.GenerateContentConfig(
            image_config=types.ImageConfig(
                aspect_ratio="16:9"
            )
        )
        
        # Retry loop for transient errors
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=model_to_use,
                        contents=[prompt],
                        config=config
                    ),
                    timeout=120.0  # 2 minute timeout
                )
                break  # Success, exit retry loop
            except asyncio.TimeoutError:
                logger.error(f"[ImageGen] API call timed out after 120 seconds for {location_id} (attempt {attempt + 1}/{MAX_RETRIES})")
                last_error = ImageGenerationError(
                    "API call timed out after 120 seconds. The model may be overloaded.",
                    is_retryable=True,
                    status_code=504
                )
                if attempt < MAX_RETRIES - 1:
                    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
                    logger.info(f"[ImageGen] Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
                raise last_error
            except Exception as api_error:
                error_str = str(api_error)
                logger.warning(f"[ImageGen] API error on attempt {attempt + 1}/{MAX_RETRIES}: {error_str}")
                
                # Check if it's a retryable error (503, 429, etc.)
                is_retryable = any(code in error_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded"])
                
                if is_retryable and attempt < MAX_RETRIES - 1:
                    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
                    logger.info(f"[ImageGen] Retryable error, waiting {delay:.1f}s before retry...")
                    await asyncio.sleep(delay)
                    last_error = api_error
                    continue
                
                # Parse error for better messaging
                if "503" in error_str or "UNAVAILABLE" in error_str or "overloaded" in error_str:
                    raise ImageGenerationError(
                        "The model is overloaded. Please try again in a few minutes.",
                        is_retryable=True,
                        status_code=503
                    )
                elif "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    raise ImageGenerationError(
                        "Rate limit exceeded. Please wait before generating more images.",
                        is_retryable=True,
                        status_code=429
                    )
                elif "403" in error_str or "PERMISSION_DENIED" in error_str:
                    raise ImageGenerationError(
                        "Permission denied. Check your API key permissions.",
                        is_retryable=False,
                        status_code=403
                    )
                elif "404" in error_str:
                    raise ImageGenerationError(
                        f"Model '{model_to_use}' not found or not available.",
                        is_retryable=False,
                        status_code=404
                    )
                else:
                    raise ImageGenerationError(
                        f"API error: {error_str}",
                        is_retryable=False,
                        status_code=500
                    )
        else:
            # All retries exhausted
            if last_error:
                raise last_error
            raise ImageGenerationError("All retry attempts failed", is_retryable=True, status_code=503)
        
        # Log response details for debugging
        logger.info(f"[ImageGen] Got response from API")
        
        # Handle GenerateImagesResponse
        if hasattr(response, 'generated_images') and response.generated_images:
            for i, img in enumerate(response.generated_images):
                if hasattr(img, 'image') and img.image:
                    image_path = output_dir / f"{location_id}.png"
                    
                    try:
                        # Save using the image object's save method
                        # The Image object in google-genai has a save method
                        if hasattr(img.image, 'save'):
                            await asyncio.to_thread(img.image.save, str(image_path))
                            logger.info(f"[ImageGen] Saved generated image to {image_path}")
                            _save_prompt_markdown(output_dir, location_id, location_name, prompt)
                            return str(image_path)
                        else:
                            # Fallback to writing bytes directly
                            with open(image_path, 'wb') as f:
                                f.write(img.image.image_bytes)
                            logger.info(f"[ImageGen] Saved generated image bytes to {image_path}")
                            _save_prompt_markdown(output_dir, location_id, location_name, prompt)
                            return str(image_path)
                    except Exception as save_err:
                        logger.error(f"[ImageGen] Failed to save image: {save_err}")
        
        # Fallback for generate_content response (legacy path or if mixed response)
        if hasattr(response, 'candidates') and response.candidates:
            for i, candidate in enumerate(response.candidates):
                logger.info(f"[ImageGen] Candidate {i}: finish_reason={getattr(candidate, 'finish_reason', 'N/A')}")
                safety_ratings = getattr(candidate, 'safety_ratings', None)
                if safety_ratings:
                    for rating in safety_ratings:
                        if hasattr(rating, 'probability') and rating.probability and rating.probability.name != 'NEGLIGIBLE':
                            logger.warning(f"[ImageGen] Safety rating: {rating.category.name}={rating.probability.name}")
        
        # Check for blocking
        if hasattr(response, 'prompt_feedback'):
            feedback = response.prompt_feedback
            if hasattr(feedback, 'block_reason') and feedback.block_reason:
                logger.error(f"[ImageGen] BLOCKED: {feedback.block_reason}")
                return None
        
        # Extract image data from response parts (generate_content style)
        if hasattr(response, 'parts'):
            logger.info(f"[ImageGen] Response has {len(response.parts) if response.parts else 0} parts")
            
            for i, part in enumerate(response.parts):
                logger.info(f"[ImageGen] Part {i}: inline_data={part.inline_data is not None}")
                if part.inline_data is not None:
                    # Save the image using PIL if available, otherwise raw bytes
                    image_path = output_dir / f"{location_id}.png"
                    
                    try:
                        # Try using the as_image() method (returns PIL Image)
                        image = part.as_image()
                        await asyncio.to_thread(image.save, str(image_path))
                        logger.info(f"[ImageGen] Saved image via PIL to {image_path}")
                    except Exception as pil_err:
                        logger.warning(f"[ImageGen] PIL save failed ({pil_err}), trying raw bytes")
                        # Fallback: save raw bytes
                        image_data = part.inline_data.data
                        if isinstance(image_data, str):
                            image_data = base64.b64decode(image_data)
                        with open(image_path, 'wb') as f:
                            f.write(image_data)
                        logger.info(f"[ImageGen] Saved image via raw bytes to {image_path}")
                    
                    _save_prompt_markdown(output_dir, location_id, location_name, prompt)
                    return str(image_path)
        
        logger.warning(f"[ImageGen] No image data in response for {location_id}")
        raise ImageGenerationError(
            "No image data in API response. The model may have rejected the prompt or returned only text.",
            is_retryable=False,
            status_code=500
        )
        
    except ImageGenerationError:
        # Re-raise our custom errors as-is
        raise
    except Exception as e:
        logger.error(f"[ImageGen] Error generating image for {location_id}: {e}", exc_info=True)
        raise ImageGenerationError(
            f"Unexpected error: {str(e)}",
            is_retryable=False,
            status_code=500
        )


def _build_location_context(
    location_id: str,
    loc_data: dict,
    locations: dict,
    npcs_data: dict,
    items_data: dict,
    include_npc_ids: Optional[list[str]] = None
) -> LocationContext:
    """
    Build a LocationContext from world data for image generation.
    
    Args:
        location_id: ID of the current location
        loc_data: Location data from locations.yaml
        locations: All locations data for looking up destination names
        npcs_data: All NPCs data from npcs.yaml
        items_data: All items data from items.yaml
        include_npc_ids: Optional list of NPC IDs to include. If None, includes all NPCs
                        at this location. If empty list, excludes all NPCs.
    
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
    item_placements = loc_data.get("item_placements", {})
    for item_id in location_items:
        item_data = items_data.get(item_id, {})
        if item_data:
            # Use location-specific placement if available, otherwise fall back to found_description
            placement = item_placements.get(item_id, item_data.get("found_description", ""))
            context.items.append(ItemInfo(
                name=item_data.get("name", item_id),
                description=item_data.get("found_description", ""),
                is_hidden=item_data.get("hidden", False),
                is_artifact=item_data.get("properties", {}).get("artifact", False),
                placement=placement
            ))
    
    # Also check for items that have this location set
    for item_id, item_data in items_data.items():
        if item_data.get("location") == location_id and item_id not in location_items:
            placement = item_placements.get(item_id, item_data.get("found_description", ""))
            context.items.append(ItemInfo(
                name=item_data.get("name", item_id),
                description=item_data.get("found_description", ""),
                is_hidden=item_data.get("hidden", False),
                is_artifact=item_data.get("properties", {}).get("artifact", False),
                placement=placement
            ))
    
    # Build NPCs info - NPCs at this location
    # If include_npc_ids is an empty list, skip all NPCs
    if include_npc_ids is not None and len(include_npc_ids) == 0:
        return context
    
    location_npcs = loc_data.get("npcs", [])
    npc_placements = loc_data.get("npc_placements", {})
    
    # Collect all NPCs that could be at this location
    all_potential_npcs: list[tuple[str, dict]] = []
    
    # NPCs explicitly listed in location
    for npc_id in location_npcs:
        npc_data = npcs_data.get(npc_id, {})
        if npc_data:
            all_potential_npcs.append((npc_id, npc_data))
    
    # NPCs that have this location set or in their locations list
    for npc_id, npc_data in npcs_data.items():
        if npc_id in location_npcs:
            continue  # Already added
        npc_location = npc_data.get("location")
        npc_locations = npc_data.get("locations", [])
        if npc_location == location_id or location_id in npc_locations:
            all_potential_npcs.append((npc_id, npc_data))
    
    # Filter and add NPCs based on include_npc_ids
    for npc_id, npc_data in all_potential_npcs:
        # If include_npc_ids is specified, only include those NPCs
        if include_npc_ids is not None and npc_id not in include_npc_ids:
            continue
        
        context.npcs.append(NPCInfo(
            name=npc_data.get("name", npc_id),
            appearance=npc_data.get("appearance", ""),
            role=npc_data.get("role", ""),
            placement=npc_placements.get(npc_id, "")
        ))
    
    return context


def _get_conditional_npcs_at_location(
    location_id: str,
    loc_data: dict,
    npcs_data: dict
) -> list[str]:
    """
    Get list of NPC IDs that have appears_when conditions at this location.
    
    These are the NPCs that need image variants.
    """
    conditional_npcs = []
    location_npcs = loc_data.get("npcs", [])
    
    # Check NPCs explicitly in location
    for npc_id in location_npcs:
        npc_data = npcs_data.get(npc_id, {})
        if npc_data and npc_data.get("appears_when"):
            conditional_npcs.append(npc_id)
    
    # Check NPCs that have this location in their locations list
    for npc_id, npc_data in npcs_data.items():
        if npc_id in location_npcs:
            continue
        npc_location = npc_data.get("location")
        npc_locations = npc_data.get("locations", [])
        if (npc_location == location_id or location_id in npc_locations) and npc_data.get("appears_when"):
            conditional_npcs.append(npc_id)
    
    return conditional_npcs


def _get_unconditional_npcs_at_location(
    location_id: str,
    loc_data: dict,
    npcs_data: dict
) -> list[str]:
    """
    Get list of NPC IDs that do NOT have appears_when conditions at this location.
    
    These NPCs should always appear in all variants.
    """
    unconditional_npcs = []
    location_npcs = loc_data.get("npcs", [])
    
    # Check NPCs explicitly in location
    for npc_id in location_npcs:
        npc_data = npcs_data.get(npc_id, {})
        if npc_data and not npc_data.get("appears_when"):
            unconditional_npcs.append(npc_id)
    
    # Check NPCs that have this location in their locations list
    for npc_id, npc_data in npcs_data.items():
        if npc_id in location_npcs:
            continue
        npc_location = npc_data.get("location")
        npc_locations = npc_data.get("locations", [])
        if (npc_location == location_id or location_id in npc_locations) and not npc_data.get("appears_when"):
            unconditional_npcs.append(npc_id)
    
    return unconditional_npcs


def get_variant_image_filename(location_id: str, npc_ids: list[str]) -> str:
    """
    Generate the filename for a variant image.
    
    Args:
        location_id: Base location ID
        npc_ids: List of NPC IDs visible in this variant (sorted)
    
    Returns:
        Filename like "upper_landing__with__ghost_child.png" or "upper_landing.png" for base
    """
    if not npc_ids:
        return f"{location_id}.png"
    
    sorted_ids = sorted(npc_ids)
    npc_suffix = "_".join(sorted_ids)
    return f"{location_id}__with__{npc_suffix}.png"


def parse_variant_filename(filename: str) -> tuple[str, list[str]]:
    """
    Parse a variant filename to extract location_id and NPC IDs.
    
    Args:
        filename: Filename like "upper_landing__with__ghost_child.png"
    
    Returns:
        Tuple of (location_id, [npc_ids])
    """
    stem = filename.replace(".png", "")
    if "__with__" not in stem:
        return stem, []
    
    parts = stem.split("__with__")
    location_id = parts[0]
    npc_ids = parts[1].split("_") if len(parts) > 1 else []
    return location_id, npc_ids


@dataclass
class ImageVariantManifest:
    """Manifest describing all image variants for a location"""
    location_id: str
    base: str  # Base image filename (no conditional NPCs)
    variants: list[dict]  # List of {"npcs": [...], "image": "filename.png"}
    
    def to_dict(self) -> dict:
        return {
            "location_id": self.location_id,
            "base": self.base,
            "variants": self.variants
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ImageVariantManifest":
        return cls(
            location_id=data["location_id"],
            base=data["base"],
            variants=data.get("variants", [])
        )
    
    def get_image_for_npcs(self, visible_npc_ids: list[str]) -> str:
        """
        Get the appropriate image filename for a set of visible NPCs.
        
        Args:
            visible_npc_ids: List of NPC IDs currently visible
        
        Returns:
            Filename of the matching variant, or base if no match
        """
        # Sort for consistent comparison
        sorted_visible = sorted(visible_npc_ids)
        
        for variant in self.variants:
            variant_npcs = sorted(variant.get("npcs", []))
            if variant_npcs == sorted_visible:
                return variant["image"]
        
        # No exact match - return base image
        return self.base


def save_variant_manifest(manifest: ImageVariantManifest, output_dir: Path) -> None:
    """Save a variant manifest to JSON file."""
    manifest_path = output_dir / f"{manifest.location_id}_variants.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest.to_dict(), f, indent=2)


def load_variant_manifest(location_id: str, images_dir: Path) -> Optional[ImageVariantManifest]:
    """Load a variant manifest from JSON file if it exists."""
    manifest_path = images_dir / f"{location_id}_variants.json"
    if not manifest_path.exists():
        return None
    
    with open(manifest_path, 'r') as f:
        data = json.load(f)
    return ImageVariantManifest.from_dict(data)


async def generate_world_images(
    world_id: str,
    worlds_dir: Path,
    location_ids: Optional[list[str]] = None
) -> dict[str, Optional[str]]:
    """
    Generate images for all (or specified) locations in a world.
    
    Images include visual hints for exits, items, and NPCs present
    at each location to give players indication for interaction.
    
    NOTE: This function generates simple images without variant support.
    For locations with conditional NPCs, use generate_location_variants instead.
    
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
        
        try:
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
        except ImageGenerationError as e:
            print(f"  - Failed: {e.message}")
            results[loc_id] = None
        except Exception as e:
            print(f"  - Unexpected error: {e}")
            results[loc_id] = None
        
        # Small delay between generations to avoid rate limiting
        await asyncio.sleep(0.5)
    
    return results


async def generate_location_variants(
    world_id: str,
    worlds_dir: Path,
    location_id: str
) -> Optional[ImageVariantManifest]:
    """
    Generate all image variants for a location with conditional NPCs.
    
    Creates:
    - Base image (no conditional NPCs, only unconditional ones)
    - One variant for each conditional NPC combination
    - Manifest JSON file mapping conditions to images
    
    For a location with N conditional NPCs, this generates up to 2^N images.
    Currently limited to single-NPC variants for simplicity.
    
    Args:
        world_id: ID of the world
        worlds_dir: Base directory containing worlds
        location_id: ID of the location to generate variants for
    
    Returns:
        ImageVariantManifest describing all generated variants, or None if failed
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
    
    # Load all data
    with open(locations_yaml) as f:
        locations = yaml.safe_load(f) or {}
    
    npcs_data = {}
    if npcs_yaml.exists():
        with open(npcs_yaml) as f:
            npcs_data = yaml.safe_load(f) or {}
    
    items_data = {}
    if items_yaml.exists():
        with open(items_yaml) as f:
            items_data = yaml.safe_load(f) or {}
    
    loc_data = locations.get(location_id)
    if not loc_data:
        raise ValueError(f"Location not found: {location_id}")
    
    loc_name = loc_data.get("name", location_id)
    atmosphere = loc_data.get("atmosphere", "")
    
    # Identify conditional and unconditional NPCs
    conditional_npcs = _get_conditional_npcs_at_location(location_id, loc_data, npcs_data)
    unconditional_npcs = _get_unconditional_npcs_at_location(location_id, loc_data, npcs_data)
    
    print(f"Generating variants for: {loc_name}")
    print(f"  - Unconditional NPCs (always shown): {unconditional_npcs}")
    print(f"  - Conditional NPCs (need variants): {conditional_npcs}")
    
    images_dir.mkdir(parents=True, exist_ok=True)
    
    manifest = ImageVariantManifest(
        location_id=location_id,
        base=get_variant_image_filename(location_id, []),
        variants=[]
    )
    
    # Generate base image (only unconditional NPCs)
    print(f"  Generating base image (no conditional NPCs)...")
    base_context = _build_location_context(
        location_id=location_id,
        loc_data=loc_data,
        locations=locations,
        npcs_data=npcs_data,
        items_data=items_data,
        include_npc_ids=unconditional_npcs
    )
    
    base_filename = get_variant_image_filename(location_id, [])
    base_image_path = images_dir / base_filename
    
    try:
        # Generate base image with full generation (no base image input)
        await _generate_variant_image(
            location_id=location_id,
            location_name=loc_name,
            atmosphere=atmosphere,
            theme=theme,
            tone=tone,
            output_dir=images_dir,
            context=base_context,
            output_filename=base_filename
        )
        print(f"    - Base image generated: {base_filename}")
    except Exception as e:
        print(f"    - Failed to generate base image: {e}")
        return None
    
    # Get NPC placements from location data for building NPCInfo
    npc_placements = loc_data.get("npc_placements", {})
    
    # Generate variants for each conditional NPC using image editing mode
    # This uses the base image as input and adds the NPC to maintain visual consistency
    for npc_id in conditional_npcs:
        print(f"  Generating variant with {npc_id} (using image editing)...")
        
        # Get the NPC data for the conditional NPC we're adding
        npc_data = npcs_data.get(npc_id, {})
        if not npc_data:
            print(f"    - Skipping {npc_id}: NPC data not found")
            continue
        
        # Build NPCInfo for the NPC to add
        npc_to_add = NPCInfo(
            name=npc_data.get("name", npc_id),
            appearance=npc_data.get("appearance", ""),
            role=npc_data.get("role", ""),
            placement=npc_placements.get(npc_id, "")
        )
        
        try:
            variant_filename = get_variant_image_filename(location_id, [npc_id])
            
            # Use image editing mode: pass the base image and specify NPCs to add
            await _generate_variant_image(
                location_id=location_id,
                location_name=loc_name,
                atmosphere=atmosphere,
                theme=theme,
                tone=tone,
                output_dir=images_dir,
                context=base_context,  # Context is for reference, not used in edit mode
                output_filename=variant_filename,
                base_image_path=base_image_path,  # Pass the base image
                npcs_to_add=[npc_to_add]  # Specify which NPC(s) to add
            )
            
            manifest.variants.append({
                "npcs": [npc_id],
                "image": variant_filename
            })
            print(f"    - Variant generated: {variant_filename}")
            
        except Exception as e:
            print(f"    - Failed to generate variant: {e}")
        
        # Delay between generations
        await asyncio.sleep(1.0)
    
    # Save manifest
    save_variant_manifest(manifest, images_dir)
    print(f"  Manifest saved: {location_id}_variants.json")
    
    return manifest


async def _generate_variant_image(
    location_id: str,
    location_name: str,
    atmosphere: str,
    theme: str,
    tone: str,
    output_dir: Path,
    context: LocationContext,
    output_filename: str,
    model_override: Optional[str] = None,
    base_image_path: Optional[Path] = None,
    npcs_to_add: Optional[list[NPCInfo]] = None
) -> str:
    """
    Internal function to generate a variant image with a specific filename.
    
    Supports two modes:
    1. Full generation: Creates a new image from scratch using the full scene prompt
    2. Image editing: Uses a base image and adds NPCs to it (when base_image_path is provided)
    
    Args:
        location_id: Unique ID of the location
        location_name: Display name of the location
        atmosphere: Atmospheric description
        theme: World theme
        tone: World tone
        output_dir: Directory to save the generated image
        context: LocationContext with exits, items, and NPCs for visual hints
        output_filename: Custom filename for the output image
        model_override: Optional model name to use instead of the default
        base_image_path: Optional path to base image for image editing mode
        npcs_to_add: Optional list of NPCs to add via image editing (used with base_image_path)
    
    Returns:
        Path to the generated image
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from google import genai
    from google.genai import types
    
    model_to_use = model_override or IMAGE_MODEL
    
    # Determine if we're in editing mode or full generation mode
    is_edit_mode = base_image_path is not None and npcs_to_add is not None
    
    if is_edit_mode:
        logger.info(f"[ImageGen] Generating variant via image editing: {output_filename}")
    else:
        logger.info(f"[ImageGen] Generating variant: {output_filename}")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    client = genai.Client(api_key=api_key)
    
    # Build prompt and contents based on mode
    if is_edit_mode:
        # Image editing mode: use edit prompt and include base image
        prompt = get_edit_prompt(location_name, npcs_to_add, theme, tone)
        
        # Read the base image and encode it
        with open(base_image_path, 'rb') as f:
            base_image_bytes = f.read()
        
        # Create image part using Part.from_bytes
        image_part = types.Part.from_bytes(data=base_image_bytes, mime_type="image/png")
        
        # Contents: image first, then the edit prompt
        contents = [image_part, prompt]
        logger.info(f"[ImageGen] Using base image: {base_image_path}")
    else:
        # Full generation mode: use standard scene prompt
        prompt = get_image_prompt(location_name, atmosphere, theme, tone, context)
        contents = [prompt]
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    config = types.GenerateContentConfig(
        image_config=types.ImageConfig(aspect_ratio="16:9")
    )
    
    # Retry loop
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=model_to_use,
                    contents=contents,
                    config=config
                ),
                timeout=120.0
            )
            break
        except asyncio.TimeoutError:
            last_error = ImageGenerationError("API timeout", is_retryable=True, status_code=504)
            if attempt < MAX_RETRIES - 1:
                delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
                await asyncio.sleep(delay)
                continue
            raise last_error
        except Exception as api_error:
            error_str = str(api_error)
            is_retryable = any(code in error_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"])
            if is_retryable and attempt < MAX_RETRIES - 1:
                delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
                await asyncio.sleep(delay)
                last_error = api_error
                continue
            raise ImageGenerationError(f"API error: {error_str}", is_retryable=is_retryable, status_code=500)
    else:
        if last_error:
            raise last_error
        raise ImageGenerationError("All retry attempts failed", is_retryable=True, status_code=503)
    
    # Extract and save image (use custom filename)
    image_path = output_dir / output_filename
    
    # Handle GenerateImagesResponse
    if hasattr(response, 'generated_images') and response.generated_images:
        for img in response.generated_images:
            if hasattr(img, 'image') and img.image:
                if hasattr(img.image, 'save'):
                    await asyncio.to_thread(img.image.save, str(image_path))
                else:
                    with open(image_path, 'wb') as f:
                        f.write(img.image.image_bytes)
                _save_prompt_markdown(output_dir, output_filename.replace(".png", ""), location_name, prompt)
                return str(image_path)
    
    # Handle generate_content response
    if hasattr(response, 'parts'):
        for part in response.parts:
            if part.inline_data is not None:
                try:
                    image = part.as_image()
                    await asyncio.to_thread(image.save, str(image_path))
                except Exception:
                    image_data = part.inline_data.data
                    if isinstance(image_data, str):
                        image_data = base64.b64decode(image_data)
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                
                _save_prompt_markdown(output_dir, output_filename.replace(".png", ""), location_name, prompt)
                return str(image_path)
    
    raise ImageGenerationError("No image data in response", is_retryable=False, status_code=500)


def get_location_image_path(
    world_id: str,
    location_id: str,
    worlds_dir: Path,
    visible_npc_ids: Optional[list[str]] = None
) -> Optional[str]:
    """
    Get the path to a location's image, considering NPC variants.
    
    Args:
        world_id: ID of the world
        location_id: ID of the location
        worlds_dir: Base directory containing worlds
        visible_npc_ids: Optional list of NPC IDs currently visible.
                        If provided and variants exist, returns the matching variant.
    
    Returns:
        Path to the image, or None if not found
    """
    images_dir = worlds_dir / world_id / "images"
    
    # Check for variant manifest
    manifest = load_variant_manifest(location_id, images_dir)
    
    if manifest and visible_npc_ids is not None:
        # Get the appropriate variant image
        image_filename = manifest.get_image_for_npcs(visible_npc_ids)
        image_path = images_dir / image_filename
        if image_path.exists():
            return str(image_path)
    
    # Fallback to base image (legacy path)
    image_path = images_dir / f"{location_id}.png"
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
