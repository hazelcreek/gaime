"""
Engine version enum for the two-phase game loop migration.

This module defines the available engine versions that can be selected
when starting a new game. Engine selection is session-level metadata,
kept separate from GameState for easy removal post-migration.

See planning/two-phase-game-loop-spec.md Section: Engine Coexistence
"""

from enum import Enum


class EngineVersion(str, Enum):
    """Available game engine versions.

    Attributes:
        CLASSIC: Current single-LLM architecture (default)
        TWO_PHASE: New separated parsing (Interactor) and narration (Narrator)
    """

    CLASSIC = "classic"
    TWO_PHASE = "two_phase"


# Engine metadata for the /engines endpoint
ENGINE_INFO = [
    {
        "id": EngineVersion.CLASSIC.value,
        "name": "Classic Engine",
        "description": "Single LLM call for action processing and narration",
    },
    {
        "id": EngineVersion.TWO_PHASE.value,
        "name": "Two-Phase Engine",
        "description": "Separated parsing (Interactor) and narration (Narrator)",
    },
]

DEFAULT_ENGINE = EngineVersion.TWO_PHASE
