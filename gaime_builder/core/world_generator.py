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
        reality_level: str,
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
        logger.info(f"  Reality Level: {reality_level}")
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
                reality_level=reality_level,
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
        reality_level: str,
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
                reality_level=reality_level,
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
                visual_setting=world_dict.get("visual_setting", ""),
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
                        # V3: reveals_exit is deprecated - use hidden exits with find_condition
                        gives_item=int_data.get("gives_item"),
                        removes_item=int_data.get("removes_item"),
                    )

                # V3: exits, details, item_placements, npc_placements are structured objects
                # Pydantic auto-coerces nested dicts to ExitDefinition, DetailDefinition, etc.
                locations[loc_id] = Location(
                    name=loc_data.get("name", ""),
                    atmosphere=loc_data.get("atmosphere", ""),
                    visual_description=loc_data.get("visual_description", ""),
                    exits=loc_data.get("exits", {}),
                    details=loc_data.get("details", {}),
                    interactions=interactions,
                    requires=requires,
                    item_placements=loc_data.get("item_placements", {}),
                    npc_placements=loc_data.get("npc_placements", {}),
                    # V3: items and npcs lists are deprecated - use placements keys
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

            # Build Item models (V3 schema)
            items = {}
            for item_id, item_data in items_dict.items():
                items[item_id] = Item(
                    name=item_data.get("name", ""),
                    portable=item_data.get("portable", True),
                    # V3 field names
                    scene_description=item_data.get("scene_description", ""),
                    examine_description=item_data.get("examine_description", ""),
                    take_description=item_data.get("take_description", ""),
                    unlocks=item_data.get("unlocks"),
                    # V3: hidden, find_condition, location are deprecated (now in item_placements)
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

            # Attempt rule-based fixes for structural issues
            # Creative issues will be handled by WorldAnalyzer AI passes
            logger.info(f"PASS 3: Found {len(result.errors)} error(s), attempting structural fixes...")
            for error in result.errors:
                logger.debug(f"  ❌ {error}")

            fixer = WorldFixer(world_data, world_id)
            fix_result = fixer.fix()

            logger.info(f"PASS 3: Fix result after {fix_result.attempts} attempt(s):")
            logger.info(f"  Fixes applied: {len(fix_result.fixes_applied)}")
            logger.info(f"  Remaining errors: {len(fix_result.remaining_errors)}")

            for fix in fix_result.fixes_applied:
                logger.debug(f"  🔧 {fix.description}")

            for error in fix_result.remaining_errors:
                logger.warning(f"  ❌ Unfixed: {error}")

            if fix_result.fixes_applied:
                # Re-serialize fixed world data back to YAML
                logger.debug("Re-serializing fixed world data to YAML...")
                yaml_result = self._serialize_world_data_to_yaml(world_data, yaml_result)

            # AI Analysis Passes (after structural fixes)
            yaml_result = await self._run_ai_analysis_passes(
                yaml_result, world_data, world_id, design_brief
            )

            return yaml_result

        except Exception as e:
            # Validation failures shouldn't block world generation
            # Log the error but continue
            logger.warning(f"PASS 3 validation/fix failed: {type(e).__name__}: {e}")
            logger.debug(traceback.format_exc())
            return yaml_result

    async def _run_ai_analysis_passes(
        self,
        yaml_result: dict,
        world_data,  # WorldData - not type-annotated to avoid import issues
        world_id: str,
        design_brief: dict,
    ) -> dict:
        """
        Run AI analysis passes for playability and narrative quality.

        These passes holistically analyze the world and apply targeted fixes
        that rule-based validation cannot detect.
        """
        from gaime_builder.core.world_analyzer import WorldAnalyzer

        # Build yaml_content dict for the analyzer to modify
        yaml_content = {
            "world": yaml.safe_load(yaml_result.get("world_yaml", "")),
            "locations": yaml.safe_load(yaml_result.get("locations_yaml", "")),
            "npcs": yaml.safe_load(yaml_result.get("npcs_yaml", "")),
            "items": yaml.safe_load(yaml_result.get("items_yaml", "")),
        }

        analyzer = WorldAnalyzer(
            world_data=world_data,
            world_id=world_id,
            design_brief=design_brief,
            yaml_content=yaml_content,
        )

        # Playability Analysis Pass (up to 2 iterations)
        logger.info("PASS 4: AI Playability Analysis...")
        for iteration in range(2):
            playability = await analyzer.analyze_playability()

            if not playability.has_issues:
                logger.info(f"  Iteration {iteration + 1}: No playability issues found")
                break

            logger.info(
                f"  Iteration {iteration + 1}: Found {len(playability.issues)} issue(s)"
            )
            for issue in playability.issues:
                logger.debug(f"    [{issue.severity}] {issue.description}")

            # Apply fixes
            fix_result = await analyzer.fix_playability(playability)
            logger.info(f"  Applied {len(fix_result.fixes_applied)} fix(es)")

            if not fix_result.yaml_updated:
                logger.info("  No YAML changes needed, stopping iterations")
                break

            # Re-validate after fixes
            world_data_updated = self._reload_world_data_from_yaml(yaml_content)
            if world_data_updated:
                validator = WorldValidator(world_data_updated, world_id)
                result = validator.validate()
                if result.is_valid:
                    logger.info("  World now valid after playability fixes")
                    world_data = world_data_updated
                    break

        # Narrative Analysis Pass (single shot)
        logger.info("PASS 5: AI Narrative Analysis...")
        narrative = await analyzer.analyze_narrative()

        if narrative.has_issues:
            logger.info(f"  Found {len(narrative.issues)} narrative issue(s)")
            for issue in narrative.issues:
                logger.debug(f"    [{issue.severity}] {issue.description}")

            fix_result = await analyzer.fix_narrative(narrative)
            logger.info(f"  Applied {len(fix_result.fixes_applied)} fix(es)")
        else:
            logger.info("  No narrative issues found")

        # Re-serialize if yaml_content was modified
        if analyzer.yaml_content:
            yaml_result = self._serialize_yaml_content(analyzer.yaml_content, yaml_result)

        return yaml_result

    def _reload_world_data_from_yaml(self, yaml_content: dict):
        """Reload WorldData from modified yaml_content dict. Returns WorldData or None."""
        try:
            world_dict = yaml_content.get("world", {})
            locations_dict = yaml_content.get("locations", {})
            npcs_dict = yaml_content.get("npcs", {})
            items_dict = yaml_content.get("items", {})

            # Build WorldData (simplified - reuse existing parsing logic)
            # This is a partial rebuild for validation purposes
            from app.models.world import (
                WorldDefinition,
                PlayerSetup,
                VictoryCondition,
                Location,
                NPC,
                Item,
                ExitDefinition,
                ItemPlacement,
                NPCPlacement,
            )

            # Parse world
            player_data = world_dict.get("player", {})
            player = PlayerSetup(
                starting_location=player_data.get("starting_location", ""),
                starting_inventory=player_data.get("starting_inventory", []),
            )

            victory_data = world_dict.get("victory", {})
            victory = VictoryCondition(
                location=victory_data.get("location"),
                flag=victory_data.get("flag"),
                item=victory_data.get("item"),
                narrative=victory_data.get("narrative", ""),
            ) if victory_data else None

            world = WorldDefinition(
                name=world_dict.get("name", ""),
                theme=world_dict.get("theme", ""),
                tone=world_dict.get("tone", ""),
                premise=world_dict.get("premise", ""),
                starting_situation=world_dict.get("starting_situation", ""),
                player=player,
                victory=victory,
            )

            # Parse locations
            locations = {}
            for loc_id, loc_data in locations_dict.items():
                exits = {}
                for direction, exit_data in loc_data.get("exits", {}).items():
                    if isinstance(exit_data, dict):
                        exits[direction] = ExitDefinition(
                            destination=exit_data.get("destination", ""),
                            scene_description=exit_data.get("scene_description", ""),
                            destination_known=exit_data.get("destination_known", True),
                            hidden=exit_data.get("hidden", False),
                            locked=exit_data.get("locked", False),
                            requires_key=exit_data.get("requires_key"),
                        )
                    else:
                        exits[direction] = ExitDefinition(destination=exit_data)

                item_placements = {}
                for item_id, placement_data in loc_data.get("item_placements", {}).items():
                    if isinstance(placement_data, dict):
                        item_placements[item_id] = ItemPlacement(
                            scene_description=placement_data.get("scene_description", ""),
                        )
                    else:
                        item_placements[item_id] = ItemPlacement()

                npc_placements = {}
                for npc_id, placement_data in loc_data.get("npc_placements", {}).items():
                    if isinstance(placement_data, dict):
                        npc_placements[npc_id] = NPCPlacement(
                            scene_description=placement_data.get("scene_description", ""),
                        )
                    else:
                        npc_placements[npc_id] = NPCPlacement()

                locations[loc_id] = Location(
                    name=loc_data.get("name", ""),
                    atmosphere=loc_data.get("atmosphere", ""),
                    exits=exits,
                    item_placements=item_placements,
                    npc_placements=npc_placements,
                )

            # Parse NPCs
            npcs = {}
            for npc_id, npc_data in npcs_dict.items():
                npcs[npc_id] = NPC(
                    name=npc_data.get("name", ""),
                    role=npc_data.get("role", ""),
                    location=npc_data.get("location"),
                    personality=npc_data.get("personality", ""),
                )

            # Parse Items
            items = {}
            for item_id, item_data in items_dict.items():
                items[item_id] = Item(
                    name=item_data.get("name", ""),
                    scene_description=item_data.get("scene_description", ""),
                    examine_description=item_data.get("examine_description", ""),
                )

            return WorldData(world=world, locations=locations, npcs=npcs, items=items)

        except Exception as e:
            logger.warning(f"Failed to reload WorldData from YAML: {e}")
            return None

    def _serialize_yaml_content(self, yaml_content: dict, original_result: dict) -> dict:
        """Serialize yaml_content dict back to YAML strings"""
        result = dict(original_result)

        if "world" in yaml_content and yaml_content["world"]:
            result["world_yaml"] = yaml.dump(
                yaml_content["world"], default_flow_style=False, sort_keys=False
            )

        if "locations" in yaml_content and yaml_content["locations"]:
            result["locations_yaml"] = yaml.dump(
                yaml_content["locations"], default_flow_style=False, sort_keys=False
            )

        if "npcs" in yaml_content and yaml_content["npcs"]:
            result["npcs_yaml"] = yaml.dump(
                yaml_content["npcs"], default_flow_style=False, sort_keys=False
            )

        if "items" in yaml_content and yaml_content["items"]:
            result["items_yaml"] = yaml.dump(
                yaml_content["items"], default_flow_style=False, sort_keys=False
            )

        return result

    def _serialize_world_data_to_yaml(self, world_data, original_result: dict) -> dict:
        """
        Serialize WorldData back to YAML strings (V3 schema).

        Preserves the original structure as much as possible while
        incorporating fixes from the WorldFixer.
        """
        # For now, we do a simple serialization. More sophisticated
        # approaches could preserve comments and formatting.

        # Serialize locations (V3)
        locations_dict = {}
        for loc_id, loc in world_data.locations.items():
            loc_dict = {
                "name": loc.name,
                "atmosphere": loc.atmosphere,
            }
            if loc.visual_description:
                loc_dict["visual_description"] = loc.visual_description

            # V3: Serialize exits as ExitDefinition dicts
            if loc.exits:
                exits_dict = {}
                for direction, exit_def in loc.exits.items():
                    exit_data = {"destination": exit_def.destination}
                    if exit_def.scene_description:
                        exit_data["scene_description"] = exit_def.scene_description
                    if exit_def.examine_description:
                        exit_data["examine_description"] = exit_def.examine_description
                    if not exit_def.destination_known:
                        exit_data["destination_known"] = False
                    if exit_def.hidden:
                        exit_data["hidden"] = True
                    if exit_def.find_condition:
                        exit_data["find_condition"] = exit_def.find_condition
                    if exit_def.locked:
                        exit_data["locked"] = True
                    if exit_def.requires_key:
                        exit_data["requires_key"] = exit_def.requires_key
                    exits_dict[direction] = exit_data
                loc_dict["exits"] = exits_dict

            # V3: Serialize item_placements as ItemPlacement dicts
            if loc.item_placements:
                placements_dict = {}
                for item_id, placement in loc.item_placements.items():
                    placement_data = {"placement": placement.placement}
                    if placement.hidden:
                        placement_data["hidden"] = True
                    if placement.find_condition:
                        placement_data["find_condition"] = placement.find_condition
                    placements_dict[item_id] = placement_data
                loc_dict["item_placements"] = placements_dict

            # V3: Serialize npc_placements as NPCPlacement dicts
            if loc.npc_placements:
                npc_placements_dict = {}
                for npc_id, placement in loc.npc_placements.items():
                    placement_data = {"placement": placement.placement}
                    if placement.hidden:
                        placement_data["hidden"] = True
                    if placement.find_condition:
                        placement_data["find_condition"] = placement.find_condition
                    npc_placements_dict[npc_id] = placement_data
                loc_dict["npc_placements"] = npc_placements_dict

            # V3: Serialize details as DetailDefinition dicts
            if loc.details:
                details_dict = {}
                for detail_id, detail in loc.details.items():
                    detail_data = {
                        "name": detail.name,
                        "scene_description": detail.scene_description,
                    }
                    if detail.examine_description:
                        detail_data["examine_description"] = detail.examine_description
                    if detail.on_examine:
                        on_examine_data = {}
                        if detail.on_examine.sets_flag:
                            on_examine_data["sets_flag"] = detail.on_examine.sets_flag
                        if detail.on_examine.narrative_hint:
                            on_examine_data["narrative_hint"] = detail.on_examine.narrative_hint
                        if on_examine_data:
                            detail_data["on_examine"] = on_examine_data
                    if detail.hidden:
                        detail_data["hidden"] = True
                    if detail.find_condition:
                        detail_data["find_condition"] = detail.find_condition
                    details_dict[detail_id] = detail_data
                loc_dict["details"] = details_dict

            # Serialize interactions (V3: no reveals_exit)
            if loc.interactions:
                loc_dict["interactions"] = {
                    int_id: {
                        "triggers": int_effect.triggers,
                        "narrative_hint": int_effect.narrative_hint,
                        **({"sets_flag": int_effect.sets_flag} if int_effect.sets_flag else {}),
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

        # Serialize Items (V3 schema)
        items_dict = {}
        for item_id, item in world_data.items.items():
            item_dict = {
                "name": item.name,
                "portable": item.portable,
            }
            # V3 field names
            if item.scene_description:
                item_dict["scene_description"] = item.scene_description
            if item.examine_description:
                item_dict["examine_description"] = item.examine_description
            if item.take_description:
                item_dict["take_description"] = item.take_description
            if item.unlocks:
                item_dict["unlocks"] = item.unlocks
            # V3: hidden, find_condition, location are deprecated (now in item_placements)

            items_dict[item_id] = item_dict

        # Convert to YAML strings
        result = dict(original_result)
        result["locations_yaml"] = yaml.dump(locations_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
        result["npcs_yaml"] = yaml.dump(npcs_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
        result["items_yaml"] = yaml.dump(items_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Re-serialize world.yaml if victory or player was modified
        world_dict = yaml.safe_load(original_result["world_yaml"]) or {}
        if world_data.world.visual_setting:
            world_dict["visual_setting"] = world_data.world.visual_setting
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
        reality_level: str = "stylized",
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
            reality_level: How grounded vs fantastical (grounded/stylized/surreal/fantasy)
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
        logger.info(f"  Reality Level: {reality_level}")
        logger.info(f"  Locations: {num_locations}, NPCs: {num_npcs}")
        logger.info(f"  Prompt length: {len(prompt)} chars")
        logger.info("=" * 60)

        try:
            # Pass 1: Generate design brief
            brief_result = await self._generate_design_brief(
                prompt=prompt,
                theme=theme,
                reality_level=reality_level,
                num_locations=num_locations,
                num_npcs=num_npcs,
                progress_callback=progress_callback
            )

            logger.info("Pass 1 complete, starting Pass 2...")

            # Pass 2: Generate YAML from brief
            yaml_result = await self._generate_yaml_from_brief(
                prompt=prompt,
                theme=theme,
                reality_level=reality_level,
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

        # Level 4: Quality checks (only if no errors)
        quality_warnings = []
        if not errors:
            quality_warnings = self._check_quality(yaml_data)

        # Format output: errors first, then warnings, then quality suggestions
        messages = list(errors)
        messages.extend(f"WARNING: {w}" for w in warnings)
        messages.extend(f"QUALITY: {w}" for w in quality_warnings)

        return len(errors) == 0, messages

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

    def _check_quality(self, yaml_data: dict) -> list[str]:
        """
        Check for quality issues in world content (V3).

        These are not errors but suggestions for improvement.
        Returns list of quality warnings.
        """
        warnings = []

        world_data = yaml_data.get("world.yaml", {})
        locations_data = yaml_data.get("locations.yaml", {})
        items_data = yaml_data.get("items.yaml", {})
        npcs_data = yaml_data.get("npcs.yaml", {})

        # === World-level quality checks ===

        # Visual setting length (should be 5-10 sentences)
        visual_setting = world_data.get("visual_setting", "")
        if visual_setting:
            sentences = [s.strip() for s in visual_setting.replace('\n', ' ').split('.') if s.strip()]
            if len(sentences) < 3:
                warnings.append(
                    f"visual_setting is short ({len(sentences)} sentences) - aim for 5-10 for rich image generation"
                )
        else:
            warnings.append("Missing visual_setting - images will lack consistent visual language")

        # Starting situation
        if not world_data.get("starting_situation"):
            warnings.append("Missing starting_situation - players won't know why they can act")

        # Victory condition (note: unobtainable victory items are now validation ERRORS, not quality warnings)
        if not world_data.get("victory"):
            warnings.append("Missing victory condition - game has no defined ending")

        # === Item quality checks ===

        items_placed = set()
        for loc in locations_data.values():
            if isinstance(loc, dict):
                placements = loc.get("item_placements", {})
                items_placed.update(placements.keys())

        starting_inventory = world_data.get("player", {}).get("starting_inventory", [])

        for item_id, item_data in items_data.items():
            if not isinstance(item_data, dict):
                continue

            # Missing scene_description (item invisible in scene)
            if not item_data.get("scene_description"):
                warnings.append(
                    f"Item '{item_id}' missing scene_description - item will be invisible in room descriptions"
                )

            # Missing examine_description
            if not item_data.get("examine_description"):
                warnings.append(
                    f"Item '{item_id}' missing examine_description - examine will feel empty"
                )

            # Orphaned item (defined but never placed)
            if item_id not in items_placed and item_id not in starting_inventory:
                warnings.append(
                    f"Item '{item_id}' is defined but never placed in any location or starting inventory"
                )

        # === Location quality checks ===

        for loc_id, loc_data in locations_data.items():
            if not isinstance(loc_data, dict):
                continue

            # Get exits early for use in multiple checks
            exits = loc_data.get("exits", {})

            # Visual description length
            visual_desc = loc_data.get("visual_description", "")
            if visual_desc:
                sentences = [s.strip() for s in visual_desc.replace('\n', ' ').split('.') if s.strip()]
                if len(sentences) < 2:
                    warnings.append(
                        f"Location '{loc_id}' visual_description is short ({len(sentences)} sentences) - aim for 3-5"
                    )

                # Check for non-visual content in visual_description
                non_visual_patterns = [
                    ("freeze", "dynamic behavior"),
                    ("when looked at", "conditional description"),
                    ("if you", "conditional description"),
                    ("when you", "conditional description"),
                    ("you can hear", "sound - belongs in atmosphere"),
                    ("you hear", "sound - belongs in atmosphere"),
                    ("smell", "smell - belongs in atmosphere"),
                    ("sounds of", "sound - belongs in atmosphere"),
                ]
                visual_desc_lower = visual_desc.lower()
                for pattern, issue_type in non_visual_patterns:
                    if pattern in visual_desc_lower:
                        warnings.append(
                            f"Location '{loc_id}' visual_description contains '{pattern}' ({issue_type}) - "
                            f"visual_description should only contain what a camera would capture"
                        )
                        break  # Only report first issue per location

                # Check for exit directions mentioned in visual_description (redundant)
                exit_directions = exits.keys() if exits else []
                for direction in exit_directions:
                    # Check for "to the north", "to the east", etc.
                    if f"to the {direction}" in visual_desc_lower:
                        warnings.append(
                            f"Location '{loc_id}' visual_description mentions exit direction '{direction}' - "
                            f"exit descriptions belong in exits.scene_description only"
                        )
                        break  # Only report first
            else:
                warnings.append(
                    f"Location '{loc_id}' missing visual_description - image generation will lack detail"
                )

            # Exit quality checks
            for direction, exit_data in exits.items():
                if isinstance(exit_data, dict):
                    if not exit_data.get("scene_description"):
                        warnings.append(
                            f"Exit '{direction}' in '{loc_id}' missing scene_description - visual continuity risk"
                        )
                    # Hidden exit without find_condition
                    if exit_data.get("hidden") and not exit_data.get("find_condition"):
                        warnings.append(
                            f"Exit '{direction}' in '{loc_id}' is hidden but has no find_condition - will never be revealed"
                        )
                    # requires_key should reference an actual item
                    requires_key = exit_data.get("requires_key")
                    if requires_key and requires_key not in items_data:
                        warnings.append(
                            f"Exit '{direction}' in '{loc_id}' has requires_key '{requires_key}' which is not a valid item - use 'locked' with find_condition for flag-based unlocking"
                        )
                    # destination_known checks
                    dest_known = exit_data.get("destination_known", True)
                    dest_id = exit_data.get("destination", "")
                    is_hidden_exit = exit_data.get("hidden", False)

                    # Hidden exits should have destination_known: false
                    # You don't know where a secret passage leads until you've been through it
                    if is_hidden_exit and dest_known:
                        warnings.append(
                            f"Exit '{direction}' in '{loc_id}' is hidden but has destination_known: true - "
                            f"secret passages should typically have destination_known: false"
                        )
                    # Also check for secret/utility destination names
                    elif dest_known:
                        is_secret_dest = any(
                            kw in dest_id.lower()
                            for kw in ["secret", "hidden", "utility", "maintenance", "private", "restricted"]
                        )
                        if is_secret_dest:
                            warnings.append(
                                f"Exit '{direction}' in '{loc_id}' has destination_known: true "
                                f"but leads to '{dest_id}' - consider setting destination_known: false for unfamiliar areas"
                            )

            # Detail quality checks
            details = loc_data.get("details", {})
            for detail_id, detail_data in details.items():
                if isinstance(detail_data, dict):
                    if not detail_data.get("examine_description"):
                        warnings.append(
                            f"Detail '{detail_id}' in '{loc_id}' missing examine_description - examine will feel empty"
                        )
                    # Hidden detail without find_condition
                    if detail_data.get("hidden") and not detail_data.get("find_condition"):
                        warnings.append(
                            f"Detail '{detail_id}' in '{loc_id}' is hidden but has no find_condition - will never be revealed"
                        )

            # Item placement quality checks
            item_placements = loc_data.get("item_placements", {})
            for item_id, placement_data in item_placements.items():
                if isinstance(placement_data, dict):
                    # Hidden item without find_condition
                    if placement_data.get("hidden") and not placement_data.get("find_condition"):
                        warnings.append(
                            f"Item '{item_id}' in '{loc_id}' is hidden but has no find_condition - will never be revealed"
                        )
                    # Check item exists
                    if item_id not in items_data:
                        # This is an error, not quality - caught by validator
                        pass

        # === NPC quality checks ===

        npcs_placed = set()
        for loc in locations_data.values():
            if isinstance(loc, dict):
                placements = loc.get("npc_placements", {})
                npcs_placed.update(placements.keys())

        for npc_id, npc_data in npcs_data.items():
            if not isinstance(npc_data, dict):
                continue

            # Check NPC is placed somewhere
            has_location = npc_data.get("location") or npc_data.get("locations")
            if not has_location and npc_id not in npcs_placed:
                warnings.append(
                    f"NPC '{npc_id}' is defined but has no location and isn't in any npc_placements"
                )

            # Missing appearance
            if not npc_data.get("appearance"):
                warnings.append(
                    f"NPC '{npc_id}' missing appearance - image generation won't show them correctly"
                )

        return warnings

    def _check_deprecated_schema(self, yaml_data: dict) -> list[str]:
        """
        Check for deprecated schema patterns (V3).

        Detects patterns that should be updated to V3 schema.
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

        # Check items for deprecated patterns (V3)
        items_data = yaml_data.get("items.yaml", {})
        for item_id, item_data in items_data.items():
            if not isinstance(item_data, dict):
                continue

            # V3: Check for old field names
            if "found_description" in item_data:
                errors.append(
                    f"Item '{item_id}': 'found_description' is deprecated, "
                    f"use 'scene_description' instead"
                )
            if "examine" in item_data and "examine_description" not in item_data:
                errors.append(
                    f"Item '{item_id}': 'examine' is deprecated, "
                    f"use 'examine_description' instead"
                )
            # V3: Check for visibility fields that should be in item_placements
            if "hidden" in item_data:
                errors.append(
                    f"Item '{item_id}': 'hidden' is deprecated in items.yaml, "
                    f"use item_placements with hidden/find_condition in locations.yaml"
                )
            if "location" in item_data:
                errors.append(
                    f"Item '{item_id}': 'location' is deprecated in items.yaml, "
                    f"place items via item_placements in locations.yaml"
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

            # V3: Check for deprecated items list (use item_placements keys)
            if "items" in loc_data:
                errors.append(
                    f"Location '{loc_id}': 'items' list is deprecated, "
                    f"use item_placements keys to define items at this location"
                )

            # V3: Check for deprecated npcs list (use npc_placements keys)
            if "npcs" in loc_data:
                errors.append(
                    f"Location '{loc_id}': 'npcs' list is deprecated, "
                    f"use npc_placements keys to define NPCs at this location"
                )

            # V3: Check for reveals_exit in interactions
            interactions = loc_data.get("interactions", {})
            for int_id, int_data in interactions.items():
                if isinstance(int_data, dict) and "reveals_exit" in int_data:
                    errors.append(
                        f"Location '{loc_id}' interaction '{int_id}': 'reveals_exit' is deprecated, "
                        f"use hidden exits with find_condition instead"
                    )

            # V3: Check for string details (should be DetailDefinition)
            details = loc_data.get("details", {})
            for detail_id, detail_data in details.items():
                if isinstance(detail_data, str):
                    errors.append(
                        f"Location '{loc_id}' detail '{detail_id}': string details are deprecated, "
                        f"use DetailDefinition with name/scene_description/examine_description"
                    )

            # V3: Check for string exits (should be ExitDefinition)
            exits = loc_data.get("exits", {})
            for direction, exit_data in exits.items():
                if isinstance(exit_data, str):
                    errors.append(
                        f"Location '{loc_id}' exit '{direction}': string exits are deprecated, "
                        f"use ExitDefinition with destination/scene_description"
                    )

        return errors
