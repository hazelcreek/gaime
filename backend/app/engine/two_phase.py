"""
Two-Phase game loop processor.

This module implements the main orchestrator for the two-phase game engine,
coordinating parsing, validation, execution, and narration.

See planning/two-phase-game-loop-spec.md for the full specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.parser import RuleBasedParser
from app.engine.validators.movement import MovementValidator
from app.engine.visibility import DefaultVisibilityResolver
from app.llm.narrator import NarratorAI
from app.models.event import Event, EventType
from app.models.intent import ActionIntent, ActionType
from app.models.two_phase_state import TwoPhaseActionResponse, TwoPhaseDebugInfo
from app.models.game import LLMDebugInfo
from app.models.validation import ValidationResult

if TYPE_CHECKING:
    from app.engine.two_phase_state import TwoPhaseStateManager


class TwoPhaseProcessor:
    """Two-phase game loop processor.

    Coordinates the complete action processing pipeline:
        1. Parse: Rule-based parser extracts ActionIntent
        2. Validate: Validators check against world rules
        3. Execute: State changes are applied
        4. Narrate: NarratorAI generates prose

    Phase 1 supports only movement actions. Unsupported actions
    return a simple "command not understood" response without LLM.

    Example:
        >>> manager = TwoPhaseStateManager("cursed-manor")
        >>> processor = TwoPhaseProcessor(manager)
        >>> response = await processor.process("go north")
        >>> print(response.narrative)
    """

    # Response for unsupported actions (no LLM call)
    UNSUPPORTED_ACTION_MESSAGE = (
        "I don't understand that command. "
        "Try movement commands like 'north', 'go east', or 'back'."
    )

    def __init__(
        self,
        state_manager: "TwoPhaseStateManager",
        debug: bool = False,
    ):
        """Initialize the two-phase processor.

        Args:
            state_manager: The TwoPhaseStateManager for this session
            debug: Whether to capture debug info for LLM calls
        """
        self.state_manager = state_manager
        self.debug = debug

        # Initialize components
        self.parser = RuleBasedParser()
        self.movement_validator = MovementValidator()
        self.visibility_resolver = DefaultVisibilityResolver()
        self.narrator = NarratorAI(
            world_data=state_manager.world_data,
            session_id=state_manager.session_id,
            debug=debug,
        )

    async def get_initial_narrative(self) -> tuple[str, LLMDebugInfo | None]:
        """Generate the opening narrative for a new game.

        Creates a LOCATION_CHANGED event for the starting location
        and uses the NarratorAI to generate the opening prose.

        Returns:
            Tuple of (narrative text, debug info if enabled)
        """
        state = self.state_manager.get_state()
        world = self.state_manager.world_data

        # Create opening event
        event = Event(
            type=EventType.LOCATION_CHANGED,
            subject=state.current_location,
            context={
                "first_visit": True,
                "is_opening": True,
            },
        )

        # Build perception snapshot
        snapshot = self.visibility_resolver.build_snapshot(state, world)

        # Generate narrative
        narrative, debug_info = await self.narrator.narrate([event], snapshot)

        return narrative, debug_info

    async def process(self, action: str) -> TwoPhaseActionResponse:
        """Process a player action through the two-phase pipeline.

        Pipeline:
            1. Parse action into ActionIntent
            2. If None, return "command not understood"
            3. Validate intent against world rules
            4. If invalid, generate rejection narrative
            5. If valid, execute state changes and generate success narrative

        Args:
            action: The raw player action string

        Returns:
            TwoPhaseActionResponse with narrative and updated state
        """
        action = action.strip()
        state = self.state_manager.get_state()
        world = self.state_manager.world_data

        # Check if game is already over
        if state.status != "playing":
            return TwoPhaseActionResponse(
                narrative="The game has ended. Start a new game to play again.",
                state=state,
                events=[],
                game_complete=True,
            )

        # Phase 1: Parse
        intent = self.parser.parse(action, state, world)

        if intent is None:
            # Action not recognized - return simple message (no LLM)
            # Build minimal debug info if debug mode enabled
            pipeline_debug = None
            if self.debug:
                pipeline_debug = TwoPhaseDebugInfo(
                    raw_input=action,
                    parser_type="rule_based",
                    parsed_intent=None,
                    events=[],
                )

            return TwoPhaseActionResponse(
                narrative=self.UNSUPPORTED_ACTION_MESSAGE,
                state=state,
                events=[],
                pipeline_debug=pipeline_debug,
            )

        # Phase 2: Validate & Execute based on action type
        if intent.action_type == ActionType.MOVE:
            return await self._process_movement(intent, action)
        else:
            # Action type not yet supported in Phase 1
            # Build debug info for unsupported action type
            pipeline_debug = None
            if self.debug:
                pipeline_debug = TwoPhaseDebugInfo(
                    raw_input=action,
                    parser_type="rule_based",
                    parsed_intent=intent.model_dump(),
                    events=[],
                )

            return TwoPhaseActionResponse(
                narrative=self.UNSUPPORTED_ACTION_MESSAGE,
                state=state,
                events=[],
                pipeline_debug=pipeline_debug,
            )

    async def _process_movement(
        self, intent: ActionIntent, raw_input: str
    ) -> TwoPhaseActionResponse:
        """Process a movement action.

        Args:
            intent: The parsed MOVE ActionIntent
            raw_input: The original player input string (for debug info)

        Returns:
            TwoPhaseActionResponse with movement result
        """
        state = self.state_manager.get_state()
        world = self.state_manager.world_data

        # Validate movement
        result = self.movement_validator.validate(intent, state, world)

        if not result.valid:
            # Movement rejected - create rejection event
            event = result.to_rejection_event(subject=intent.target_id)
            events = [event]

            # Build snapshot (still at current location)
            snapshot = self.visibility_resolver.build_snapshot(state, world)

            # Generate rejection narrative
            narrative, narrator_debug = await self.narrator.narrate(events, snapshot)

            # Increment turn even for failed actions
            self.state_manager.increment_turn()

            # Build pipeline debug info
            pipeline_debug = self._build_pipeline_debug(
                raw_input=raw_input,
                intent=intent,
                validation_result=result,
                events=events,
                narrator_debug=narrator_debug,
            )

            return TwoPhaseActionResponse(
                narrative=narrative,
                state=self.state_manager.get_state(),
                events=[e.model_dump() for e in events],
                pipeline_debug=pipeline_debug,
            )

        # Movement valid - execute
        destination_id = result.context["destination"]
        first_visit = self.state_manager.move_to(destination_id)

        # Create success event
        event = Event(
            type=EventType.LOCATION_CHANGED,
            subject=destination_id,
            context={
                "from_location": result.context.get("from_location"),
                "direction": result.context.get("direction"),
                "first_visit": first_visit,
                "destination_name": result.context.get("destination_name"),
            },
        )
        events = [event]

        # Build snapshot at new location
        snapshot = self.visibility_resolver.build_snapshot(
            self.state_manager.get_state(), world
        )

        # Generate success narrative
        narrative, narrator_debug = await self.narrator.narrate(events, snapshot)

        # Increment turn
        self.state_manager.increment_turn()

        # Build pipeline debug info
        pipeline_debug = self._build_pipeline_debug(
            raw_input=raw_input,
            intent=intent,
            validation_result=result,
            events=events,
            narrator_debug=narrator_debug,
        )

        # Check for victory
        is_victory, ending_narrative = self.state_manager.check_victory()

        if is_victory:
            full_narrative = narrative + "\n\n---\n\n" + ending_narrative
            return TwoPhaseActionResponse(
                narrative=full_narrative,
                state=self.state_manager.get_state(),
                events=[e.model_dump() for e in events],
                game_complete=True,
                ending_narrative=ending_narrative,
                pipeline_debug=pipeline_debug,
            )

        return TwoPhaseActionResponse(
            narrative=narrative,
            state=self.state_manager.get_state(),
            events=[e.model_dump() for e in events],
            pipeline_debug=pipeline_debug,
        )

    def _build_pipeline_debug(
        self,
        raw_input: str,
        intent: ActionIntent | None,
        validation_result: ValidationResult | None,
        events: list[Event],
        narrator_debug: LLMDebugInfo | None,
    ) -> TwoPhaseDebugInfo | None:
        """Build pipeline debug info if debug mode is enabled.

        Args:
            raw_input: Original player input
            intent: Parsed ActionIntent (or None)
            validation_result: ValidationResult from validator
            events: List of events generated
            narrator_debug: LLM debug info from narrator

        Returns:
            TwoPhaseDebugInfo if debug mode enabled, else None
        """
        if not self.debug:
            return None

        # Serialize validation result if present
        validation_dict = None
        if validation_result:
            validation_dict = {
                "valid": validation_result.valid,
                "rejection_code": (
                    validation_result.rejection_code.value
                    if validation_result.rejection_code
                    else None
                ),
                "rejection_reason": validation_result.rejection_reason,
                "context": validation_result.context,
                "hint": validation_result.hint,
            }

        return TwoPhaseDebugInfo(
            raw_input=raw_input,
            parser_type="rule_based",  # Currently only rule-based parser
            parsed_intent=intent.model_dump() if intent else None,
            interactor_debug=None,  # Future: InteractorAI debug info
            validation_result=validation_dict,
            events=[e.model_dump() for e in events],
            narrator_debug=narrator_debug,
        )
