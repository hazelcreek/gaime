"""
World Validator - Validates consistency of YAML world definitions

Checks:
- Flag consistency: flags checked are set somewhere
- Location references: exits, item locations, NPC locations are valid
- Item references: requires_item, unlocks reference valid items
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
        self._validate_location_references()
        self._validate_item_references()
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

        # Flags SET by item use_actions
        for item_id, item in self.world_data.items.items():
            if item.use_actions:
                for action_id, action in item.use_actions.items():
                    if action.sets_flag:
                        self._record_flag_set(
                            action.sets_flag, f"item:{item_id}/action:{action_id}"
                        )

        # Flags CHECKED by location requires
        for loc_id, location in self.world_data.locations.items():
            if location.requires and location.requires.flag:
                self._record_flag_checked(
                    location.requires.flag, f"location:{loc_id}/requires"
                )

        # Flags CHECKED by item find_condition
        for item_id, item in self.world_data.items.items():
            if item.find_condition:
                required_flag = item.find_condition.get("requires_flag")
                if required_flag:
                    self._record_flag_checked(
                        required_flag, f"item:{item_id}/find_condition"
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

    def _validate_location_references(self):
        """Validate all location references are valid"""
        valid_locations = set(self.world_data.locations.keys())

        # Check exits
        for loc_id, location in self.world_data.locations.items():
            for direction, dest_id in location.exits.items():
                if dest_id not in valid_locations:
                    self.result.add_error(
                        f"Location '{loc_id}' exit '{direction}' points to invalid location '{dest_id}'"
                    )

        # Check item locations
        for item_id, item in self.world_data.items.items():
            if item.location and item.location not in valid_locations:
                self.result.add_error(
                    f"Item '{item_id}' has invalid location '{item.location}'"
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

        # Check items listed in locations
        for loc_id, location in self.world_data.locations.items():
            for item_id in location.items:
                if item_id not in valid_items:
                    self.result.add_error(
                        f"Location '{loc_id}' lists invalid item '{item_id}'"
                    )

        # Check victory item
        if self.world_data.world.victory and self.world_data.world.victory.item:
            if self.world_data.world.victory.item not in valid_items:
                self.result.add_error(
                    f"Victory item '{self.world_data.world.victory.item}' is invalid"
                )

        # Check location requires_item
        for loc_id, location in self.world_data.locations.items():
            if location.requires and location.requires.item:
                if location.requires.item not in valid_items:
                    self.result.add_error(
                        f"Location '{loc_id}' requires invalid item '{location.requires.item}'"
                    )

    def _detect_orphan_flags(self):
        """Detect flags that are set but never checked (warnings only)"""
        for flag, set_locations in self.flags_set.items():
            if flag not in self.flags_checked:
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
