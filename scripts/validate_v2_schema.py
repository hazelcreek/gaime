#!/usr/bin/env python3
"""
V2 Schema Validation Script

Validates world YAML files against the V2 schema (structured exits, details).
This script is used during migration to verify that worlds have been correctly
converted to the new format.

Usage:
    python scripts/validate_v2_schema.py --world cursed-manor
    python scripts/validate_v2_schema.py --all
    python scripts/validate_v2_schema.py --world test_world --fixture

The script checks:
- locations.yaml: exits should be ExitDefinition, details should be DetailDefinition
- items.yaml: should use scene_description/examine_description (or legacy aliases)
- Cross-references: exit destinations exist, revealed items exist
"""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Add backend to path for imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.models.world import (  # noqa: E402
    DetailDefinition,
    ExaminationEffect,
    ExitDefinition,
)


@dataclass
class ValidationMessage:
    """A validation error or warning."""

    level: str  # "error" or "warning"
    file: str  # "locations.yaml", "items.yaml", etc.
    path: str  # e.g., "entrance_hall.exits.north"
    message: str

    def __str__(self) -> str:
        icon = "❌" if self.level == "error" else "⚠️"
        return f"  {icon} {self.path}: {self.message}"


@dataclass
class WorldValidationResult:
    """Result of validating a world against V2 schema."""

    world_id: str
    messages: list[ValidationMessage] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for m in self.messages if m.level == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for m in self.messages if m.level == "warning")

    @property
    def is_v2_compliant(self) -> bool:
        """True if no errors (warnings are OK for transition)."""
        return self.error_count == 0

    def add_error(self, file: str, path: str, message: str) -> None:
        self.messages.append(ValidationMessage("error", file, path, message))

    def add_warning(self, file: str, path: str, message: str) -> None:
        self.messages.append(ValidationMessage("warning", file, path, message))

    def messages_by_file(self) -> dict[str, list[ValidationMessage]]:
        """Group messages by source file."""
        result: dict[str, list[ValidationMessage]] = {}
        for msg in self.messages:
            if msg.file not in result:
                result[msg.file] = []
            result[msg.file].append(msg)
        return result


class V2SchemaValidator:
    """Validates world YAML files against V2 schema."""

    def __init__(self, world_path: Path, world_id: str):
        self.world_path = world_path
        self.world_id = world_id
        self.result = WorldValidationResult(world_id=world_id)

        # Loaded YAML data
        self.locations_data: dict[str, Any] = {}
        self.items_data: dict[str, Any] = {}
        self.npcs_data: dict[str, Any] = {}

    def validate(self) -> WorldValidationResult:
        """Run all validation checks."""
        # Load YAML files
        if not self._load_yaml_files():
            return self.result

        # Validate each file
        self._validate_locations()
        self._validate_items()
        self._validate_cross_references()

        return self.result

    def _load_yaml_files(self) -> bool:
        """Load all YAML files. Returns False if critical files missing."""
        locations_file = self.world_path / "locations.yaml"
        items_file = self.world_path / "items.yaml"
        npcs_file = self.world_path / "npcs.yaml"

        if not locations_file.exists():
            self.result.add_error("locations.yaml", "", "File not found")
            return False

        with open(locations_file) as f:
            self.locations_data = yaml.safe_load(f) or {}

        if items_file.exists():
            with open(items_file) as f:
                self.items_data = yaml.safe_load(f) or {}

        if npcs_file.exists():
            with open(npcs_file) as f:
                self.npcs_data = yaml.safe_load(f) or {}

        return True

    def _validate_locations(self) -> None:
        """Validate locations.yaml against V2 schema."""
        for loc_id, loc_data in self.locations_data.items():
            if not isinstance(loc_data, dict):
                self.result.add_error(
                    "locations.yaml", loc_id, "Location must be a dict"
                )
                continue

            # Validate exits
            exits = loc_data.get("exits", {})
            for direction, exit_def in exits.items():
                self._validate_exit(loc_id, direction, exit_def)

            # Validate details
            details = loc_data.get("details", {})
            for detail_id, detail_def in details.items():
                self._validate_detail(loc_id, detail_id, detail_def)

    def _validate_exit(
        self, loc_id: str, direction: str, exit_def: Any
    ) -> None:
        """Validate a single exit definition."""
        path = f"{loc_id}.exits.{direction}"

        # V1 format: just a string (destination)
        if isinstance(exit_def, str):
            self.result.add_error(
                "locations.yaml",
                path,
                f'expected ExitDefinition object, got string "{exit_def}"',
            )
            return

        # V2 format: should be a dict matching ExitDefinition
        if not isinstance(exit_def, dict):
            self.result.add_error(
                "locations.yaml",
                path,
                f"expected ExitDefinition object, got {type(exit_def).__name__}",
            )
            return

        # Try to parse as ExitDefinition
        try:
            ExitDefinition.model_validate(exit_def)
        except Exception as e:
            # Extract the most relevant error message
            error_msg = str(e).split("\n")[0]
            self.result.add_error(
                "locations.yaml",
                path,
                f"invalid ExitDefinition: {error_msg}",
            )
            return

        # Check for missing recommended fields
        if not exit_def.get("scene_description"):
            self.result.add_warning(
                "locations.yaml",
                path,
                "missing scene_description (recommended for image generation)",
            )

    def _validate_detail(
        self, loc_id: str, detail_id: str, detail_def: Any
    ) -> None:
        """Validate a single detail definition."""
        path = f"{loc_id}.details.{detail_id}"

        # Skip direction-based details (these are legacy exit descriptions)
        directions = {"north", "south", "east", "west", "up", "down", "back"}
        if detail_id.lower() in directions:
            self.result.add_warning(
                "locations.yaml",
                path,
                "direction-based detail should be moved to exits[direction].scene_description",
            )
            return

        # V1 format: just a string (description)
        if isinstance(detail_def, str):
            self.result.add_error(
                "locations.yaml",
                path,
                f"expected DetailDefinition object, got string",
            )
            return

        # V2 format: should be a dict matching DetailDefinition
        if not isinstance(detail_def, dict):
            self.result.add_error(
                "locations.yaml",
                path,
                f"expected DetailDefinition object, got {type(detail_def).__name__}",
            )
            return

        # Try to parse as DetailDefinition
        try:
            DetailDefinition.model_validate(detail_def)
        except Exception as e:
            error_msg = str(e).split("\n")[0]
            self.result.add_error(
                "locations.yaml",
                path,
                f"invalid DetailDefinition: {error_msg}",
            )
            return

        # Validate on_examine if present
        on_examine = detail_def.get("on_examine")
        if on_examine:
            try:
                ExaminationEffect.model_validate(on_examine)
            except Exception as e:
                error_msg = str(e).split("\n")[0]
                self.result.add_error(
                    "locations.yaml",
                    f"{path}.on_examine",
                    f"invalid ExaminationEffect: {error_msg}",
                )

    def _validate_items(self) -> None:
        """Validate items.yaml against V2 schema."""
        for item_id, item_data in self.items_data.items():
            if not isinstance(item_data, dict):
                self.result.add_error(
                    "items.yaml", item_id, "Item must be a dict"
                )
                continue

            # Check for legacy field names (warning, not error - aliases work)
            if "found_description" in item_data:
                self.result.add_warning(
                    "items.yaml",
                    item_id,
                    "using legacy field 'found_description' (should be 'scene_description')",
                )

            if "examine" in item_data:
                self.result.add_warning(
                    "items.yaml",
                    item_id,
                    "using legacy field 'examine' (should be 'examine_description')",
                )

    def _validate_cross_references(self) -> None:
        """Validate cross-references between files."""
        valid_locations = set(self.locations_data.keys())
        valid_items = set(self.items_data.keys())

        # Check exit destinations
        for loc_id, loc_data in self.locations_data.items():
            if not isinstance(loc_data, dict):
                continue

            exits = loc_data.get("exits", {})
            for direction, exit_def in exits.items():
                # Get destination from either format
                if isinstance(exit_def, str):
                    dest = exit_def
                elif isinstance(exit_def, dict):
                    dest = exit_def.get("destination")
                else:
                    continue

                if dest and dest not in valid_locations:
                    self.result.add_error(
                        "locations.yaml",
                        f"{loc_id}.exits.{direction}",
                        f"destination '{dest}' does not exist",
                    )

        # Check reveals_item references in details
        for loc_id, loc_data in self.locations_data.items():
            if not isinstance(loc_data, dict):
                continue

            details = loc_data.get("details", {})
            for detail_id, detail_def in details.items():
                if not isinstance(detail_def, dict):
                    continue

                on_examine = detail_def.get("on_examine", {})
                if isinstance(on_examine, dict):
                    reveals_item = on_examine.get("reveals_item")
                    if reveals_item and reveals_item not in valid_items:
                        self.result.add_error(
                            "locations.yaml",
                            f"{loc_id}.details.{detail_id}.on_examine.reveals_item",
                            f"item '{reveals_item}' does not exist",
                        )


def validate_world(
    world_id: str, worlds_dir: Path | None = None, is_fixture: bool = False
) -> WorldValidationResult:
    """Validate a single world against V2 schema."""
    if is_fixture:
        world_path = BACKEND_DIR / "tests" / "fixtures" / world_id
    else:
        world_path = (worlds_dir or PROJECT_ROOT / "worlds") / world_id

    if not world_path.exists():
        result = WorldValidationResult(world_id=world_id)
        result.add_error("", "", f"World directory not found: {world_path}")
        return result

    validator = V2SchemaValidator(world_path, world_id)
    return validator.validate()


def print_result(result: WorldValidationResult) -> None:
    """Print validation result to console."""
    print(f"\nWorld: {result.world_id}")
    print("=" * 60)

    if not result.messages:
        print("✅ V2 compliant - no issues found!")
        return

    # Group messages by file
    by_file = result.messages_by_file()
    for file, messages in by_file.items():
        print(f"\n{file}:")
        for msg in messages:
            print(str(msg))

    # Summary
    print(f"\nSummary: {result.error_count} error(s), {result.warning_count} warning(s)")
    if result.is_v2_compliant:
        print("✅ V2 compliant (warnings only - migration recommended)")
    else:
        print("❌ Not V2 compliant - migration required")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate world YAML files against V2 schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_v2_schema.py --world cursed-manor
  python scripts/validate_v2_schema.py --all
  python scripts/validate_v2_schema.py --world test_world --fixture
        """,
    )
    parser.add_argument(
        "--world",
        type=str,
        help="Validate a specific world by name",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate all worlds in the worlds/ directory",
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Look for world in test fixtures instead of worlds/",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only show summary, not individual issues",
    )

    args = parser.parse_args()

    if not args.world and not args.all:
        parser.error("Either --world <name> or --all must be specified")

    print("🔍 V2 Schema Validation")
    print("=" * 60)

    worlds_to_check: list[str] = []
    is_fixture = args.fixture

    if args.all:
        if is_fixture:
            fixtures_dir = BACKEND_DIR / "tests" / "fixtures"
            worlds_to_check = [
                d.name for d in fixtures_dir.iterdir()
                if d.is_dir() and (d / "locations.yaml").exists()
            ]
        else:
            worlds_dir = PROJECT_ROOT / "worlds"
            worlds_to_check = [
                d.name for d in worlds_dir.iterdir()
                if d.is_dir() and (d / "locations.yaml").exists()
            ]
    else:
        worlds_to_check = [args.world]

    print(f"Worlds to validate: {', '.join(worlds_to_check)}")

    total_errors = 0
    total_warnings = 0
    v2_compliant = 0

    for world_id in sorted(worlds_to_check):
        result = validate_world(world_id, is_fixture=is_fixture)

        if args.summary_only:
            status = "✅" if result.is_v2_compliant else "❌"
            print(f"  {status} {world_id}: {result.error_count} errors, {result.warning_count} warnings")
        else:
            print_result(result)

        total_errors += result.error_count
        total_warnings += result.warning_count
        if result.is_v2_compliant:
            v2_compliant += 1

    # Final summary
    print("\n" + "=" * 60)
    print("OVERALL SUMMARY")
    print("=" * 60)
    print(f"Worlds checked: {len(worlds_to_check)}")
    print(f"V2 compliant: {v2_compliant}/{len(worlds_to_check)}")
    print(f"Total errors: {total_errors}")
    print(f"Total warnings: {total_warnings}")

    if total_errors > 0:
        print("\n❌ Some worlds need migration to V2 schema")
        sys.exit(1)
    elif total_warnings > 0:
        print("\n⚠️  All worlds are V2 compliant but have migration warnings")
        sys.exit(0)
    else:
        print("\n✅ All worlds are fully V2 compliant!")
        sys.exit(0)


if __name__ == "__main__":
    main()
