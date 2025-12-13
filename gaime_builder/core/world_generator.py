"""
World Generator - AI-assisted world generation from prompts.

Uses two-pass generation for richer puzzle design:
  Pass 1: Design brief (puzzle structure, gates, secrets)
  Pass 2: YAML synthesis from the brief

Copied and adapted from backend/app/llm/world_builder.py for TUI independence.
"""

import json
import logging
import traceback
from pathlib import Path

import yaml

from gaime_builder.core.llm_client import get_completion, get_model_string, parse_json_response
from gaime_builder.core.prompt_loader import get_loader

logger = logging.getLogger(__name__)


def _get_design_brief_prompt() -> str:
    """Get the design brief prompt template (Pass 1)."""
    return get_loader().get_prompt("world_builder", "design_brief_prompt.txt")


def _get_world_builder_prompt() -> str:
    """Get the world builder prompt template (Pass 2)."""
    return get_loader().get_prompt("world_builder", "world_builder_prompt.txt")


def _get_world_builder_system_message() -> str:
    """Get the world builder system message from file."""
    return get_loader().get_prompt("world_builder", "system_message.txt")


class WorldGenerator:
    """AI-assisted world generation with two-pass design."""
    
    def __init__(self, worlds_dir: Path):
        self.worlds_dir = worlds_dir
        logger.info(f"WorldGenerator initialized with worlds_dir: {worlds_dir}")
    
    async def _generate_design_brief(
        self,
        prompt: str,
        theme: str | None,
        num_locations: int,
        num_npcs: int,
        progress_callback=None
    ) -> dict:
        """
        Pass 1: Generate the design brief (puzzle structure only).
        
        Returns:
            Dict with world_id, spoiler_free_pitch, design_brief
        """
        logger.info("=" * 50)
        logger.info("PASS 1: Generating design brief")
        logger.info(f"  Theme: {theme}")
        logger.info(f"  Locations: {num_locations}, NPCs: {num_npcs}")
        logger.info(f"  Prompt: {prompt[:100]}...")
        
        if progress_callback:
            progress_callback(0.05, "Preparing design brief prompt...")
        
        try:
            logger.debug("Loading design brief template...")
            design_brief_template = _get_design_brief_prompt()
            logger.debug(f"Template loaded, length: {len(design_brief_template)} chars")
            
            user_prompt = design_brief_template.format(
                theme=theme or "to be determined from description",
                num_locations=num_locations,
                num_npcs=num_npcs,
                prompt=prompt
            )
            logger.debug(f"User prompt formatted, length: {len(user_prompt)} chars")
            
            system_message = _get_world_builder_system_message()
            logger.debug(f"System message loaded, length: {len(system_message)} chars")
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
            
            if progress_callback:
                progress_callback(0.1, "Pass 1: Designing puzzle structure...")
            
            logger.info(f"Calling LLM for design brief (model: {get_model_string()})...")
            logger.info("This may take 30-60 seconds...")
            
            response = await get_completion(
                messages,
                temperature=1.0,
                max_tokens=16384,
                response_format={"type": "json_object"}
            )
            
            logger.info(f"LLM response received, length: {len(response) if response else 0} chars")
            logger.debug(f"Response preview: {response[:500] if response else 'None'}...")
            
            if progress_callback:
                progress_callback(0.3, "Parsing design brief...")
            
            logger.debug("Parsing JSON response...")
            parsed = parse_json_response(response, strict=True)
            logger.info(f"Design brief parsed successfully, keys: {list(parsed.keys())}")
            
            # Validate design brief
            required_fields = ["world_id", "spoiler_free_pitch", "design_brief"]
            missing_fields = [f for f in required_fields if f not in parsed]
            
            if missing_fields:
                error_msg = f"Design brief missing fields: {', '.join(missing_fields)}"
                logger.error(error_msg)
                logger.error(f"Received keys: {list(parsed.keys())}")
                raise ValueError(error_msg)
            
            logger.info(f"Design brief validated: world_id={parsed.get('world_id')}")
            return parsed
            
        except Exception as e:
            logger.error(f"PASS 1 FAILED: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def _generate_yaml_from_brief(
        self,
        prompt: str,
        theme: str | None,
        num_locations: int,
        num_npcs: int,
        design_brief: dict,
        progress_callback=None
    ) -> dict:
        """
        Pass 2: Generate YAML from the design brief.
        
        Returns:
            Dict with world_id, world_yaml, locations_yaml, npcs_yaml, items_yaml
        """
        logger.info("=" * 50)
        logger.info("PASS 2: Generating YAML from design brief")
        logger.info(f"  World ID: {design_brief.get('world_id')}")
        
        if progress_callback:
            progress_callback(0.35, "Preparing YAML synthesis prompt...")
        
        try:
            logger.debug("Loading world builder template...")
            world_builder_template = _get_world_builder_prompt()
            logger.debug(f"Template loaded, length: {len(world_builder_template)} chars")
            
            # Format design brief as readable JSON for the prompt
            design_brief_json = json.dumps(design_brief, indent=2)
            logger.debug(f"Design brief JSON length: {len(design_brief_json)} chars")
            
            user_prompt = world_builder_template.format(
                theme=theme or "to be determined from description",
                num_locations=num_locations,
                num_npcs=num_npcs,
                prompt=prompt,
                design_brief=design_brief_json,
                world_id=design_brief.get("world_id", "generated-world")
            )
            logger.debug(f"User prompt formatted, length: {len(user_prompt)} chars")
            
            system_message = _get_world_builder_system_message()
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ]
            
            if progress_callback:
                progress_callback(0.4, "Pass 2: Generating detailed YAML...")
            
            logger.info(f"Calling LLM for YAML synthesis (model: {get_model_string()})...")
            logger.info("This may take 60-120 seconds for detailed YAML...")
            
            response = await get_completion(
                messages,
                temperature=1.0,
                max_tokens=32768,
                response_format={"type": "json_object"}
            )
            
            logger.info(f"LLM response received, length: {len(response) if response else 0} chars")
            logger.debug(f"Response preview: {response[:500] if response else 'None'}...")
            
            if progress_callback:
                progress_callback(0.75, "Parsing YAML response...")
            
            logger.debug("Parsing JSON response...")
            parsed = parse_json_response(response, strict=True)
            logger.info(f"YAML response parsed, keys: {list(parsed.keys())}")
            
            # Validate response
            required_fields = ["world_id", "world_yaml", "locations_yaml", "npcs_yaml", "items_yaml"]
            missing_fields = [f for f in required_fields if f not in parsed]
            empty_fields = [f for f in required_fields if f in parsed and not parsed[f]]
            
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            if empty_fields:
                error_msg = f"Empty content in fields: {', '.join(empty_fields)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Validate YAML is parseable
            if progress_callback:
                progress_callback(0.85, "Validating YAML content...")
            
            logger.debug("Validating YAML content...")
            yaml_errors = []
            for field in ["world_yaml", "locations_yaml", "npcs_yaml", "items_yaml"]:
                try:
                    content = yaml.safe_load(parsed[field])
                    if content is None:
                        yaml_errors.append(f"{field} parsed to empty content")
                        logger.warning(f"{field} is empty after parsing")
                    else:
                        logger.debug(f"{field} validated successfully")
                except yaml.YAMLError as e:
                    error_detail = f"{field}: {str(e)[:100]}"
                    yaml_errors.append(error_detail)
                    logger.error(f"YAML validation failed for {field}: {e}")
            
            if yaml_errors:
                error_msg = f"Invalid YAML: {'; '.join(yaml_errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info("PASS 2 completed successfully")
            return parsed
            
        except Exception as e:
            logger.error(f"PASS 2 FAILED: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def generate(
        self,
        prompt: str,
        theme: str | None = None,
        num_locations: int = 6,
        num_npcs: int = 3,
        progress_callback=None
    ) -> dict:
        """
        Generate a new world from a prompt using two-pass generation.
        
        Pass 1: Design brief (puzzle structure, gates, secrets)
        Pass 2: YAML synthesis from the brief
        
        Args:
            prompt: Description of the world to generate
            theme: Optional theme override
            num_locations: Number of locations to generate
            num_npcs: Number of NPCs to generate
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dict with:
              - world_id, world_yaml, locations_yaml, npcs_yaml, items_yaml (YAML content)
              - spoiler_free_pitch (safe to show)
              - design_brief (contains spoilers)
        """
        logger.info("=" * 60)
        logger.info("WORLD GENERATION STARTED")
        logger.info(f"  Model: {get_model_string()}")
        logger.info(f"  Theme: {theme}")
        logger.info(f"  Locations: {num_locations}, NPCs: {num_npcs}")
        logger.info(f"  Prompt length: {len(prompt)} chars")
        logger.info("=" * 60)
        
        try:
            # Pass 1: Generate design brief
            brief_result = await self._generate_design_brief(
                prompt=prompt,
                theme=theme,
                num_locations=num_locations,
                num_npcs=num_npcs,
                progress_callback=progress_callback
            )
            
            logger.info("Pass 1 complete, starting Pass 2...")
            
            # Pass 2: Generate YAML from brief
            yaml_result = await self._generate_yaml_from_brief(
                prompt=prompt,
                theme=theme,
                num_locations=num_locations,
                num_npcs=num_npcs,
                design_brief=brief_result,
                progress_callback=progress_callback
            )
            
            if progress_callback:
                progress_callback(0.95, "Finalizing world...")
            
            # Combine results
            result = {
                **yaml_result,
                "spoiler_free_pitch": brief_result.get("spoiler_free_pitch", ""),
                "design_brief": brief_result.get("design_brief", {}),
                "world_name": brief_result.get("world_name", yaml_result.get("world_id", "")),
                "message": "World generated successfully. Review and edit as needed."
            }
            
            if progress_callback:
                progress_callback(1.0, "World generated successfully!")
            
            logger.info("=" * 60)
            logger.info("WORLD GENERATION COMPLETED SUCCESSFULLY")
            logger.info(f"  World ID: {result.get('world_id')}")
            logger.info(f"  World Name: {result.get('world_name')}")
            logger.info("=" * 60)
            
            return result
            
        except Exception as e:
            logger.error("=" * 60)
            logger.error("WORLD GENERATION FAILED")
            logger.error(f"  Error: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            logger.error("=" * 60)
            raise
    
    def save_world(self, world_id: str, content: dict, style_preset: str | None = None):
        """Save generated world content to files.
        
        Args:
            world_id: Unique identifier for the world
            content: Dict with world_yaml, locations_yaml, npcs_yaml, items_yaml,
                     and optionally design_brief and spoiler_free_pitch
            style_preset: Optional visual style preset name to inject into world.yaml
        """
        logger.info(f"Saving world: {world_id}")
        
        world_path = self.worlds_dir / world_id
        world_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"World directory created: {world_path}")
        
        # Handle world.yaml with style injection
        world_yaml_content = content.get("world_yaml", "")
        if style_preset and world_yaml_content:
            world_yaml_content = self._inject_style_preset(world_yaml_content, style_preset)
            logger.debug(f"Style preset injected: {style_preset}")
        
        files = {
            "world.yaml": world_yaml_content,
            "locations.yaml": content.get("locations_yaml", ""),
            "npcs.yaml": content.get("npcs_yaml", ""),
            "items.yaml": content.get("items_yaml", "")
        }
        
        for filename, yaml_content in files.items():
            file_path = world_path / filename
            with open(file_path, "w") as f:
                f.write(yaml_content)
            logger.debug(f"Saved {filename} ({len(yaml_content)} chars)")
        
        # Save spoilers.md if design brief is present
        if "design_brief" in content or "spoiler_free_pitch" in content:
            self._save_spoilers(world_path, content)
            logger.debug("Saved spoilers.md")
        
        logger.info(f"World saved successfully to: {world_path}")
        return world_path
    
    def _save_spoilers(self, world_path: Path, content: dict) -> None:
        """Save the design brief as spoilers.md."""
        spoilers_path = world_path / "spoilers.md"
        
        world_name = content.get("world_name", world_path.name)
        pitch = content.get("spoiler_free_pitch", "")
        brief = content.get("design_brief", {})
        
        lines = [
            f"# Design Brief: {world_name}",
            "",
            "## Spoiler-Free Pitch",
            pitch,
            "",
            "---",
            "",
            "## SPOILERS BELOW",
            "",
        ]
        
        # Puzzle Threads
        if "puzzle_threads" in brief:
            lines.append("## Puzzle Threads")
            for i, thread in enumerate(brief["puzzle_threads"], 1):
                name = thread.get("name", f"Thread {i}")
                is_primary = thread.get("is_primary", False)
                marker = " (Primary)" if is_primary else ""
                lines.append(f"\n### {i}. {name}{marker}")
                
                gate_type = thread.get("gate_type", "")
                gate_desc = thread.get("gate_description", "")
                if gate_type:
                    lines.append(f"**Gate Type**: {gate_type}")
                if gate_desc:
                    lines.append(f"**Gate**: {gate_desc}")
                
                steps = thread.get("steps", [])
                if steps:
                    lines.append("\n**Steps**:")
                    for j, step in enumerate(steps, 1):
                        lines.append(f"{j}. {step}")
            lines.append("")
        
        # Navigation Loop
        if "navigation_loop" in brief:
            loop = brief["navigation_loop"]
            lines.append("## Navigation Loop (Shortcut)")
            lines.append(f"- **Description**: {loop.get('description', '')}")
            lines.append(f"- **Unlocked by**: {loop.get('unlocked_by', '')}")
            connects = loop.get("connects", [])
            if connects:
                lines.append(f"- **Connects**: {' ↔ '.join(connects)}")
            lines.append("")
        
        # Gate Types Used
        if "gate_types_used" in brief:
            lines.append("## Gate Types Used")
            for gate in brief["gate_types_used"]:
                lines.append(f"- {gate}")
            lines.append("")
        
        # Critical Items
        if "critical_items" in brief:
            lines.append("## Critical Items")
            for item in brief["critical_items"]:
                name = item.get("name", item.get("id", "Unknown"))
                purpose = item.get("purpose", "")
                location = item.get("location_hint", "")
                lines.append(f"- **{name}**: {purpose}")
                if location:
                    lines.append(f"  - Found: {location}")
            lines.append("")
        
        # Optional Secrets
        if "optional_secrets" in brief:
            lines.append("## Optional Secrets")
            for secret in brief["optional_secrets"]:
                name = secret.get("name", "Unknown")
                secret_type = secret.get("type", "")
                desc = secret.get("description", "")
                hint = secret.get("discovery_hint", "")
                lines.append(f"\n### {name}")
                if secret_type:
                    lines.append(f"**Type**: {secret_type}")
                if desc:
                    lines.append(f"{desc}")
                if hint:
                    lines.append(f"**Discovery**: {hint}")
            lines.append("")
        
        # Environmental Storytelling
        if "environmental_storytelling" in brief:
            lines.append("## Environmental Storytelling")
            env = brief["environmental_storytelling"]
            for location, detail in env.items():
                lines.append(f"- **{location}**: {detail}")
            lines.append("")
        
        # Victory Condition
        if "victory_condition" in brief:
            victory = brief["victory_condition"]
            lines.append("## Victory Condition")
            lines.append(f"- **Location**: {victory.get('location', '')}")
            items = victory.get("required_items", [])
            if items:
                lines.append(f"- **Required Items**: {', '.join(items)}")
            flags = victory.get("required_flags", [])
            if flags:
                lines.append(f"- **Required Flags**: {', '.join(flags)}")
            narrative = victory.get("narrative_summary", "")
            if narrative:
                lines.append(f"- **Summary**: {narrative}")
            lines.append("")
        
        # Key Constraints
        if "key_constraints" in brief:
            lines.append("## Key Constraints")
            for constraint in brief["key_constraints"]:
                lines.append(f"- {constraint}")
            lines.append("")
        
        with open(spoilers_path, "w") as f:
            f.write("\n".join(lines))
    
    def _inject_style_preset(self, world_yaml: str, style_preset: str) -> str:
        """Inject a style preset into world.yaml content.
        
        Adds the style field after theme/tone if present, otherwise after name.
        """
        lines = world_yaml.split('\n')
        result_lines = []
        style_added = False
        
        for i, line in enumerate(lines):
            result_lines.append(line)
            
            # Skip if style already exists
            if line.strip().startswith('style:'):
                style_added = True
                continue
            
            # Add style after tone, theme, or name (in that priority)
            if not style_added:
                stripped = line.strip()
                if stripped.startswith('tone:') or stripped.startswith('theme:'):
                    # Check if next line is not indented (not a multi-line value)
                    next_idx = i + 1
                    while next_idx < len(lines) and lines[next_idx].strip() == '':
                        next_idx += 1
                    if next_idx >= len(lines) or not lines[next_idx].startswith(' '):
                        result_lines.append(f"\n# Visual style preset for image generation")
                        result_lines.append(f"style: {style_preset}")
                        style_added = True
        
        # If style wasn't added (no theme/tone found), add after name
        if not style_added:
            final_lines = []
            for i, line in enumerate(result_lines):
                final_lines.append(line)
                if line.strip().startswith('name:') and not style_added:
                    # Simple name: value, not multiline
                    if not line.strip().endswith('|'):
                        final_lines.append(f"\n# Visual style preset for image generation")
                        final_lines.append(f"style: {style_preset}")
                        style_added = True
            result_lines = final_lines
        
        return '\n'.join(result_lines)
    
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
    
    def get_world_spoilers(self, world_id: str) -> str | None:
        """Get the spoilers.md content for a world, if it exists."""
        spoilers_path = self.worlds_dir / world_id / "spoilers.md"
        
        if not spoilers_path.exists():
            return None
        
        with open(spoilers_path) as f:
            return f.read()
    
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
