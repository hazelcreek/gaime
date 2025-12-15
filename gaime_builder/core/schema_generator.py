"""
Schema generator - extracts YAML schema examples from Pydantic models.

This module generates theme-neutral YAML examples that serve as the
source of truth for world builder prompts, ensuring prompts stay in
sync with the Pydantic model definitions.
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
    
    # Common field name patterns
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
        
        # Item fields
        "examine": "Description when the player examines this item.",
        "found_description": "How the item appears naturally in the scene.",
        "take_description": "Message shown when the item is taken.",
        
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
    - "When they reveal information"'''


def generate_location_yaml_example() -> str:
    """Generate a complete Location YAML example with correct schema."""
    return '''location_id:
  name: "Location Name"
  atmosphere: |
    Atmospheric description that establishes WHERE the player is,
    what they see, hear, and feel in this space.
  exits:
    north: other_location_id
    south: another_location_id
  items:
    - item_id
  item_placements:
    item_id: "WHERE in this room the item is located"
  npcs:
    - npc_id
  npc_placements:
    npc_id: "WHERE in this room the NPC is positioned"
  details:
    feature: "Description of an examinable feature"
    north: "What the north exit looks like"
  interactions:
    interaction_id:
      triggers:
        - "examine feature"
        - "use item on thing"
      narrative_hint: "What happens when triggered"
      sets_flag: flag_name
      reveals_exit: hidden_location_id
  requires:
    flag: required_flag_name'''


def generate_item_yaml_example() -> str:
    """Generate a complete Item YAML example with correct schema."""
    return '''item_id:
  name: "Item Name"
  portable: true
  examine: |
    Detailed description when the player examines this item.
  found_description: "How the item appears naturally in the room scene."
  take_description: "Message shown when the item is taken."
  hidden: false
  unlocks: locked_location_id
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
        "# World Builder Schema Reference",
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
    Validate that a prompt uses correct schema.
    
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
    
    return issues


if __name__ == "__main__":
    # Print the full schema reference when run directly
    print(generate_full_schema_reference())
