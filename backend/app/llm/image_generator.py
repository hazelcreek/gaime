"""
Image utilities for the game runtime.

Provides functions to load location images and handle NPC variants.
Image generation is handled separately by the gaime-builder TUI.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class ImageVariantManifest:
    """Manifest describing all image variants for a location.

    Variant format: {"npcs": [...], "image": "...", "default": bool}
    - npcs: List of NPC IDs shown in this variant
    - image: Filename of the variant image
    - default: If True, this NPC is present by default at this location

    The appropriate variant is selected based on which NPCs are currently visible
    at the location according to game state. If no conditional NPCs are visible,
    the base image is shown.
    """

    location_id: str
    base: str  # Base image filename (no conditional NPCs)
    variants: list[dict]  # List of variant descriptors

    def to_dict(self) -> dict:
        return {
            "location_id": self.location_id,
            "base": self.base,
            "variants": self.variants,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImageVariantManifest":
        return cls(
            location_id=data["location_id"],
            base=data["base"],
            variants=data.get("variants", []),
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

        # Find variant with exact NPC match
        for variant in self.variants:
            variant_npcs = set(variant.get("npcs", []))
            if variant_npcs == visible_set:
                return variant["image"]

        # No exact match - return base image
        return self.base


def load_variant_manifest(
    location_id: str, images_dir: Path
) -> Optional[ImageVariantManifest]:
    """Load a variant manifest from JSON file if it exists."""
    manifest_path = images_dir / f"{location_id}_variants.json"
    if not manifest_path.exists():
        return None

    with open(manifest_path, "r") as f:
        data = json.load(f)
    return ImageVariantManifest.from_dict(data)


def get_location_image_path(
    world_id: str,
    location_id: str,
    worlds_dir: Path,
    visible_npc_ids: Optional[list[str]] = None,
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

    # Fallback to base image
    image_path = images_dir / f"{location_id}.png"
    if image_path.exists():
        return str(image_path)

    return None
