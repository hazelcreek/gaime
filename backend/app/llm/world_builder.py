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
Generate valid YAML for four files. Each section should be complete and self-consistent.

1. WORLD: Overall world definition
2. LOCATIONS: All game locations with exits, atmosphere, items
3. NPCS: Characters with personalities and knowledge
4. ITEMS: Objects with descriptions and uses

Respond with JSON containing these four YAML strings:
{{
  "world_id": "snake-case-world-name",
  "world_yaml": "name: ...\\ntheme: ...\\n...",
  "locations_yaml": "location_id:\\n  name: ...\\n...",
  "npcs_yaml": "npc_id:\\n  name: ...\\n...",
  "items_yaml": "item_id:\\n  name: ...\\n..."
}}

## Guidelines
- Use snake_case for all IDs
- Make locations interconnected (exits should match)
- Give NPCs distinct personalities and useful knowledge
- Include items that serve puzzle or narrative purposes
- Add atmosphere descriptions for immersion
- Define clear constraints for the game
- Include at least one hidden secret or puzzle
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
                "content": "You are an expert game world designer. Create detailed, immersive game worlds."
            },
            {"role": "user", "content": user_prompt}
        ]
        
        response = await get_completion(
            messages,
            temperature=0.8,  # More creative for world building
            max_tokens=4000   # Worlds need more tokens
        )
        
        parsed = parse_json_response(response)
        
        # Validate the response has required fields
        required_fields = ["world_id", "world_yaml", "locations_yaml", "npcs_yaml", "items_yaml"]
        for field in required_fields:
            if field not in parsed:
                parsed[field] = ""
        
        # Validate YAML is parseable
        for field in ["world_yaml", "locations_yaml", "npcs_yaml", "items_yaml"]:
            try:
                yaml.safe_load(parsed[field])
            except yaml.YAMLError:
                # If invalid, wrap in a basic structure
                parsed[field] = f"# Generated content (may need editing)\n{parsed[field]}"
        
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

