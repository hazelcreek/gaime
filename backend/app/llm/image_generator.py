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
from app.llm.style_loader import (
    StyleBlock,
    resolve_style,
    build_mpa_prompt,
    build_mpa_edit_prompt,
    get_world_context,
    DEFAULT_PRESET
)

load_dotenv()


# Image generation model - Gemini with image output capability
# See: https://ai.google.dev/gemini-api/docs/image-generation
# We exclusively use Gemini 3 Pro Image Preview for high quality 16:9 4K images
IMAGE_MODEL = "gemini-3-pro-image-preview"

# Retry configuration for transient errors (including IMAGE_OTHER soft rejections)
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 3.0  # seconds
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
            # Clean up the appearance text without truncation
            appearance_clean = " ".join(npc.appearance.split())
            npc_descriptions.append(
                f"- {npc.name} ({npc.role}){placement_part}: {appearance_clean}"
            )
        elif npc.placement:
            # Has placement but no detailed appearance
            npc_descriptions.append(
                f"- {npc.name}, {npc.role}, {npc.placement}"
            )
        else:
            npc_descriptions.append(
                f"- {npc.name}, {npc.role}"
            )
    
    if npc_descriptions:
        # Use separate paragraphs per character (blank line between each)
        return "Characters visible in the scene:\n\n" + "\n\n".join(npc_descriptions)
    return ""


def get_edit_prompt(
    location_name: str,
    npcs: list[NPCInfo],
    theme: str,
    tone: str,
    style_block: Optional[StyleBlock] = None
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
        style_block: Optional StyleBlock for MPA-based prompt generation
    
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
            # Preserve full appearance while normalizing whitespace for clarity
            appearance_clean = " ".join(npc.appearance.split())
            npc_descriptions.append(
                f"- {npc.name} ({npc.role}){placement_part}: {appearance_clean}"
            )
        else:
            npc_descriptions.append(
                f"- {npc.name}, {npc.role},{placement_part}"
            )
    
    npcs_text = "\n".join(npc_descriptions)
    
    # Use MPA edit template if style_block is provided
    if style_block is not None:
        # Get placement from first NPC (primary)
        first_npc = npcs[0]
        npc_placement = first_npc.placement or "positioned naturally in the scene"
        
        return build_mpa_edit_prompt(
            npc_description=npcs_text,
            npc_placement=npc_placement,
            style_block=style_block
        )
    
    # Fallback to legacy template
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
    context: Optional[LocationContext] = None,
    style_block: Optional[StyleBlock] = None
) -> str:
    """
    Generate a prompt for creating a scene image.
    
    Args:
        location_name: Name of the location
        atmosphere: Atmospheric description from location YAML
        theme: World theme (e.g., "Victorian gothic horror")
        tone: World tone (e.g., "atmospheric, mysterious")
        context: Optional LocationContext with exits, items, and NPCs
        style_block: Optional StyleBlock for MPA-based prompt generation
    
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
    
    # Use MPA template if style_block is provided
    if style_block is not None:
        world_context = get_world_context(theme, tone)
        return build_mpa_prompt(
            location_name=location_name,
            atmosphere=atmosphere_clean,
            world_context=world_context,
            style_block=style_block,
            interactive_section=interactive_section
        )
    
    # Fallback to legacy template
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
    prompt_dir = output_dir / "promptlogs"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{location_id}_prompt.md"
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
    model_override: Optional[str] = None,
    style_block: Optional[StyleBlock] = None
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
        style_block: Optional StyleBlock for MPA-based prompt generation
    
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
    
    # Create the prompt with context and optional style
    prompt = get_image_prompt(location_name, atmosphere, theme, tone, context, style_block)
    logger.info(f"[ImageGen] Prompt created (length: {len(prompt)} chars)")
    if style_block:
        logger.info(f"[ImageGen] Using style: {style_block.name or 'custom'}")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save prompt to logs immediately (before API call) for debugging
    _save_prompt_markdown(output_dir, location_id, location_name, prompt)
    logger.info(f"[ImageGen] Prompt saved to promptlogs/{location_id}_prompt.md")
    
    try:
        logger.info(f"[ImageGen] Calling {model_to_use}...")
        
        # Configure for Gemini 3 Pro Image Preview via generate_content
        # Matching AI Studio settings: temperature=1, explicitly request image output
        config = types.GenerateContentConfig(
            temperature=1.0,
            response_modalities=["IMAGE"],  # Explicitly request image output
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT",
                    threshold="BLOCK_ONLY_HIGH"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH",
                    threshold="BLOCK_ONLY_HIGH"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    threshold="BLOCK_ONLY_HIGH"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT",
                    threshold="BLOCK_ONLY_HIGH"
                ),
            ]
        )
        
        # Retry loop for transient errors AND soft rejections (IMAGE_OTHER)
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=model_to_use,
                        contents=prompt,  # Pass as string, not list (matching AI Studio)
                        config=config
                    ),
                    timeout=120.0  # 2 minute timeout
                )
                
                # Log response details for debugging
                logger.info(f"[ImageGen] Got response from API (attempt {attempt + 1}/{MAX_RETRIES})")
                logger.info(f"[ImageGen] Response type: {type(response).__name__}")
                
                # Try to extract image from response
                image_path = output_dir / f"{location_id}.png"
                
                # Handle GenerateImagesResponse
                if hasattr(response, 'generated_images') and response.generated_images:
                    for img in response.generated_images:
                        if hasattr(img, 'image') and img.image:
                            if hasattr(img.image, 'save'):
                                await asyncio.to_thread(img.image.save, str(image_path))
                            else:
                                with open(image_path, 'wb') as f:
                                    f.write(img.image.image_bytes)
                            logger.info(f"[ImageGen] Saved generated image to {image_path}")
                            return str(image_path)
                
                # Extract image data from response parts (generate_content style)
                if hasattr(response, 'parts') and response.parts:
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
                            logger.info(f"[ImageGen] Saved image to {image_path}")
                            return str(image_path)
                
                # No image found - check finish reason for retryable conditions
                finish_reason = None
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    finish_reason = getattr(candidate, 'finish_reason', None)
                    logger.warning(f"[ImageGen] No image data, finish_reason={finish_reason} (attempt {attempt + 1}/{MAX_RETRIES})")
                
                # IMAGE_OTHER is a soft rejection that may succeed on retry
                finish_reason_str = str(finish_reason) if finish_reason else ""
                if "IMAGE_OTHER" in finish_reason_str or "OTHER" in finish_reason_str:
                    if attempt < MAX_RETRIES - 1:
                        delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
                        logger.info(f"[ImageGen] IMAGE_OTHER - retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                        continue
                
                # Check for explicit blocking
                if hasattr(response, 'prompt_feedback'):
                    feedback = response.prompt_feedback
                    if hasattr(feedback, 'block_reason') and feedback.block_reason:
                        raise ImageGenerationError(
                            f"Prompt blocked: {feedback.block_reason}",
                            is_retryable=False,
                            status_code=400
                        )
                
                # No image and not retryable
                raise ImageGenerationError(
                    f"No image data in API response (finish_reason={finish_reason}). The model may have rejected the prompt.",
                    is_retryable=False,
                    status_code=500
                )
                
            except asyncio.TimeoutError:
                logger.error(f"[ImageGen] API call timed out (attempt {attempt + 1}/{MAX_RETRIES})")
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
            except ImageGenerationError:
                raise  # Don't retry our own errors
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
        
        # All retries exhausted
        if last_error:
            raise last_error
        raise ImageGenerationError("All retry attempts failed", is_retryable=True, status_code=503)
        
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


def _npc_can_be_at_location(npc_id: str, npc_data: dict, location_id: str) -> bool:
    """
    Check if an NPC can potentially be at a location (considering location_changes).
    
    An NPC can be at a location if:
    - Their starting `location` matches
    - The location is in their `locations` list
    - A `location_changes` entry has `move_to` pointing to this location
    """
    # Check starting location
    if npc_data.get("location") == location_id:
        return True
    
    # Check locations list
    if location_id in npc_data.get("locations", []):
        return True
    
    # Check location_changes destinations
    for change in npc_data.get("location_changes", []):
        if change.get("move_to") == location_id:
            return True
    
    return False


def _npc_is_conditional_at_location(npc_data: dict, location_id: str) -> bool:
    """
    Check if an NPC is conditional (needs image variants) at a specific location.
    
    An NPC is conditional at a location if:
    1. They have `appears_when` conditions (standard conditional appearance)
    2. They have `location_changes` that involve this location:
       - At their starting location: only if a change moves them AWAY (to a different location)
       - At a move_to destination: only if they're arriving FROM somewhere else
    """
    # Standard conditional: has appears_when
    if npc_data.get("appears_when"):
        return True
    
    # Dynamic location: has location_changes
    location_changes = npc_data.get("location_changes", [])
    if location_changes:
        starting_location = npc_data.get("location")
        
        # Check if any change moves them AWAY from their starting location
        # (i.e., move_to is a DIFFERENT location than starting_location)
        if starting_location == location_id:
            for change in location_changes:
                move_to = change.get("move_to")
                if move_to and move_to != starting_location:
                    # This change moves them away from here
                    return True
        
        # Check if this location is a move_to destination FROM somewhere else
        for change in location_changes:
            move_to = change.get("move_to")
            if move_to == location_id and starting_location != location_id:
                # They arrive here from their starting location
                return True
    
    return False


def _npc_default_present_at_location(npc_data: dict, location_id: str) -> bool:
    """
    Check if an NPC is present by DEFAULT at a location (before any conditions apply).
    
    This is used to determine the correct image variant strategy:
    - If default present: base image HAS the NPC, variant is WITHOUT
    - If default absent: base image is WITHOUT the NPC, variant is WITH
    
    An NPC is present by default if:
    - Their starting `location` matches this location (for location_changes NPCs)
    - The location is in their `locations` list (multi-location NPCs)
    - They DON'T have `appears_when` (which means absent by default)
    """
    # If they have appears_when, they're absent by default
    if npc_data.get("appears_when"):
        return False
    
    # Check starting location (for location_changes NPCs)
    if npc_data.get("location") == location_id:
        return True
    
    # Check locations list (multi-location NPCs without conditions)
    if location_id in npc_data.get("locations", []):
        return True
    
    # Destinations in location_changes are "arrive" locations (absent by default)
    return False


def _get_conditional_npcs_at_location(
    location_id: str,
    loc_data: dict,
    npcs_data: dict
) -> list[str]:
    """
    Get list of NPC IDs that are conditional at this location.
    
    These are the NPCs that need image variants. An NPC is conditional if:
    1. They have `appears_when` conditions
    2. They have `location_changes` that involve this location
    """
    conditional_npcs = []
    location_npcs = loc_data.get("npcs", [])
    
    # Check NPCs explicitly in location
    for npc_id in location_npcs:
        npc_data = npcs_data.get(npc_id, {})
        if npc_data and _npc_is_conditional_at_location(npc_data, location_id):
            conditional_npcs.append(npc_id)
    
    # Check all NPCs that could potentially be at this location
    for npc_id, npc_data in npcs_data.items():
        if npc_id in location_npcs:
            continue
        if npc_id in conditional_npcs:
            continue
        
        # Check if this NPC can be at this location
        if _npc_can_be_at_location(npc_id, npc_data, location_id):
            if _npc_is_conditional_at_location(npc_data, location_id):
                conditional_npcs.append(npc_id)
    
    return conditional_npcs


def _get_unconditional_npcs_at_location(
    location_id: str,
    loc_data: dict,
    npcs_data: dict
) -> list[str]:
    """
    Get list of NPC IDs that are NOT conditional at this location.
    
    These NPCs should always appear in all variants. An NPC is unconditional if:
    - They are at this location (via `location`, `locations`, or listed in loc_data)
    - They do NOT have `appears_when` conditions
    - They do NOT have `location_changes` involving this location
    """
    unconditional_npcs = []
    location_npcs = loc_data.get("npcs", [])
    
    # Check NPCs explicitly in location
    for npc_id in location_npcs:
        npc_data = npcs_data.get(npc_id, {})
        if npc_data and not _npc_is_conditional_at_location(npc_data, location_id):
            unconditional_npcs.append(npc_id)
    
    # Check all NPCs that could be at this location
    for npc_id, npc_data in npcs_data.items():
        if npc_id in location_npcs:
            continue
        if npc_id in unconditional_npcs:
            continue
        
        # Only include if they can be here AND they're not conditional
        if _npc_can_be_at_location(npc_id, npc_data, location_id):
            if not _npc_is_conditional_at_location(npc_data, location_id):
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
    """Manifest describing all image variants for a location.
    
    Variant format: {"npcs": [...], "image": "...", "default": bool}
    - npcs: List of NPC IDs shown in this variant
    - image: Filename of the variant image
    - default: If True, this variant should be shown when the NPC is present by default
               (e.g., Picard on the bridge before he moves to the ready room)
    
    Base image always has NO conditional NPCs (only unconditional ones).
    """
    location_id: str
    base: str  # Base image filename (no conditional NPCs)
    variants: list[dict]  # List of variant descriptors
    
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
            visible_npc_ids: List of NPC IDs currently visible at this location
        
        Returns:
            Filename of the matching variant, or base if no match
        """
        visible_set = set(visible_npc_ids)
        
        for variant in self.variants:
            variant_npcs = set(variant.get("npcs", []))
            # If all NPCs in this variant are visible, use this variant
            if variant_npcs and variant_npcs.issubset(visible_set):
                return variant["image"]
        
        # No variant match - return base image
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
    style_config = None
    
    if world_yaml.exists():
        with open(world_yaml) as f:
            world_data = yaml.safe_load(f) or {}
            theme = world_data.get("theme", theme)
            tone = world_data.get("tone", tone)
            # Load style configuration (can be preset name, dict with preset+overrides, or full style_block)
            style_config = world_data.get("style") or world_data.get("style_block")
    
    # Resolve style configuration into a StyleBlock
    style_block = resolve_style(style_config)
    print(f"Using style: {style_block.name or DEFAULT_PRESET}")
    
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
                context=context,
                style_block=style_block
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
    
    Always generates:
    - Base image WITHOUT any conditional NPCs (only unconditional ones)
    - "With" variants for each conditional NPC (added via image editing)
    
    The manifest tracks which NPCs are "default present" so the runtime knows
    which image to show initially:
    - For "present by default" NPCs: show the "with" variant initially
    - For "absent by default" NPCs: show the base image initially
    
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
    style_config = None
    
    if world_yaml.exists():
        with open(world_yaml) as f:
            world_data = yaml.safe_load(f) or {}
            theme = world_data.get("theme", theme)
            tone = world_data.get("tone", tone)
            style_config = world_data.get("style") or world_data.get("style_block")
    
    # Resolve style configuration
    style_block = resolve_style(style_config)
    
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
    
    # Determine which conditional NPCs are present by default (for manifest metadata)
    default_present_npcs = []
    for npc_id in conditional_npcs:
        npc_data = npcs_data.get(npc_id, {})
        if npc_data and _npc_default_present_at_location(npc_data, location_id):
            default_present_npcs.append(npc_id)
    
    print(f"Generating variants for: {loc_name}")
    print(f"  - Unconditional NPCs (always shown): {unconditional_npcs}")
    print(f"  - Conditional NPCs (need variants): {conditional_npcs}")
    print(f"  - Default present (show 'with' variant initially): {default_present_npcs}")
    
    images_dir.mkdir(parents=True, exist_ok=True)
    
    manifest = ImageVariantManifest(
        location_id=location_id,
        base=get_variant_image_filename(location_id, []),
        variants=[]
    )
    
    # Base image: only unconditional NPCs (no conditional NPCs)
    print(f"  Generating base image (NPCs: {unconditional_npcs or 'none'})...")
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
        await _generate_variant_image(
            location_id=location_id,
            location_name=loc_name,
            atmosphere=atmosphere,
            theme=theme,
            tone=tone,
            output_dir=images_dir,
            context=base_context,
            output_filename=base_filename,
            style_block=style_block
        )
        print(f"    - Base image generated: {base_filename}")
    except Exception as e:
        print(f"    - Failed to generate base image: {e}")
        return None
    
    # Get NPC placements from location data
    npc_placements = loc_data.get("npc_placements", {})
    
    # Generate "with" variants for ALL conditional NPCs using image editing
    for npc_id in conditional_npcs:
        print(f"  Generating variant with {npc_id} (using image editing)...")
        
        npc_data = npcs_data.get(npc_id, {})
        if not npc_data:
            print(f"    - Skipping {npc_id}: NPC data not found")
            continue
        
        npc_to_add = NPCInfo(
            name=npc_data.get("name", npc_id),
            appearance=npc_data.get("appearance", ""),
            role=npc_data.get("role", ""),
            placement=npc_placements.get(npc_id, "")
        )
        
        variant_filename = get_variant_image_filename(location_id, [npc_id])
        variant_generated = False
        
        # Try image editing first
        try:
            await _generate_variant_image(
                location_id=location_id,
                location_name=loc_name,
                atmosphere=atmosphere,
                theme=theme,
                tone=tone,
                output_dir=images_dir,
                context=base_context,
                output_filename=variant_filename,
                base_image_path=base_image_path,
                npcs_to_add=[npc_to_add],
                style_block=style_block
            )
            variant_generated = True
            print(f"    - Variant generated via image editing: {variant_filename}")
            
        except Exception as e:
            print(f"    - Image editing failed: {e}")
            print(f"    - Falling back to full image generation with NPC...")
            
            # Fallback: generate full image with NPC included (not editing mode)
            try:
                # Create context that includes both unconditional NPCs AND this conditional NPC
                variant_context = _build_location_context(
                    location_id=location_id,
                    loc_data=loc_data,
                    locations=locations,
                    npcs_data=npcs_data,
                    items_data=items_data,
                    include_npc_ids=unconditional_npcs + [npc_id]
                )
                
                await _generate_variant_image(
                    location_id=location_id,
                    location_name=loc_name,
                    atmosphere=atmosphere,
                    theme=theme,
                    tone=tone,
                    output_dir=images_dir,
                    context=variant_context,
                    output_filename=variant_filename,
                    style_block=style_block
                    # No base_image_path or npcs_to_add = full generation mode
                )
                variant_generated = True
                print(f"    - Variant generated via full regeneration: {variant_filename}")
                
            except Exception as e2:
                print(f"    - Full regeneration also failed: {e2}")
        
        if variant_generated:
            # Track whether this NPC is present by default
            is_default = npc_id in default_present_npcs
            
            manifest.variants.append({
                "npcs": [npc_id],
                "image": variant_filename,
                "default": is_default  # True = show this variant initially
            })
            print(f"    - Manifest updated (default={is_default})")
        
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
    npcs_to_add: Optional[list[NPCInfo]] = None,
    style_block: Optional[StyleBlock] = None
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
        style_block: Optional StyleBlock for MPA-based prompt generation
    
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
        prompt = get_edit_prompt(location_name, npcs_to_add, theme, tone, style_block)
        
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
        prompt = get_image_prompt(location_name, atmosphere, theme, tone, context, style_block)
        contents = prompt  # Pass as string for text-only generation
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save prompt to logs immediately (before API call) for debugging
    prompt_log_id = output_filename.replace(".png", "")
    _save_prompt_markdown(output_dir, prompt_log_id, location_name, prompt)
    logger.info(f"[ImageGen] Prompt saved to promptlogs/{prompt_log_id}_prompt.md")
    
    # Matching AI Studio settings: temperature=1, explicitly request image output
    config = types.GenerateContentConfig(
        temperature=1.0,
        response_modalities=["IMAGE"],  # Explicitly request image output
        safety_settings=[
            types.SafetySetting(
                category="HARM_CATEGORY_HARASSMENT",
                threshold="BLOCK_ONLY_HIGH"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_HATE_SPEECH",
                threshold="BLOCK_ONLY_HIGH"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                threshold="BLOCK_ONLY_HIGH"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT",
                threshold="BLOCK_ONLY_HIGH"
            ),
        ]
    )
    
    # Retry loop with IMAGE_OTHER handling (soft rejections that may succeed on retry)
    last_error = None
    image_path = output_dir / output_filename
    
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
            
            logger.info(f"[ImageGen] Got response (attempt {attempt + 1}/{MAX_RETRIES})")
            
            # Handle GenerateImagesResponse
            if hasattr(response, 'generated_images') and response.generated_images:
                for img in response.generated_images:
                    if hasattr(img, 'image') and img.image:
                        if hasattr(img.image, 'save'):
                            await asyncio.to_thread(img.image.save, str(image_path))
                        else:
                            with open(image_path, 'wb') as f:
                                f.write(img.image.image_bytes)
                        return str(image_path)
            
            # Handle generate_content response
            if hasattr(response, 'parts') and response.parts:
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
                        
                        return str(image_path)
                
                # Log what we got instead of an image (for debugging)
                text_parts = []
                for part in response.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text[:200])  # First 200 chars
                if text_parts:
                    logger.warning(f"[ImageGen] Model returned text instead of image: {text_parts}")
            
            # No image found - check finish reason for retryable conditions
            finish_reason = None
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, 'finish_reason', None)
                logger.warning(f"[ImageGen] No image data, finish_reason={finish_reason} (attempt {attempt + 1}/{MAX_RETRIES})")
            
            # IMAGE_OTHER is a soft rejection that may succeed on retry
            finish_reason_str = str(finish_reason) if finish_reason else ""
            if "IMAGE_OTHER" in finish_reason_str or "OTHER" in finish_reason_str:
                if attempt < MAX_RETRIES - 1:
                    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
                    logger.info(f"[ImageGen] IMAGE_OTHER - retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    continue
            
            # Check for explicit blocking
            if hasattr(response, 'prompt_feedback'):
                feedback = response.prompt_feedback
                if hasattr(feedback, 'block_reason') and feedback.block_reason:
                    raise ImageGenerationError(
                        f"Prompt blocked: {feedback.block_reason}",
                        is_retryable=False,
                        status_code=400
                    )
            
            # No image and not retryable
            raise ImageGenerationError(
                f"No image data in response (finish_reason={finish_reason}). "
                "The model may not support image editing for this content.",
                is_retryable=False,
                status_code=500
            )
            
        except asyncio.TimeoutError:
            last_error = ImageGenerationError("API timeout", is_retryable=True, status_code=504)
            if attempt < MAX_RETRIES - 1:
                delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
                logger.info(f"[ImageGen] Timeout - retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
                continue
            raise last_error
        except ImageGenerationError:
            raise  # Don't retry our own errors
        except Exception as api_error:
            error_str = str(api_error)
            is_retryable = any(code in error_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"])
            if is_retryable and attempt < MAX_RETRIES - 1:
                delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
                logger.info(f"[ImageGen] Retryable error - retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
                last_error = api_error
                continue
            raise ImageGenerationError(f"API error: {error_str}", is_retryable=is_retryable, status_code=500)
    
    # All retries exhausted
    if last_error:
        raise last_error
    raise ImageGenerationError("All retry attempts failed", is_retryable=True, status_code=503)


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
