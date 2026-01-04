"""LLM integration components.

This package contains LLM clients and prompts for the two-phase game engine.

Shared Components (at this level):
- `client.py`: LiteLLM client wrapper
- `prompt_loader.py`: Prompt template loading utility
- `session_logger.py`: Session logging utilities
- `image_generator.py`: Image generation utilities

Two-Phase Engine Components:
- `two_phase/`: InteractorAI and NarratorAI for the two-phase engine

Import directly from submodules to avoid circular imports:
    from app.llm.two_phase.interactor import InteractorAI
    from app.llm.two_phase.narrator import NarratorAI
"""

# Only import shared utilities that don't cause circular imports
from app.llm.client import (
    get_completion,
    parse_json_response,
    get_model_string,
    LLMCompletionResult,
)
from app.llm.prompt_loader import get_loader

__all__ = [
    # Shared utilities
    "get_completion",
    "parse_json_response",
    "get_model_string",
    "get_loader",
    "LLMCompletionResult",
]
