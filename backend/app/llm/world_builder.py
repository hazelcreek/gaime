"""
World Builder - AI-assisted world generation from prompts
"""

import logging
from pathlib import Path

import yaml

from app.llm.client import get_completion, parse_json_response

logger = logging.getLogger(__name__)


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
  "world_yaml": "name: \\"World Name\\"\\ntheme: \\"theme here\\"\\ntone: \\"tone here\\"\\n\\npremise: |\\n  Description of the world premise...\\n\\nstarting_situation: |\\n  Describe WHY the player can act NOW. What event, opportunity, or change has occurred that enables the adventure to begin? This is crucial for immersion.\\n\\nvictory:\\n  location: final_location_id\\n  item: optional_required_item\\n  flag: optional_required_flag\\n  narrative: |\\n    The ending narrative when the player wins...\\n\\nplayer:\\n  starting_location: first_location_id\\n  starting_inventory:\\n    - item_id\\n  stats:\\n    health: 100\\n\\nconstraints:\\n  - \\"Constraint 1\\"\\n  - \\"Constraint 2\\"\\n\\ncommands:\\n  help: \\"Display available commands\\"\\n  look: \\"Examine surroundings\\"\\n  inventory: \\"Check inventory\\"\\n  go: \\"Move in a direction\\"",
  "locations_yaml": "location_id:\\n  name: \\"Location Name\\"\\n  atmosphere: |\\n    Atmospheric description that establishes WHERE the player is...\\n  exits:\\n    north: other_location_id\\n  items:\\n    - item_id\\n  item_placements:\\n    item_id: \\"WHERE in this room the item is located (e.g., 'lies crumpled on the dusty side table near the door')\\"\\n  npcs:\\n    - npc_id\\n  npc_placements:\\n    npc_id: \\"WHERE in this room the NPC is positioned (e.g., 'stands rigidly by the grandfather clock, pale hands clasped')\\"\\n  details:\\n    thing: \\"Description of examinable thing\\"\\n    north: \\"Narrative description of what the north exit looks like (e.g., 'A flickering barrier blocks the passage north')\\"",
  "npcs_yaml": "npc_id:\\n  name: \\"NPC Name\\"\\n  role: \\"Their role\\"\\n  location: location_id\\n  personality: \\"Their personality\\"\\n  knowledge:\\n    - \\"Something they know\\"\\n  dialogue_hints:\\n    greeting: \\"How they greet\\"",
  "items_yaml": "item_id:\\n  name: \\"Item Name\\"\\n  portable: true\\n  examine: |\\n    Description when examined...\\n  found_description: \\"REQUIRED: How the item appears naturally in the room scene. This MUST be provided for every item so it can be mentioned when the player looks around.\\"\\n  take_description: \\"Message when taken\\""
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

## CRITICAL CONSISTENCY RULES (MUST FOLLOW):
1. Every exit MUST have narrative justification in the atmosphere or details. Add a detail entry for each exit direction explaining what it looks like (e.g., details.north: "A heavy wooden door leads north")
2. The starting_situation MUST explain WHY the player can begin acting NOW (e.g., "The guard fell asleep", "The storm knocked out the power", "You just discovered a hidden key")
3. Every item MUST have a found_description that naturally integrates into scene description. This is how items become discoverable!
4. Include a victory condition with at least a target location, and optionally a required item or flag
5. The starting location must make narrative sense - if the player is imprisoned, explain why they can leave their cell
6. Exits should feel realistic - don't have open passages where there should be locked doors
7. Every item in a location MUST have an item_placements entry describing WHERE in the room it is (e.g., "lies on the dusty mantelpiece", "rests beneath the window sill")
8. Every NPC in a location MUST have an npc_placements entry describing WHERE they are positioned (e.g., "stands by the fireplace, warming his hands", "sits hunched at the desk")

## Guidelines
- Use snake_case for all IDs (e.g., dark_forest, old_hermit, rusty_key)
- Make locations interconnected (exits should match bidirectionally)
- Give NPCs distinct personalities and useful knowledge
- Include items that serve puzzle or narrative purposes
- Add rich atmosphere descriptions for immersion
- Define 3-5 clear constraints/rules for the game
- Include at least one hidden secret or puzzle
- Create a compelling premise that hooks the player
- Every location should clearly establish WHERE the player is
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
        
        logger.info(f"Generating world: theme={theme}, locations={num_locations}, npcs={num_npcs}")
        logger.debug(f"User prompt: {prompt[:100]}..." if len(prompt) > 100 else f"User prompt: {prompt}")
        
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
        
        logger.info("Calling LLM for world generation...")
        # Use gemini-3-pro-preview for world building (has thinking/reasoning)
        # Need higher max_tokens to account for both thinking + output tokens
        response = await get_completion(
            messages,
            model="gemini/gemini-3-pro-preview",
            temperature=0.8,  # More creative for world building
            max_tokens=16384  # High limit for thinking tokens + output
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

