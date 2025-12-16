"""
Prompt Loader - Loads and manages prompts from text files with hot reloading support.

Prompts are organized in subdirectories:
- game_master/ - Game engine prompts
- image_generator/ - Image generation prompts

Note: World builder prompts are in gaime_builder/core/prompts/ (TUI app).

Prompts are loaded at startup and can be reloaded on demand for development.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class PromptLoader:
    """Loads and caches prompts from text files with hot reloading support."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize the prompt loader.

        Args:
            prompts_dir: Directory containing prompt files. If None, uses default location
                        relative to this module.
        """
        if prompts_dir is None:
            # Default to prompts/ directory next to this module
            module_dir = Path(__file__).parent
            prompts_dir = module_dir / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}
        self._file_timestamps: Dict[str, float] = {}

        # Load all prompts at startup
        self.reload_all()

    def _get_prompt_path(self, category: str, filename: str) -> Path:
        """Get the full path to a prompt file."""
        return self.prompts_dir / category / filename

    def _read_prompt_file(self, category: str, filename: str) -> str:
        """Read a prompt file and cache its timestamp."""
        path = self._get_prompt_path(category, filename)

        if not path.exists():
            raise FileNotFoundError(
                f"Prompt file not found: {path}\n"
                f"Expected location: {self.prompts_dir}/{category}/{filename}"
            )

        # Read the file
        content = path.read_text(encoding="utf-8")

        # Cache timestamp for hot reloading
        cache_key = f"{category}/{filename}"
        self._file_timestamps[cache_key] = path.stat().st_mtime

        return content

    def get_prompt(self, category: str, filename: str, reload: bool = False) -> str:
        """
        Get a prompt from cache or file.

        Args:
            category: Subdirectory name (e.g., 'game_master', 'world_builder')
            filename: Prompt filename (e.g., 'system_prompt.txt')
            reload: If True, force reload from file even if cached

        Returns:
            Prompt content as string
        """
        cache_key = f"{category}/{filename}"
        path = self._get_prompt_path(category, filename)

        # Determine if we need to load/reload
        needs_reload = reload or cache_key not in self._cache

        # Hot reload: check if file has been modified since last load
        if not needs_reload and path.exists():
            current_mtime = path.stat().st_mtime
            cached_mtime = self._file_timestamps.get(cache_key, 0)
            if current_mtime > cached_mtime:
                needs_reload = True
                logger.info(f"Hot reloading modified prompt: {cache_key}")

        if needs_reload:
            if path.exists():
                logger.debug(f"Loading prompt: {cache_key}")
                self._cache[cache_key] = self._read_prompt_file(category, filename)
            elif cache_key in self._cache:
                # File was deleted but we have cache - keep using cache but warn
                logger.warning(
                    f"Prompt file deleted but using cached version: {cache_key}"
                )
            else:
                raise FileNotFoundError(
                    f"Prompt file not found: {path}\n"
                    f"Expected location: {self.prompts_dir}/{category}/{filename}"
                )

        return self._cache[cache_key]

    def reload_all(self):
        """Reload all prompts from files."""
        logger.info(f"Loading prompts from: {self.prompts_dir}")
        self._cache.clear()
        self._file_timestamps.clear()

        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory does not exist: {self.prompts_dir}")
            logger.warning("Prompts will be loaded on-demand when requested")
            return

        # Load all prompt files we can find
        loaded_count = 0
        for category_dir in self.prompts_dir.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                for prompt_file in category_dir.glob("*.txt"):
                    filename = prompt_file.name
                    try:
                        cache_key = f"{category}/{filename}"
                        self._cache[cache_key] = self._read_prompt_file(
                            category, filename
                        )
                        loaded_count += 1
                        logger.debug(f"Loaded: {cache_key}")
                    except Exception as e:
                        logger.error(
                            f"Failed to load prompt {category}/{filename}: {e}"
                        )

        logger.info(f"Loaded {loaded_count} prompt file(s)")

    def reload_category(self, category: str):
        """Reload all prompts in a specific category."""
        category_dir = self.prompts_dir / category
        if not category_dir.exists():
            logger.warning(f"Category directory does not exist: {category_dir}")
            return

        reloaded_count = 0
        for prompt_file in category_dir.glob("*.txt"):
            filename = prompt_file.name
            cache_key = f"{category}/{filename}"
            try:
                self._cache[cache_key] = self._read_prompt_file(category, filename)
                reloaded_count += 1
                logger.info(f"Reloaded: {cache_key}")
            except Exception as e:
                logger.error(f"Failed to reload prompt {category}/{filename}: {e}")

        logger.info(
            f"Reloaded {reloaded_count} prompt file(s) in category '{category}'"
        )


# Global instance - initialized at module import
_loader: Optional[PromptLoader] = None


def get_loader() -> PromptLoader:
    """Get the global prompt loader instance."""
    global _loader
    if _loader is None:
        _loader = PromptLoader()
    return _loader


def reload_prompts():
    """Reload all prompts (useful for development/hot reloading)."""
    get_loader().reload_all()


def reload_category(category: str):
    """Reload prompts in a specific category."""
    get_loader().reload_category(category)
