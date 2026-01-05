"""
Two-Phase game loop processor.

This module implements the main orchestrator for the two-phase game engine,
coordinating parsing, validation, execution, and narration.

See planning/two-phase-game-loop-spec.md for the full specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.two_phase.handlers import (
    BrowseHandler,
    ExamineHandler,
    FlavorHandler,
    MovementHandler,
    TakeHandler,
)
from app.engine.two_phase.parser import RuleBasedParser
from app.engine.two_phase.visibility import DefaultVisibilityResolver
from app.llm.two_phase.interactor import InteractorAI
from app.llm.two_phase.narrator import NarratorAI
from app.llm.session_logger import log_two_phase_turn
from app.engine.two_phase.models.event import Event, EventType
from app.models.game import LLMDebugInfo
from app.engine.two_phase.models.intent import (
    ActionIntent,
    ActionType,
    FlavorIntent,
    Intent,
)
from app.engine.two_phase.models.state import (
    NarrationEntry,
    TwoPhaseActionResponse,
    TwoPhaseDebugInfo,
)
from app.engine.two_phase.models.validation import ValidationResult

if TYPE_CHECKING:
    from app.engine.two_phase.state import TwoPhaseStateManager


class TwoPhaseProcessor:
    """Two-phase game loop processor.

    Coordinates the complete action processing pipeline:
        1. Parse: Rule-based parser for movement, InteractorAI for others
        2. Validate: Handlers validate against world rules
        3. Execute: State changes are applied
        4. Narrate: NarratorAI generates prose

    The processor uses IntentHandlers for a unified action processing flow.
    Each handler encapsulates validation, execution, and event creation
    for its action type.

    Example:
        >>> manager = TwoPhaseStateManager("cursed-manor")
        >>> processor = TwoPhaseProcessor(manager)
        >>> response = await processor.process("examine the letter")
        >>> print(response.narrative)
    """

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
        self.visibility_resolver = DefaultVisibilityResolver()

        # Initialize handlers (inject visibility resolver where needed)
        self._movement_handler = MovementHandler(self.visibility_resolver)
        self._examine_handler = ExamineHandler(self.visibility_resolver)
        self._take_handler = TakeHandler(self.visibility_resolver)
        self._browse_handler = BrowseHandler(self.visibility_resolver)
        self._flavor_handler = FlavorHandler()

        # LLM components
        self.interactor = InteractorAI(
            world_data=state_manager.world_data,
            session_id=state_manager.session_id,
            debug=debug,
        )
        self.narrator = NarratorAI(
            world_data=state_manager.world_data,
            session_id=state_manager.session_id,
            debug=debug,
        )

    async def get_initial_narrative(self) -> tuple[str, TwoPhaseDebugInfo | None]:
        """Generate the opening narrative for a new game.

        Creates a SCENE_BROWSED event for the starting location
        and uses the NarratorAI to generate the opening prose.

        Returns:
            Tuple of (narrative text, TwoPhaseDebugInfo if debug enabled)
        """
        state = self.state_manager.get_state()
        world = self.state_manager.world_data

        # Build perception snapshot
        snapshot = self.visibility_resolver.build_snapshot(state, world)

        # Create opening event using SCENE_BROWSED for comprehensive description
        # Include premise/starting_situation if available for rich opening context
        event = Event(
            type=EventType.SCENE_BROWSED,
            subject=state.current_location,
            context={
                "first_visit": True,
                "is_opening": True,
                "premise": getattr(world.world, "premise", None),
                "starting_situation": getattr(world.world, "starting_situation", None),
                "hero_name": getattr(world.world, "hero_name", None),
                "visible_items": [item.name for item in snapshot.visible_items],
                "visible_npcs": [npc.name for npc in snapshot.visible_npcs],
                "visible_exits": [
                    {
                        "direction": e.direction,
                        "destination": (
                            e.destination_name if e.destination_known else "unknown"
                        ),
                        "description": e.description,
                        "destination_known": e.destination_known,
                    }
                    for e in snapshot.visible_exits
                ],
            },
        )

        # Get narration history for context
        history = state.narration_history

        # Generate narrative
        narrative, narrator_debug = await self.narrator.narrate(
            [event], snapshot, history=history
        )

        # Store narration in history
        self._store_narration(narrative, state.current_location, "scene_browsed")

        # Log the opening
        self._log_turn(
            raw_input="(opening)",
            intent=None,
            validation_result=None,
            events=[event],
            narrator_debug=narrator_debug,
            narrative=narrative,
            interactor_debug=None,
        )

        # Build TwoPhaseDebugInfo for opening
        pipeline_debug = self._build_pipeline_debug(
            raw_input="(opening)",
            intent=None,
            validation_result=None,
            events=[event],
            narrator_debug=narrator_debug,
            interactor_debug=None,
        )

        return narrative, pipeline_debug

    async def process(self, action: str) -> TwoPhaseActionResponse:
        """Process a player action through the two-phase pipeline.

        Pipeline:
            1. Parse action: rule-based for movement, InteractorAI for others
            2. Route to appropriate handler based on intent type
            3. Unified processing: validate -> execute -> create_event -> narrate

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
        # Try rule-based parser first (fast path for movement)
        intent: Intent | None = self.parser.parse(action, state, world)
        interactor_debug = None

        if intent is None:
            # Use InteractorAI for non-movement actions
            snapshot = self.visibility_resolver.build_snapshot(state, world)
            intent, interactor_debug = await self.interactor.parse(action, snapshot)

        # Phase 2: Route to handler and process
        if isinstance(intent, FlavorIntent):
            return await self._process_intent(
                handler=self._flavor_handler,
                intent=intent,
                raw_input=action,
                interactor_debug=interactor_debug,
            )
        elif isinstance(intent, ActionIntent):
            handler = self._get_action_handler(intent.action_type)
            if handler:
                return await self._process_intent(
                    handler=handler,
                    intent=intent,
                    raw_input=action,
                    interactor_debug=interactor_debug,
                )
            else:
                # Action type not yet supported
                return await self._process_unsupported(intent, action, interactor_debug)
        else:
            # Shouldn't happen, but handle gracefully
            return await self._process_unsupported(None, action, interactor_debug)

    def _get_action_handler(
        self, action_type: ActionType
    ) -> MovementHandler | ExamineHandler | TakeHandler | BrowseHandler | None:
        """Get the appropriate handler for an action type.

        Args:
            action_type: The action type to handle

        Returns:
            The handler for this action type, or None if unsupported
        """
        handlers = {
            ActionType.MOVE: self._movement_handler,
            ActionType.EXAMINE: self._examine_handler,
            ActionType.TAKE: self._take_handler,
            ActionType.BROWSE: self._browse_handler,
        }
        return handlers.get(action_type)

    async def _process_intent(
        self,
        handler: (
            MovementHandler
            | ExamineHandler
            | TakeHandler
            | BrowseHandler
            | FlavorHandler
        ),
        intent: Intent,
        raw_input: str,
        interactor_debug: LLMDebugInfo | None = None,
    ) -> TwoPhaseActionResponse:
        """Unified action processing flow.

        This method implements the core processing pattern for all intents:
            1. Validate the intent
            2. If invalid, create rejection event
            3. If valid, execute state changes and create success event
            4. Build snapshot and narrate
            5. Increment turn and log
            6. Check victory if applicable

        Args:
            handler: The IntentHandler for this action type
            intent: The parsed intent (ActionIntent or FlavorIntent)
            raw_input: The original player input string
            interactor_debug: Debug info from Interactor (if used)

        Returns:
            TwoPhaseActionResponse with narrative and updated state
        """
        state = self.state_manager.get_state()
        world = self.state_manager.world_data

        # 1. Validate
        result = handler.validate(intent, state, world)

        if not result.valid:
            # 2a. Rejection path
            target_id = None
            if isinstance(intent, ActionIntent):
                target_id = intent.target_id

            event = result.to_rejection_event(subject=target_id)
            events = [event]

            # Build snapshot (still at current location)
            snapshot = self.visibility_resolver.build_snapshot(state, world)

            # Generate rejection narrative
            narrative, narrator_debug = await self.narrator.narrate(events, snapshot)

            # Increment turn even for failed actions
            self.state_manager.increment_turn()

            # Build debug and log
            pipeline_debug = self._build_pipeline_debug(
                raw_input=raw_input,
                intent=intent if isinstance(intent, ActionIntent) else None,
                validation_result=result,
                events=events,
                narrator_debug=narrator_debug,
                interactor_debug=interactor_debug,
                flavor_intent=intent if isinstance(intent, FlavorIntent) else None,
            )

            self._log_turn(
                raw_input=raw_input,
                intent=intent if isinstance(intent, ActionIntent) else None,
                validation_result=result,
                events=events,
                narrator_debug=narrator_debug,
                narrative=narrative,
                interactor_debug=interactor_debug,
                flavor_intent=intent if isinstance(intent, FlavorIntent) else None,
            )

            return TwoPhaseActionResponse(
                narrative=narrative,
                state=self.state_manager.get_state(),
                events=[e.model_dump() for e in events],
                pipeline_debug=pipeline_debug,
            )

        # 2b. Success path

        # For movement, we need to handle first_visit tracking specially
        first_visit = False
        if isinstance(handler, MovementHandler):
            first_visit = handler.execute(intent, result, self.state_manager)
        else:
            handler.execute(intent, result, self.state_manager)

        # Build snapshot (after state changes)
        snapshot = self.visibility_resolver.build_snapshot(
            self.state_manager.get_state(), world
        )

        # Create success event
        if isinstance(handler, MovementHandler):
            event = handler.create_event(
                intent,
                result,
                self.state_manager.get_state(),
                world,
                first_visit=first_visit,
                snapshot=snapshot,
            )
        elif isinstance(handler, BrowseHandler):
            event = handler.create_event(
                intent, result, self.state_manager.get_state(), world, snapshot=snapshot
            )
        else:
            event = handler.create_event(
                intent, result, self.state_manager.get_state(), world
            )
        events = [event]

        # Get narration history for context
        history = self.state_manager.get_state().narration_history

        # Generate success narrative
        narrative, narrator_debug = await self.narrator.narrate(
            events, snapshot, history=history
        )

        # Store narration in history for certain event types
        if event.type in (EventType.LOCATION_CHANGED, EventType.SCENE_BROWSED):
            location_id = self.state_manager.get_state().current_location
            self._store_narration(narrative, location_id, event.type.value)

        # Increment turn
        self.state_manager.increment_turn()

        # Build debug and log
        pipeline_debug = self._build_pipeline_debug(
            raw_input=raw_input,
            intent=intent if isinstance(intent, ActionIntent) else None,
            validation_result=result,
            events=events,
            narrator_debug=narrator_debug,
            interactor_debug=interactor_debug,
            flavor_intent=intent if isinstance(intent, FlavorIntent) else None,
        )

        self._log_turn(
            raw_input=raw_input,
            intent=intent if isinstance(intent, ActionIntent) else None,
            validation_result=result,
            events=events,
            narrator_debug=narrator_debug,
            narrative=narrative,
            interactor_debug=interactor_debug,
            flavor_intent=intent if isinstance(intent, FlavorIntent) else None,
        )

        # Check for victory if applicable
        if handler.checks_victory:
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

    async def _process_unsupported(
        self,
        intent: ActionIntent | None,
        raw_input: str,
        interactor_debug: LLMDebugInfo | None = None,
    ) -> TwoPhaseActionResponse:
        """Process an unsupported action type.

        Args:
            intent: The ActionIntent (if parsed)
            raw_input: The original player input string
            interactor_debug: Debug info from Interactor

        Returns:
            TwoPhaseActionResponse with helpful message
        """
        state = self.state_manager.get_state()

        # Generate a helpful message based on the action type
        if intent and intent.action_type:
            message = (
                f"The '{intent.action_type.value}' action is not yet supported. "
                "Try examining objects, taking items, or moving around."
            )
        else:
            message = (
                "I don't understand that command. "
                "Try examining objects, taking items, or moving around."
            )

        pipeline_debug = None
        if self.debug:
            pipeline_debug = TwoPhaseDebugInfo(
                raw_input=raw_input,
                parser_type="interactor" if interactor_debug else "rule_based",
                parsed_intent=intent.model_dump() if intent else None,
                interactor_debug=interactor_debug,
                events=[],
            )

        # Log the turn (no narrator for unsupported actions)
        self._log_turn(
            raw_input=raw_input,
            intent=intent,
            validation_result=None,
            events=[],
            narrator_debug=None,
            narrative=message,
            interactor_debug=interactor_debug,
        )

        return TwoPhaseActionResponse(
            narrative=message,
            state=state,
            events=[],
            pipeline_debug=pipeline_debug,
        )

    def _serialize_validation_result(
        self, result: ValidationResult | None
    ) -> dict | None:
        """Serialize a ValidationResult to a dict.

        Args:
            result: The validation result to serialize

        Returns:
            Dict representation, or None if result is None
        """
        if not result:
            return None
        return {
            "valid": result.valid,
            "rejection_code": (
                result.rejection_code.value if result.rejection_code else None
            ),
            "rejection_reason": result.rejection_reason,
            "context": result.context,
            "hint": result.hint,
        }

    def _build_pipeline_debug(
        self,
        raw_input: str,
        intent: ActionIntent | None,
        validation_result: ValidationResult | None,
        events: list[Event],
        narrator_debug: LLMDebugInfo | None,
        interactor_debug: LLMDebugInfo | None = None,
        flavor_intent: FlavorIntent | None = None,
    ) -> TwoPhaseDebugInfo | None:
        """Build pipeline debug info if debug mode is enabled.

        Args:
            raw_input: Original player input
            intent: Parsed ActionIntent (or None)
            validation_result: ValidationResult from validator
            events: List of events generated
            narrator_debug: LLM debug info from narrator
            interactor_debug: LLM debug info from interactor
            flavor_intent: FlavorIntent if this was a flavor action

        Returns:
            TwoPhaseDebugInfo if debug mode enabled, else None
        """
        if not self.debug:
            return None

        validation_dict = self._serialize_validation_result(validation_result)

        # Determine parser type
        parser_type = "interactor" if interactor_debug else "rule_based"

        # Get parsed intent dict
        if intent:
            parsed_intent = intent.model_dump()
        elif flavor_intent:
            parsed_intent = flavor_intent.model_dump()
        else:
            parsed_intent = None

        return TwoPhaseDebugInfo(
            raw_input=raw_input,
            parser_type=parser_type,
            parsed_intent=parsed_intent,
            interactor_debug=interactor_debug,
            validation_result=validation_dict,
            events=[e.model_dump() for e in events],
            narrator_debug=narrator_debug,
        )

    def _log_turn(
        self,
        raw_input: str,
        intent: ActionIntent | None,
        validation_result: ValidationResult | None,
        events: list[Event],
        narrator_debug: LLMDebugInfo | None,
        narrative: str,
        interactor_debug: LLMDebugInfo | None = None,
        flavor_intent: FlavorIntent | None = None,
    ) -> None:
        """Log a complete turn to the session log file.

        Args:
            raw_input: Original player input
            intent: Parsed ActionIntent (or None)
            validation_result: ValidationResult from validator
            events: List of events generated
            narrator_debug: LLM debug info from narrator
            narrative: The final narrative text
            interactor_debug: LLM debug info from interactor
            flavor_intent: FlavorIntent if this was a flavor action
        """
        validation_dict = self._serialize_validation_result(validation_result)

        # Determine parser type
        parser_type = "interactor" if interactor_debug else "rule_based"

        # Get parsed intent dict
        if intent:
            parsed_intent = intent.model_dump()
        elif flavor_intent:
            parsed_intent = flavor_intent.model_dump()
        else:
            parsed_intent = None

        log_two_phase_turn(
            session_id=self.state_manager.session_id,
            world_id=self.state_manager.world_id,
            raw_input=raw_input,
            parser_type=parser_type,
            parsed_intent=parsed_intent,
            interactor_debug=interactor_debug,
            validation_result=validation_dict,
            events=[e.model_dump() for e in events],
            narrator_debug=narrator_debug,
            narrative=narrative,
        )

    def _store_narration(
        self,
        narrative: str,
        location_id: str,
        event_type: str,
    ) -> None:
        """Store a narration in the history for style variation.

        Maintains a rolling window of the last 5 narrations.

        Args:
            narrative: The narrative text generated
            location_id: Where the narration occurred
            event_type: Type of event that triggered the narration
        """
        state = self.state_manager.get_state()

        # Create new entry
        entry = NarrationEntry(
            text=narrative,
            location_id=location_id,
            turn=state.turn_count,
            event_type=event_type,
        )

        # Add to history (cap at 5 entries)
        history = list(state.narration_history)
        history.append(entry)
        if len(history) > 5:
            history = history[-5:]

        # Update state with new history
        self.state_manager.update_narration_history(history)
