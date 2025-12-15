#!/usr/bin/env python3
"""
Migration script to fix schema issues in existing worlds.

Transforms:
- NPC `personality` from string to object with traits/speech_style/quirks
- NPC `dialogue_hints` to `dialogue_rules` list
- Location `constraints` with locked_exit patterns to `requires` object
"""

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

import yaml


# Preserve YAML formatting with custom representer
def str_representer(dumper: yaml.Dumper, data: str) -> yaml.Node:
    """Use literal block style for multiline strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, str_representer)


WORLDS_DIR = Path(__file__).parent.parent / "worlds"

# Worlds that need migration (confirmed from inspection)
WORLDS_TO_MIGRATE = [
    "islay-mist-mystery",
    "whistlewood_fable",
    "hazel_city_1885",
    "detention_survival_high",
    "echoes_of_subjugation",
]


def parse_personality_string(personality_str: str) -> dict:
    """
    Convert personality string to structured object.
    
    Example:
        "Gruff, suspicious, superstitious." 
        -> {traits: ["gruff", "suspicious", "superstitious"], speech_style: "...", quirks: []}
    """
    # Extract traits from comma-separated string
    # Remove trailing period and split
    clean = personality_str.rstrip(".").strip()
    raw_traits = [t.strip().lower() for t in clean.split(",") if t.strip()]
    
    return {
        "traits": raw_traits,
        "speech_style": f"Speaks with a {', '.join(raw_traits)} manner",
        "quirks": [],
    }


def convert_dialogue_hints_to_rules(dialogue_hints: dict) -> list[str]:
    """
    Convert dialogue_hints dict to dialogue_rules list.
    
    Example:
        {greeting: "'Ay? Who are you?'", refusal: "'I don't talk to strangers.'"}
        -> ["Greets with: 'Ay? Who are you?'", "Refuses with: 'I don't talk to strangers.'"]
    """
    rules = []
    for hint_type, hint_text in dialogue_hints.items():
        # Clean up the hint type for readability
        readable_type = hint_type.replace("_", " ").title()
        rules.append(f"{readable_type}: {hint_text}")
    return rules


def migrate_npc(npc_id: str, npc_data: dict, dry_run: bool = False) -> tuple[dict, list[str]]:
    """
    Migrate a single NPC to the new schema.
    
    Returns:
        Tuple of (migrated_data, list of changes made)
    """
    changes = []
    migrated = dict(npc_data)  # Shallow copy
    
    # Migrate personality string -> object
    if "personality" in migrated and isinstance(migrated["personality"], str):
        old_personality = migrated["personality"]
        migrated["personality"] = parse_personality_string(old_personality)
        changes.append(f"  personality: '{old_personality[:50]}...' -> structured object")
    
    # Migrate dialogue_hints -> dialogue_rules
    if "dialogue_hints" in migrated:
        old_hints = migrated.pop("dialogue_hints")
        migrated["dialogue_rules"] = convert_dialogue_hints_to_rules(old_hints)
        changes.append(f"  dialogue_hints ({len(old_hints)} entries) -> dialogue_rules list")
    
    return migrated, changes


def parse_locked_exit_constraint(constraint: str) -> tuple[str | None, str | None]:
    """
    Parse a locked_exit constraint string.
    
    Example:
        "locked_exit: north requires code_revealed flag"
        -> ("north", "code_revealed")
    
    Returns:
        Tuple of (direction, flag_name) or (None, None) if not a locked_exit constraint
    """
    pattern = r"locked_exit:\s*(\w+)\s+requires\s+(\w+)\s+flag"
    match = re.match(pattern, constraint, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    return None, None


def migrate_location(loc_id: str, loc_data: dict, dry_run: bool = False) -> tuple[dict, list[str]]:
    """
    Migrate a single location to the new schema.
    
    Returns:
        Tuple of (migrated_data, list of changes made)
    """
    changes = []
    migrated = dict(loc_data)
    
    # Migrate constraints with locked_exit patterns -> requires
    if "constraints" in migrated:
        constraints = migrated.get("constraints", [])
        remaining_constraints = []
        
        for constraint in constraints:
            direction, flag = parse_locked_exit_constraint(constraint)
            if direction and flag:
                # Convert to requires field
                if "requires" not in migrated:
                    migrated["requires"] = {}
                migrated["requires"]["flag"] = flag
                changes.append(f"  constraint '{constraint}' -> requires.flag: {flag}")
            else:
                remaining_constraints.append(constraint)
        
        # Remove constraints if all were converted
        if not remaining_constraints:
            del migrated["constraints"]
        else:
            migrated["constraints"] = remaining_constraints
    
    return migrated, changes


def migrate_npcs_file(world_path: Path, dry_run: bool = False) -> list[str]:
    """Migrate all NPCs in a world's npcs.yaml file."""
    npcs_file = world_path / "npcs.yaml"
    if not npcs_file.exists():
        return [f"  No npcs.yaml found in {world_path.name}"]
    
    with open(npcs_file) as f:
        npcs = yaml.safe_load(f) or {}
    
    all_changes = []
    migrated_npcs = {}
    
    for npc_id, npc_data in npcs.items():
        migrated, changes = migrate_npc(npc_id, npc_data, dry_run)
        migrated_npcs[npc_id] = migrated
        if changes:
            all_changes.append(f"NPC '{npc_id}':")
            all_changes.extend(changes)
    
    if all_changes and not dry_run:
        with open(npcs_file, "w") as f:
            yaml.dump(migrated_npcs, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return all_changes


def migrate_locations_file(world_path: Path, dry_run: bool = False) -> list[str]:
    """Migrate all locations in a world's locations.yaml file."""
    locations_file = world_path / "locations.yaml"
    if not locations_file.exists():
        return [f"  No locations.yaml found in {world_path.name}"]
    
    with open(locations_file) as f:
        locations = yaml.safe_load(f) or {}
    
    all_changes = []
    migrated_locations = {}
    
    for loc_id, loc_data in locations.items():
        migrated, changes = migrate_location(loc_id, loc_data, dry_run)
        migrated_locations[loc_id] = migrated
        if changes:
            all_changes.append(f"Location '{loc_id}':")
            all_changes.extend(changes)
    
    if all_changes and not dry_run:
        with open(locations_file, "w") as f:
            yaml.dump(migrated_locations, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return all_changes


def backup_world(world_path: Path) -> Path:
    """Create a timestamped backup of a world folder."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = world_path.parent / f"{world_path.name}_backup_{timestamp}"
    shutil.copytree(world_path, backup_path)
    return backup_path


def migrate_world(world_name: str, dry_run: bool = False, skip_backup: bool = False) -> None:
    """Migrate a single world to the new schema."""
    world_path = WORLDS_DIR / world_name
    
    if not world_path.exists():
        print(f"❌ World '{world_name}' not found at {world_path}")
        return
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating: {world_name}")
    print("=" * 50)
    
    # Create backup unless skipped or dry run
    if not dry_run and not skip_backup:
        backup_path = backup_world(world_path)
        print(f"📦 Backup created: {backup_path.name}")
    
    # Migrate NPCs
    npc_changes = migrate_npcs_file(world_path, dry_run)
    if npc_changes:
        print("\n📝 NPC Changes:")
        for change in npc_changes:
            print(f"  {change}")
    else:
        print("\n✅ NPCs: No changes needed")
    
    # Migrate locations
    loc_changes = migrate_locations_file(world_path, dry_run)
    if loc_changes:
        print("\n📍 Location Changes:")
        for change in loc_changes:
            print(f"  {change}")
    else:
        print("\n✅ Locations: No changes needed")
    
    if not npc_changes and not loc_changes:
        print("\n✅ World already compliant with schema")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate world YAML files to match Pydantic schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_worlds.py --dry-run              # Preview all changes
  python migrate_worlds.py                        # Migrate all worlds (with backup)
  python migrate_worlds.py --world islay-mist-mystery  # Migrate single world
  python migrate_worlds.py --skip-backup          # Migrate without backup
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without modifying files",
    )
    parser.add_argument(
        "--world",
        type=str,
        help="Migrate only the specified world",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip creating backup before migration",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Migrate all worlds, not just known problematic ones",
    )
    
    args = parser.parse_args()
    
    print("🔧 World Schema Migration Tool")
    print("=" * 50)
    
    if args.world:
        worlds = [args.world]
    elif args.all:
        worlds = [d.name for d in WORLDS_DIR.iterdir() if d.is_dir()]
    else:
        worlds = WORLDS_TO_MIGRATE
    
    print(f"Worlds to process: {', '.join(worlds)}")
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No files will be modified\n")
    
    for world_name in worlds:
        migrate_world(world_name, dry_run=args.dry_run, skip_backup=args.skip_backup)
    
    print("\n" + "=" * 50)
    if args.dry_run:
        print("✅ Dry run complete. Run without --dry-run to apply changes.")
    else:
        print("✅ Migration complete!")


if __name__ == "__main__":
    main()
