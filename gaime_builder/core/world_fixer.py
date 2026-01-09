"""
World Fixer - Attempts to auto-fix validation errors in generated worlds.

Uses rule-based fixes for structural issues (typos, invalid references).
Creative issues are handled by the separate WorldAnalyzer AI passes.
"""

import logging
import re
import sys
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path

# Add backend to path for model imports
BACKEND_PATH = Path(__file__).parent.parent.parent / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.engine.validator import ValidationResult, WorldValidator
from app.models.world import (
    ItemPlacement,
    WorldData,
)

logger = logging.getLogger(__name__)


@dataclass
class FixResult:
    """Result of a fix attempt"""
    fixed: bool
    description: str
    error_pattern: str  # Original error message pattern


@dataclass
class WorldFixerResult:
    """Result of world fixing attempts"""
    original_errors: list[str] = field(default_factory=list)
    fixes_applied: list[FixResult] = field(default_factory=list)
    remaining_errors: list[str] = field(default_factory=list)
    attempts: int = 0

    @property
    def fully_fixed(self) -> bool:
        return len(self.remaining_errors) == 0


def classify_error(error: str) -> dict | None:
    """
    Parse a validation error to extract details for rule-based fixing.

    Returns:
        Dict with error details if parseable, None otherwise
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
        (r"Victory item '(.+?)' is not obtainable",
         {"type": "victory_item_not_placed", "item": 1}),
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
            return details

    # Unknown error type - not fixable by rules
    return None


class WorldFixer:
    """
    Attempts to auto-fix validation errors in world data.

    Uses rule-based fixes for structural issues (typos, invalid references).
    Creative issues are handled by the separate WorldAnalyzer AI passes.
    """

    MAX_ATTEMPTS = 3

    def __init__(self, world_data: WorldData, world_id: str):
        self.world_data = world_data
        self.world_id = world_id
        self.result = WorldFixerResult()

    def fix(self) -> WorldFixerResult:
        """
        Attempt to fix validation errors using rule-based fixes.

        Handles structural issues like typos and invalid references using
        fuzzy matching. Creative issues should be handled by WorldAnalyzer.

        Returns:
            WorldFixerResult with fixes applied and remaining errors
        """
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

    def _validate(self) -> ValidationResult:
        """Run validation on current world data"""
        validator = WorldValidator(self.world_data, self.world_id)
        return validator.validate()

    def _attempt_rule_fixes(self, errors: list[str]) -> list[FixResult]:
        """Attempt rule-based fixes for each error"""
        fixes = []

        for error in errors:
            details = classify_error(error)
            if details is None:
                continue  # Not a fixable structural error

            fix_result = self._try_rule_fix(error, details)
            if fix_result and fix_result.fixed:
                fixes.append(fix_result)
                self.result.fixes_applied.append(fix_result)
                logger.debug(f"Rule fix: {fix_result.description}")

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
        elif error_type == "victory_item_not_placed":
            return self._fix_victory_item_not_placed(details["item"])
        elif error_type == "invalid_starting_item":
            return self._fix_invalid_starting_item(details["item"])

        return None

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

    def _fix_victory_item_not_placed(self, item_id: str) -> FixResult:
        """
        Fix a victory item that exists but is not placed in any location.

        Strategy: Place the item in the victory location, or a location
        that seems like a good place for a key item (not starting location).
        """
        # Check the item actually exists
        if item_id not in self.world_data.items:
            return FixResult(
                fixed=False,
                description=f"Cannot fix: item '{item_id}' not found in items",
                error_pattern=f"Victory item '{item_id}' is not obtainable"
            )

        # Find a suitable location to place the item
        # Preference order:
        # 1. Victory location (if valid)
        # 2. A location that sounds like an ending area
        # 3. Any location that's not the starting location
        target_location = None

        victory = self.world_data.world.victory
        starting_loc = self.world_data.world.player.starting_location
        valid_locations = list(self.world_data.locations.keys())

        # Try victory location first
        if victory and victory.location and victory.location in valid_locations:
            target_location = victory.location
        else:
            # Look for ending-sounding locations
            ending_keywords = ["final", "end", "exit", "throne", "sanctuary", "chamber", "core", "boss", "treasure"]
            for loc_id in valid_locations:
                if any(kw in loc_id.lower() for kw in ending_keywords) and loc_id != starting_loc:
                    target_location = loc_id
                    break

            # Fall back to any non-starting location
            if not target_location:
                for loc_id in valid_locations:
                    if loc_id != starting_loc:
                        target_location = loc_id
                        break

            # Last resort: starting location
            if not target_location:
                target_location = starting_loc

        # Place the item
        location = self.world_data.locations[target_location]
        item = self.world_data.items[item_id]

        # Create a placement with a generic description
        placement_desc = f"rests here, awaiting discovery"
        if item.description:
            placement_desc = f"can be found here"

        location.item_placements[item_id] = ItemPlacement(
            placement=placement_desc,
            hidden=False  # Make it visible so the game is completable
        )

        return FixResult(
            fixed=True,
            description=f"Placed victory item '{item_id}' in location '{target_location}'",
            error_pattern=f"Victory item '{item_id}' is not obtainable"
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
