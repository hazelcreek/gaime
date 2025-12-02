"""
World Builder - AI-assisted world generation from prompts
"""

import os
from pathlib import Path

import yaml

from app.llm.client import get_completion, parse_json_response


WORLD_BUILDER_PROMPT = '''You are a game world designer. Create a complete text adventure game world based on the user's description.

Generate a cohesive world with interconnected locations, interesting NPCs, and meaningful items.

## Requirements
- Theme: {theme}
- Number of locations: {num_locations}
- Number of NPCs: {num_npcs}

## User's Description
{prompt}

## Output Format
You MUST respond with valid JSON containing four YAML strings. Follow this EXACT structure:

```json
{{
  "world_id": "snake-case-world-name",
  "world_yaml": "name: \\"World Name\\"\\ntheme: \\"theme here\\"\\ntone: \\"tone here\\"\\n\\npremise: |\\n  Description of the world premise...\\n\\nplayer:\\n  starting_location: first_location_id\\n  starting_inventory:\\n    - item_id\\n  stats:\\n    health: 100\\n\\nconstraints:\\n  - \\"Constraint 1\\"\\n  - \\"Constraint 2\\"\\n\\ncommands:\\n  help: \\"Display available commands\\"\\n  look: \\"Examine surroundings\\"\\n  inventory: \\"Check inventory\\"\\n  go: \\"Move in a direction\\"",
  "locations_yaml": "location_id:\\n  name: \\"Location Name\\"\\n  atmosphere: |\\n    Atmospheric description...\\n  exits:\\n    north: other_location_id\\n  items:\\n    - item_id\\n  npcs: []\\n  details:\\n    thing: \\"Description of thing\\"",
  "npcs_yaml": "npc_id:\\n  name: \\"NPC Name\\"\\n  role: \\"Their role\\"\\n  location: location_id\\n  personality: \\"Their personality\\"\\n  knowledge:\\n    - \\"Something they know\\"\\n  dialogue_hints:\\n    greeting: \\"How they greet\\"",
  "items_yaml": "item_id:\\n  name: \\"Item Name\\"\\n  portable: true\\n  examine: |\\n    Description when examined...\\n  found_description: \\"How it appears in the room\\"\\n  take_description: \\"Message when taken\\""
}}
```

CRITICAL RULES FOR JSON OUTPUT:
1. Use \\n for newlines inside YAML strings
2. Escape all quotes inside YAML with backslash: \\"
3. Use | for multi-line YAML text blocks
4. Ensure all location exits reference valid location IDs
5. Ensure player starting_location matches a defined location
6. Ensure player starting_inventory items are defined in items_yaml
7. Each YAML string must be valid YAML when newlines are unescaped

## Guidelines
- Use snake_case for all IDs (e.g., dark_forest, old_hermit, rusty_key)
- Make locations interconnected (exits should match bidirectionally)
- Give NPCs distinct personalities and useful knowledge
- Include items that serve puzzle or narrative purposes
- Add rich atmosphere descriptions for immersion
- Define 3-5 clear constraints/rules for the game
- Include at least one hidden secret or puzzle
- Create a compelling premise that hooks the player
'''


class WorldBuilder:
    """AI-assisted world generation"""
    
    def __init__(self, worlds_dir: str | None = None):
        if worlds_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            worlds_dir = project_root / "worlds"
        self.worlds_dir = Path(worlds_dir)
    
    async def generate(
        self,
        prompt: str,
        theme: str | None = None,
        num_locations: int = 6,
        num_npcs: int = 3
    ) -> dict:
        """Generate a new world from a prompt"""
        
        user_prompt = WORLD_BUILDER_PROMPT.format(
            theme=theme or "to be determined from description",
            num_locations=num_locations,
            num_npcs=num_npcs,
            prompt=prompt
        )
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert game world designer. Create detailed, immersive game worlds. Always respond with valid JSON containing YAML strings as specified in the prompt."
            },
            {"role": "user", "content": user_prompt}
        ]
        
        response = await get_completion(
            messages,
            temperature=0.8,  # More creative for world building
            max_tokens=4000   # Worlds need more tokens
        )
        
        parsed = parse_json_response(response)
        
        # Validate the response has required fields with actual content
        required_fields = ["world_id", "world_yaml", "locations_yaml", "npcs_yaml", "items_yaml"]
        missing_fields = []
        empty_fields = []
        
        for field in required_fields:
            if field not in parsed:
                missing_fields.append(field)
            elif not parsed[field] or (isinstance(parsed[field], str) and not parsed[field].strip()):
                empty_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"World generation failed: Missing required fields: {', '.join(missing_fields)}. The AI did not return a valid world structure. Please try again.")
        
        if empty_fields:
            raise ValueError(f"World generation failed: Empty content in fields: {', '.join(empty_fields)}. The AI returned incomplete content. Please try again with a more detailed description.")
        
        # Validate YAML is parseable and has content
        yaml_errors = []
        for field in ["world_yaml", "locations_yaml", "npcs_yaml", "items_yaml"]:
            try:
                content = yaml.safe_load(parsed[field])
                if content is None:
                    yaml_errors.append(f"{field} parsed to empty content")
            except yaml.YAMLError as e:
                yaml_errors.append(f"{field}: {str(e)[:100]}")
        
        if yaml_errors:
            raise ValueError(f"World generation produced invalid YAML: {'; '.join(yaml_errors)}. Please try again.")
        
        parsed["message"] = "World generated successfully. Review and edit as needed."
        return parsed
    
    def save_world(self, world_id: str, content: dict):
        """Save generated world content to files"""
        world_path = self.worlds_dir / world_id
        world_path.mkdir(parents=True, exist_ok=True)
        
        files = {
            "world.yaml": content.get("world_yaml", ""),
            "locations.yaml": content.get("locations_yaml", ""),
            "npcs.yaml": content.get("npcs_yaml", ""),
            "items.yaml": content.get("items_yaml", "")
        }
        
        for filename, yaml_content in files.items():
            file_path = world_path / filename
            with open(file_path, "w") as f:
                f.write(yaml_content)
    
    def validate_world(self, world_id: str) -> tuple[bool, list[str]]:
        """Validate a world's YAML files"""
        world_path = self.worlds_dir / world_id
        errors = []
        
        required_files = ["world.yaml", "locations.yaml", "npcs.yaml", "items.yaml"]
        
        for filename in required_files:
            file_path = world_path / filename
            
            if not file_path.exists():
                errors.append(f"Missing file: {filename}")
                continue
            
            try:
                with open(file_path) as f:
                    data = yaml.safe_load(f)
                
                if data is None:
                    errors.append(f"Empty file: {filename}")
                    continue
                
                # Basic validation
                if filename == "world.yaml":
                    if "name" not in data:
                        errors.append("world.yaml missing 'name'")
                    if "player" not in data:
                        errors.append("world.yaml missing 'player' setup")
                
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML in {filename}: {e}")
        
        return len(errors) == 0, errors

