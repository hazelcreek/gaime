"""
Browse handler for the two-phase game engine.

This handler processes BROWSE actions (look around, survey surroundings).
BROWSE always succeeds - there's no validation needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.two_phase.models.event import Event, EventType
from app.engine.two_phase.models.validation import ValidationResult, valid_result

if TYPE_CHECKING:
    from app.engine.two_phase.models.intent import Intent
    from app.engine.two_phase.models.perception import PerceptionSnapshot
    from app.engine.two_phase.models.state import TwoPhaseGameState
    from app.engine.two_phase.state import TwoPhaseStateManager
    from app.engine.two_phase.visibility import DefaultVisibilityResolver
    from app.models.world import WorldData


class BrowseHandler:
    """Handles BROWSE actions in the two-phase engine.

    BROWSE surveys the current location without changing state.
    It always succeeds, so validate() always returns valid.

    Attributes:
        checks_victory: False - browsing doesn't trigger victory
        visibility_resolver: For building perception snapshots

    Example:
        >>> handler = BrowseHandler(visibility_resolver)
        >>> result = handler.validate(intent, state, world)  # Always valid
        >>> event = handler.create_event(intent, result, state, world)
    """

    checks_victory: bool = False

    def __init__(self, visibility_resolver: "DefaultVisibilityResolver"):
        """Initialize the browse handler.

        Args:
            visibility_resolver: For building perception snapshots
        """
        self.visibility_resolver = visibility_resolver

    def validate(
        self,
        intent: "Intent",
        state: "TwoPhaseGameState",
        world: "WorldData",
    ) -> ValidationResult:
        """Validate the browse intent (always valid).

        Args:
            intent: The BROWSE ActionIntent
            state: Current game state
            world: World data

        Returns:
            ValidationResult with valid=True
        """
        # Browse is always valid
        return valid_result()

    def execute(
        self,
        intent: "Intent",
        result: ValidationResult,
        state_manager: "TwoPhaseStateManager",
    ) -> None:
        """Execute the browse action (no-op).

        Browsing doesn't change state.

        Args:
            intent: The validated BROWSE intent
            result: Validation result
            state_manager: State manager (unused)
        """
        # Browsing doesn't change state
        pass

    def create_event(
        self,
        intent: "Intent",
        result: ValidationResult,
        state: "TwoPhaseGameState",
        world: "WorldData",
        snapshot: "PerceptionSnapshot | None" = None,
    ) -> Event:
        """Create the SCENE_BROWSED event.

        Args:
            intent: The processed intent
            result: The validation result
            state: Current game state
            world: World data
            snapshot: Perception snapshot at current location

        Returns:
            SCENE_BROWSED event for narration
        """
        context: dict[str, object] = {
            "first_visit": False,  # Manual browse is never "first visit"
            "is_manual_browse": True,
        }

        if snapshot:
            context["visible_items"] = [item.name for item in snapshot.visible_items]
            context["visible_npcs"] = [npc.name for npc in snapshot.visible_npcs]
            context["visible_exits"] = [
                {"direction": e.direction, "destination": e.destination_name}
                for e in snapshot.visible_exits
            ]

        return Event(
            type=EventType.SCENE_BROWSED,
            subject=state.current_location,
            context=context,
        )
