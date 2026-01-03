"""
Rule-based parser for the two-phase game engine.

This module provides fast-path parsing for common action patterns
without requiring LLM calls. It implements the ActionParser protocol.

See planning/two-phase-game-loop-spec.md Section: Phase 1 - Parse Intent
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.engine.two_phase.models.intent import ActionIntent, ActionType

if TYPE_CHECKING:
    from app.engine.two_phase.models.state import TwoPhaseGameState
    from app.models.world import WorldData


class RuleBasedParser:
    """Parse common actions without LLM.

    This parser handles movement and browse commands using regex patterns.
    For input that doesn't match known patterns, it returns None
    to indicate the input cannot be handled.

    Supported patterns:
        Movement:
            - Cardinal directions: north, n, south, s, east, e, west, w
            - Vertical: up, u, down, d
            - Go commands: go north, go n, etc.
            - Return: back, leave, exit
        Browse:
            - look, look around, l, survey, scan

    Example:
        >>> parser = RuleBasedParser()
        >>> intent = parser.parse("go north", state, world)
        >>> intent.action_type == ActionType.MOVE
        True
        >>> intent.target_id
        'north'

        >>> intent = parser.parse("look around", state, world)
        >>> intent.action_type == ActionType.BROWSE
        True
    """

    # Direction patterns: maps regex pattern to (normalized_direction, verb)
    DIRECTION_PATTERNS: dict[str, tuple[str, str]] = {
        r"^(go\s+)?(north|n)$": ("north", "go"),
        r"^(go\s+)?(south|s)$": ("south", "go"),
        r"^(go\s+)?(east|e)$": ("east", "go"),
        r"^(go\s+)?(west|w)$": ("west", "go"),
        r"^(go\s+)?(up|u)$": ("up", "go"),
        r"^(go\s+)?(down|d)$": ("down", "go"),
        r"^(go\s+)?back$": ("back", "go"),
        r"^leave$": ("back", "leave"),
        r"^exit$": ("back", "exit"),
        # Also support full directions without "go"
        r"^northeast|ne$": ("northeast", "go"),
        r"^northwest|nw$": ("northwest", "go"),
        r"^southeast|se$": ("southeast", "go"),
        r"^southwest|sw$": ("southwest", "go"),
    }

    # Browse patterns: look around, l, survey, scan
    BROWSE_PATTERNS: list[str] = [
        r"^look(\s+around)?$",
        r"^l$",
        r"^survey$",
        r"^scan$",
    ]

    def parse(
        self,
        raw_input: str,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> ActionIntent | None:
        """Parse player input into a structured ActionIntent.

        Args:
            raw_input: The raw player input string
            state: Current game state for context
            world: World data for entity resolution

        Returns:
            ActionIntent if parsing succeeds, None if input not recognized
        """
        normalized = raw_input.lower().strip()

        # Try browse patterns first (before movement, since "l" is short)
        for pattern in self.BROWSE_PATTERNS:
            if re.match(pattern, normalized):
                return ActionIntent(
                    action_type=ActionType.BROWSE,
                    raw_input=raw_input,
                    verb="look",
                    target_id="",  # BROWSE has no target
                    confidence=1.0,
                )

        # Try movement patterns
        for pattern, (direction, verb) in self.DIRECTION_PATTERNS.items():
            if re.match(pattern, normalized):
                return ActionIntent(
                    action_type=ActionType.MOVE,
                    raw_input=raw_input,
                    verb=verb,
                    target_id=direction,
                    confidence=1.0,
                )

        # No pattern matched - return None to indicate unrecognized input
        return None
