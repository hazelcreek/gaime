"""
Style Loader - Handles loading visual style presets for image generation.

Copied and adapted from backend/app/llm/style_loader.py for TUI independence.
"""

import yaml
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field

from gaime_builder.core.prompt_loader import get_loader


# Default preset to use when no style is specified
DEFAULT_PRESET = "classic-fantasy"


def _get_presets_dir() -> Path:
    """Get path to presets directory bundled with gaime_builder."""
    return Path(__file__).parent / "prompts" / "image_generator" / "presets"


@dataclass
class MoodConfig:
    """L3: Mood configuration for emotional atmosphere."""
    tone: str = "atmospheric"
    lighting: str = "dramatic lighting"
    color_palette: str = "rich and natural colors"


@dataclass
class TechnicalConfig:
    """L5: Technical configuration for composition and camera."""
    perspective: str = "first-person"
    shot: str = "medium wide shot"
    camera: str = "eye level"
    effects: str = ""


@dataclass
class StyleBlock:
    """Complete style configuration resolved from preset and overrides."""
    mood: MoodConfig = field(default_factory=MoodConfig)
    style: str = ""
    technical: TechnicalConfig = field(default_factory=TechnicalConfig)
    anti_styles: list[str] = field(default_factory=list)
    quality_constraints: list[str] = field(default_factory=lambda: [
        "watermarks or signatures",
        "blurry or low-quality artifacts",
        "distorted proportions"
    ])
    name: str = ""
    description: str = ""


class StylePresets:
    """Manages loading and caching of style presets from YAML files."""

    def __init__(self, presets_dir: Optional[Path] = None):
        self.presets_dir = presets_dir or _get_presets_dir()
        self._presets: dict[str, dict] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Lazily load all presets on first access."""
        if self._loaded:
            return

        if not self.presets_dir.exists():
            raise FileNotFoundError(f"Presets directory not found: {self.presets_dir}")

        for preset_file in self.presets_dir.glob("*.yaml"):
            preset_name = preset_file.stem
            try:
                with open(preset_file, 'r') as f:
                    self._presets[preset_name] = yaml.safe_load(f)
            except Exception as e:
                print(f"Warning: Failed to load preset {preset_name}: {e}")

        self._loaded = True

    def list_presets(self) -> list[str]:
        """Return list of available preset names."""
        self._ensure_loaded()
        return list(self._presets.keys())

    def get_preset(self, name: str) -> Optional[dict]:
        """Get raw preset data by name."""
        self._ensure_loaded()
        return self._presets.get(name)

    def has_preset(self, name: str) -> bool:
        """Check if a preset exists."""
        self._ensure_loaded()
        return name in self._presets

    def reload(self) -> None:
        """Force reload all presets from disk."""
        self._loaded = False
        self._presets = {}
        self._ensure_loaded()


# Global singleton instance
_presets_instance: Optional[StylePresets] = None


def get_presets() -> StylePresets:
    """Get the global StylePresets instance."""
    global _presets_instance
    if _presets_instance is None:
        _presets_instance = StylePresets()
    return _presets_instance


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override dict into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_style(style_config: Any) -> StyleBlock:
    """
    Resolve a style configuration into a complete StyleBlock.

    Args:
        style_config: Can be:
            - str: Preset name (e.g., "noir")
            - dict with "preset" key: Preset with overrides
            - dict without "preset": Full custom style_block
            - None: Use default preset
    """
    presets = get_presets()

    # Handle None - use default
    if style_config is None:
        style_config = DEFAULT_PRESET

    # Handle string - just a preset name
    if isinstance(style_config, str):
        preset_data = presets.get_preset(style_config)
        if preset_data is None:
            preset_data = presets.get_preset(DEFAULT_PRESET) or {}
        return _dict_to_style_block(preset_data)

    # Handle dict
    if isinstance(style_config, dict):
        if "preset" in style_config:
            preset_name = style_config["preset"]
            preset_data = presets.get_preset(preset_name)
            if preset_data is None:
                preset_data = presets.get_preset(DEFAULT_PRESET) or {}

            overrides = style_config.get("overrides", {})
            merged_data = _deep_merge(preset_data, overrides)
            return _dict_to_style_block(merged_data)

        return _dict_to_style_block(style_config)

    # Fallback to default
    preset_data = presets.get_preset(DEFAULT_PRESET) or {}
    return _dict_to_style_block(preset_data)


def _dict_to_style_block(data: dict) -> StyleBlock:
    """Convert a dict (from YAML) to a StyleBlock dataclass."""
    mood_data = data.get("mood", {})
    mood = MoodConfig(
        tone=mood_data.get("tone", "atmospheric"),
        lighting=mood_data.get("lighting", "dramatic lighting"),
        color_palette=mood_data.get("color_palette", "rich and natural colors")
    )

    tech_data = data.get("technical", {})
    technical = TechnicalConfig(
        perspective=tech_data.get("perspective", "first-person"),
        shot=tech_data.get("shot", "medium wide shot"),
        camera=tech_data.get("camera", "eye level"),
        effects=tech_data.get("effects", "")
    )

    style = data.get("style", "")
    if isinstance(style, str):
        style = style.strip()

    anti_styles = data.get("anti_styles", [])
    quality_constraints = data.get("quality_constraints", [
        "watermarks or signatures",
        "blurry or low-quality artifacts",
        "distorted proportions"
    ])

    return StyleBlock(
        mood=mood,
        style=style,
        technical=technical,
        anti_styles=anti_styles,
        quality_constraints=quality_constraints,
        name=data.get("name", ""),
        description=data.get("description", "")
    )


def build_mpa_prompt(
    location_name: str,
    atmosphere: str,
    world_context: str,
    style_block: StyleBlock,
    interactive_section: str = "",
    visual_description: str = "",
    visual_setting: str = ""
) -> str:
    """Build a complete MPA-structured prompt for image generation.

    Args:
        location_name: Display name of the location
        atmosphere: Narrative atmosphere (fallback if visual_description not provided)
        world_context: Theme and tone of the world
        style_block: Visual style configuration
        interactive_section: Scene elements (exits, items, NPCs, details)
        visual_description: Pure visual scene description (3-5 sentences)
        visual_setting: World-level visual language (5-10 sentences)
    """
    loader = get_loader()
    template = loader.get_prompt("image_generator", "mpa_template.txt")

    # Use visual_description if provided, otherwise fall back to atmosphere
    scene_description = visual_description.strip() if visual_description else atmosphere.strip()

    anti_styles_text = "\n".join(f"- {item}" for item in style_block.anti_styles)
    quality_text = "\n".join(f"- {item}" for item in style_block.quality_constraints)

    effects_text = style_block.technical.effects
    if effects_text:
        effects_text = f" {effects_text}"
    else:
        effects_text = ""

    prompt = template.format(
        location_name=location_name,
        scene_description=scene_description,
        interactive_section=interactive_section,
        visual_setting=visual_setting.strip() if visual_setting else "",
        world_context=world_context,
        mood_tone=style_block.mood.tone,
        mood_lighting=style_block.mood.lighting,
        mood_color_palette=style_block.mood.color_palette,
        style=style_block.style,
        technical_perspective=style_block.technical.perspective,
        technical_shot=style_block.technical.shot,
        technical_camera=style_block.technical.camera,
        technical_effects=effects_text,
        anti_styles=anti_styles_text,
        quality_constraints=quality_text
    )

    return prompt


def build_mpa_edit_prompt(
    npc_description: str,
    npc_placement: str,
    style_block: StyleBlock
) -> str:
    """Build an MPA-structured prompt for NPC variant generation."""
    loader = get_loader()
    template = loader.get_prompt("image_generator", "mpa_edit_template.txt")

    style_summary = style_block.style.split('\n')[0] if style_block.style else "the original visual style"
    brief_anti_styles = style_block.anti_styles[:4] if style_block.anti_styles else []
    anti_styles_text = "\n".join(f"- {item}" for item in brief_anti_styles)

    prompt = template.format(
        npc_description=npc_description,
        npc_placement=npc_placement or "positioned naturally in the scene",
        style_summary=style_summary,
        anti_styles_brief=anti_styles_text
    )

    return prompt


def get_world_context(theme: str, tone: str) -> str:
    """Build L2 world context from theme and tone."""
    parts = []
    if theme:
        parts.append(theme)
    if tone:
        parts.append(tone)
    return ", ".join(parts) if parts else "fantasy setting"
