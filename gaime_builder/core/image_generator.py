"""
Image Generator - Uses Google Gemini for creating scene images.

Copied and adapted from backend/app/llm/image_generator.py for TUI independence.
Supports variant-based images for conditional NPCs.
"""

import os
import base64
import asyncio
import random
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

import yaml
from dotenv import load_dotenv

from gaime_builder.core.prompt_loader import get_loader
from gaime_builder.core.style_loader import (
    StyleBlock,
    resolve_style,
    build_mpa_prompt,
    build_mpa_edit_prompt,
    get_world_context,
    DEFAULT_PRESET
)
from gaime_builder.core.tasks import ImageHashTracker

load_dotenv()

# Image generation model
IMAGE_MODEL = "gemini-3-pro-image-preview"

# Retry configuration
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 3.0
MAX_RETRY_DELAY = 30.0


class ImageGenerationError(Exception):
    """Custom exception for image generation failures."""
    def __init__(self, message: str, is_retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.is_retryable = is_retryable


@dataclass
class ExitInfo:
    """Information about an exit for visual representation (V3).

    Attributes:
        direction: Cardinal direction or named exit (e.g., "north", "secret")
        destination_name: Display name of the destination location (for internal use)
        scene_description: Authored visual description of the exit
        destination_known: Whether to include destination hint in prompt
        destination_visual_hint: Visual description of destination (for image prompt)
        hidden: Whether exit is hidden at build time (not rendered if true)
        is_secret: Legacy flag for subtle environmental hints
        requires_key: Whether exit is locked (adds lock visual)
    """
    direction: str
    destination_name: str
    scene_description: str = ""  # V3: Authored visual description
    destination_known: bool = True  # V3: Whether to hint at destination
    destination_visual_hint: str = ""  # V3: Visual description of destination
    hidden: bool = False  # V3: For filtering (not rendered if true)
    is_secret: bool = False  # Legacy: subtle hints for secret passages
    requires_key: bool = False


@dataclass
class ItemInfo:
    """Information about an item for visual representation (V3).

    Attributes:
        name: Display name of the item
        description: Scene description from Item definition
        placement: Placement description from ItemPlacement
        hidden: Whether item is hidden at build time (from ItemPlacement.hidden)
        is_artifact: Whether item is a significant artifact
    """
    name: str
    description: str = ""  # From Item.scene_description
    placement: str = ""  # From ItemPlacement.placement
    hidden: bool = False  # V3: From ItemPlacement.hidden
    is_artifact: bool = False


@dataclass
class NPCInfo:
    """Information about an NPC for visual representation."""
    name: str
    appearance: str = ""
    role: str = ""
    placement: str = ""


@dataclass
class DetailInfo:
    """Information about a scene detail for visual representation.

    Details are interactive/scenic elements defined in locations.yaml
    that aren't items or NPCs, such as furniture, decorations, or
    environmental features.

    Attributes:
        name: Display name of the detail
        scene_description: How the detail appears in the scene
    """
    name: str
    scene_description: str = ""


@dataclass
class LocationContext:
    """Full context for a location to generate appropriate imagery."""
    exits: list[ExitInfo] = field(default_factory=list)
    items: list[ItemInfo] = field(default_factory=list)
    npcs: list[NPCInfo] = field(default_factory=list)
    details: list[DetailInfo] = field(default_factory=list)


@dataclass
class ImageVariantManifest:
    """Manifest describing all image variants for a location."""
    location_id: str
    base: str
    variants: list[dict]

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


def _is_entity_visible_at_build_time(hidden: bool) -> bool:
    """Check if entity is visible at world-building time.

    At build time, we only check the hidden flag - find_condition
    is runtime state that we ignore. This is used to filter out
    entities that should not appear in the base image.

    Args:
        hidden: Whether the entity is marked as hidden in the schema

    Returns:
        True if the entity should be included in image generation
    """
    return not hidden


def _build_exits_description(exits: list[ExitInfo]) -> str:
    """Build a description of exits for the image prompt (V3).

    V3: Uses authored scene_description instead of generic direction mappings.
    Adds destination hints when destination_known is true.

    Args:
        exits: List of ExitInfo objects (already filtered for visibility)

    Returns:
        Text description of exits for the image prompt
    """
    if not exits:
        return ""

    # Minimal directional context hints (used as suffix, not primary description)
    direction_hints = {
        "north": "ahead",
        "south": "behind",
        "east": "to the right",
        "west": "to the left",
        "up": "above",
        "down": "below",
        "back": "behind",
    }

    # Secret hint templates for hidden exits that might show subtle clues
    secret_hint_templates = {
        "horizontal": "a faint draft or subtle irregularity in the wall",
        "up": "shadows on the ceiling that hint at an unseen passage",
        "down": "a barely visible crack in the floor or subtle depression",
    }

    exit_descriptions = []
    secret_hints = []

    for exit in exits:
        direction = exit.direction.lower()

        # Handle hidden exits - only show subtle hints if marked as secret
        if exit.hidden:
            if exit.is_secret:
                if direction in ["north", "south", "east", "west"]:
                    secret_hints.append(secret_hint_templates["horizontal"])
                elif direction == "up":
                    secret_hints.append(secret_hint_templates["up"])
                elif direction == "down":
                    secret_hints.append(secret_hint_templates["down"])
            # Skip hidden non-secret exits entirely
            continue

        # Build description from authored content or fallback
        if exit.scene_description:
            # V3: Use authored description as primary
            desc = exit.scene_description
        else:
            # Minimal fallback for missing descriptions
            hint = direction_hints.get(direction, direction)
            desc = f"a passage {hint}"

        # Add lock visual if required
        if exit.requires_key:
            desc = f"{desc}, secured with a heavy lock"

        # Add destination visual hint for open passages (not destination name to avoid wrong signage)
        if exit.destination_visual_hint:
            # Include glimpse of what's through the passage
            desc = f"{desc}. Through it: {exit.destination_visual_hint}"

        # Get directional context for bullet prefix
        dir_hint = direction_hints.get(direction, "")

        # Build bullet with directional prefix
        if dir_hint:
            exit_descriptions.append(f"- Visible pathway {dir_hint}: {desc}")
        else:
            exit_descriptions.append(f"- Visible pathway: {desc}")

    parts = []
    if exit_descriptions:
        parts.extend(exit_descriptions)
    if secret_hints:
        for hint in secret_hints:
            parts.append(f"- Subtle detail: {hint}")

    return "\n".join(parts)


def _build_items_description(items: list[ItemInfo]) -> str:
    """Build a description of items for the image prompt (V3).

    V3: Hidden items should already be filtered out in _build_location_context.
    This function only receives visible items.

    Args:
        items: List of ItemInfo objects (already filtered for visibility)

    Returns:
        Text description of items for the image prompt
    """
    if not items:
        return ""

    visible_items = []
    artifact_items = []

    for item in items:
        # Skip any hidden items that made it through (defensive)
        if item.hidden:
            continue

        placement_desc = item.placement if item.placement else "placed naturally within the scene"

        if item.is_artifact:
            if item.placement:
                artifact_items.append(f"- Notable object: {item.name} {item.placement}")
            else:
                artifact_items.append(f"- Notable object: {item.name} that draws the eye")
        else:
            visible_items.append(f"- {item.name} {placement_desc}")

    parts = []
    parts.extend(visible_items)
    parts.extend(artifact_items)

    return "\n".join(parts)


def _build_npcs_description(npcs: list[NPCInfo]) -> str:
    """Build a description of NPCs for the image prompt."""
    if not npcs:
        return ""

    npc_descriptions = []

    for npc in npcs:
        placement_part = f", {npc.placement}" if npc.placement else ""

        if npc.appearance:
            appearance_clean = " ".join(npc.appearance.split())
            npc_descriptions.append(
                f"- {npc.name} ({npc.role}){placement_part}: {appearance_clean}"
            )
        elif npc.placement:
            npc_descriptions.append(f"- {npc.name}, {npc.role}, {npc.placement}")
        else:
            npc_descriptions.append(f"- {npc.name}, {npc.role}")

    return "\n".join(npc_descriptions)


def _build_details_description(details: list[DetailInfo]) -> str:
    """Build a description of scene details for the image prompt.

    Details are interactive/scenic elements like furniture, decorations,
    or environmental features that should appear in the generated image.

    Args:
        details: List of DetailInfo objects

    Returns:
        Text description of details for the image prompt
    """
    if not details:
        return ""

    detail_descriptions = []
    for detail in details:
        if detail.scene_description:
            # Clean up multi-line descriptions
            desc_clean = " ".join(detail.scene_description.split())
            detail_descriptions.append(f"- {detail.name}: {desc_clean}")
        else:
            detail_descriptions.append(f"- {detail.name}")

    return "\n".join(detail_descriptions)


def get_image_prompt(
    location_name: str,
    atmosphere: str,
    theme: str,
    tone: str,
    context: Optional[LocationContext] = None,
    style_block: Optional[StyleBlock] = None,
    visual_description: str = "",
    visual_setting: str = ""
) -> str:
    """Generate a prompt for creating a scene image.

    Args:
        location_name: Display name of the location
        atmosphere: Narrative atmosphere (fallback if visual_description not provided)
        theme: World theme
        tone: World tone
        context: Location context with exits, items, NPCs, details
        style_block: Visual style configuration
        visual_description: Pure visual scene description (3-5 sentences)
        visual_setting: World-level visual language (5-10 sentences)
    """
    atmosphere_clean = atmosphere.strip().replace('\n', ' ')

    exits_desc = ""
    items_desc = ""
    npcs_desc = ""
    details_desc = ""

    if context:
        exits_desc = _build_exits_description(context.exits)
        items_desc = _build_items_description(context.items)
        npcs_desc = _build_npcs_description(context.npcs)
        details_desc = _build_details_description(context.details)

    interactive_elements = []
    if details_desc:
        interactive_elements.append(details_desc)
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

    if style_block is not None:
        world_context = get_world_context(theme, tone)
        return build_mpa_prompt(
            location_name=location_name,
            atmosphere=atmosphere_clean,
            world_context=world_context,
            style_block=style_block,
            interactive_section=interactive_section,
            visual_description=visual_description,
            visual_setting=visual_setting
        )

    # Fallback to legacy template
    image_template = get_loader().get_prompt("image_generator", "image_prompt_template.txt")
    return image_template.format(
        location_name=location_name,
        theme=theme,
        tone=tone,
        atmosphere=atmosphere_clean,
        interactive_section=interactive_section
    )


def get_edit_prompt(
    location_name: str,
    npcs: list[NPCInfo],
    theme: str,
    tone: str,
    style_block: Optional[StyleBlock] = None
) -> str:
    """Generate a prompt for adding NPCs to an existing image."""
    if not npcs:
        return "Keep this image exactly as it is."

    npc_descriptions = []
    for npc in npcs:
        placement_part = f" {npc.placement}" if npc.placement else " positioned naturally in the scene"

        if npc.appearance:
            appearance_clean = " ".join(npc.appearance.split())
            npc_descriptions.append(
                f"- {npc.name} ({npc.role}){placement_part}: {appearance_clean}"
            )
        else:
            npc_descriptions.append(f"- {npc.name}, {npc.role},{placement_part}")

    npcs_text = "\n".join(npc_descriptions)

    if style_block is not None:
        first_npc = npcs[0]
        npc_placement = first_npc.placement or "positioned naturally in the scene"

        return build_mpa_edit_prompt(
            npc_description=npcs_text,
            npc_placement=npc_placement,
            style_block=style_block
        )

    template = get_loader().get_prompt("image_generator", "edit_prompt_template.txt")
    return template.format(
        location_name=location_name,
        theme=theme,
        tone=tone,
        npcs_text=npcs_text
    )


def _save_prompt_markdown(output_dir: Path, location_id: str, location_name: str, prompt: str) -> None:
    """Save the image generation prompt as a markdown file for debugging."""
    prompt_dir = output_dir / "promptlogs"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{location_id}_prompt.md"
    prompt_content = f"# Image Prompt: {location_name}\n\n{prompt}"
    with open(prompt_path, 'w') as f:
        f.write(prompt_content)


def get_variant_image_filename(location_id: str, npc_ids: list[str]) -> str:
    """Generate the filename for a variant image."""
    if not npc_ids:
        return f"{location_id}.png"

    sorted_ids = sorted(npc_ids)
    npc_suffix = "_".join(sorted_ids)
    return f"{location_id}__with__{npc_suffix}.png"


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


class ImageGenerator:
    """Generate location images for game worlds."""

    def __init__(self, worlds_dir: Path):
        self.worlds_dir = worlds_dir
        self.hash_tracker = ImageHashTracker(worlds_dir)

    async def generate_location_image(
        self,
        location_id: str,
        location_name: str,
        atmosphere: str,
        theme: str,
        tone: str,
        output_dir: Path,
        context: Optional[LocationContext] = None,
        style_block: Optional[StyleBlock] = None,
        visual_description: str = "",
        visual_setting: str = ""
    ) -> Optional[str]:
        """Generate an image for a single location."""
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        client = genai.Client(api_key=api_key)
        prompt = get_image_prompt(
            location_name, atmosphere, theme, tone, context, style_block,
            visual_description=visual_description,
            visual_setting=visual_setting
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        _save_prompt_markdown(output_dir, location_id, location_name, prompt)

        config = types.GenerateContentConfig(
            temperature=1.0,
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9"),
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
            ]
        )

        image_path = output_dir / f"{location_id}.png"

        for attempt in range(MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=IMAGE_MODEL,
                        contents=prompt,
                        config=config
                    ),
                    timeout=120.0
                )

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

                # Check finish reason for retry
                finish_reason = None
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    finish_reason = getattr(candidate, 'finish_reason', None)

                finish_reason_str = str(finish_reason) if finish_reason else ""
                if "IMAGE_OTHER" in finish_reason_str or "OTHER" in finish_reason_str:
                    if attempt < MAX_RETRIES - 1:
                        delay = min(INITIAL_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_DELAY)
                        await asyncio.sleep(delay)
                        continue

                raise ImageGenerationError(f"No image data in response (finish_reason={finish_reason})")

            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES - 1:
                    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                    await asyncio.sleep(delay)
                    continue
                raise ImageGenerationError("API timeout", is_retryable=True)
            except ImageGenerationError:
                raise
            except Exception as e:
                error_str = str(e)
                is_retryable = any(code in error_str for code in ["503", "429", "UNAVAILABLE"])
                if is_retryable and attempt < MAX_RETRIES - 1:
                    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                    await asyncio.sleep(delay)
                    continue
                raise ImageGenerationError(f"API error: {error_str}", is_retryable=is_retryable)

        raise ImageGenerationError("All retry attempts failed", is_retryable=True)

    async def generate_all_images(
        self,
        world_id: str,
        location_ids: Optional[list[str]] = None,
        progress_callback=None,
        location_callback=None  # New: Called with (loc_id, status, message) for per-location updates
    ) -> dict[str, Optional[str]]:
        """
        Generate images for all (or specified) locations in a world.
        Includes variants for locations with conditional NPCs.

        Args:
            world_id: World to generate images for
            location_ids: Optional list of specific locations (default: all)
            progress_callback: Called with (progress_float, message) for overall progress
            location_callback: Called with (loc_id, status, message) for per-location updates
                             status is one of: 'pending', 'generating', 'variants', 'done', 'error'
        """
        world_path = self.worlds_dir / world_id
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
        visual_setting = ""
        style_config = None
        style_preset_name = ""

        if world_yaml.exists():
            with open(world_yaml) as f:
                world_data = yaml.safe_load(f) or {}
                theme = world_data.get("theme", theme)
                tone = world_data.get("tone", tone)
                visual_setting = world_data.get("visual_setting", "")
                style_config = world_data.get("style") or world_data.get("style_block")
                if isinstance(style_config, str):
                    style_preset_name = style_config
                elif isinstance(style_config, dict):
                    style_preset_name = style_config.get("preset", "")

        style_block = resolve_style(style_config)

        # Load locations
        with open(locations_yaml) as f:
            locations = yaml.safe_load(f) or {}

        # Load NPCs
        npcs_data = {}
        if npcs_yaml.exists():
            with open(npcs_yaml) as f:
                npcs_data = yaml.safe_load(f) or {}

        # Load items
        items_data = {}
        if items_yaml.exists():
            with open(items_yaml) as f:
                items_data = yaml.safe_load(f) or {}

        # Filter to requested locations
        target_locations = locations
        if location_ids:
            target_locations = {k: v for k, v in locations.items() if k in location_ids}

        results = {}
        total = len(target_locations)

        for i, (loc_id, loc_data) in enumerate(target_locations.items()):
            loc_name = loc_data.get("name", loc_id)
            atmosphere = loc_data.get("atmosphere", "")
            visual_description = loc_data.get("visual_description", "")

            if progress_callback:
                progress_callback(i / total, f"Generating {loc_name}...")

            if location_callback:
                location_callback(loc_id, "generating", f"Generating base image...")

            # Build context
            context = self._build_location_context(
                loc_id, loc_data, locations, npcs_data, items_data
            )

            # Check for conditional NPCs
            conditional_npcs = self._get_conditional_npcs(loc_id, loc_data, npcs_data)

            # Compute hash for metadata
            prompt_hash = self.hash_tracker.compute_location_hash(world_id, loc_id)

            if conditional_npcs:
                # Generate base image (without conditional NPCs)
                unconditional_npcs = self._get_unconditional_npcs(loc_id, loc_data, npcs_data)
                base_context = self._build_location_context(
                    loc_id, loc_data, locations, npcs_data, items_data,
                    include_npc_ids=unconditional_npcs
                )

                try:
                    await self.generate_location_image(
                        location_id=loc_id,
                        location_name=loc_name,
                        atmosphere=atmosphere,
                        theme=theme,
                        tone=tone,
                        output_dir=images_dir,
                        context=base_context,
                        style_block=style_block,
                        visual_description=visual_description,
                        visual_setting=visual_setting
                    )
                    results[loc_id] = str(images_dir / f"{loc_id}.png")

                    # Save metadata for base image
                    self.hash_tracker.update_metadata(
                        world_id, loc_id, prompt_hash, style_preset_name
                    )
                except Exception as e:
                    results[loc_id] = None
                    if location_callback:
                        location_callback(loc_id, "error", str(e))
                    continue

                # Generate variants for conditional NPCs
                if location_callback:
                    location_callback(loc_id, "variants", f"Generating {len(conditional_npcs)} variant(s)...")

                await self._generate_variants(
                    loc_id, loc_name, atmosphere, theme, tone,
                    images_dir, loc_data, npcs_data, conditional_npcs,
                    style_block, world_id, style_preset_name
                )
            else:
                # Simple case: no conditional NPCs
                try:
                    result = await self.generate_location_image(
                        location_id=loc_id,
                        location_name=loc_name,
                        atmosphere=atmosphere,
                        theme=theme,
                        tone=tone,
                        output_dir=images_dir,
                        context=context,
                        style_block=style_block,
                        visual_description=visual_description,
                        visual_setting=visual_setting
                    )
                    results[loc_id] = result

                    # Save metadata
                    self.hash_tracker.update_metadata(
                        world_id, loc_id, prompt_hash, style_preset_name
                    )
                except Exception as e:
                    results[loc_id] = None
                    if location_callback:
                        location_callback(loc_id, "error", str(e))
                    continue

            if location_callback:
                location_callback(loc_id, "done", "Complete")

            await asyncio.sleep(0.5)

        if progress_callback:
            progress_callback(1.0, "All images generated!")

        return results

    async def regenerate_location(
        self,
        world_id: str,
        location_id: str,
        include_variants: bool = True,
        progress_callback=None
    ) -> Optional[str]:
        """Regenerate image for a specific location, including variants."""
        world_path = self.worlds_dir / world_id
        locations_yaml = world_path / "locations.yaml"
        world_yaml = world_path / "world.yaml"
        npcs_yaml = world_path / "npcs.yaml"
        items_yaml = world_path / "items.yaml"
        images_dir = world_path / "images"

        if not locations_yaml.exists():
            raise FileNotFoundError(f"Locations file not found")

        # Load world data
        theme = "fantasy"
        tone = "atmospheric"
        visual_setting = ""
        style_config = None
        style_preset_name = ""

        if world_yaml.exists():
            with open(world_yaml) as f:
                world_data = yaml.safe_load(f) or {}
                theme = world_data.get("theme", theme)
                tone = world_data.get("tone", tone)
                visual_setting = world_data.get("visual_setting", "")
                style_config = world_data.get("style") or world_data.get("style_block")
                if isinstance(style_config, str):
                    style_preset_name = style_config
                elif isinstance(style_config, dict):
                    style_preset_name = style_config.get("preset", "")

        style_block = resolve_style(style_config)

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
        visual_description = loc_data.get("visual_description", "")

        if progress_callback:
            progress_callback(0.1, f"Regenerating {loc_name}...")

        # Compute hash for metadata
        prompt_hash = self.hash_tracker.compute_location_hash(world_id, location_id)

        conditional_npcs = self._get_conditional_npcs(location_id, loc_data, npcs_data)

        if conditional_npcs and include_variants:
            unconditional_npcs = self._get_unconditional_npcs(location_id, loc_data, npcs_data)
            base_context = self._build_location_context(
                location_id, loc_data, locations, npcs_data, items_data,
                include_npc_ids=unconditional_npcs
            )

            if progress_callback:
                progress_callback(0.2, "Generating base image...")

            result = await self.generate_location_image(
                location_id=location_id,
                location_name=loc_name,
                atmosphere=atmosphere,
                theme=theme,
                tone=tone,
                output_dir=images_dir,
                context=base_context,
                style_block=style_block,
                visual_description=visual_description,
                visual_setting=visual_setting
            )

            # Save metadata for base image
            self.hash_tracker.update_metadata(
                world_id, location_id, prompt_hash, style_preset_name
            )

            if progress_callback:
                progress_callback(0.5, "Generating variants...")

            await self._generate_variants(
                location_id, loc_name, atmosphere, theme, tone,
                images_dir, loc_data, npcs_data, conditional_npcs,
                style_block, world_id, style_preset_name
            )

            if progress_callback:
                progress_callback(1.0, "Done!")

            return result
        else:
            context = self._build_location_context(
                location_id, loc_data, locations, npcs_data, items_data
            )

            result = await self.generate_location_image(
                location_id=location_id,
                location_name=loc_name,
                atmosphere=atmosphere,
                theme=theme,
                tone=tone,
                output_dir=images_dir,
                context=context,
                style_block=style_block,
                visual_description=visual_description,
                visual_setting=visual_setting
            )

            # Save metadata
            self.hash_tracker.update_metadata(
                world_id, location_id, prompt_hash, style_preset_name
            )

            if progress_callback:
                progress_callback(1.0, "Done!")

            return result

    async def _generate_variants(
        self,
        location_id: str,
        location_name: str,
        atmosphere: str,
        theme: str,
        tone: str,
        images_dir: Path,
        loc_data: dict,
        npcs_data: dict,
        conditional_npcs: list[str],
        style_block: StyleBlock,
        world_id: str = "",
        style_preset_name: str = ""
    ):
        """Generate variant images for conditional NPCs."""
        from google import genai
        from google.genai import types

        manifest = ImageVariantManifest(
            location_id=location_id,
            base=f"{location_id}.png",
            variants=[]
        )

        base_image_path = images_dir / f"{location_id}.png"
        npc_placements = loc_data.get("npc_placements", {})

        for npc_id in conditional_npcs:
            npc_data = npcs_data.get(npc_id, {})
            if not npc_data:
                continue

            # V3: Parse placement from structured or string format
            placement_info = npc_placements.get(npc_id, "")
            if isinstance(placement_info, dict):
                placement = placement_info.get("placement", "")
            else:
                placement = placement_info

            npc_to_add = NPCInfo(
                name=npc_data.get("name", npc_id),
                appearance=npc_data.get("appearance", ""),
                role=npc_data.get("role", ""),
                placement=placement
            )

            variant_filename = get_variant_image_filename(location_id, [npc_id])

            try:
                await self._generate_variant_via_edit(
                    location_name=location_name,
                    base_image_path=base_image_path,
                    npc=npc_to_add,
                    output_path=images_dir / variant_filename,
                    theme=theme,
                    tone=tone,
                    style_block=style_block
                )

                _save_prompt_markdown(
                    images_dir,
                    variant_filename.replace(".png", ""),
                    location_name,
                    get_edit_prompt(location_name, [npc_to_add], theme, tone, style_block)
                )

                # Track default presence
                is_default = self._npc_default_present(npc_data, location_id)
                manifest.variants.append({
                    "npcs": [npc_id],
                    "image": variant_filename,
                    "default": is_default
                })

                # Save metadata for variant
                if world_id:
                    variant_hash = self.hash_tracker.compute_location_hash(
                        world_id, location_id, [npc_id]
                    )
                    self.hash_tracker.update_metadata(
                        world_id, location_id, variant_hash, style_preset_name, [npc_id]
                    )

            except Exception as e:
                print(f"Failed to generate variant {variant_filename}: {e}")

            await asyncio.sleep(1.0)

        save_variant_manifest(manifest, images_dir)

    async def _generate_variant_via_edit(
        self,
        location_name: str,
        base_image_path: Path,
        npc: NPCInfo,
        output_path: Path,
        theme: str,
        tone: str,
        style_block: StyleBlock
    ):
        """Generate a variant image by editing the base image to add an NPC."""
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        client = genai.Client(api_key=api_key)
        prompt = get_edit_prompt(location_name, [npc], theme, tone, style_block)

        with open(base_image_path, 'rb') as f:
            base_image_bytes = f.read()

        image_part = types.Part.from_bytes(data=base_image_bytes, mime_type="image/png")
        contents = [image_part, prompt]

        config = types.GenerateContentConfig(
            temperature=1.0,
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9"),
            safety_settings=[
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_ONLY_HIGH"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_ONLY_HIGH"),
            ]
        )

        for attempt in range(MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=IMAGE_MODEL,
                        contents=contents,
                        config=config
                    ),
                    timeout=120.0
                )

                if hasattr(response, 'parts') and response.parts:
                    for part in response.parts:
                        if part.inline_data is not None:
                            try:
                                image = part.as_image()
                                await asyncio.to_thread(image.save, str(output_path))
                            except Exception:
                                image_data = part.inline_data.data
                                if isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data)
                                with open(output_path, 'wb') as f:
                                    f.write(image_data)
                            return

                # Retry on IMAGE_OTHER
                finish_reason = None
                if hasattr(response, 'candidates') and response.candidates:
                    finish_reason = getattr(response.candidates[0], 'finish_reason', None)

                if "IMAGE_OTHER" in str(finish_reason):
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))
                        continue

                raise ImageGenerationError(f"No image in response")

            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))
                    continue
                raise
            except ImageGenerationError:
                raise
            except Exception as e:
                if attempt < MAX_RETRIES - 1 and any(x in str(e) for x in ["503", "429"]):
                    await asyncio.sleep(INITIAL_RETRY_DELAY * (2 ** attempt))
                    continue
                raise

    def _build_location_context(
        self,
        location_id: str,
        loc_data: dict,
        locations: dict,
        npcs_data: dict,
        items_data: dict,
        include_npc_ids: Optional[list[str]] = None
    ) -> LocationContext:
        """Build a LocationContext from world data (V3 schema).

        V3 changes:
        - Exits are dicts with ExitDefinition structure (not just destination strings)
        - Items are defined by item_placements keys (not items list)
        - NPCs are defined by npc_placements keys (not npcs list)
        - Details are scene elements defined in the details field
        - Hidden entities are filtered out at build time

        Args:
            location_id: The location being processed
            loc_data: Raw location data from YAML
            locations: All locations data for destination lookups
            npcs_data: All NPC definitions
            items_data: All item definitions
            include_npc_ids: Optional filter for specific NPCs (for variants)

        Returns:
            LocationContext with exits, items, NPCs, and details for image generation
        """
        context = LocationContext()

        # Build details (scene elements like furniture, decorations, etc.)
        details_data = loc_data.get("details", {})
        for detail_id, detail_info in details_data.items():
            if isinstance(detail_info, dict):
                name = detail_info.get("name", detail_id)
                scene_description = detail_info.get("scene_description", "")
            else:
                # Simple string format (just the description)
                name = detail_id
                scene_description = detail_info if detail_info else ""

            context.details.append(DetailInfo(
                name=name,
                scene_description=scene_description,
            ))

        # Build exits (V3: structured ExitDefinition format)
        exits_data = loc_data.get("exits", {})
        for direction, exit_info in exits_data.items():
            if isinstance(exit_info, dict):
                # V3 structured format
                destination_id = exit_info.get("destination", direction)
                scene_description = exit_info.get("scene_description", "")
                destination_known = exit_info.get("destination_known", True)
                hidden = exit_info.get("hidden", False)
                locked = exit_info.get("locked", False)
                requires_key = exit_info.get("requires_key")
            else:
                # Legacy string format (just destination)
                destination_id = exit_info
                scene_description = ""
                destination_known = True
                hidden = False
                locked = False
                requires_key = None

            # Get destination info
            destination_data = locations.get(destination_id, {})
            destination_name = destination_data.get("name", destination_id)
            destination_visual = destination_data.get("visual_description", "")
            dest_requires = destination_data.get("requires", {})

            # Determine is_secret from destination requirements (legacy pattern)
            is_secret = bool(dest_requires.get("flag") if dest_requires else False)

            # For open passages, include destination visual (not name) to avoid wrong signage
            # Only include for non-locked exits (can see through open passage)
            destination_visual_hint = ""
            if destination_known and destination_visual and not (locked or requires_key):
                destination_visual_hint = destination_visual

            context.exits.append(ExitInfo(
                direction=direction,
                destination_name=destination_name,
                scene_description=scene_description,
                destination_known=destination_known,
                destination_visual_hint=destination_visual_hint,
                hidden=hidden,
                is_secret=is_secret,
                requires_key=bool(locked or requires_key),
            ))

        # Build items (V3: item_placements is source of truth)
        item_placements = loc_data.get("item_placements", {})
        for item_id, placement_info in item_placements.items():
            # Parse placement info (V3 structured or simple string)
            if isinstance(placement_info, dict):
                placement = placement_info.get("placement", "")
                hidden = placement_info.get("hidden", False)
            else:
                # Simple string placement (visible by default)
                placement = placement_info
                hidden = False

            # Filter hidden items at build time
            if not _is_entity_visible_at_build_time(hidden):
                continue

            # Get item definition
            item_data = items_data.get(item_id, {})
            if item_data:
                context.items.append(ItemInfo(
                    name=item_data.get("name", item_id),
                    description=item_data.get("scene_description", ""),
                    placement=placement,
                    hidden=hidden,
                    is_artifact=item_data.get("properties", {}).get("artifact", False),
                ))

        # Build NPCs (V3: npc_placements is source of truth for this location)
        if include_npc_ids is not None and len(include_npc_ids) == 0:
            return context

        npc_placements = loc_data.get("npc_placements", {})
        all_potential_npcs = []

        # V3: Get NPCs from npc_placements at this location
        for npc_id, placement_info in npc_placements.items():
            npc_data = npcs_data.get(npc_id, {})
            if not npc_data:
                continue

            # Parse placement info
            if isinstance(placement_info, dict):
                placement = placement_info.get("placement", "")
                hidden = placement_info.get("hidden", False)
            else:
                placement = placement_info
                hidden = False

            # Filter hidden NPCs at build time
            if not _is_entity_visible_at_build_time(hidden):
                continue

            all_potential_npcs.append((npc_id, npc_data, placement))

        # Also include NPCs that have location/locations pointing here
        # (for backward compatibility and roaming NPCs)
        for npc_id, npc_data in npcs_data.items():
            # Skip if already in npc_placements
            if npc_id in npc_placements:
                continue
            npc_location = npc_data.get("location")
            npc_locations = npc_data.get("locations", [])
            if npc_location == location_id or location_id in npc_locations:
                # Use placement from npc_placements if available, else empty
                placement = ""
                if npc_id in npc_placements:
                    pi = npc_placements[npc_id]
                    placement = pi.get("placement", "") if isinstance(pi, dict) else pi
                all_potential_npcs.append((npc_id, npc_data, placement))

        # Build NPC context, respecting include_npc_ids filter
        for npc_id, npc_data, placement in all_potential_npcs:
            if include_npc_ids is not None and npc_id not in include_npc_ids:
                continue

            context.npcs.append(NPCInfo(
                name=npc_data.get("name", npc_id),
                appearance=npc_data.get("appearance", ""),
                role=npc_data.get("role", ""),
                placement=placement,
            ))

        return context

    def _get_conditional_npcs(self, location_id: str, loc_data: dict, npcs_data: dict) -> list[str]:
        """Get list of NPC IDs that are conditional at this location (V3).

        V3: Uses npc_placements instead of npcs list. Hidden NPCs are excluded.
        """
        conditional_npcs = []
        npc_placements = loc_data.get("npc_placements", {})

        # V3: Get NPCs from npc_placements
        for npc_id, placement_info in npc_placements.items():
            # Skip hidden NPCs
            if isinstance(placement_info, dict) and placement_info.get("hidden", False):
                continue

            npc_data = npcs_data.get(npc_id, {})
            if npc_data and self._is_npc_conditional(npc_data, location_id):
                conditional_npcs.append(npc_id)

        # Also check NPCs with location/locations pointing here
        for npc_id, npc_data in npcs_data.items():
            if npc_id in npc_placements or npc_id in conditional_npcs:
                continue

            if self._npc_can_be_at_location(npc_id, npc_data, location_id):
                if self._is_npc_conditional(npc_data, location_id):
                    conditional_npcs.append(npc_id)

        return conditional_npcs

    def _get_unconditional_npcs(self, location_id: str, loc_data: dict, npcs_data: dict) -> list[str]:
        """Get list of NPC IDs that are NOT conditional at this location (V3).

        V3: Uses npc_placements instead of npcs list. Hidden NPCs are excluded.
        """
        unconditional_npcs = []
        npc_placements = loc_data.get("npc_placements", {})

        # V3: Get NPCs from npc_placements
        for npc_id, placement_info in npc_placements.items():
            # Skip hidden NPCs
            if isinstance(placement_info, dict) and placement_info.get("hidden", False):
                continue

            npc_data = npcs_data.get(npc_id, {})
            if npc_data and not self._is_npc_conditional(npc_data, location_id):
                unconditional_npcs.append(npc_id)

        # Also check NPCs with location/locations pointing here
        for npc_id, npc_data in npcs_data.items():
            if npc_id in npc_placements or npc_id in unconditional_npcs:
                continue

            if self._npc_can_be_at_location(npc_id, npc_data, location_id):
                if not self._is_npc_conditional(npc_data, location_id):
                    unconditional_npcs.append(npc_id)

        return unconditional_npcs

    def _npc_can_be_at_location(self, npc_id: str, npc_data: dict, location_id: str) -> bool:
        """Check if an NPC can potentially be at a location."""
        if npc_data.get("location") == location_id:
            return True
        if location_id in npc_data.get("locations", []):
            return True
        for change in npc_data.get("location_changes", []):
            if change.get("move_to") == location_id:
                return True
        return False

    def _is_npc_conditional(self, npc_data: dict, location_id: str) -> bool:
        """Check if an NPC is conditional at a location."""
        if npc_data.get("appears_when"):
            return True

        location_changes = npc_data.get("location_changes", [])
        if location_changes:
            starting_location = npc_data.get("location")

            if starting_location == location_id:
                for change in location_changes:
                    move_to = change.get("move_to")
                    if move_to and move_to != starting_location:
                        return True

            for change in location_changes:
                move_to = change.get("move_to")
                if move_to == location_id and starting_location != location_id:
                    return True

        return False

    def _npc_default_present(self, npc_data: dict, location_id: str) -> bool:
        """Check if an NPC is present at a location at game start."""
        if npc_data.get("appears_when"):
            return False
        if npc_data.get("location") == location_id:
            return True
        if location_id in npc_data.get("locations", []):
            return True
        return False

    def list_location_images(self, world_id: str) -> dict[str, dict]:
        """List all images for a world with variant info."""
        images_dir = self.worlds_dir / world_id / "images"

        if not images_dir.exists():
            return {}

        result = {}

        for image_file in images_dir.glob("*.png"):
            filename = image_file.name

            # Skip variant images (they're tracked in manifests)
            if "__with__" in filename:
                continue

            location_id = image_file.stem

            # Check for variants
            manifest = load_variant_manifest(location_id, images_dir)

            result[location_id] = {
                "path": str(image_file),
                "has_variants": manifest is not None,
                "variant_count": len(manifest.variants) if manifest else 0
            }

        return result

    def get_location_image_status(self, world_id: str, location_id: str) -> dict:
        """
        Get detailed status for a location's images including outdated detection.

        Returns:
            Dict with:
            - has_image: bool
            - is_outdated: bool (base image)
            - outdated_reason: str
            - variant_count: int
            - variants_outdated: int
            - outdated_variant_npc_ids: list[list[str]] - NPC IDs for each outdated variant
        """
        images_dir = self.worlds_dir / world_id / "images"
        base_image = images_dir / f"{location_id}.png"

        has_image = base_image.exists()

        # Check if base image is outdated
        is_outdated = False
        outdated_reason = ""
        if has_image:
            is_outdated, outdated_reason = self.hash_tracker.is_outdated(world_id, location_id)

        # Check variants
        manifest = load_variant_manifest(location_id, images_dir)
        variant_count = len(manifest.variants) if manifest else 0
        variants_outdated = 0
        outdated_variant_npc_ids = []

        if manifest:
            for variant in manifest.variants:
                npc_ids = variant.get("npcs", [])
                variant_outdated, _ = self.hash_tracker.is_outdated(
                    world_id, location_id, npc_ids
                )
                if variant_outdated:
                    variants_outdated += 1
                    outdated_variant_npc_ids.append(npc_ids)

        return {
            "has_image": has_image,
            "is_outdated": is_outdated,
            "outdated_reason": outdated_reason,
            "variant_count": variant_count,
            "variants_outdated": variants_outdated,
            "outdated_variant_npc_ids": outdated_variant_npc_ids,
        }

    def get_locations_needing_generation(self, world_id: str) -> list[dict]:
        """
        Get list of locations that need image generation (missing or outdated).

        Returns:
            List of dicts with:
            - location_id: str
            - location_name: str
            - reason: str
            - regenerate_base: bool - whether base image needs regeneration
            - regenerate_variants: list[list[str]] - NPC IDs for variants to regenerate
        """
        from gaime_builder.core.world_generator import WorldGenerator

        generator = WorldGenerator(self.worlds_dir)
        locations = generator.get_world_locations(world_id)

        needs_generation = []

        for loc in locations:
            loc_id = loc["id"]
            status = self.get_location_image_status(world_id, loc_id)

            if not status["has_image"]:
                # Missing base image - need to generate everything
                needs_generation.append({
                    "location_id": loc_id,
                    "location_name": loc["name"],
                    "reason": "missing",
                    "regenerate_base": True,
                    "regenerate_variants": "all",  # Will regenerate all variants
                })
            elif status["is_outdated"]:
                # Base image outdated - need to regenerate base + ALL variants
                # (because variants are edited versions of the base)
                needs_generation.append({
                    "location_id": loc_id,
                    "location_name": loc["name"],
                    "reason": f"base outdated ({status['outdated_reason']})",
                    "regenerate_base": True,
                    "regenerate_variants": "all",
                })
            elif status["variants_outdated"] > 0:
                # Only variants outdated - regenerate just those variants
                needs_generation.append({
                    "location_id": loc_id,
                    "location_name": loc["name"],
                    "reason": f"{status['variants_outdated']} variant(s) outdated",
                    "regenerate_base": False,
                    "regenerate_variants": status["outdated_variant_npc_ids"],
                })

        return needs_generation

    async def regenerate_outdated(
        self,
        world_id: str,
        location_id: str,
        progress_callback=None
    ) -> Optional[str]:
        """
        Smart regeneration that only regenerates what's needed.

        - If base is outdated: regenerate base + all variants
        - If only variants are outdated: regenerate just those variants
        """
        status = self.get_location_image_status(world_id, location_id)

        if not status["has_image"] or status["is_outdated"]:
            # Base needs regeneration - do full regeneration
            return await self.regenerate_location(
                world_id=world_id,
                location_id=location_id,
                include_variants=True,
                progress_callback=progress_callback
            )
        elif status["variants_outdated"] > 0:
            # Only variants need regeneration
            return await self.regenerate_variants_only(
                world_id=world_id,
                location_id=location_id,
                variant_npc_ids_list=status["outdated_variant_npc_ids"],
                progress_callback=progress_callback
            )
        else:
            # Nothing to do
            if progress_callback:
                progress_callback(1.0, "Already up to date")
            return None

    async def regenerate_variants_only(
        self,
        world_id: str,
        location_id: str,
        variant_npc_ids_list: list[list[str]],
        progress_callback=None
    ) -> Optional[str]:
        """
        Regenerate specific variants without regenerating the base image.

        Uses the existing base image and applies NPC edits to create variants.
        """
        world_path = self.worlds_dir / world_id
        locations_yaml = world_path / "locations.yaml"
        world_yaml = world_path / "world.yaml"
        npcs_yaml = world_path / "npcs.yaml"
        images_dir = world_path / "images"

        base_image_path = images_dir / f"{location_id}.png"
        if not base_image_path.exists():
            raise FileNotFoundError(f"Base image not found: {base_image_path}")

        # Load world data
        theme = "fantasy"
        tone = "atmospheric"
        style_config = None
        style_preset_name = ""

        if world_yaml.exists():
            with open(world_yaml) as f:
                world_data = yaml.safe_load(f) or {}
                theme = world_data.get("theme", theme)
                tone = world_data.get("tone", tone)
                style_config = world_data.get("style") or world_data.get("style_block")
                if isinstance(style_config, str):
                    style_preset_name = style_config
                elif isinstance(style_config, dict):
                    style_preset_name = style_config.get("preset", "")

        style_block = resolve_style(style_config)

        with open(locations_yaml) as f:
            locations = yaml.safe_load(f) or {}

        npcs_data = {}
        if npcs_yaml.exists():
            with open(npcs_yaml) as f:
                npcs_data = yaml.safe_load(f) or {}

        loc_data = locations.get(location_id)
        if not loc_data:
            raise ValueError(f"Location not found: {location_id}")

        loc_name = loc_data.get("name", location_id)
        npc_placements = loc_data.get("npc_placements", {})

        total = len(variant_npc_ids_list)

        for i, npc_ids in enumerate(variant_npc_ids_list):
            if progress_callback:
                progress_callback(i / total, f"Regenerating variant {i+1}/{total}...")

            # Current implementation only supports single-NPC variants
            # If multi-NPC support is needed, _generate_variant_via_edit must be updated
            for npc_id in npc_ids:
                npc_data = npcs_data.get(npc_id, {})
                if not npc_data:
                    continue

                # V3: Parse placement from structured or string format
                placement_info = npc_placements.get(npc_id, "")
                if isinstance(placement_info, dict):
                    placement = placement_info.get("placement", "")
                else:
                    placement = placement_info

                npc_to_add = NPCInfo(
                    name=npc_data.get("name", npc_id),
                    appearance=npc_data.get("appearance", ""),
                    role=npc_data.get("role", ""),
                    placement=placement
                )

                # Generate one variant per NPC (matching _generate_variants pattern)
                variant_filename = get_variant_image_filename(location_id, [npc_id])

                try:
                    await self._generate_variant_via_edit(
                        location_name=loc_name,
                        base_image_path=base_image_path,
                        npc=npc_to_add,
                        output_path=images_dir / variant_filename,
                        theme=theme,
                        tone=tone,
                        style_block=style_block
                    )

                    # Save prompt log
                    _save_prompt_markdown(
                        images_dir,
                        variant_filename.replace(".png", ""),
                        loc_name,
                        get_edit_prompt(loc_name, [npc_to_add], theme, tone, style_block)
                    )

                    # Update metadata for this variant (single NPC)
                    variant_hash = self.hash_tracker.compute_location_hash(
                        world_id, location_id, [npc_id]
                    )
                    self.hash_tracker.update_metadata(
                        world_id, location_id, variant_hash, style_preset_name, [npc_id]
                    )

                except Exception as e:
                    if progress_callback:
                        progress_callback(i / total, f"Error: {e}")
                    raise

                await asyncio.sleep(1.0)

        if progress_callback:
            progress_callback(1.0, f"Regenerated {total} variant(s)")

        return str(base_image_path)
