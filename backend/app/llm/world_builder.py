"""
World Builder - AI-assisted world generation from prompts
"""

import logging
from pathlib import Path

import yaml

from app.llm.client import get_completion, parse_json_response
from app.llm.prompt_loader import get_loader

logger = logging.getLogger(__name__)


def _get_world_builder_prompt() -> str:
    """Get the world builder prompt template from file."""
    return get_loader().get_prompt("world_builder", "world_builder_prompt.txt")


def _get_world_builder_system_message() -> str:
    """Get the world builder system message from file."""
    return get_loader().get_prompt("world_builder", "system_message.txt")


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
        style_preset: str | None = None,
        num_locations: int = 6,
        num_npcs: int = 3
    ) -> dict:
        """Generate a new world from a prompt"""
        
        logger.info(f"Generating world: theme={theme}, locations={num_locations}, npcs={num_npcs}")
        logger.debug(f"User prompt: {prompt[:100]}..." if len(prompt) > 100 else f"User prompt: {prompt}")
        
        world_builder_template = _get_world_builder_prompt()
        user_prompt = world_builder_template.format(
            theme=theme or "to be determined from description",
            style_preset=style_preset or "to be chosen by the author",
            num_locations=num_locations,
            num_npcs=num_npcs,
            prompt=prompt
        )
        
        system_message = _get_world_builder_system_message()
        messages = [
            {
                "role": "system",
                "content": system_message
            },
            {"role": "user", "content": user_prompt}
        ]
        
        logger.info("Calling LLM for world generation...")
        # Use gemini-3-pro-preview for world building (has thinking/reasoning)
        # Need very high max_tokens to account for:
        # 1. Thinking tokens (model's internal reasoning)
        # 2. Large output (4 YAML files with detailed content)
        # For 6+ locations and 3+ NPCs, the output alone can be 8k+ tokens
        # Note: Gemini 3 models require temperature=1.0 for best results
        response = await get_completion(
            messages,
            model="gemini/gemini-3-pro-preview",
            temperature=1.0,  # Required for Gemini 3 models
            max_tokens=32768,  # Very high limit for thinking + large worlds
            response_format={"type": "json_object"}
        )
        
        logger.info(f"LLM response received, length: {len(response) if response else 0}")
        if response:
            logger.debug(f"Raw response preview: {response[:300]}..." if len(response) > 300 else f"Raw response: {response}")
        else:
            logger.error("LLM returned None or empty response")
        
        # Use strict mode to get clear errors instead of game-master fallbacks
        parsed = parse_json_response(response, strict=True)
        logger.info(f"JSON parsed successfully, keys: {list(parsed.keys())}")
        
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

        # Save spoiler metadata separately so playthroughs stay spoiler-free.
        spoiler_free_pitch = content.get("spoiler_free_pitch")
        spoilers = content.get("spoilers")
        if spoiler_free_pitch or spoilers:
            import json
            spoilers_path = world_path / "_world_builder_spoilers.json"
            with open(spoilers_path, "w") as f:
                json.dump(
                    {
                        "world_id": world_id,
                        "spoiler_free_pitch": spoiler_free_pitch,
                        "spoilers": spoilers,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
    
    def validate_world(self, world_id: str) -> tuple[bool, list[str]]:
        """Validate a world's YAML files"""
        world_path = self.worlds_dir / world_id
        errors = []
        warnings = []
        
        required_files = ["world.yaml", "locations.yaml", "npcs.yaml", "items.yaml"]
        loaded_data = {}
        
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
                
                loaded_data[filename] = data
                
                # Basic validation
                if filename == "world.yaml":
                    if "name" not in data:
                        errors.append("world.yaml missing 'name'")
                    if "player" not in data:
                        errors.append("world.yaml missing 'player' setup")
                    if "starting_situation" not in data or not data.get("starting_situation"):
                        warnings.append("world.yaml missing 'starting_situation' - players may be confused about why they can act")
                    if "victory" not in data:
                        warnings.append("world.yaml missing 'victory' condition - game has no ending")
                
            except yaml.YAMLError as e:
                errors.append(f"Invalid YAML in {filename}: {e}")
        
        # Cross-file validation
        if "items.yaml" in loaded_data:
            items = loaded_data["items.yaml"]
            for item_id, item_data in items.items():
                if isinstance(item_data, dict):
                    if not item_data.get("found_description"):
                        warnings.append(f"Item '{item_id}' missing 'found_description' - item may not be discoverable")
        
        if "locations.yaml" in loaded_data and "world.yaml" in loaded_data:
            locations = loaded_data["locations.yaml"]
            world = loaded_data["world.yaml"]
            
            # Check starting location exists
            starting_loc = world.get("player", {}).get("starting_location")
            if starting_loc and starting_loc not in locations:
                errors.append(f"Starting location '{starting_loc}' not found in locations.yaml")
            
            # Check victory location exists
            victory = world.get("victory", {})
            if victory and victory.get("location"):
                if victory["location"] not in locations:
                    errors.append(f"Victory location '{victory['location']}' not found in locations.yaml")
            
            # Check exits have narrative context
            for loc_id, loc_data in locations.items():
                if isinstance(loc_data, dict):
                    exits = loc_data.get("exits", {})
                    details = loc_data.get("details", {})
                    for direction in exits.keys():
                        if direction not in details:
                            warnings.append(f"Location '{loc_id}' exit '{direction}' has no detail description")
                    
                    # Check item placements
                    items = loc_data.get("items", [])
                    item_placements = loc_data.get("item_placements", {})
                    for item_id in items:
                        if item_id not in item_placements:
                            warnings.append(f"Location '{loc_id}' item '{item_id}' has no placement description")
                    
                    # Check NPC placements
                    npcs = loc_data.get("npcs", [])
                    npc_placements = loc_data.get("npc_placements", {})
                    for npc_id in npcs:
                        if npc_id not in npc_placements:
                            warnings.append(f"Location '{loc_id}' NPC '{npc_id}' has no placement description")
        
        # Log warnings but don't fail validation
        for warning in warnings:
            logger.warning(f"World '{world_id}': {warning}")
        
        return len(errors) == 0, errors + [f"WARNING: {w}" for w in warnings]

