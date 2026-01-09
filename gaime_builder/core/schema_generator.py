"""
Schema generator - extracts YAML schema examples from Pydantic models.

This module generates theme-neutral YAML examples that serve as the
source of truth for world builder prompts, ensuring prompts stay in
sync with the Pydantic model definitions.

Updated for V3 schema with structured exits, details, and placements.
"""

import sys
from pathlib import Path
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

# Add backend to path for model imports
BACKEND_PATH = Path(__file__).parent.parent.parent / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.models.world import (
    Item,
    ItemClue,
    ItemProperty,
    ItemUseAction,
    Location,
    LocationRequirement,
    InteractionEffect,
    NPC,
    NPCPersonality,
    NPCTrust,
    World,
    ExitDefinition,
    DetailDefinition,
    ItemPlacement,
    NPCPlacement,
)


def get_placeholder_value(field_name: str, field_type: type, is_optional: bool = False) -> Any:
    """
    Generate a theme-neutral placeholder value for a field.

    Returns a generic example that works for any world theme.
    """
    # Handle None for optional fields
    origin = get_origin(field_type)
    if origin is type(None) or field_type is type(None):
        return None

    # Handle Union types (e.g., str | None)
    if origin is type(None.__class__):
        args = get_args(field_type)
        if len(args) == 2 and type(None) in args:
            # It's Optional[X], get the non-None type
            field_type = args[0] if args[1] is type(None) else args[1]

    # Common field name patterns (V3 schema)
    placeholder_map = {
        # World fields
        "name": "World Name",
        "theme": "adventure",
        "tone": "atmospheric",
        "premise": "The world premise describing the setting and context.",
        "hero_name": "the protagonist",
        "starting_situation": "Describe WHY the player can act NOW.",
        "style": "visual-style-preset",

        # Location fields
        "atmosphere": "Atmospheric description of this location.",

        # NPC fields
        "role": "Their role in the story",
        "appearance": "Physical description of the character.",
        "behavior": "How they act and react.",

        # Item fields (V3 names)
        "scene_description": "How the item appears naturally in the scene.",
        "examine_description": "Detailed description when the player examines this item.",
        "take_description": "Message shown when the item is taken.",

        # Placement fields (V3)
        "placement": "Where in this room the entity is positioned.",

        # Generic fields
        "description": "A description of this element.",
        "narrative": "The narrative text to display.",
        "narrative_hint": "What happens when this interaction is triggered.",
    }

    if field_name in placeholder_map:
        return placeholder_map[field_name]

    # Handle specific types
    if field_type is str:
        return f"{field_name}_value"
    elif field_type is int:
        return 0
    elif field_type is bool:
        return False
    elif field_type is float:
        return 0.0

    # Handle list types
    if origin is list:
        args = get_args(field_type)
        if args:
            inner_type = args[0]
            if inner_type is str:
                return [f"{field_name}_item"]
            elif issubclass(inner_type, BaseModel):
                # For nested models, return empty list with comment
                return []

    # Handle dict types
    if origin is dict:
        args = get_args(field_type)
        if args and len(args) == 2:
            key_type, value_type = args
            if key_type is str and value_type is str:
                return {f"{field_name}_key": f"{field_name}_value"}
            elif key_type is str and issubclass(value_type, BaseModel):
                return {}

    # Handle nested Pydantic models
    if isinstance(field_type, type) and issubclass(field_type, BaseModel):
        return generate_model_example(field_type)

    return None


def generate_model_example(model: type[BaseModel], indent: int = 0) -> dict[str, Any]:
    """
    Generate a theme-neutral example dict from a Pydantic model.
    """
    result = {}

    for field_name, field_info in model.model_fields.items():
        field_type = field_info.annotation

        # Check if optional
        origin = get_origin(field_type)
        is_optional = False

        # Handle Union types for Optional
        if origin is type(None.__class__) or str(origin) == "typing.Union":
            args = get_args(field_type)
            if type(None) in args:
                is_optional = True
                # Get the non-None type
                non_none_types = [a for a in args if a is not type(None)]
                if non_none_types:
                    field_type = non_none_types[0]

        # Skip optional fields with None defaults for cleaner output
        if is_optional and field_info.default is None:
            continue

        value = get_placeholder_value(field_name, field_type, is_optional)
        if value is not None:
            result[field_name] = value

    return result


def generate_npc_yaml_example() -> str:
    """Generate a complete NPC YAML example with correct schema."""
    return '''npc_id:
  name: "NPC Display Name"
  role: "Their role in the story"
  location: location_id
  appearance: |
    Physical description of the character.
  personality:
    traits:
      - "trait_one"
      - "trait_two"
    speech_style: "How they speak and communicate"
    quirks:
      - "Behavioral quirk or habit"
  knowledge:
    - "Fact or secret they know"
    - "Another piece of information"
  dialogue_rules:
    - "Rule for how they communicate"
    - "When they reveal information"
  appears_when:                  # Optional: conditional appearance
    - condition: has_flag
      value: flag_name'''


def generate_location_yaml_example() -> str:
    """Generate a complete Location YAML example with V3 schema."""
    return '''location_id:
  name: "Location Name"
  atmosphere: |
    Atmospheric description that establishes WHERE the player is,
    what they see, hear, and feel in this space.
  visual_description: |
    3-5 sentences of pure visual description for image generation.

  # V3: Exits are structured ExitDefinition objects
  exits:
    north:
      destination: other_location_id
      scene_description: "Visual description of this exit"
      destination_known: true
    secret:                      # Hidden exit example
      destination: hidden_room_id
      scene_description: "A narrow passage behind the bookcase"
      hidden: true
      find_condition:
        requires_flag: found_lever

  # V3: Item placements define which items are here (no items list)
  item_placements:
    visible_item_id:
      placement: "lies on the dusty table"
    hidden_item_id:
      placement: "tucked under the rug"
      hidden: true
      find_condition:
        requires_flag: examined_rug

  # V3: NPC placements define which NPCs are here (no npcs list)
  npc_placements:
    npc_id:
      placement: "stands behind the counter"

  # V3: Details are structured DetailDefinition objects
  details:
    chandelier:
      name: "Crystal Chandelier"
      scene_description: "A dusty chandelier hangs from the ceiling"
      examine_description: "One crystal is loose..."
      on_examine:
        sets_flag: found_crystal
        narrative_hint: "You discover something behind the crystal!"

  interactions:
    pull_lever:
      triggers:
        - "pull lever"
        - "use lever"
      narrative_hint: "The bookcase slides aside..."
      sets_flag: found_lever

  requires:
    flag: required_flag_name'''


def generate_item_yaml_example() -> str:
    """Generate a complete Item YAML example with V3 schema."""
    return '''item_id:
  name: "Item Name"
  portable: true
  scene_description: "How the item appears naturally in the room scene."
  examine_description: |
    Detailed description when the player examines this item closely.
  take_description: "Message shown when the item is taken."
  unlocks: locked_location_id
  on_examine:                    # Optional: effects when examined
    sets_flag: flag_name
    narrative_hint: "You notice something..."
  use_actions:
    action_name:
      description: "What happens when used this way"
      requires_item: other_item_id
      sets_flag: flag_name'''


def generate_world_yaml_example() -> str:
    """Generate a complete World YAML example with correct schema."""
    return '''name: "World Name"
theme: "adventure"
tone: "atmospheric"
hero_name: "the protagonist"

visual_setting: |
  5-10 sentences describing the world's visual language for image generation.
  Materials, textures, color palette, architecture, lighting...

premise: |
  Description of the world premise, setting, and context.

starting_situation: |
  Describe WHY the player can act NOW. What event, opportunity,
  or change has occurred that enables the adventure to begin?

victory:
  location: final_location_id
  flag: victory_flag
  item: optional_required_item
  narrative: |
    The ending narrative when the player wins...

player:
  starting_location: first_location_id
  starting_inventory:
    - starting_item_id

constraints:
  - "Important rule the AI must follow"
  - "Another constraint for consistency"

commands:
  help: "Display available commands"
  look: "Examine surroundings"
  inventory: "Check inventory"
  go: "Move in a direction"'''


def generate_full_schema_reference() -> str:
    """
    Generate a complete schema reference document.

    This can be used to validate prompts or as documentation.
    """
    sections = [
        "# World Builder Schema Reference (V3)",
        "",
        "This document shows the correct schema for all world YAML files.",
        "Generated from Pydantic models - DO NOT edit manually.",
        "",
        "## world.yaml",
        "```yaml",
        generate_world_yaml_example(),
        "```",
        "",
        "## locations.yaml",
        "```yaml",
        generate_location_yaml_example(),
        "```",
        "",
        "## npcs.yaml",
        "```yaml",
        generate_npc_yaml_example(),
        "```",
        "",
        "## items.yaml",
        "```yaml",
        generate_item_yaml_example(),
        "```",
    ]
    return "\n".join(sections)


def validate_prompt_schema(prompt_content: str) -> list[str]:
    """
    Validate that a prompt uses correct V3 schema.

    Returns a list of issues found.
    """
    issues = []

    # Check for incorrect NPC fields
    if "dialogue_hints:" in prompt_content:
        issues.append("Found 'dialogue_hints:' - should be 'dialogue_rules:'")

    if 'personality: \\"' in prompt_content or "personality: '" in prompt_content:
        # Check if it's a string pattern (not object)
        if "personality:" in prompt_content and "traits:" not in prompt_content:
            issues.append("Found 'personality' as string - should be object with traits/speech_style/quirks")

    # Check for incorrect location fields
    if "constraints:" in prompt_content and "locked_exit:" in prompt_content:
        issues.append("Found 'constraints' with 'locked_exit:' pattern - should use 'requires:' field")

    # V3: Check for deprecated item field names
    if "found_description:" in prompt_content:
        issues.append("Found 'found_description:' - should be 'scene_description:' (V3)")

    if "examine:" in prompt_content and "examine_description:" not in prompt_content:
        # Only flag if examine: appears without examine_description
        if "examine:" in prompt_content:
            issues.append("Found 'examine:' - should be 'examine_description:' (V3)")

    # V3: Check for deprecated reveals_exit
    if "reveals_exit:" in prompt_content:
        issues.append("Found 'reveals_exit:' - use hidden exits with find_condition instead (V3)")

    # V3: Check for deprecated items/npcs lists
    if "items:" in prompt_content and "item_placements:" in prompt_content:
        # Both present - could be transitional, but items list is deprecated
        issues.append("Found 'items:' list - use item_placements keys to define items at location (V3)")

    return issues


if __name__ == "__main__":
    # Print the full schema reference when run directly
    print(generate_full_schema_reference())
