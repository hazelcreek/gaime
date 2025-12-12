"""
World Generator - AI-assisted world generation from prompts.

Copied and adapted from backend/app/llm/world_builder.py for TUI independence.
"""

import logging
from pathlib import Path

import yaml

from gaime_builder.core.llm_client import get_completion, parse_json_response
from gaime_builder.core.prompt_loader import get_loader

logger = logging.getLogger(__name__)


def _get_world_builder_prompt() -> str:
    """Get the world builder prompt template from file."""
    return get_loader().get_prompt("world_builder", "world_builder_prompt.txt")


def _get_world_builder_system_message() -> str:
    """Get the world builder system message from file."""
    return get_loader().get_prompt("world_builder", "system_message.txt")


class WorldGenerator:
    """AI-assisted world generation."""
    
    def __init__(self, worlds_dir: Path):
        self.worlds_dir = worlds_dir
    
    async def generate(
        self,
        prompt: str,
        theme: str | None = None,
        num_locations: int = 6,
        num_npcs: int = 3,
        progress_callback=None
    ) -> dict:
        """
        Generate a new world from a prompt.
        
        Args:
            prompt: Description of the world to generate
            theme: Optional theme override
            num_locations: Number of locations to generate
            num_npcs: Number of NPCs to generate
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dict with world_id, world_yaml, locations_yaml, npcs_yaml, items_yaml
        """
        if progress_callback:
            progress_callback(0.1, "Preparing prompt...")
        
        world_builder_template = _get_world_builder_prompt()
        user_prompt = world_builder_template.format(
            theme=theme or "to be determined from description",
            num_locations=num_locations,
            num_npcs=num_npcs,
            prompt=prompt
        )
        
        system_message = _get_world_builder_system_message()
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt}
        ]
        
        if progress_callback:
            progress_callback(0.2, "Calling AI to generate world structure...")
        
        # Use gemini-3-pro-preview for world building
        response = await get_completion(
            messages,
            model="gemini/gemini-3-pro-preview",
            temperature=1.0,
            max_tokens=32768,
            response_format={"type": "json_object"}
        )
        
        if progress_callback:
            progress_callback(0.7, "Parsing AI response...")
        
        # Parse response
        parsed = parse_json_response(response, strict=True)
        
        # Validate response
        required_fields = ["world_id", "world_yaml", "locations_yaml", "npcs_yaml", "items_yaml"]
        missing_fields = [f for f in required_fields if f not in parsed]
        empty_fields = [f for f in required_fields if f in parsed and not parsed[f]]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        if empty_fields:
            raise ValueError(f"Empty content in fields: {', '.join(empty_fields)}")
        
        # Validate YAML is parseable
        if progress_callback:
            progress_callback(0.85, "Validating YAML content...")
        
        yaml_errors = []
        for field in ["world_yaml", "locations_yaml", "npcs_yaml", "items_yaml"]:
            try:
                content = yaml.safe_load(parsed[field])
                if content is None:
                    yaml_errors.append(f"{field} parsed to empty content")
            except yaml.YAMLError as e:
                yaml_errors.append(f"{field}: {str(e)[:100]}")
        
        if yaml_errors:
            raise ValueError(f"Invalid YAML: {'; '.join(yaml_errors)}")
        
        if progress_callback:
            progress_callback(1.0, "World generated successfully!")
        
        parsed["message"] = "World generated successfully. Review and edit as needed."
        return parsed
    
    def save_world(self, world_id: str, content: dict):
        """Save generated world content to files."""
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
        
        return world_path
    
    def list_worlds(self) -> list[dict]:
        """List all available worlds."""
        worlds = []
        
        if not self.worlds_dir.exists():
            return worlds
        
        for world_path in self.worlds_dir.iterdir():
            if world_path.is_dir():
                world_yaml = world_path / "world.yaml"
                if world_yaml.exists():
                    try:
                        with open(world_yaml) as f:
                            data = yaml.safe_load(f) or {}
                        worlds.append({
                            "id": world_path.name,
                            "name": data.get("name", world_path.name),
                            "theme": data.get("theme", ""),
                            "path": str(world_path)
                        })
                    except Exception:
                        worlds.append({
                            "id": world_path.name,
                            "name": world_path.name,
                            "theme": "",
                            "path": str(world_path)
                        })
        
        return sorted(worlds, key=lambda w: w["name"])
    
    def get_world_locations(self, world_id: str) -> list[dict]:
        """Get all locations for a world."""
        locations_yaml = self.worlds_dir / world_id / "locations.yaml"
        
        if not locations_yaml.exists():
            return []
        
        with open(locations_yaml) as f:
            locations = yaml.safe_load(f) or {}
        
        result = []
        for loc_id, loc_data in locations.items():
            result.append({
                "id": loc_id,
                "name": loc_data.get("name", loc_id),
                "atmosphere": loc_data.get("atmosphere", "")
            })
        
        return result
    
    def validate_world(self, world_id: str) -> tuple[bool, list[str]]:
        """Validate a world's YAML files."""
        world_path = self.worlds_dir / world_id
        errors = []
        warnings = []
        
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
                
                if filename == "world.yaml":
                    if "name" not in data:
                        errors.append("world.yaml missing 'name'")
                    if "player" not in data:
                        errors.append("world.yaml missing 'player' setup")
                    if "starting_situation" not in data:
                        warnings.append("world.yaml missing 'starting_situation'")
                    if "victory" not in data:
                        warnings.append("world.yaml missing 'victory' condition")
                
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML in {filename}: {e}")
        
        return len(errors) == 0, errors + [f"WARNING: {w}" for w in warnings]

