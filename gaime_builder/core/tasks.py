"""
Background Task Manager for GAIME Builder TUI.

Provides a task queue system that runs LLM operations in background workers
while keeping the TUI responsive. Uses Textual's Worker system under the hood.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
from datetime import datetime

import yaml


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a queued task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """Progress information for a task."""
    current: float = 0.0  # 0.0 to 1.0
    message: str = ""
    sub_task: str = ""  # For multi-step tasks


@dataclass
class TaskResult:
    """Result of a completed task."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class QueuedTask:
    """A task in the queue."""
    id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Optional[TaskResult] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "progress": {
                "current": self.progress.current,
                "message": self.progress.message,
                "sub_task": self.progress.sub_task,
            },
            "error": self.result.error if self.result else None,
        }


class TaskQueue:
    """
    Manages a queue of background tasks.

    This is primarily a data structure for tracking task state.
    Actual execution is handled by the Textual Worker system.
    """

    def __init__(self):
        self.tasks: dict[str, QueuedTask] = {}
        self._listeners: list[Callable[[str, QueuedTask], None]] = []

    def add_listener(self, callback: Callable[[str, QueuedTask], None]) -> None:
        """Add a listener for task state changes."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str, QueuedTask], None]) -> None:
        """Remove a listener."""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, task_id: str) -> None:
        """Notify all listeners of a task state change."""
        task = self.tasks.get(task_id)
        if task:
            for listener in self._listeners:
                try:
                    listener(task_id, task)
                except Exception as e:
                    logger.error(f"Task listener error: {e}")

    def enqueue(self, task_id: str, name: str) -> QueuedTask:
        """Add a new task to the queue."""
        task = QueuedTask(id=task_id, name=name)
        self.tasks[task_id] = task
        self._notify_listeners(task_id)
        return task

    def start(self, task_id: str) -> None:
        """Mark a task as started."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now()
            task.progress.message = "Starting..."
            self._notify_listeners(task_id)

    def update_progress(
        self,
        task_id: str,
        progress: float,
        message: str = "",
        sub_task: str = ""
    ) -> None:
        """Update task progress."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.progress.current = progress
            task.progress.message = message
            task.progress.sub_task = sub_task
            self._notify_listeners(task_id)

    def complete(
        self,
        task_id: str,
        success: bool,
        data: Any = None,
        error: Optional[str] = None
    ) -> None:
        """Mark a task as completed."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED if success else TaskStatus.ERROR
            task.completed_at = datetime.now()
            task.progress.current = 1.0 if success else task.progress.current

            duration = 0.0
            if task.started_at:
                duration = (task.completed_at - task.started_at).total_seconds()

            task.result = TaskResult(
                success=success,
                data=data,
                error=error,
                duration_seconds=duration
            )
            self._notify_listeners(task_id)

    def cancel(self, task_id: str) -> None:
        """Cancel a task."""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                self._notify_listeners(task_id)

    def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_pending_tasks(self) -> list[QueuedTask]:
        """Get all pending tasks in order."""
        return [
            t for t in self.tasks.values()
            if t.status == TaskStatus.PENDING
        ]

    def get_active_task(self) -> Optional[QueuedTask]:
        """Get the currently running task, if any."""
        for task in self.tasks.values():
            if task.status == TaskStatus.IN_PROGRESS:
                return task
        return None

    def clear_completed(self) -> None:
        """Remove completed/cancelled/error tasks from the queue."""
        self.tasks = {
            k: v for k, v in self.tasks.items()
            if v.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS)
        }

    def get_all_tasks(self) -> list[QueuedTask]:
        """Get all tasks in order of creation."""
        return sorted(self.tasks.values(), key=lambda t: t.created_at)


# =============================================================================
# Image Hash Tracking for Outdated Detection
# =============================================================================

@dataclass
class ImageMetadata:
    """Metadata for a generated image, including hash for outdated detection."""
    location_id: str
    prompt_hash: str
    generated_at: str  # ISO format
    generator_version: str = "1.0"
    style_preset: str = ""
    variant_npc_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "location_id": self.location_id,
            "prompt_hash": self.prompt_hash,
            "generated_at": self.generated_at,
            "generator_version": self.generator_version,
            "style_preset": self.style_preset,
            "variant_npc_ids": self.variant_npc_ids,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImageMetadata":
        return cls(
            location_id=data.get("location_id", ""),
            prompt_hash=data.get("prompt_hash", ""),
            generated_at=data.get("generated_at", ""),
            generator_version=data.get("generator_version", "1.0"),
            style_preset=data.get("style_preset", ""),
            variant_npc_ids=data.get("variant_npc_ids", []),
        )


class ImageHashTracker:
    """
    Tracks image generation parameters via hashes to detect outdated images.

    Uses a "dry-run" approach: generates the actual prompts without calling the API,
    then hashes them. This is robust against ANY change to:
    - Prompt templates
    - Style presets
    - World/location/NPC/item data
    - Code that constructs prompts

    No duplicated logic - uses the exact same code path as real generation.
    """

    def __init__(self, worlds_dir: Path):
        self.worlds_dir = worlds_dir

    def _get_metadata_path(self, world_id: str) -> Path:
        """Get path to the image metadata file."""
        return self.worlds_dir / world_id / "images" / "_metadata.json"

    def compute_location_hash(
        self,
        world_id: str,
        location_id: str,
        variant_npc_ids: Optional[list[str]] = None
    ) -> str:
        """
        Compute a hash by generating the actual prompt in dry-run mode.

        This uses the exact same code path as real image generation,
        ensuring ANY change that affects the prompt is detected.
        """
        prompt = self._generate_prompt_dry_run(world_id, location_id, variant_npc_ids)
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def _generate_prompt_dry_run(
        self,
        world_id: str,
        location_id: str,
        variant_npc_ids: Optional[list[str]] = None
    ) -> str:
        """
        Generate the image prompt without calling the API.

        This is the core of the dry-run approach - we run the exact same
        prompt generation code that would be used for real generation.
        """
        from gaime_builder.core.image_generator import (
            get_image_prompt,
            get_edit_prompt,
            LocationContext,
            ExitInfo,
            ItemInfo,
            NPCInfo,
        )
        from gaime_builder.core.style_loader import resolve_style

        world_path = self.worlds_dir / world_id

        # Load all world data
        world_data = self._load_yaml(world_path / "world.yaml")
        locations_data = self._load_yaml(world_path / "locations.yaml")
        npcs_data = self._load_yaml(world_path / "npcs.yaml")
        items_data = self._load_yaml(world_path / "items.yaml")

        loc_data = locations_data.get(location_id, {})
        if not loc_data:
            return f"LOCATION_NOT_FOUND:{location_id}"

        # Extract world parameters
        theme = world_data.get("theme", "fantasy")
        tone = world_data.get("tone", "atmospheric")
        style_config = world_data.get("style") or world_data.get("style_block")
        style_block = resolve_style(style_config)

        loc_name = loc_data.get("name", location_id)
        atmosphere = loc_data.get("atmosphere", "")

        # Build context (same logic as ImageGenerator._build_location_context)
        context = self._build_location_context(
            location_id, loc_data, locations_data, npcs_data, items_data,
            variant_npc_ids
        )

        if variant_npc_ids:
            # For variants, we generate an edit prompt to add NPCs to base image
            npcs_to_add = []
            npc_placements = loc_data.get("npc_placements", {})
            for npc_id in variant_npc_ids:
                npc_data = npcs_data.get(npc_id, {})
                if npc_data:
                    npcs_to_add.append(NPCInfo(
                        name=npc_data.get("name", npc_id),
                        appearance=npc_data.get("appearance", ""),
                        role=npc_data.get("role", ""),
                        placement=npc_placements.get(npc_id, "")
                    ))

            return get_edit_prompt(loc_name, npcs_to_add, theme, tone, style_block)
        else:
            # Base image prompt
            return get_image_prompt(
                location_name=loc_name,
                atmosphere=atmosphere,
                theme=theme,
                tone=tone,
                context=context,
                style_block=style_block
            )

    def _build_location_context(
        self,
        location_id: str,
        loc_data: dict,
        locations_data: dict,
        npcs_data: dict,
        items_data: dict,
        variant_npc_ids: Optional[list[str]] = None
    ):
        """Build LocationContext for prompt generation."""
        from gaime_builder.core.image_generator import (
            LocationContext,
            ExitInfo,
            ItemInfo,
            NPCInfo,
        )

        context = LocationContext()

        # Build exits
        exits_data = loc_data.get("exits", {})
        for direction, destination_id in exits_data.items():
            destination_data = locations_data.get(destination_id, {})
            destination_name = destination_data.get("name", destination_id)
            dest_requires = destination_data.get("requires", {})

            context.exits.append(ExitInfo(
                direction=direction,
                destination_name=destination_name,
                is_secret=bool(dest_requires.get("flag") if dest_requires else False),
                requires_key=bool(dest_requires.get("item") if dest_requires else False)
            ))

        # Build items
        location_items = loc_data.get("items", [])
        item_placements = loc_data.get("item_placements", {})
        for item_id in location_items:
            item_data = items_data.get(item_id, {})
            if item_data:
                context.items.append(ItemInfo(
                    name=item_data.get("name", item_id),
                    description=item_data.get("found_description", ""),
                    is_hidden=item_data.get("hidden", False),
                    is_artifact=item_data.get("properties", {}).get("artifact", False),
                    placement=item_placements.get(item_id, "")
                ))

        # Build NPCs - for base image, exclude variant NPCs
        # For variant prompt, NPCs are handled separately via get_edit_prompt
        if variant_npc_ids is None:
            location_npcs = loc_data.get("npcs", [])
            npc_placements = loc_data.get("npc_placements", {})

            # Get all NPCs at this location
            all_npc_ids = set(location_npcs)
            for npc_id, npc_data in npcs_data.items():
                if npc_data.get("location") == location_id:
                    all_npc_ids.add(npc_id)
                if location_id in npc_data.get("locations", []):
                    all_npc_ids.add(npc_id)

            # Filter to unconditional NPCs only (for base image)
            for npc_id in all_npc_ids:
                npc_data = npcs_data.get(npc_id, {})
                if not npc_data:
                    continue

                # Skip conditional NPCs (they get variant images)
                if self._is_npc_conditional(npc_data, location_id):
                    continue

                context.npcs.append(NPCInfo(
                    name=npc_data.get("name", npc_id),
                    appearance=npc_data.get("appearance", ""),
                    role=npc_data.get("role", ""),
                    placement=npc_placements.get(npc_id, "")
                ))

        return context

    def _is_npc_conditional(self, npc_data: dict, location_id: str) -> bool:
        """Check if an NPC is conditional at a location."""
        if npc_data.get("appears_when"):
            return True

        location_changes = npc_data.get("location_changes", [])
        if location_changes:
            starting_location = npc_data.get("location")

            if starting_location == location_id:
                for change in location_changes:
                    move_to = change.get("move_to")
                    if move_to and move_to != starting_location:
                        return True

            for change in location_changes:
                move_to = change.get("move_to")
                if move_to == location_id and starting_location != location_id:
                    return True

        return False

    def _load_yaml(self, path: Path) -> dict:
        """Load YAML file, returning empty dict if not found."""
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def load_metadata(self, world_id: str) -> dict[str, ImageMetadata]:
        """Load all image metadata for a world."""
        metadata_path = self._get_metadata_path(world_id)
        if not metadata_path.exists():
            return {}

        try:
            with open(metadata_path) as f:
                data = json.load(f)
            return {
                k: ImageMetadata.from_dict(v)
                for k, v in data.items()
            }
        except Exception as e:
            logger.warning(f"Failed to load image metadata: {e}")
            return {}

    def save_metadata(self, world_id: str, metadata: dict[str, ImageMetadata]) -> None:
        """Save image metadata for a world."""
        metadata_path = self._get_metadata_path(world_id)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        data = {k: v.to_dict() for k, v in metadata.items()}
        with open(metadata_path, 'w') as f:
            json.dump(data, f, indent=2)

    def update_metadata(
        self,
        world_id: str,
        location_id: str,
        prompt_hash: str,
        style_preset: str = "",
        variant_npc_ids: Optional[list[str]] = None
    ) -> None:
        """Update metadata for a single image."""
        metadata = self.load_metadata(world_id)

        # Key includes variant info
        if variant_npc_ids:
            key = f"{location_id}__with__{'_'.join(sorted(variant_npc_ids))}"
        else:
            key = location_id

        metadata[key] = ImageMetadata(
            location_id=location_id,
            prompt_hash=prompt_hash,
            generated_at=datetime.now().isoformat(),
            generator_version="dry-run-hash",  # Hash captures everything, version is just a marker
            style_preset=style_preset,
            variant_npc_ids=variant_npc_ids or [],
        )

        self.save_metadata(world_id, metadata)

    def is_outdated(
        self,
        world_id: str,
        location_id: str,
        variant_npc_ids: Optional[list[str]] = None
    ) -> tuple[bool, str]:
        """
        Check if an image is outdated by comparing prompt hashes.

        Uses dry-run prompt generation - the hash captures the EXACT prompt
        that would be sent to the API, so ANY change is detected:
        - Template file changes
        - Style preset changes
        - World/location data changes
        - Code changes that affect prompt output

        Returns:
            Tuple of (is_outdated, reason)
        """
        # Key includes variant info
        if variant_npc_ids:
            key = f"{location_id}__with__{'_'.join(sorted(variant_npc_ids))}"
        else:
            key = location_id

        metadata = self.load_metadata(world_id)
        stored = metadata.get(key)

        if not stored:
            return True, "no metadata"

        # Compute current hash (includes templates, style, data, and code version)
        current_hash = self.compute_location_hash(world_id, location_id, variant_npc_ids)

        if stored.prompt_hash != current_hash:
            # Hash changed - could be data, templates, style preset, or code version
            return True, "inputs changed"

        return False, ""

    def get_location_status(
        self,
        world_id: str,
        location_id: str
    ) -> dict:
        """
        Get comprehensive status for a location's images.

        Returns:
            Dict with keys: has_base, base_outdated, variants_status
        """
        images_dir = self.worlds_dir / world_id / "images"
        base_image = images_dir / f"{location_id}.png"

        has_base = base_image.exists()
        base_outdated, base_reason = self.is_outdated(world_id, location_id)

        # Check variants
        variants_status = []
        for img_file in images_dir.glob(f"{location_id}__with__*.png"):
            filename = img_file.stem
            # Extract NPC IDs from filename: location_id__with__npc1_npc2
            npc_part = filename.split("__with__")[1] if "__with__" in filename else ""
            npc_ids = npc_part.split("_") if npc_part else []

            outdated, reason = self.is_outdated(world_id, location_id, npc_ids)
            variants_status.append({
                "npc_ids": npc_ids,
                "exists": True,
                "outdated": outdated,
                "reason": reason,
            })

        return {
            "has_base": has_base,
            "base_outdated": base_outdated if has_base else False,
            "base_reason": base_reason if has_base else "",
            "variants": variants_status,
        }


# =============================================================================
# Style Test Hash Tracking for Outdated Detection
# =============================================================================

@dataclass
class StyleTestMetadata:
    """Metadata for a style test image, including hash for outdated detection."""
    location_id: str
    preset_name: str
    prompt_hash: str
    generated_at: str  # ISO format
    generator_version: str = "1.0"

    def to_dict(self) -> dict:
        return {
            "location_id": self.location_id,
            "preset_name": self.preset_name,
            "prompt_hash": self.prompt_hash,
            "generated_at": self.generated_at,
            "generator_version": self.generator_version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StyleTestMetadata":
        return cls(
            location_id=data.get("location_id", ""),
            preset_name=data.get("preset_name", ""),
            prompt_hash=data.get("prompt_hash", ""),
            generated_at=data.get("generated_at", ""),
            generator_version=data.get("generator_version", "1.0"),
        )


class StyleTestHashTracker:
    """
    Tracks style test image generation parameters via hashes to detect outdated images.

    Similar to ImageHashTracker but works with the style test output directory structure:
    - Images are stored in: {output_dir}/{world_id}/{location_id}/
    - Each preset creates: {location_id}_{preset_name}.png
    - Metadata stored in: {output_dir}/{world_id}/{location_id}/_metadata.json
    """

    def __init__(self, worlds_dir: Path, output_dir: Path):
        self.worlds_dir = worlds_dir
        self.output_dir = output_dir

    def _get_metadata_path(self, world_id: str, location_id: str) -> Path:
        """Get path to the style test metadata file."""
        return self.output_dir / world_id / location_id / "_metadata.json"

    def compute_preset_hash(
        self,
        world_id: str,
        location_id: str,
        preset_name: str
    ) -> str:
        """
        Compute a hash by generating the actual prompt in dry-run mode.

        This uses the exact same code path as real image generation,
        ensuring ANY change that affects the prompt is detected.
        """
        prompt = self._generate_prompt_dry_run(world_id, location_id, preset_name)
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def _generate_prompt_dry_run(
        self,
        world_id: str,
        location_id: str,
        preset_name: str
    ) -> str:
        """
        Generate the image prompt without calling the API.

        Includes the preset_name in the hash to differentiate style tests.
        """
        from gaime_builder.core.image_generator import (
            get_image_prompt,
            LocationContext,
            ExitInfo,
            ItemInfo,
            NPCInfo,
        )
        from gaime_builder.core.style_loader import resolve_style

        world_path = self.worlds_dir / world_id

        # Load all world data
        world_data = self._load_yaml(world_path / "world.yaml")
        locations_data = self._load_yaml(world_path / "locations.yaml")
        npcs_data = self._load_yaml(world_path / "npcs.yaml")
        items_data = self._load_yaml(world_path / "items.yaml")

        loc_data = locations_data.get(location_id, {})
        if not loc_data:
            return f"LOCATION_NOT_FOUND:{location_id}:{preset_name}"

        # Extract world parameters
        theme = world_data.get("theme", "fantasy")
        tone = world_data.get("tone", "atmospheric")

        # Use the specified preset instead of world's style
        style_block = resolve_style(preset_name)

        loc_name = loc_data.get("name", location_id)
        atmosphere = loc_data.get("atmosphere", "")

        # Build context (same logic as ImageGenerator._build_location_context)
        context = self._build_location_context(
            location_id, loc_data, locations_data, npcs_data, items_data
        )

        # Generate the prompt
        return get_image_prompt(
            location_name=loc_name,
            atmosphere=atmosphere,
            theme=theme,
            tone=tone,
            context=context,
            style_block=style_block
        )

    def _build_location_context(
        self,
        location_id: str,
        loc_data: dict,
        locations_data: dict,
        npcs_data: dict,
        items_data: dict,
    ):
        """Build LocationContext for prompt generation."""
        from gaime_builder.core.image_generator import (
            LocationContext,
            ExitInfo,
            ItemInfo,
            NPCInfo,
        )

        context = LocationContext()

        # Build exits
        exits_data = loc_data.get("exits", {})
        for direction, destination_id in exits_data.items():
            destination_data = locations_data.get(destination_id, {})
            destination_name = destination_data.get("name", destination_id)
            dest_requires = destination_data.get("requires", {})

            context.exits.append(ExitInfo(
                direction=direction,
                destination_name=destination_name,
                is_secret=bool(dest_requires.get("flag") if dest_requires else False),
                requires_key=bool(dest_requires.get("item") if dest_requires else False)
            ))

        # Build items
        location_items = loc_data.get("items", [])
        item_placements = loc_data.get("item_placements", {})
        for item_id in location_items:
            item_data = items_data.get(item_id, {})
            if item_data:
                context.items.append(ItemInfo(
                    name=item_data.get("name", item_id),
                    description=item_data.get("found_description", ""),
                    is_hidden=item_data.get("hidden", False),
                    is_artifact=item_data.get("properties", {}).get("artifact", False),
                    placement=item_placements.get(item_id, "")
                ))

        # Build NPCs - for style tests, include all unconditional NPCs
        location_npcs = loc_data.get("npcs", [])
        npc_placements = loc_data.get("npc_placements", {})

        all_npc_ids = set(location_npcs)
        for npc_id, npc_data in npcs_data.items():
            if npc_data.get("location") == location_id:
                all_npc_ids.add(npc_id)
            if location_id in npc_data.get("locations", []):
                all_npc_ids.add(npc_id)

        for npc_id in all_npc_ids:
            npc_data = npcs_data.get(npc_id, {})
            if not npc_data:
                continue

            # Skip conditional NPCs
            if self._is_npc_conditional(npc_data, location_id):
                continue

            context.npcs.append(NPCInfo(
                name=npc_data.get("name", npc_id),
                appearance=npc_data.get("appearance", ""),
                role=npc_data.get("role", ""),
                placement=npc_placements.get(npc_id, "")
            ))

        return context

    def _is_npc_conditional(self, npc_data: dict, location_id: str) -> bool:
        """Check if an NPC is conditional at a location."""
        if npc_data.get("appears_when"):
            return True

        location_changes = npc_data.get("location_changes", [])
        if location_changes:
            starting_location = npc_data.get("location")

            if starting_location == location_id:
                for change in location_changes:
                    move_to = change.get("move_to")
                    if move_to and move_to != starting_location:
                        return True

            for change in location_changes:
                move_to = change.get("move_to")
                if move_to == location_id and starting_location != location_id:
                    return True

        return False

    def _load_yaml(self, path: Path) -> dict:
        """Load YAML file, returning empty dict if not found."""
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def load_metadata(self, world_id: str, location_id: str) -> dict[str, StyleTestMetadata]:
        """Load all style test metadata for a world/location."""
        metadata_path = self._get_metadata_path(world_id, location_id)
        if not metadata_path.exists():
            return {}

        try:
            with open(metadata_path) as f:
                data = json.load(f)
            return {
                k: StyleTestMetadata.from_dict(v)
                for k, v in data.items()
            }
        except Exception as e:
            logger.warning(f"Failed to load style test metadata: {e}")
            return {}

    def save_metadata(self, world_id: str, location_id: str, metadata: dict[str, StyleTestMetadata]) -> None:
        """Save style test metadata for a world/location."""
        metadata_path = self._get_metadata_path(world_id, location_id)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        data = {k: v.to_dict() for k, v in metadata.items()}
        with open(metadata_path, 'w') as f:
            json.dump(data, f, indent=2)

    def update_metadata(
        self,
        world_id: str,
        location_id: str,
        preset_name: str,
        prompt_hash: str
    ) -> None:
        """Update metadata for a single style test image."""
        metadata = self.load_metadata(world_id, location_id)

        metadata[preset_name] = StyleTestMetadata(
            location_id=location_id,
            preset_name=preset_name,
            prompt_hash=prompt_hash,
            generated_at=datetime.now().isoformat(),
            generator_version="dry-run-hash",
        )

        self.save_metadata(world_id, location_id, metadata)

    def is_outdated(
        self,
        world_id: str,
        location_id: str,
        preset_name: str
    ) -> tuple[bool, str]:
        """
        Check if a style test image is outdated by comparing prompt hashes.

        Returns:
            Tuple of (is_outdated, reason)
        """
        metadata = self.load_metadata(world_id, location_id)
        stored = metadata.get(preset_name)

        if not stored:
            return True, "no metadata"

        # Compute current hash
        current_hash = self.compute_preset_hash(world_id, location_id, preset_name)

        if stored.prompt_hash != current_hash:
            return True, "inputs changed"

        return False, ""

    def get_preset_status(
        self,
        world_id: str,
        location_id: str,
        preset_name: str
    ) -> dict:
        """
        Get status for a specific preset's image.

        Returns:
            Dict with: has_image, is_outdated, outdated_reason
        """
        image_dir = self.output_dir / world_id / location_id
        image_path = image_dir / f"{location_id}_{preset_name}.png"

        has_image = image_path.exists()

        is_outdated = False
        outdated_reason = ""
        if has_image:
            is_outdated, outdated_reason = self.is_outdated(world_id, location_id, preset_name)

        return {
            "has_image": has_image,
            "is_outdated": is_outdated,
            "outdated_reason": outdated_reason,
        }

    def get_all_preset_statuses(
        self,
        world_id: str,
        location_id: str,
        preset_names: list[str]
    ) -> dict[str, dict]:
        """
        Get status for all presets for a location.

        Returns:
            Dict mapping preset_name to status dict
        """
        return {
            preset_name: self.get_preset_status(world_id, location_id, preset_name)
            for preset_name in preset_names
        }

    def get_presets_needing_generation(
        self,
        world_id: str,
        location_id: str,
        preset_names: list[str]
    ) -> list[dict]:
        """
        Get list of presets that need image generation (missing or outdated).

        Returns:
            List of dicts with: preset_name, reason
        """
        needs_generation = []

        for preset_name in preset_names:
            status = self.get_preset_status(world_id, location_id, preset_name)

            if not status["has_image"]:
                needs_generation.append({
                    "preset_name": preset_name,
                    "reason": "missing",
                })
            elif status["is_outdated"]:
                needs_generation.append({
                    "preset_name": preset_name,
                    "reason": f"outdated ({status['outdated_reason']})",
                })

        return needs_generation
