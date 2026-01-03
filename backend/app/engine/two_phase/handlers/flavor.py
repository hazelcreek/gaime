"""
Flavor handler for the two-phase game engine.

This handler processes FlavorIntent - atmospheric actions that
don't change game state (dance, wave, sing, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.two_phase.models.event import Event, EventType
from app.engine.two_phase.models.validation import ValidationResult, valid_result

if TYPE_CHECKING:
    from app.engine.two_phase.models.intent import FlavorIntent, Intent
    from app.engine.two_phase.models.state import TwoPhaseGameState
    from app.engine.two_phase.state import TwoPhaseStateManager
    from app.models.world import WorldData


class FlavorHandler:
    """Handles FlavorIntent in the two-phase engine.

    Flavor actions are atmospheric - they don't change state.
    They always succeed, so validate() always returns valid.

    Attributes:
        checks_victory: False - flavor actions don't trigger victory

    Example:
        >>> handler = FlavorHandler()
        >>> result = handler.validate(intent, state, world)  # Always valid
        >>> event = handler.create_event(intent, result, state, world)
    """

    checks_victory: bool = False

    def validate(
        self,
        intent: "Intent",
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> ValidationResult:
        """Validate the flavor intent (always valid).

        Args:
            intent: The FlavorIntent
            state: Current game state
            world: World data

        Returns:
            ValidationResult with valid=True
        """
        # Flavor actions are always valid
        return valid_result()

    def execute(
        self,
        intent: "Intent",
        result: ValidationResult,
        state_manager: "TwoPhaseStateManager",
    ) -> None:
        """Execute the flavor action (no-op).

        Flavor actions don't change state.

        Args:
            intent: The validated FlavorIntent
            result: Validation result
            state_manager: State manager (unused)
        """
        # Flavor actions don't change state
        pass

    def create_event(
        self,
        intent: "Intent",
        result: ValidationResult,
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> Event:
        """Create the FLAVOR_ACTION event.

        Args:
            intent: The FlavorIntent
            result: The validation result
            state: Current game state
            world: World data

        Returns:
            FLAVOR_ACTION event for narration
        """
        # Type narrowing - this handler only handles FlavorIntent
        flavor_intent: FlavorIntent = intent  # type: ignore[assignment]

        return Event(
            type=EventType.FLAVOR_ACTION,
            context={
                "verb": flavor_intent.verb,
                "action_hint": (
                    flavor_intent.action_hint.value
                    if flavor_intent.action_hint
                    else None
                ),
                "target": flavor_intent.target,
                "target_id": flavor_intent.target_id,
                "topic": flavor_intent.topic,
                "manner": flavor_intent.manner,
            },
        )
