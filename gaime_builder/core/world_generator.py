"""
World Generator - AI-assisted world generation from prompts.

Uses two-pass generation for richer puzzle design:
  Pass 1: Design brief (puzzle structure, gates, secrets)
  Pass 2: YAML synthesis from the brief
  Pass 3: Validation and auto-fix (if needed)

Copied and adapted from backend/app/llm/world_builder.py for TUI independence.
"""

import json
import logging
import sys
import traceback
from pathlib import Path

import yaml

from gaime_builder.core.llm_client import get_completion, get_model_string, parse_json_response
from gaime_builder.core.prompt_loader import get_loader

# Add backend to path for validation imports
BACKEND_PATH = Path(__file__).parent.parent.parent / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

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
    
    async def _validate_and_fix(
        self,
        yaml_result: dict,
        design_brief: dict | None = None,
        progress_callback=None
    ) -> dict:
        """
        Pass 3: Validate the generated world and attempt auto-fixes.
        
        Uses the full WorldValidator from the backend and WorldFixer
        to automatically fix common issues. For creative issues,
        uses LLM-based fixes with the design brief for context.
        
        Returns:
            Updated yaml_result with fixes applied (YAML strings updated)
        """
        logger.info("=" * 50)
        logger.info("PASS 3: Validating and auto-fixing world")
        
        try:
            # Import validation and fixing modules
            from app.engine.validator import WorldValidator
            from app.models.world import (
                Item, Location, NPC, World, WorldData,
                PlayerSetup, VictoryCondition, NPCPersonality,
                InteractionEffect, LocationRequirement,
            )
            from gaime_builder.core.world_fixer import WorldFixer
            
            world_id = yaml_result.get("world_id", "generated-world")
            
            # Parse YAML into dicts
            world_dict = yaml.safe_load(yaml_result["world_yaml"]) or {}
            locations_dict = yaml.safe_load(yaml_result["locations_yaml"]) or {}
            npcs_dict = yaml.safe_load(yaml_result["npcs_yaml"]) or {}
            items_dict = yaml.safe_load(yaml_result["items_yaml"]) or {}
            
            # Check for deprecated schema patterns (don't auto-fix - prompts should be correct)
            yaml_data = {
                "npcs.yaml": npcs_dict,
                "locations.yaml": locations_dict,
            }
            schema_errors = self._check_deprecated_schema(yaml_data)
            if schema_errors:
                logger.warning(f"Found {len(schema_errors)} deprecated schema pattern(s)!")
                logger.warning("This indicates the prompts may need updating.")
                for err in schema_errors:
                    logger.warning(f"  ⚠️ {err}")
            
            # Build WorldData from parsed YAML
            # We need to construct Pydantic models carefully
            
            # Build World model
            player_data = world_dict.get("player", {})
            player_setup = PlayerSetup(
                starting_location=player_data.get("starting_location", ""),
                starting_inventory=player_data.get("starting_inventory", [])
            )
            
            victory_data = world_dict.get("victory")
            victory = None
            if victory_data:
                victory = VictoryCondition(
                    location=victory_data.get("location"),
                    flag=victory_data.get("flag"),
                    item=victory_data.get("item"),
                    narrative=victory_data.get("narrative", "")
                )
            
            world = World(
                name=world_dict.get("name", ""),
                theme=world_dict.get("theme", ""),
                tone=world_dict.get("tone", "atmospheric"),
                hero_name=world_dict.get("hero_name", "the hero"),
                premise=world_dict.get("premise", ""),
                player=player_setup,
                constraints=world_dict.get("constraints", []),
                commands=world_dict.get("commands", {}),
                starting_situation=world_dict.get("starting_situation", ""),
                victory=victory,
                style=world_dict.get("style"),
            )
            
            # Build Location models
            locations = {}
            for loc_id, loc_data in locations_dict.items():
                requires = None
                if loc_data.get("requires"):
                    requires = LocationRequirement(
                        flag=loc_data["requires"].get("flag"),
                        item=loc_data["requires"].get("item")
                    )
                
                interactions = {}
                for int_id, int_data in (loc_data.get("interactions") or {}).items():
                    interactions[int_id] = InteractionEffect(
                        triggers=int_data.get("triggers", []),
                        narrative_hint=int_data.get("narrative_hint", ""),
                        sets_flag=int_data.get("sets_flag"),
                        reveals_exit=int_data.get("reveals_exit"),
                        gives_item=int_data.get("gives_item"),
                        removes_item=int_data.get("removes_item"),
                    )
                
                locations[loc_id] = Location(
                    name=loc_data.get("name", ""),
                    atmosphere=loc_data.get("atmosphere", ""),
                    exits=loc_data.get("exits", {}),
                    items=loc_data.get("items", []),
                    npcs=loc_data.get("npcs", []),
                    details=loc_data.get("details", {}),
                    interactions=interactions,
                    requires=requires,
                    item_placements=loc_data.get("item_placements", {}),
                    npc_placements=loc_data.get("npc_placements", {}),
                )
            
            # Build NPC models
            npcs = {}
            for npc_id, npc_data in npcs_dict.items():
                personality_data = npc_data.get("personality", {})
                if isinstance(personality_data, str):
                    # Handle old-style string personality (shouldn't happen with fixed prompts)
                    personality = NPCPersonality(
                        traits=[t.strip().lower() for t in personality_data.rstrip(".").split(",")],
                        speech_style=personality_data,
                        quirks=[]
                    )
                else:
                    personality = NPCPersonality(
                        traits=personality_data.get("traits", []),
                        speech_style=personality_data.get("speech_style", ""),
                        quirks=personality_data.get("quirks", [])
                    )
                
                npcs[npc_id] = NPC(
                    name=npc_data.get("name", ""),
                    role=npc_data.get("role", ""),
                    location=npc_data.get("location"),
                    locations=npc_data.get("locations", []),
                    appearance=npc_data.get("appearance", ""),
                    personality=personality,
                    knowledge=npc_data.get("knowledge", []),
                    dialogue_rules=npc_data.get("dialogue_rules", []),
                    behavior=npc_data.get("behavior", ""),
                )
            
            # Build Item models
            items = {}
            for item_id, item_data in items_dict.items():
                items[item_id] = Item(
                    name=item_data.get("name", ""),
                    portable=item_data.get("portable", True),
                    examine=item_data.get("examine", ""),
                    found_description=item_data.get("found_description", ""),
                    take_description=item_data.get("take_description", ""),
                    unlocks=item_data.get("unlocks"),
                    location=item_data.get("location"),
                    hidden=item_data.get("hidden", False),
                )
            
            # Create WorldData
            world_data = WorldData(
                world=world,
                locations=locations,
                npcs=npcs,
                items=items
            )
            
            # Validate
            validator = WorldValidator(world_data, world_id)
            result = validator.validate()
            
            if result.is_valid:
                logger.info("PASS 3: World is valid, no fixes needed")
                if result.warnings:
                    logger.info(f"  Warnings: {len(result.warnings)}")
                    for warning in result.warnings:
                        logger.debug(f"  ⚠️  {warning}")
                return yaml_result
            
            # Attempt fixes (hybrid: rules first, then LLM for creative issues)
            logger.info(f"PASS 3: Found {len(result.errors)} error(s), attempting fixes...")
            for error in result.errors:
                logger.debug(f"  ❌ {error}")
            
            fixer = WorldFixer(world_data, world_id, design_brief=design_brief)
            fix_result = await fixer.fix_async()
            
            logger.info(f"PASS 3: Fix result after {fix_result.attempts} attempt(s):")
            logger.info(f"  Rule fixes: {len([f for f in fix_result.fixes_applied if f.fix_type == 'rule'])}")
            logger.info(f"  LLM fixes: {len([f for f in fix_result.fixes_applied if f.fix_type == 'llm'])}")
            logger.info(f"  LLM calls: {fix_result.llm_calls}")
            logger.info(f"  Remaining errors: {len(fix_result.remaining_errors)}")
            
            for fix in fix_result.fixes_applied:
                fix_marker = "🔧" if fix.fix_type == "rule" else "🤖"
                logger.debug(f"  {fix_marker} {fix.description}")
            
            for error in fix_result.remaining_errors:
                logger.warning(f"  ❌ Unfixed: {error}")
            
            if fix_result.fixes_applied:
                # Re-serialize fixed world data back to YAML
                logger.debug("Re-serializing fixed world data to YAML...")
                yaml_result = self._serialize_world_data_to_yaml(world_data, yaml_result)
            
            return yaml_result
            
        except Exception as e:
            # Validation failures shouldn't block world generation
            # Log the error but continue
            logger.warning(f"PASS 3 validation/fix failed: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            return yaml_result
    
    def _serialize_world_data_to_yaml(self, world_data, original_result: dict) -> dict:
        """
        Serialize WorldData back to YAML strings.
        
        Preserves the original structure as much as possible while
        incorporating fixes from the WorldFixer.
        """
        # For now, we do a simple serialization. More sophisticated
        # approaches could preserve comments and formatting.
        
        # Serialize locations
        locations_dict = {}
        for loc_id, loc in world_data.locations.items():
            loc_dict = {
                "name": loc.name,
                "atmosphere": loc.atmosphere,
                "exits": loc.exits,
            }
            if loc.items:
                loc_dict["items"] = loc.items
            if loc.item_placements:
                loc_dict["item_placements"] = loc.item_placements
            if loc.npcs:
                loc_dict["npcs"] = loc.npcs
            if loc.npc_placements:
                loc_dict["npc_placements"] = loc.npc_placements
            if loc.details:
                loc_dict["details"] = loc.details
            if loc.interactions:
                loc_dict["interactions"] = {
                    int_id: {
                        "triggers": int_effect.triggers,
                        "narrative_hint": int_effect.narrative_hint,
                        **({"sets_flag": int_effect.sets_flag} if int_effect.sets_flag else {}),
                        **({"reveals_exit": int_effect.reveals_exit} if int_effect.reveals_exit else {}),
                        **({"gives_item": int_effect.gives_item} if int_effect.gives_item else {}),
                        **({"removes_item": int_effect.removes_item} if int_effect.removes_item else {}),
                    }
                    for int_id, int_effect in loc.interactions.items()
                }
            if loc.requires:
                loc_dict["requires"] = {}
                if loc.requires.flag:
                    loc_dict["requires"]["flag"] = loc.requires.flag
                if loc.requires.item:
                    loc_dict["requires"]["item"] = loc.requires.item
            
            locations_dict[loc_id] = loc_dict
        
        # Serialize NPCs
        npcs_dict = {}
        for npc_id, npc in world_data.npcs.items():
            npc_dict = {
                "name": npc.name,
                "role": npc.role,
            }
            if npc.location:
                npc_dict["location"] = npc.location
            if npc.locations:
                npc_dict["locations"] = npc.locations
            if npc.appearance:
                npc_dict["appearance"] = npc.appearance
            npc_dict["personality"] = {
                "traits": npc.personality.traits,
                "speech_style": npc.personality.speech_style,
                "quirks": npc.personality.quirks,
            }
            if npc.knowledge:
                npc_dict["knowledge"] = npc.knowledge
            if npc.dialogue_rules:
                npc_dict["dialogue_rules"] = npc.dialogue_rules
            if npc.behavior:
                npc_dict["behavior"] = npc.behavior
            
            npcs_dict[npc_id] = npc_dict
        
        # Serialize Items
        items_dict = {}
        for item_id, item in world_data.items.items():
            item_dict = {
                "name": item.name,
                "portable": item.portable,
            }
            if item.examine:
                item_dict["examine"] = item.examine
            if item.found_description:
                item_dict["found_description"] = item.found_description
            if item.take_description:
                item_dict["take_description"] = item.take_description
            if item.unlocks:
                item_dict["unlocks"] = item.unlocks
            if item.location:
                item_dict["location"] = item.location
            if item.hidden:
                item_dict["hidden"] = item.hidden
            
            items_dict[item_id] = item_dict
        
        # Convert to YAML strings
        result = dict(original_result)
        result["locations_yaml"] = yaml.dump(locations_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
        result["npcs_yaml"] = yaml.dump(npcs_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
        result["items_yaml"] = yaml.dump(items_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        # Re-serialize world.yaml if victory or player was modified
        world_dict = yaml.safe_load(original_result["world_yaml"]) or {}
        if world_data.world.victory:
            world_dict["victory"] = {
                "location": world_data.world.victory.location,
                "flag": world_data.world.victory.flag,
                "item": world_data.world.victory.item,
                "narrative": world_data.world.victory.narrative,
            }
            # Remove None values
            world_dict["victory"] = {k: v for k, v in world_dict["victory"].items() if v}
        result["world_yaml"] = yaml.dump(world_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        return result
    
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
                progress_callback(0.9, "Validating and fixing world...")
            
            # Pass 3: Validate and auto-fix (with design brief for LLM fixes)
            design_brief = brief_result.get("design_brief", {})
            yaml_result = await self._validate_and_fix(yaml_result, design_brief, progress_callback)
            
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
        """
        Validate a world's YAML files on disk.
        
        Performs three levels of validation:
        1. File existence and YAML syntax
        2. Schema compliance (deprecated field detection)
        3. Consistency checks (flags, references)
        """
        world_path = self.worlds_dir / world_id
        errors = []
        warnings = []
        
        # Level 1: File existence and basic YAML
        required_files = ["world.yaml", "locations.yaml", "npcs.yaml", "items.yaml"]
        yaml_data = {}
        
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
                
                yaml_data[filename] = data
                
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
        
        # If file checks failed, return early
        if errors:
            return False, errors + [f"WARNING: {w}" for w in warnings]
        
        # Levels 2 & 3: Schema + Consistency (shared logic)
        schema_errors, consistency_errors, consistency_warnings = self._validate_yaml_data(
            yaml_data, world_id
        )
        errors.extend(schema_errors)
        errors.extend(consistency_errors)
        warnings.extend(consistency_warnings)
        
        return len(errors) == 0, errors + [f"WARNING: {w}" for w in warnings]
    
    def _validate_yaml_data(
        self,
        yaml_data: dict,
        world_id: str
    ) -> tuple[list[str], list[str], list[str]]:
        """
        Validate parsed YAML data for schema and consistency.
        
        This is the shared validation logic used by both:
        - validate_world() for on-disk worlds
        - _validate_and_fix() for in-memory generated worlds
        
        Args:
            yaml_data: Dict with keys like "npcs.yaml", "locations.yaml", etc.
            world_id: World identifier for error messages
        
        Returns:
            Tuple of (schema_errors, consistency_errors, consistency_warnings)
        """
        from app.engine.world import WorldLoader
        from app.engine.validator import WorldValidator
        
        schema_errors = []
        consistency_errors = []
        consistency_warnings = []
        
        # Level 2: Schema compliance - check for deprecated patterns
        schema_errors = self._check_deprecated_schema(yaml_data)
        
        # Level 3: Consistency validation via WorldLoader + WorldValidator
        # Only run if schema is valid (otherwise loader may have issues)
        if not schema_errors:
            try:
                loader = WorldLoader(self.worlds_dir)
                world_data = loader.load_world(world_id)
                
                validator = WorldValidator(world_data, world_id)
                result = validator.validate()
                
                consistency_errors.extend(result.errors)
                consistency_warnings.extend(result.warnings)
                
            except ValueError as e:
                error_msg = str(e)
                if "validation failed" in error_msg.lower():
                    consistency_errors.append(f"Consistency error: {error_msg}")
                else:
                    consistency_errors.append(str(e))
            except Exception as e:
                error_str = str(e)
                if "validation error" in error_str.lower():
                    consistency_errors.append(f"Schema error: {error_str[:200]}...")
                else:
                    consistency_errors.append(f"Validation error: {error_str}")
        
        return schema_errors, consistency_errors, consistency_warnings
    
    def _check_deprecated_schema(self, yaml_data: dict) -> list[str]:
        """
        Check for deprecated schema patterns that the loader accepts
        for backwards compatibility but should be migrated.
        """
        errors = []
        
        # Check NPCs for deprecated patterns
        npcs_data = yaml_data.get("npcs.yaml", {})
        for npc_id, npc_data in npcs_data.items():
            if not isinstance(npc_data, dict):
                continue
            
            # Check for string personality (should be object)
            personality = npc_data.get("personality")
            if isinstance(personality, str):
                errors.append(
                    f"NPC '{npc_id}': 'personality' should be an object with "
                    f"traits/speech_style/quirks, not a string"
                )
            
            # Check for dialogue_hints (should be dialogue_rules)
            if "dialogue_hints" in npc_data:
                errors.append(
                    f"NPC '{npc_id}': 'dialogue_hints' is deprecated, "
                    f"use 'dialogue_rules' instead"
                )
        
        # Check locations for deprecated patterns
        locations_data = yaml_data.get("locations.yaml", {})
        for loc_id, loc_data in locations_data.items():
            if not isinstance(loc_data, dict):
                continue
            
            # Check for constraints with locked_exit pattern
            constraints = loc_data.get("constraints", [])
            for constraint in constraints:
                if isinstance(constraint, str) and "locked_exit:" in constraint.lower():
                    errors.append(
                        f"Location '{loc_id}': 'constraints' with 'locked_exit:' pattern "
                        f"is deprecated, use 'requires' field instead"
                    )
        
        return errors
