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
    
    Computes a hash from:
    - Location atmosphere and details
    - World theme and tone
    - Style preset configuration (full YAML content, not just name)
    - NPC data (for variants)
    - Prompt template file contents
    - Code version for prompt generation logic
    """
    
    # Increment this when prompt generation CODE changes (not templates - those are auto-hashed)
    # This covers changes to: get_image_prompt(), build_mpa_prompt(), _build_exits_description(), etc.
    CODE_VERSION = "2024.12.1"
    
    # Cache for template hashes (computed once per session)
    _template_hash_cache: Optional[str] = None
    _style_presets_cache: dict[str, str] = {}
    
    def __init__(self, worlds_dir: Path):
        self.worlds_dir = worlds_dir
    
    def _get_metadata_path(self, world_id: str) -> Path:
        """Get path to the image metadata file."""
        return self.worlds_dir / world_id / "images" / "_metadata.json"
    
    def _get_template_hash(self) -> str:
        """
        Compute a hash of all image generation prompt templates.
        
        This automatically detects when template files change.
        """
        if ImageHashTracker._template_hash_cache is not None:
            return ImageHashTracker._template_hash_cache
        
        from gaime_builder.core.prompt_loader import get_loader
        
        # List of template files used in image generation
        template_files = [
            ("image_generator", "mpa_template.txt"),
            ("image_generator", "mpa_edit_template.txt"),
            ("image_generator", "interactive_elements_section.txt"),
            ("image_generator", "image_prompt_template.txt"),
            ("image_generator", "edit_prompt_template.txt"),
        ]
        
        loader = get_loader()
        template_contents = []
        
        for category, filename in template_files:
            try:
                content = loader.get_prompt(category, filename)
                template_contents.append(f"{category}/{filename}:{content}")
            except Exception:
                # Template not found - include placeholder so hash changes if added later
                template_contents.append(f"{category}/{filename}:MISSING")
        
        combined = "\n---\n".join(template_contents)
        template_hash = hashlib.sha256(combined.encode()).hexdigest()[:12]
        
        ImageHashTracker._template_hash_cache = template_hash
        return template_hash
    
    def _get_style_preset_hash(self, style_config: Any) -> str:
        """
        Compute a hash of the resolved style preset configuration.
        
        This detects changes to style preset YAML files, not just the preset name.
        """
        from gaime_builder.core.style_loader import resolve_style
        
        # Get the cache key
        cache_key = json.dumps(style_config, sort_keys=True) if style_config else "default"
        
        if cache_key in ImageHashTracker._style_presets_cache:
            return ImageHashTracker._style_presets_cache[cache_key]
        
        # Resolve the full style block
        style_block = resolve_style(style_config)
        
        # Create a dict of all style properties
        style_dict = {
            "name": style_block.name,
            "description": style_block.description,
            "style": style_block.style,
            "mood": {
                "tone": style_block.mood.tone,
                "lighting": style_block.mood.lighting,
                "color_palette": style_block.mood.color_palette,
            },
            "technical": {
                "perspective": style_block.technical.perspective,
                "shot": style_block.technical.shot,
                "camera": style_block.technical.camera,
                "effects": style_block.technical.effects,
            },
            "anti_styles": style_block.anti_styles,
            "quality_constraints": style_block.quality_constraints,
        }
        
        style_hash = hashlib.sha256(
            json.dumps(style_dict, sort_keys=True).encode()
        ).hexdigest()[:12]
        
        ImageHashTracker._style_presets_cache[cache_key] = style_hash
        return style_hash
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached template and style hashes. Call after modifying templates."""
        cls._template_hash_cache = None
        cls._style_presets_cache = {}
    
    def compute_location_hash(
        self,
        world_id: str,
        location_id: str,
        variant_npc_ids: Optional[list[str]] = None
    ) -> str:
        """
        Compute a hash for a location's image based on all relevant inputs.
        
        This hash changes when any parameter affecting the generated prompt changes:
        - World data (theme, tone, style)
        - Location data (atmosphere, exits, items, NPCs)
        - Style preset content (not just name)
        - Prompt template files
        - Code version
        """
        world_path = self.worlds_dir / world_id
        
        # Load all relevant data
        world_data = self._load_yaml(world_path / "world.yaml")
        locations_data = self._load_yaml(world_path / "locations.yaml")
        npcs_data = self._load_yaml(world_path / "npcs.yaml")
        items_data = self._load_yaml(world_path / "items.yaml")
        
        loc_data = locations_data.get(location_id, {})
        style_config = world_data.get("style") or world_data.get("style_block")
        
        # Build hash input from all relevant parameters
        hash_input = {
            "code_version": self.CODE_VERSION,
            "template_hash": self._get_template_hash(),
            "style_hash": self._get_style_preset_hash(style_config),
            "world": {
                "theme": world_data.get("theme", ""),
                "tone": world_data.get("tone", ""),
            },
            "location": {
                "id": location_id,
                "name": loc_data.get("name", ""),
                "atmosphere": loc_data.get("atmosphere", ""),
                "exits": loc_data.get("exits", {}),
                "items": loc_data.get("items", []),
                "item_placements": loc_data.get("item_placements", {}),
                "npcs": loc_data.get("npcs", []),
                "npc_placements": loc_data.get("npc_placements", {}),
            },
            "items": {},
            "npcs": {},
        }
        
        # Include item details for items in this location
        for item_id in loc_data.get("items", []):
            item_data = items_data.get(item_id, {})
            hash_input["items"][item_id] = {
                "name": item_data.get("name", ""),
                "found_description": item_data.get("found_description", ""),
                "hidden": item_data.get("hidden", False),
            }
        
        # Get all NPCs that could be at this location
        location_npcs = set(loc_data.get("npcs", []))
        for npc_id, npc_data in npcs_data.items():
            if npc_data.get("location") == location_id:
                location_npcs.add(npc_id)
            if location_id in npc_data.get("locations", []):
                location_npcs.add(npc_id)
        
        # Include NPC details
        for npc_id in location_npcs:
            npc_data = npcs_data.get(npc_id, {})
            hash_input["npcs"][npc_id] = {
                "name": npc_data.get("name", ""),
                "appearance": npc_data.get("appearance", ""),
                "role": npc_data.get("role", ""),
            }
        
        # For variants, include specific NPC data
        if variant_npc_ids:
            hash_input["variant_npcs"] = sorted(variant_npc_ids)
        
        # Compute hash
        hash_str = json.dumps(hash_input, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()[:16]
    
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
            generator_version=self.CODE_VERSION,
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
        Check if an image is outdated.
        
        The hash includes:
        - World/location/NPC/item data
        - Prompt template file contents  
        - Style preset configuration
        - Code version
        
        So comparing hashes catches ALL changes that affect the generated prompt.
        
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
