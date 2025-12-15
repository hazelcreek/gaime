"""
World Fixer - Attempts to auto-fix validation errors in generated worlds.

This module uses a hybrid approach:
1. Rule-based fixes for structural issues (typos, invalid references)
2. LLM-based fixes for creative issues (missing interactions, unreachable items)

The LLM fixes are optional and only used when rule-based fixes can't solve the problem.
"""

import json
import logging
import re
import sys
from dataclasses import dataclass, field
from difflib import get_close_matches
from enum import Enum
from pathlib import Path
from typing import Any

# Add backend to path for model imports
BACKEND_PATH = Path(__file__).parent.parent.parent / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.engine.validator import ValidationResult, WorldValidator
from app.models.world import (
    InteractionEffect,
    Item,
    ItemUseAction,
    Location,
    LocationRequirement,
    NPC,
    WorldData,
)

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of validation errors"""
    STRUCTURAL = "structural"  # Can be fixed with rules (typos, bad refs)
    CREATIVE = "creative"      # Needs LLM to generate content


@dataclass
class FixResult:
    """Result of a fix attempt"""
    fixed: bool
    description: str
    error_pattern: str  # Original error message pattern
    fix_type: str = "rule"  # "rule" or "llm"


@dataclass
class WorldFixerResult:
    """Result of world fixing attempts"""
    original_errors: list[str] = field(default_factory=list)
    fixes_applied: list[FixResult] = field(default_factory=list)
    remaining_errors: list[str] = field(default_factory=list)
    attempts: int = 0
    llm_calls: int = 0
    
    @property
    def fully_fixed(self) -> bool:
        return len(self.remaining_errors) == 0


def classify_error(error: str) -> tuple[ErrorType, dict]:
    """
    Classify an error as structural or creative.
    
    Returns:
        Tuple of (ErrorType, parsed error details)
    """
    # Structural errors - can be fixed with pattern matching
    structural_patterns = [
        (r"Location '(.+?)' exit '(.+?)' points to invalid location '(.+?)'", 
         {"type": "invalid_exit", "loc": 1, "dir": 2, "dest": 3}),
        (r"Victory location '(.+?)' is invalid",
         {"type": "invalid_victory_location", "loc": 1}),
        (r"Item '(.+?)' has invalid location '(.+?)'",
         {"type": "invalid_item_location", "item": 1, "loc": 2}),
        (r"NPC '(.+?)' has invalid location '(.+?)'",
         {"type": "invalid_npc_location", "npc": 1, "loc": 2}),
        (r"Location '(.+?)' lists invalid item '(.+?)'",
         {"type": "invalid_location_item", "loc": 1, "item": 2}),
        (r"Victory item '(.+?)' is invalid",
         {"type": "invalid_victory_item", "item": 1}),
        (r"Starting inventory contains invalid item '(.+?)'",
         {"type": "invalid_starting_item", "item": 1}),
    ]
    
    for pattern, info in structural_patterns:
        match = re.match(pattern, error)
        if match:
            details = {"error_type": info["type"]}
            for key, group_num in info.items():
                if key != "type" and isinstance(group_num, int):
                    details[key] = match.group(group_num)
            return ErrorType.STRUCTURAL, details
    
    # Creative errors - need LLM intervention
    creative_patterns = [
        (r"Flag '(.+?)' is checked at (.+?) but never set anywhere",
         {"type": "flag_never_set", "flag": 1, "checked_at": 2}),
    ]
    
    for pattern, info in creative_patterns:
        match = re.match(pattern, error)
        if match:
            details = {"error_type": info["type"]}
            for key, group_num in info.items():
                if key != "type" and isinstance(group_num, int):
                    details[key] = match.group(group_num)
            return ErrorType.CREATIVE, details
    
    # Unknown error type
    return ErrorType.CREATIVE, {"error_type": "unknown", "raw": error}


class WorldFixer:
    """
    Attempts to auto-fix validation errors in world data.
    
    Uses a hybrid approach:
    - Rule-based fixes for structural issues (fast, no API calls)
    - LLM-based fixes for creative issues (when enabled)
    """
    
    MAX_ATTEMPTS = 3
    
    def __init__(self, world_data: WorldData, world_id: str, design_brief: dict | None = None):
        self.world_data = world_data
        self.world_id = world_id
        self.design_brief = design_brief
        self.result = WorldFixerResult()
    
    def fix(self) -> WorldFixerResult:
        """
        Attempt to fix all validation errors using rule-based fixes only.
        
        For LLM-based fixes, use fix_async() instead.
        
        Returns:
            WorldFixerResult with fixes applied and remaining errors
        """
        return self._fix_loop(use_llm=False)
    
    async def fix_async(self) -> WorldFixerResult:
        """
        Attempt to fix all validation errors using both rules and LLM.
        
        First applies rule-based fixes, then uses LLM for creative issues.
        
        Returns:
            WorldFixerResult with fixes applied and remaining errors
        """
        return await self._fix_loop_async(use_llm=True)
    
    def _fix_loop(self, use_llm: bool = False) -> WorldFixerResult:
        """Synchronous fix loop (rule-based only)"""
        validation = self._validate()
        self.result.original_errors = list(validation.errors)
        
        if validation.is_valid:
            logger.info(f"World '{self.world_id}' is already valid")
            return self.result
        
        for attempt in range(self.MAX_ATTEMPTS):
            self.result.attempts = attempt + 1
            logger.info(f"Fix attempt {attempt + 1}/{self.MAX_ATTEMPTS}")
            
            fixes_this_round = self._attempt_rule_fixes(validation.errors)
            
            if not fixes_this_round:
                logger.info("No more rule-based fixes available")
                break
            
            validation = self._validate()
            
            if validation.is_valid:
                logger.info(f"World fixed after {attempt + 1} attempt(s)")
                break
        
        self.result.remaining_errors = list(validation.errors)
        return self.result
    
    async def _fix_loop_async(self, use_llm: bool = True) -> WorldFixerResult:
        """Async fix loop with LLM support"""
        validation = self._validate()
        self.result.original_errors = list(validation.errors)
        
        if validation.is_valid:
            logger.info(f"World '{self.world_id}' is already valid")
            return self.result
        
        for attempt in range(self.MAX_ATTEMPTS):
            self.result.attempts = attempt + 1
            logger.info(f"Fix attempt {attempt + 1}/{self.MAX_ATTEMPTS}")
            
            # First, try rule-based fixes
            rule_fixes = self._attempt_rule_fixes(validation.errors)
            
            # Re-validate
            validation = self._validate()
            
            if validation.is_valid:
                logger.info(f"World fixed after {attempt + 1} attempt(s) (rules only)")
                break
            
            # Then, try LLM fixes for remaining creative errors
            if use_llm and validation.errors:
                llm_fixes = await self._attempt_llm_fixes(validation.errors)
                
                # Re-validate after LLM fixes
                validation = self._validate()
                
                if validation.is_valid:
                    logger.info(f"World fixed after {attempt + 1} attempt(s) (with LLM)")
                    break
            
            # If no fixes were made this round, stop
            if not rule_fixes and (not use_llm or self.result.llm_calls == 0):
                logger.info("No more fixes available")
                break
        
        self.result.remaining_errors = list(validation.errors)
        return self.result
    
    def _validate(self) -> ValidationResult:
        """Run validation on current world data"""
        validator = WorldValidator(self.world_data, self.world_id)
        return validator.validate()
    
    def _attempt_rule_fixes(self, errors: list[str]) -> list[FixResult]:
        """Attempt rule-based fixes for each error"""
        fixes = []
        
        for error in errors:
            error_type, details = classify_error(error)
            
            # Only handle structural errors with rules
            if error_type == ErrorType.STRUCTURAL:
                fix_result = self._try_rule_fix(error, details)
                if fix_result and fix_result.fixed:
                    fixes.append(fix_result)
                    self.result.fixes_applied.append(fix_result)
                    logger.debug(f"Rule fix: {fix_result.description}")
        
        return fixes
    
    async def _attempt_llm_fixes(self, errors: list[str]) -> list[FixResult]:
        """Attempt LLM-based fixes for creative errors"""
        fixes = []
        
        for error in errors:
            error_type, details = classify_error(error)
            
            # Only handle creative errors with LLM
            if error_type == ErrorType.CREATIVE:
                fix_result = await self._try_llm_fix(error, details)
                if fix_result and fix_result.fixed:
                    fixes.append(fix_result)
                    self.result.fixes_applied.append(fix_result)
                    logger.debug(f"LLM fix: {fix_result.description}")
        
        return fixes
    
    def _try_rule_fix(self, error: str, details: dict) -> FixResult | None:
        """Try to fix a structural error using rules"""
        error_type = details.get("error_type")
        
        if error_type == "invalid_exit":
            return self._fix_invalid_exit(details["loc"], details["dir"], details["dest"])
        elif error_type == "invalid_victory_location":
            return self._fix_invalid_victory_location(details["loc"])
        elif error_type == "invalid_item_location":
            return self._fix_invalid_item_location(details["item"], details["loc"])
        elif error_type == "invalid_npc_location":
            return self._fix_invalid_npc_location(details["npc"], details["loc"])
        elif error_type == "invalid_location_item":
            return self._fix_invalid_location_item(details["loc"], details["item"])
        elif error_type == "invalid_victory_item":
            return self._fix_invalid_victory_item(details["item"])
        elif error_type == "invalid_starting_item":
            return self._fix_invalid_starting_item(details["item"])
        
        return None
    
    async def _try_llm_fix(self, error: str, details: dict) -> FixResult | None:
        """Try to fix a creative error using LLM"""
        from gaime_builder.core.llm_client import get_completion, parse_json_response
        from gaime_builder.core.prompt_loader import get_loader
        
        error_type = details.get("error_type")
        
        if error_type == "flag_never_set":
            return await self._llm_fix_missing_flag(error, details)
        elif error_type == "unknown":
            # Try a generic LLM fix
            return await self._llm_fix_generic(error, details)
        
        return None
    
    async def _llm_fix_missing_flag(self, error: str, details: dict) -> FixResult | None:
        """Use LLM to fix a missing flag by generating an appropriate interaction"""
        from gaime_builder.core.llm_client import get_completion, parse_json_response
        from gaime_builder.core.prompt_loader import get_loader
        
        flag_name = details.get("flag")
        checked_at = details.get("checked_at")
        
        logger.info(f"Attempting LLM fix for missing flag '{flag_name}'")
        
        try:
            # Build context for the LLM
            prompt_template = get_loader().get_prompt("world_builder", "fix_error_prompt.txt")
            
            # Find relevant locations (where the flag is checked and potential places to set it)
            relevant_context = self._build_context_for_flag(flag_name, checked_at)
            
            # Format the prompt
            prompt = prompt_template.format(
                error_description=error,
                world_name=self.world_data.world.name,
                theme=self.world_data.world.theme,
                tone=self.world_data.world.tone,
                relevant_context=relevant_context,
                design_intent=json.dumps(self.design_brief, indent=2) if self.design_brief else "Not available",
            )
            
            messages = [
                {"role": "system", "content": "You are a game designer fixing validation errors in text adventure worlds."},
                {"role": "user", "content": prompt}
            ]
            
            self.result.llm_calls += 1
            response = await get_completion(
                messages,
                temperature=0.7,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            # Parse the fix
            fix_data = parse_json_response(response, strict=True)
            
            # Apply the fix
            return self._apply_llm_fix(fix_data, f"Flag '{flag_name}'")
            
        except Exception as e:
            logger.warning(f"LLM fix failed for flag '{flag_name}': {e}")
            # Fall back to simple rule-based fix
            return self._fix_missing_flag_simple(flag_name, checked_at)
    
    async def _llm_fix_generic(self, error: str, details: dict) -> FixResult | None:
        """Use LLM to fix an unknown error type"""
        from gaime_builder.core.llm_client import get_completion, parse_json_response
        from gaime_builder.core.prompt_loader import get_loader
        
        logger.info(f"Attempting generic LLM fix for: {error[:50]}...")
        
        try:
            prompt_template = get_loader().get_prompt("world_builder", "fix_error_prompt.txt")
            
            prompt = prompt_template.format(
                error_description=error,
                world_name=self.world_data.world.name,
                theme=self.world_data.world.theme,
                tone=self.world_data.world.tone,
                relevant_context=self._build_generic_context(),
                design_intent=json.dumps(self.design_brief, indent=2) if self.design_brief else "Not available",
            )
            
            messages = [
                {"role": "system", "content": "You are a game designer fixing validation errors in text adventure worlds."},
                {"role": "user", "content": prompt}
            ]
            
            self.result.llm_calls += 1
            response = await get_completion(
                messages,
                temperature=0.7,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            fix_data = parse_json_response(response, strict=True)
            return self._apply_llm_fix(fix_data, error[:30])
            
        except Exception as e:
            logger.warning(f"Generic LLM fix failed: {e}")
            return None
    
    def _build_context_for_flag(self, flag_name: str, checked_at: str) -> str:
        """Build relevant context for fixing a missing flag"""
        lines = []
        
        # Show where the flag is checked
        lines.append(f"## Flag '{flag_name}' is required at: {checked_at}")
        lines.append("")
        
        # Show locations that could set the flag (accessible before the check)
        lines.append("## Available Locations:")
        for loc_id, loc in self.world_data.locations.items():
            loc_info = f"- **{loc_id}** ({loc.name})"
            if loc.items:
                loc_info += f" - Items: {', '.join(loc.items)}"
            if loc.npcs:
                loc_info += f" - NPCs: {', '.join(loc.npcs)}"
            lines.append(loc_info)
        
        lines.append("")
        lines.append("## Existing Interactions:")
        for loc_id, loc in self.world_data.locations.items():
            if loc.interactions:
                for int_id, interaction in loc.interactions.items():
                    lines.append(f"- {loc_id}/{int_id}: sets_flag={interaction.sets_flag}")
        
        return "\n".join(lines)
    
    def _build_generic_context(self) -> str:
        """Build generic context for unknown errors"""
        lines = ["## World Overview"]
        lines.append(f"Locations: {', '.join(self.world_data.locations.keys())}")
        lines.append(f"NPCs: {', '.join(self.world_data.npcs.keys())}")
        lines.append(f"Items: {', '.join(self.world_data.items.keys())}")
        return "\n".join(lines)
    
    def _apply_llm_fix(self, fix_data: dict, error_pattern: str) -> FixResult | None:
        """Apply a fix generated by the LLM"""
        try:
            fix_type = fix_data.get("fix_type")
            target_file = fix_data.get("target_file")
            target_id = fix_data.get("target_id")
            patch = fix_data.get("patch", {})
            explanation = fix_data.get("explanation", "")
            
            logger.debug(f"Applying LLM fix: {fix_type} to {target_file}/{target_id}")
            
            if target_file == "locations" and target_id in self.world_data.locations:
                location = self.world_data.locations[target_id]
                
                if fix_type == "add_interaction" and "interactions" in patch:
                    if location.interactions is None:
                        location.interactions = {}
                    
                    for int_id, int_data in patch["interactions"].items():
                        location.interactions[int_id] = InteractionEffect(
                            triggers=int_data.get("triggers", []),
                            narrative_hint=int_data.get("narrative_hint", ""),
                            sets_flag=int_data.get("sets_flag"),
                            reveals_exit=int_data.get("reveals_exit"),
                            gives_item=int_data.get("gives_item"),
                            removes_item=int_data.get("removes_item"),
                        )
                    
                    return FixResult(
                        fixed=True,
                        description=f"Added interaction to '{target_id}': {explanation}",
                        error_pattern=error_pattern,
                        fix_type="llm"
                    )
            
            logger.warning(f"Could not apply LLM fix: unsupported fix_type={fix_type}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to apply LLM fix: {e}")
            return None
    
    def _fix_missing_flag_simple(self, flag_name: str, check_location: str) -> FixResult:
        """Simple fallback fix for missing flag (when LLM fails)"""
        starting_loc = self.world_data.world.player.starting_location
        location = self.world_data.locations.get(starting_loc)
        
        if not location:
            return FixResult(
                fixed=False,
                description=f"Cannot fix flag '{flag_name}': starting location not found",
                error_pattern=f"Flag '{flag_name}'"
            )
        
        interaction_id = f"discover_{flag_name}"
        
        if location.interactions is None:
            location.interactions = {}
        
        location.interactions[interaction_id] = InteractionEffect(
            triggers=["look around", "examine surroundings", "search"],
            narrative_hint="You notice something important about your situation.",
            sets_flag=flag_name,
        )
        
        return FixResult(
            fixed=True,
            description=f"Added fallback interaction '{interaction_id}' to '{starting_loc}' (simple fix)",
            error_pattern=f"Flag '{flag_name}'",
            fix_type="rule"
        )
    
    # =========================================================================
    # Structural Fix Methods (Rule-based)
    # =========================================================================
    
    def _fix_invalid_exit(self, loc_id: str, direction: str, invalid_dest: str) -> FixResult:
        """
        Fix an exit that points to an invalid location.
        
        Strategy: Find closest matching location name, or remove the exit.
        """
        location = self.world_data.locations.get(loc_id)
        if not location:
            return FixResult(
                fixed=False,
                description=f"Cannot fix exit: location '{loc_id}' not found",
                error_pattern=f"exit '{direction}' points to invalid location"
            )
        
        # Try to find a close match
        valid_locations = list(self.world_data.locations.keys())
        matches = get_close_matches(invalid_dest, valid_locations, n=1, cutoff=0.6)
        
        if matches:
            # Use the close match
            new_dest = matches[0]
            location.exits[direction] = new_dest
            return FixResult(
                fixed=True,
                description=f"Changed exit '{direction}' in '{loc_id}' from '{invalid_dest}' to '{new_dest}'",
                error_pattern=f"exit '{direction}' points to invalid location"
            )
        else:
            # Remove the invalid exit
            del location.exits[direction]
            return FixResult(
                fixed=True,
                description=f"Removed invalid exit '{direction}' from '{loc_id}' (pointed to '{invalid_dest}')",
                error_pattern=f"exit '{direction}' points to invalid location"
            )
    
    def _fix_invalid_victory_location(self, invalid_loc: str) -> FixResult:
        """
        Fix an invalid victory location.
        
        Strategy: Use a valid location, preferring one that seems like an ending.
        """
        if not self.world_data.world.victory:
            return FixResult(
                fixed=False,
                description="No victory condition to fix",
                error_pattern="Victory location"
            )
        
        valid_locations = list(self.world_data.locations.keys())
        
        # Try to find a close match first
        matches = get_close_matches(invalid_loc, valid_locations, n=1, cutoff=0.6)
        if matches:
            self.world_data.world.victory.location = matches[0]
            return FixResult(
                fixed=True,
                description=f"Changed victory location from '{invalid_loc}' to '{matches[0]}'",
                error_pattern="Victory location"
            )
        
        # Fall back to a location that sounds like an ending
        ending_keywords = ["final", "end", "exit", "throne", "sanctuary", "chamber", "core"]
        for loc_id in valid_locations:
            if any(kw in loc_id.lower() for kw in ending_keywords):
                self.world_data.world.victory.location = loc_id
                return FixResult(
                    fixed=True,
                    description=f"Changed victory location from '{invalid_loc}' to '{loc_id}'",
                    error_pattern="Victory location"
                )
        
        # Use starting location as last resort
        self.world_data.world.victory.location = self.world_data.world.player.starting_location
        return FixResult(
            fixed=True,
            description=f"Changed victory location from '{invalid_loc}' to starting location",
            error_pattern="Victory location"
        )
    
    def _fix_invalid_item_location(self, item_id: str, invalid_loc: str) -> FixResult:
        """
        Fix an item with an invalid location.
        
        Strategy: Find closest matching location or set to None (item in inventory).
        """
        item = self.world_data.items.get(item_id)
        if not item:
            return FixResult(
                fixed=False,
                description=f"Cannot fix: item '{item_id}' not found",
                error_pattern=f"Item '{item_id}' has invalid location"
            )
        
        valid_locations = list(self.world_data.locations.keys())
        matches = get_close_matches(invalid_loc, valid_locations, n=1, cutoff=0.6)
        
        if matches:
            item.location = matches[0]
            return FixResult(
                fixed=True,
                description=f"Changed item '{item_id}' location from '{invalid_loc}' to '{matches[0]}'",
                error_pattern=f"Item '{item_id}' has invalid location"
            )
        else:
            item.location = None
            return FixResult(
                fixed=True,
                description=f"Removed invalid location from item '{item_id}'",
                error_pattern=f"Item '{item_id}' has invalid location"
            )
    
    def _fix_invalid_npc_location(self, npc_id: str, invalid_loc: str) -> FixResult:
        """
        Fix an NPC with an invalid location.
        
        Strategy: Find closest matching location or use starting location.
        """
        npc = self.world_data.npcs.get(npc_id)
        if not npc:
            return FixResult(
                fixed=False,
                description=f"Cannot fix: NPC '{npc_id}' not found",
                error_pattern=f"NPC '{npc_id}' has invalid location"
            )
        
        valid_locations = list(self.world_data.locations.keys())
        matches = get_close_matches(invalid_loc, valid_locations, n=1, cutoff=0.6)
        
        if matches:
            npc.location = matches[0]
            return FixResult(
                fixed=True,
                description=f"Changed NPC '{npc_id}' location from '{invalid_loc}' to '{matches[0]}'",
                error_pattern=f"NPC '{npc_id}' has invalid location"
            )
        else:
            npc.location = self.world_data.world.player.starting_location
            return FixResult(
                fixed=True,
                description=f"Changed NPC '{npc_id}' location from '{invalid_loc}' to starting location",
                error_pattern=f"NPC '{npc_id}' has invalid location"
            )
    
    def _fix_invalid_location_item(self, loc_id: str, invalid_item: str) -> FixResult:
        """
        Fix a location that lists an invalid item.
        
        Strategy: Find closest matching item or remove from list.
        """
        location = self.world_data.locations.get(loc_id)
        if not location:
            return FixResult(
                fixed=False,
                description=f"Cannot fix: location '{loc_id}' not found",
                error_pattern=f"Location '{loc_id}' lists invalid item"
            )
        
        valid_items = list(self.world_data.items.keys())
        matches = get_close_matches(invalid_item, valid_items, n=1, cutoff=0.6)
        
        if matches and invalid_item in location.items:
            idx = location.items.index(invalid_item)
            location.items[idx] = matches[0]
            return FixResult(
                fixed=True,
                description=f"Changed item in '{loc_id}' from '{invalid_item}' to '{matches[0]}'",
                error_pattern=f"Location '{loc_id}' lists invalid item"
            )
        elif invalid_item in location.items:
            location.items.remove(invalid_item)
            # Also remove from item_placements if present
            if invalid_item in location.item_placements:
                del location.item_placements[invalid_item]
            return FixResult(
                fixed=True,
                description=f"Removed invalid item '{invalid_item}' from location '{loc_id}'",
                error_pattern=f"Location '{loc_id}' lists invalid item"
            )
        
        return FixResult(
            fixed=False,
            description=f"Could not find item '{invalid_item}' in location '{loc_id}'",
            error_pattern=f"Location '{loc_id}' lists invalid item"
        )
    
    def _fix_invalid_victory_item(self, invalid_item: str) -> FixResult:
        """
        Fix an invalid victory item.
        
        Strategy: Find closest matching item or remove requirement.
        """
        if not self.world_data.world.victory:
            return FixResult(
                fixed=False,
                description="No victory condition to fix",
                error_pattern="Victory item"
            )
        
        valid_items = list(self.world_data.items.keys())
        matches = get_close_matches(invalid_item, valid_items, n=1, cutoff=0.6)
        
        if matches:
            self.world_data.world.victory.item = matches[0]
            return FixResult(
                fixed=True,
                description=f"Changed victory item from '{invalid_item}' to '{matches[0]}'",
                error_pattern="Victory item"
            )
        else:
            self.world_data.world.victory.item = None
            return FixResult(
                fixed=True,
                description=f"Removed invalid victory item '{invalid_item}'",
                error_pattern="Victory item"
            )
    
    def _fix_invalid_starting_item(self, invalid_item: str) -> FixResult:
        """
        Fix an invalid item in starting inventory.
        
        Strategy: Find closest matching item or remove from inventory.
        """
        valid_items = list(self.world_data.items.keys())
        matches = get_close_matches(invalid_item, valid_items, n=1, cutoff=0.6)
        
        inventory = self.world_data.world.player.starting_inventory
        
        if matches and invalid_item in inventory:
            idx = inventory.index(invalid_item)
            inventory[idx] = matches[0]
            return FixResult(
                fixed=True,
                description=f"Changed starting inventory item from '{invalid_item}' to '{matches[0]}'",
                error_pattern="Starting inventory contains invalid item"
            )
        elif invalid_item in inventory:
            inventory.remove(invalid_item)
            return FixResult(
                fixed=True,
                description=f"Removed invalid item '{invalid_item}' from starting inventory",
                error_pattern="Starting inventory contains invalid item"
            )
        
        return FixResult(
            fixed=False,
            description=f"Could not find item '{invalid_item}' in starting inventory",
            error_pattern="Starting inventory contains invalid item"
        )


def fix_world_data(world_data: WorldData, world_id: str) -> WorldFixerResult:
    """
    Attempt to fix validation errors in world data.
    
    Args:
        world_data: The world data to fix (modified in place)
        world_id: The world identifier for logging
    
    Returns:
        WorldFixerResult with details about fixes applied
    """
    fixer = WorldFixer(world_data, world_id)
    return fixer.fix()
