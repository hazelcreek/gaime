"""
World Validator - Validates consistency of YAML world definitions

Checks:
- Flag consistency: flags checked are set somewhere
- Flag uniqueness: each flag is set by exactly one source
- Location references: exits, item locations, NPC locations are valid
- Item references: requires_item, unlocks reference valid items
- Puzzle solvability:
  - No duplicate item placements (item in both inventory and location)
  - No circular key dependencies (key behind the lock it opens)
  - All requires_key items exist and are reachable
- NPC placements: NPCs with location must have placement entry
- Exit reciprocity: bidirectional exits use inverse directions (warning)
- Exit symmetry: if A→B exists, B→A must exist (error)
- Victory flag location: victory flag must only be settable in victory location
- Orphan detection: flags set but never checked (warnings)
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path

from app.engine.world import WorldLoader
from app.models.world import WorldData


@dataclass
class ValidationResult:
    """Result of world validation"""

    world_id: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """World is valid if there are no errors (warnings are OK)"""
        return len(self.errors) == 0

    def add_error(self, message: str):
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)


class WorldValidator:
    """Validates world definition consistency"""

    def __init__(self, world_data: WorldData, world_id: str):
        self.world_data = world_data
        self.world_id = world_id
        self.result = ValidationResult(world_id=world_id)

        # Collect all flags that are SET and CHECKED
        self.flags_set: dict[str, list[str]] = {}  # flag -> [locations where set]
        self.flags_checked: dict[str, list[str]] = {}  # flag -> [places where checked]

    def validate(self) -> ValidationResult:
        """Run all validation checks"""
        self._collect_flags()
        self._validate_flag_consistency()
        self._validate_flag_uniqueness()
        self._validate_location_references()
        self._validate_item_references()
        self._validate_puzzle_solvability()
        self._validate_npc_placements()
        self._validate_exit_reciprocity()
        self._validate_exit_symmetry()
        self._validate_victory_flag_location()
        self._detect_orphan_flags()

        return self.result

    def _collect_flags(self):
        """Collect all flags that are set and checked in the world"""
        # Flags SET by location interactions
        for loc_id, location in self.world_data.locations.items():
            if location.interactions:
                for int_id, interaction in location.interactions.items():
                    if interaction.sets_flag:
                        self._record_flag_set(
                            interaction.sets_flag,
                            f"location:{loc_id}/interaction:{int_id}",
                        )

        # Phase 4: Flags SET by detail.on_examine
        for loc_id, location in self.world_data.locations.items():
            if location.details:
                for detail_id, detail_def in location.details.items():
                    if detail_def.on_examine and detail_def.on_examine.sets_flag:
                        self._record_flag_set(
                            detail_def.on_examine.sets_flag,
                            f"location:{loc_id}/detail:{detail_id}/on_examine",
                        )

        # Flags SET by item use_actions
        for item_id, item in self.world_data.items.items():
            if item.use_actions:
                for action_id, action in item.use_actions.items():
                    if action.sets_flag:
                        self._record_flag_set(
                            action.sets_flag, f"item:{item_id}/action:{action_id}"
                        )

        # Phase 4: Flags SET by item.on_examine
        for item_id, item in self.world_data.items.items():
            if item.on_examine and item.on_examine.sets_flag:
                self._record_flag_set(
                    item.on_examine.sets_flag, f"item:{item_id}/on_examine"
                )

        # Flags CHECKED by location requires
        for loc_id, location in self.world_data.locations.items():
            if location.requires and location.requires.flag:
                self._record_flag_checked(
                    location.requires.flag, f"location:{loc_id}/requires"
                )

        # V3: Flags CHECKED by item_placements find_condition
        for loc_id, location in self.world_data.locations.items():
            for item_id, placement in location.item_placements.items():
                if placement.find_condition:
                    required_flag = placement.find_condition.get("requires_flag")
                    if required_flag:
                        self._record_flag_checked(
                            required_flag,
                            f"location:{loc_id}/item_placements:{item_id}",
                        )

        # V3: Flags CHECKED by exit find_condition (hidden exits)
        for loc_id, location in self.world_data.locations.items():
            for direction, exit_def in location.exits.items():
                if exit_def.find_condition:
                    required_flag = exit_def.find_condition.get("requires_flag")
                    if required_flag:
                        self._record_flag_checked(
                            required_flag,
                            f"location:{loc_id}/exit:{direction}",
                        )

        # V3: Flags CHECKED by detail find_condition (hidden details)
        for loc_id, location in self.world_data.locations.items():
            if location.details:
                for detail_id, detail_def in location.details.items():
                    if detail_def.find_condition:
                        required_flag = detail_def.find_condition.get("requires_flag")
                        if required_flag:
                            self._record_flag_checked(
                                required_flag,
                                f"location:{loc_id}/detail:{detail_id}",
                            )

        # V3: Flags CHECKED by npc_placements find_condition (hidden NPCs)
        for loc_id, location in self.world_data.locations.items():
            for npc_id, placement in location.npc_placements.items():
                if placement.find_condition:
                    required_flag = placement.find_condition.get("requires_flag")
                    if required_flag:
                        self._record_flag_checked(
                            required_flag,
                            f"location:{loc_id}/npc_placements:{npc_id}",
                        )

        # Flags CHECKED by NPC appears_when
        for npc_id, npc in self.world_data.npcs.items():
            if npc.appears_when:
                for condition in npc.appears_when:
                    if condition.condition == "has_flag":
                        self._record_flag_checked(
                            str(condition.value), f"npc:{npc_id}/appears_when"
                        )

        # Flags CHECKED by NPC location_changes
        for npc_id, npc in self.world_data.npcs.items():
            for change in npc.location_changes:
                if change.when_flag:
                    self._record_flag_checked(
                        change.when_flag, f"npc:{npc_id}/location_changes"
                    )

        # Flags CHECKED by victory condition
        if self.world_data.world.victory and self.world_data.world.victory.flag:
            self._record_flag_checked(
                self.world_data.world.victory.flag, "world/victory"
            )

    def _record_flag_set(self, flag: str, location: str):
        if flag not in self.flags_set:
            self.flags_set[flag] = []
        self.flags_set[flag].append(location)

    def _record_flag_checked(self, flag: str, location: str):
        if flag not in self.flags_checked:
            self.flags_checked[flag] = []
        self.flags_checked[flag].append(location)

    def _validate_flag_consistency(self):
        """Check that all checked flags are set somewhere"""
        for flag, check_locations in self.flags_checked.items():
            if flag not in self.flags_set:
                for loc in check_locations:
                    self.result.add_error(
                        f"Flag '{flag}' is checked at {loc} but never set anywhere"
                    )

    def _validate_flag_uniqueness(self):
        """
        Check that each flag is set by exactly one source.

        Multiple sources setting the same flag can cause unintended game states,
        especially for victory flags where the player could bypass intended paths.
        """
        for flag, set_locations in self.flags_set.items():
            if len(set_locations) > 1:
                sources = ", ".join(set_locations)
                self.result.add_error(
                    f"Flag '{flag}' is set by multiple sources: {sources} - "
                    f"each flag should be set by exactly one source"
                )

    def _validate_location_references(self):
        """Validate all location references are valid"""
        valid_locations = set(self.world_data.locations.keys())

        # Check exits (V2 schema: exits are ExitDefinition objects)
        for loc_id, location in self.world_data.locations.items():
            for direction, exit_def in location.exits.items():
                dest_id = exit_def.destination
                if dest_id not in valid_locations:
                    self.result.add_error(
                        f"Location '{loc_id}' exit '{direction}' points to invalid location '{dest_id}'"
                    )

        # V3: Check item_placements reference valid items
        for loc_id, location in self.world_data.locations.items():
            for item_id in location.item_placements.keys():
                if item_id not in self.world_data.items:
                    self.result.add_error(
                        f"Location '{loc_id}' item_placements references invalid item '{item_id}'"
                    )

        # Check NPC locations
        for npc_id, npc in self.world_data.npcs.items():
            if npc.location and npc.location not in valid_locations:
                self.result.add_error(
                    f"NPC '{npc_id}' has invalid location '{npc.location}'"
                )
            for loc in npc.locations:
                if loc not in valid_locations:
                    self.result.add_error(
                        f"NPC '{npc_id}' has invalid roaming location '{loc}'"
                    )
            # Check location_changes destinations
            for change in npc.location_changes:
                if change.move_to and change.move_to not in valid_locations:
                    self.result.add_error(
                        f"NPC '{npc_id}' location_change has invalid destination '{change.move_to}'"
                    )

        # Check starting location
        starting_loc = self.world_data.world.player.starting_location
        if starting_loc not in valid_locations:
            self.result.add_error(
                f"Player starting_location '{starting_loc}' is invalid"
            )

        # Check victory location
        if self.world_data.world.victory and self.world_data.world.victory.location:
            if self.world_data.world.victory.location not in valid_locations:
                self.result.add_error(
                    f"Victory location '{self.world_data.world.victory.location}' is invalid"
                )

    def _validate_item_references(self):
        """Validate all item references are valid"""
        valid_items = set(self.world_data.items.keys())

        # Check requires_item in use_actions
        for item_id, item in self.world_data.items.items():
            if item.use_actions:
                for action_id, action in item.use_actions.items():
                    if action.requires_item and action.requires_item not in valid_items:
                        self.result.add_error(
                            f"Item '{item_id}' action '{action_id}' requires invalid item '{action.requires_item}'"
                        )

        # Check starting inventory
        for item_id in self.world_data.world.player.starting_inventory:
            if item_id not in valid_items:
                self.result.add_error(
                    f"Starting inventory contains invalid item '{item_id}'"
                )

        # V3: Check items in item_placements are valid
        for loc_id, location in self.world_data.locations.items():
            for item_id in location.item_placements.keys():
                if item_id not in valid_items:
                    self.result.add_error(
                        f"Location '{loc_id}' item_placements references invalid item '{item_id}'"
                    )

        # Check victory item exists
        if self.world_data.world.victory and self.world_data.world.victory.item:
            victory_item = self.world_data.world.victory.item
            if victory_item not in valid_items:
                self.result.add_error(f"Victory item '{victory_item}' is invalid")
            else:
                # Check victory item is obtainable (placed or in starting inventory)
                items_obtainable = set(self.world_data.world.player.starting_inventory)
                for loc_id, location in self.world_data.locations.items():
                    items_obtainable.update(location.item_placements.keys())
                    # Also check interactions that give items
                    if location.interactions:
                        for interaction in location.interactions.values():
                            if interaction.gives_item:
                                items_obtainable.add(interaction.gives_item)

                if victory_item not in items_obtainable:
                    self.result.add_error(
                        f"Victory item '{victory_item}' is not obtainable - not placed in any location or starting inventory"
                    )

        # Check location requires_item
        for loc_id, location in self.world_data.locations.items():
            if location.requires and location.requires.item:
                if location.requires.item not in valid_items:
                    self.result.add_error(
                        f"Location '{loc_id}' requires invalid item '{location.requires.item}'"
                    )

    def _validate_puzzle_solvability(self):
        """
        Validate puzzle solvability constraints.

        Checks:
        - No duplicate item placements (item in both starting_inventory AND locations)
        - No circular key dependencies (key behind the lock it opens)
        - All requires_key items exist and are placed somewhere
        """
        starting_inventory = set(self.world_data.world.player.starting_inventory)

        # Build map of where each item is placed
        item_locations: dict[str, str] = {}
        for loc_id, location in self.world_data.locations.items():
            for item_id in location.item_placements.keys():
                item_locations[item_id] = loc_id

        # Check 1: Duplicate item placement
        for item_id in starting_inventory:
            if item_id in item_locations:
                self.result.add_error(
                    f"Item '{item_id}' is in both starting_inventory AND "
                    f"placed at location '{item_locations[item_id]}' - remove one"
                )

        # Check 2 & 3: requires_key validation and circular dependencies
        # Build a map of locked exits and what key they require
        locked_exits: list[tuple[str, str, str, str]] = (
            []
        )  # (from_loc, direction, to_loc, key_id)

        for loc_id, location in self.world_data.locations.items():
            for direction, exit_def in location.exits.items():
                if exit_def.requires_key:
                    key_id = exit_def.requires_key
                    dest_id = exit_def.destination

                    # Check 3: requires_key item must exist
                    if key_id not in self.world_data.items:
                        self.result.add_error(
                            f"Exit '{direction}' in '{loc_id}' requires_key '{key_id}' "
                            f"which does not exist in items"
                        )
                        continue

                    # Check 3: requires_key item must be placed or in inventory
                    if (
                        key_id not in item_locations
                        and key_id not in starting_inventory
                    ):
                        # Also check if any interaction gives this item
                        item_given_by_interaction = False
                        for check_loc in self.world_data.locations.values():
                            if check_loc.interactions:
                                for interaction in check_loc.interactions.values():
                                    if interaction.gives_item == key_id:
                                        item_given_by_interaction = True
                                        break
                            if item_given_by_interaction:
                                break

                        if not item_given_by_interaction:
                            self.result.add_error(
                                f"Exit '{direction}' in '{loc_id}' requires_key '{key_id}' "
                                f"but this item is not placed anywhere or in starting inventory"
                            )
                        continue

                    locked_exits.append((loc_id, direction, dest_id, key_id))

        # Check 2: Direct circular dependencies - key placed at immediate destination
        # with no alternate entry point
        #
        # A circular dependency exists when:
        # - Exit A→B requires key K
        # - Key K is at location B
        # - Location B has no OTHER unlocked entry points
        #
        # If B has another entry (even if locked by a different key), we don't
        # report circular dependency here - the "other key not placed" error
        # will catch that case instead.
        for from_loc, direction, to_loc, key_id in locked_exits:
            if key_id in starting_inventory:
                continue  # Key is in inventory, no problem

            key_location = item_locations.get(key_id)
            if not key_location:
                continue  # Already reported as error above

            # Only check if key is at the immediate destination
            if key_location != to_loc:
                continue

            # Check if destination has any OTHER entry points
            has_alternate_entry = False
            for loc_id, location in self.world_data.locations.items():
                for exit_dir, exit_def in location.exits.items():
                    if exit_def.destination == to_loc:
                        # Skip the exit we're checking
                        if loc_id == from_loc and exit_dir == direction:
                            continue
                        # Skip hidden exits (not usable)
                        if exit_def.hidden:
                            continue
                        # Found an alternate entry (even if locked by different key)
                        has_alternate_entry = True
                        break
                if has_alternate_entry:
                    break

            if not has_alternate_entry:
                self.result.add_error(
                    f"Circular dependency: Exit '{direction}' in '{from_loc}' "
                    f"requires key '{key_id}', but the key is placed at the "
                    f"destination '{to_loc}' which has no other entry points"
                )

    def _validate_npc_placements(self):
        """
        Check that NPCs with a location field have a corresponding npc_placements entry.

        If an NPC declares a location in npcs.yaml but isn't in that location's
        npc_placements, the NPC won't appear in the game.
        """
        for npc_id, npc in self.world_data.npcs.items():
            if npc.location:
                location = self.world_data.locations.get(npc.location)
                if location and npc_id not in location.npc_placements:
                    self.result.add_error(
                        f"NPC '{npc_id}' declares location '{npc.location}' but is not "
                        f"in that location's npc_placements - add placement or remove location field"
                    )

    def _validate_exit_reciprocity(self):
        """
        Check that bidirectional exits use inverse directions (warning).

        For spatial consistency, if location A has exit 'down' to B,
        then B's exit back to A should be 'up', not 'out'.

        Exceptions:
        - Vertical (up/down) combined with horizontal (north/south/east/west)
          is acceptable for stairs, subway entrances, etc.
        """
        inverse_directions = {
            "north": "south",
            "south": "north",
            "east": "west",
            "west": "east",
            "up": "down",
            "down": "up",
            "in": "out",
            "out": "in",
        }

        # Directions that can mix with verticals (subway: west → down, up → east)
        horizontal_dirs = {"north", "south", "east", "west"}
        vertical_dirs = {"up", "down"}

        for loc_id, location in self.world_data.locations.items():
            for direction, exit_def in location.exits.items():
                dest_id = exit_def.destination
                dest_loc = self.world_data.locations.get(dest_id)
                if not dest_loc:
                    continue  # Invalid destination handled elsewhere

                # Find the return exit
                for ret_dir, ret_exit in dest_loc.exits.items():
                    if ret_exit.destination == loc_id:
                        expected = inverse_directions.get(direction)

                        # Skip if mixing horizontal/vertical (common for stairs, subways)
                        dir_is_horizontal = direction in horizontal_dirs
                        dir_is_vertical = direction in vertical_dirs
                        ret_is_horizontal = ret_dir in horizontal_dirs
                        ret_is_vertical = ret_dir in vertical_dirs

                        if (dir_is_horizontal and ret_is_vertical) or (
                            dir_is_vertical and ret_is_horizontal
                        ):
                            # Mixed horizontal/vertical is OK (subway entrance pattern)
                            break

                        # Only warn if direction has an inverse AND return uses a
                        # standard direction that doesn't match expected
                        if (
                            expected
                            and ret_dir in inverse_directions
                            and ret_dir != expected
                        ):
                            self.result.add_warning(
                                f"Exit direction mismatch: '{loc_id}' -> {direction} -> "
                                f"'{dest_id}' returns via '{ret_dir}' (expected '{expected}')"
                            )
                        break  # Found return exit, stop searching

    def _validate_exit_symmetry(self):
        """
        Check for asymmetric exits (A→B exists but B→A doesn't).

        In most text adventures, if you can go from A to B, you should be able
        to go back from B to A. Missing return exits create unreachable areas
        or one-way traps.

        This is an ERROR because it usually indicates a bug in world generation
        that causes map connectivity issues.
        """
        for loc_id, location in self.world_data.locations.items():
            for direction, exit_def in location.exits.items():
                dest_id = exit_def.destination
                dest_loc = self.world_data.locations.get(dest_id)
                if not dest_loc:
                    continue  # Invalid destination handled elsewhere

                # Check if destination has ANY exit back to this location
                has_return_exit = any(
                    ret_exit.destination == loc_id
                    for ret_exit in dest_loc.exits.values()
                )

                if not has_return_exit:
                    self.result.add_error(
                        f"Asymmetric exit: '{loc_id}' has exit '{direction}' to "
                        f"'{dest_id}', but '{dest_id}' has no exit back to '{loc_id}'. "
                        f"Add a return exit or verify this one-way path is intentional."
                    )

    def _validate_victory_flag_location(self):
        """
        Check that the victory flag can only be set in the victory location.

        If the victory flag can be set outside the victory location, players
        could complete the game without following the intended path.
        """
        victory = self.world_data.world.victory
        if not victory or not victory.flag or not victory.location:
            return

        victory_flag = victory.flag
        victory_loc = victory.location

        # Check all sources that set this flag
        for flag, set_locations in self.flags_set.items():
            if flag == victory_flag:
                for source in set_locations:
                    # Parse the source to get the location
                    # Format: "location:loc_id/..." or "item:item_id/..."
                    if source.startswith("location:"):
                        # Extract location ID from "location:loc_id/..."
                        loc_part = source.split("/")[0]  # "location:loc_id"
                        source_loc = loc_part.replace("location:", "")
                        if source_loc != victory_loc:
                            self.result.add_error(
                                f"Victory flag '{victory_flag}' can be set outside "
                                f"victory location '{victory_loc}': {source} - "
                                f"this allows bypassing the intended path"
                            )

    def _detect_orphan_flags(self):
        """
        Detect flags that are set but never checked.

        Smart detection:
        - ERROR: Flags that sound like unlock mechanisms but aren't wired to exits
        - WARNING: Other orphan flags (may be intentional lore tracking)
        """
        # Patterns that suggest an unlock/gate mechanism
        unlock_patterns = [
            "unlock",
            "unlocked",
            "open",
            "opened",
            "access",
            "impressed",
            "distracted",
            "bribed",
            "convinced",
            "appeased",
            "satisfied",
            "completed",
            "solved",
            "disabled",
            "removed",
            "cleared",
        ]

        # Collect all locked exits that could be flag-gated
        # (locked: true without requires_key, or with find_condition)
        locked_exits_without_unlock: list[tuple[str, str]] = []  # (loc_id, direction)
        exits_with_find_condition: set[str] = set()  # flags that ARE checked by exits

        for loc_id, location in self.world_data.locations.items():
            for direction, exit_def in location.exits.items():
                if exit_def.locked:
                    if exit_def.find_condition:
                        # This exit properly checks a flag
                        req_flag = exit_def.find_condition.get("requires_flag")
                        if req_flag:
                            exits_with_find_condition.add(req_flag)
                    elif not exit_def.requires_key:
                        # Locked but no unlock mechanism - might be broken or permanent
                        locked_exits_without_unlock.append((loc_id, direction))

        for flag, set_locations in self.flags_set.items():
            if flag in self.flags_checked:
                continue  # Flag is used somewhere, not orphan

            # Check if this flag sounds like an unlock mechanism
            flag_lower = flag.lower()
            is_unlock_flag = any(pattern in flag_lower for pattern in unlock_patterns)

            if is_unlock_flag and locked_exits_without_unlock:
                # This looks like a broken gate - flag sounds like unlock but
                # there are locked exits that don't check any flag
                for loc in set_locations:
                    self.result.add_error(
                        f"Likely broken gate: Flag '{flag}' is set at {loc} but no locked exit "
                        f"checks this flag. Locked exits without unlock: "
                        f"{', '.join(f'{loc_id}/{direction}' for loc_id, direction in locked_exits_without_unlock[:3])}"
                    )
            else:
                # Regular orphan flag - just a warning (might be lore tracking)
                # Skip warning for flags that are clearly lore/discovery
                lore_patterns = [
                    "found",
                    "examined",
                    "read",
                    "discovered",
                    "learned",
                    "saw",
                    "heard",
                ]
                is_lore_flag = any(pattern in flag_lower for pattern in lore_patterns)

                if not is_lore_flag:
                    # Only warn about non-lore orphan flags
                    for loc in set_locations:
                        self.result.add_warning(
                            f"Flag '{flag}' is set at {loc} but never checked anywhere"
                        )


def validate_world(
    world_id: str, worlds_dir: str | Path | None = None
) -> ValidationResult:
    """
    Validate a world definition for consistency.

    Args:
        world_id: The world identifier (folder name in worlds/)
        worlds_dir: Optional path to worlds directory

    Returns:
        ValidationResult with errors and warnings
    """
    loader = WorldLoader(worlds_dir)
    world_data = loader.load_world(world_id)

    validator = WorldValidator(world_data, world_id)
    return validator.validate()


def main():
    """CLI entry point for world validation"""
    if len(sys.argv) < 2:
        print("Usage: python -m app.engine.validator <world_id>")
        print("Example: python -m app.engine.validator cursed-manor")
        sys.exit(1)

    world_id = sys.argv[1]

    try:
        result = validate_world(world_id)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Print results
    print(f"\n{'='*60}")
    print(f"World Validation: {world_id}")
    print(f"{'='*60}\n")

    if result.errors:
        print(f"ERRORS ({len(result.errors)}):")
        for error in result.errors:
            print(f"  ❌ {error}")
        print()

    if result.warnings:
        print(f"WARNINGS ({len(result.warnings)}):")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")
        print()

    if result.is_valid:
        print("✅ World is valid!")
        if result.warnings:
            print(f"   (but has {len(result.warnings)} warning(s))")
    else:
        print(f"❌ World has {len(result.errors)} error(s)")

    sys.exit(0 if result.is_valid else 1)


if __name__ == "__main__":
    main()
