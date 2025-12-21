"""
Two-Phase game loop processor.

This module implements the main orchestrator for the two-phase game engine,
coordinating parsing, validation, execution, and narration.

See planning/two-phase-game-loop-spec.md for the full specification.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.engine.parser import RuleBasedParser
from app.engine.validators.examine import ExamineValidator
from app.engine.validators.movement import MovementValidator
from app.engine.validators.take import TakeValidator
from app.engine.visibility import DefaultVisibilityResolver
from app.llm.interactor import InteractorAI
from app.llm.narrator import NarratorAI
from app.llm.session_logger import log_two_phase_turn
from app.models.event import Event, EventType
from app.models.game import LLMDebugInfo
from app.models.intent import ActionIntent, ActionType, FlavorIntent, Intent
from app.models.two_phase_state import TwoPhaseActionResponse, TwoPhaseDebugInfo
from app.models.validation import ValidationResult

if TYPE_CHECKING:
    from app.engine.two_phase_state import TwoPhaseStateManager


class TwoPhaseProcessor:
    """Two-phase game loop processor.

    Coordinates the complete action processing pipeline:
        1. Parse: Rule-based parser for movement, InteractorAI for others
        2. Validate: Validators check against world rules
        3. Execute: State changes are applied
        4. Narrate: NarratorAI generates prose

    Phase 2 supports movement, examine, and take actions.
    FlavorIntents go directly to the narrator for atmospheric responses.

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

        # Validators
        self.movement_validator = MovementValidator()
        self.examine_validator = ExamineValidator()
        self.take_validator = TakeValidator()

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

        # Log the opening
        self._log_turn(
            raw_input="(opening)",
            intent=None,
            validation_result=None,
            events=[event],
            narrator_debug=debug_info,
            narrative=narrative,
            interactor_debug=None,
        )

        return narrative, debug_info

    async def process(self, action: str) -> TwoPhaseActionResponse:
        """Process a player action through the two-phase pipeline.

        Pipeline:
            1. Parse action: rule-based for movement, InteractorAI for others
            2. If FlavorIntent, generate atmospheric narrative
            3. Validate ActionIntent against world rules
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
        # Try rule-based parser first (fast path for movement)
        intent: Intent | None = self.parser.parse(action, state, world)
        interactor_debug = None

        if intent is None:
            # Use InteractorAI for non-movement actions
            snapshot = self.visibility_resolver.build_snapshot(state, world)
            intent, interactor_debug = await self.interactor.parse(action, snapshot)

        # Phase 2: Validate & Execute based on intent type
        if isinstance(intent, FlavorIntent):
            return await self._process_flavor(intent, action, interactor_debug)
        elif isinstance(intent, ActionIntent):
            if intent.action_type == ActionType.MOVE:
                return await self._process_movement(intent, action, interactor_debug)
            elif intent.action_type == ActionType.EXAMINE:
                return await self._process_examine(intent, action, interactor_debug)
            elif intent.action_type == ActionType.TAKE:
                return await self._process_take(intent, action, interactor_debug)
            else:
                # Action type not yet supported
                return await self._process_unsupported(intent, action, interactor_debug)
        else:
            # Shouldn't happen, but handle gracefully
            return await self._process_unsupported(None, action, interactor_debug)

    async def _process_movement(
        self,
        intent: ActionIntent,
        raw_input: str,
        interactor_debug: LLMDebugInfo | None = None,
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
                interactor_debug=interactor_debug,
            )

            # Log the turn
            self._log_turn(
                raw_input=raw_input,
                intent=intent,
                validation_result=result,
                events=events,
                narrator_debug=narrator_debug,
                narrative=narrative,
                interactor_debug=interactor_debug,
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
            interactor_debug=interactor_debug,
        )

        # Log the turn
        self._log_turn(
            raw_input=raw_input,
            intent=intent,
            validation_result=result,
            events=events,
            narrator_debug=narrator_debug,
            narrative=narrative,
            interactor_debug=interactor_debug,
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

    async def _process_examine(
        self,
        intent: ActionIntent,
        raw_input: str,
        interactor_debug: LLMDebugInfo | None = None,
    ) -> TwoPhaseActionResponse:
        """Process an examine action.

        Args:
            intent: The parsed EXAMINE ActionIntent
            raw_input: The original player input string
            interactor_debug: Debug info from Interactor (if used)

        Returns:
            TwoPhaseActionResponse with examine result
        """
        state = self.state_manager.get_state()
        world = self.state_manager.world_data

        # Validate examine
        result = self.examine_validator.validate(intent, state, world)

        if not result.valid:
            # Examine rejected
            event = result.to_rejection_event(subject=intent.target_id)
            events = [event]

            snapshot = self.visibility_resolver.build_snapshot(state, world)
            narrative, narrator_debug = await self.narrator.narrate(events, snapshot)

            self.state_manager.increment_turn()

            pipeline_debug = self._build_pipeline_debug(
                raw_input=raw_input,
                intent=intent,
                validation_result=result,
                events=events,
                narrator_debug=narrator_debug,
                interactor_debug=interactor_debug,
            )

            # Log the turn
            self._log_turn(
                raw_input=raw_input,
                intent=intent,
                validation_result=result,
                events=events,
                narrator_debug=narrator_debug,
                narrative=narrative,
                interactor_debug=interactor_debug,
            )

            return TwoPhaseActionResponse(
                narrative=narrative,
                state=self.state_manager.get_state(),
                events=[e.model_dump() for e in events],
                pipeline_debug=pipeline_debug,
            )

        # Examine valid - determine event type
        entity_type = result.context.get("entity_type", "item")
        if entity_type == "detail":
            event_type = EventType.DETAIL_EXAMINED
        else:
            event_type = EventType.ITEM_EXAMINED

        event = Event(
            type=event_type,
            subject=result.context.get("entity_id"),
            context={
                "entity_name": result.context.get("entity_name"),
                "description": result.context.get("description"),
                "in_inventory": result.context.get("in_inventory", False),
                "found_description": result.context.get("found_description"),
            },
        )
        events = [event]

        snapshot = self.visibility_resolver.build_snapshot(state, world)
        narrative, narrator_debug = await self.narrator.narrate(events, snapshot)

        self.state_manager.increment_turn()

        pipeline_debug = self._build_pipeline_debug(
            raw_input=raw_input,
            intent=intent,
            validation_result=result,
            events=events,
            narrator_debug=narrator_debug,
            interactor_debug=interactor_debug,
        )

        # Log the turn
        self._log_turn(
            raw_input=raw_input,
            intent=intent,
            validation_result=result,
            events=events,
            narrator_debug=narrator_debug,
            narrative=narrative,
            interactor_debug=interactor_debug,
        )

        return TwoPhaseActionResponse(
            narrative=narrative,
            state=self.state_manager.get_state(),
            events=[e.model_dump() for e in events],
            pipeline_debug=pipeline_debug,
        )

    async def _process_take(
        self,
        intent: ActionIntent,
        raw_input: str,
        interactor_debug: LLMDebugInfo | None = None,
    ) -> TwoPhaseActionResponse:
        """Process a take action.

        Args:
            intent: The parsed TAKE ActionIntent
            raw_input: The original player input string
            interactor_debug: Debug info from Interactor (if used)

        Returns:
            TwoPhaseActionResponse with take result
        """
        state = self.state_manager.get_state()
        world = self.state_manager.world_data

        # Validate take
        result = self.take_validator.validate(intent, state, world)

        if not result.valid:
            # Take rejected
            event = result.to_rejection_event(subject=intent.target_id)
            events = [event]

            snapshot = self.visibility_resolver.build_snapshot(state, world)
            narrative, narrator_debug = await self.narrator.narrate(events, snapshot)

            self.state_manager.increment_turn()

            pipeline_debug = self._build_pipeline_debug(
                raw_input=raw_input,
                intent=intent,
                validation_result=result,
                events=events,
                narrator_debug=narrator_debug,
                interactor_debug=interactor_debug,
            )

            # Log the turn
            self._log_turn(
                raw_input=raw_input,
                intent=intent,
                validation_result=result,
                events=events,
                narrator_debug=narrator_debug,
                narrative=narrative,
                interactor_debug=interactor_debug,
            )

            return TwoPhaseActionResponse(
                narrative=narrative,
                state=self.state_manager.get_state(),
                events=[e.model_dump() for e in events],
                pipeline_debug=pipeline_debug,
            )

        # Take valid - add to inventory
        item_id = result.context.get("item_id")
        self.state_manager.add_item(item_id)

        event = Event(
            type=EventType.ITEM_TAKEN,
            subject=item_id,
            context={
                "item_name": result.context.get("item_name"),
                "take_description": result.context.get("take_description"),
                "from_location": result.context.get("from_location"),
            },
        )
        events = [event]

        snapshot = self.visibility_resolver.build_snapshot(
            self.state_manager.get_state(), world
        )
        narrative, narrator_debug = await self.narrator.narrate(events, snapshot)

        self.state_manager.increment_turn()

        pipeline_debug = self._build_pipeline_debug(
            raw_input=raw_input,
            intent=intent,
            validation_result=result,
            events=events,
            narrator_debug=narrator_debug,
            interactor_debug=interactor_debug,
        )

        # Log the turn
        self._log_turn(
            raw_input=raw_input,
            intent=intent,
            validation_result=result,
            events=events,
            narrator_debug=narrator_debug,
            narrative=narrative,
            interactor_debug=interactor_debug,
        )

        # Check for victory (might be item-based)
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

    async def _process_flavor(
        self,
        intent: FlavorIntent,
        raw_input: str,
        interactor_debug: LLMDebugInfo | None = None,
    ) -> TwoPhaseActionResponse:
        """Process a flavor action (atmospheric, no state change).

        Args:
            intent: The FlavorIntent
            raw_input: The original player input string
            interactor_debug: Debug info from Interactor

        Returns:
            TwoPhaseActionResponse with flavor narrative
        """
        state = self.state_manager.get_state()
        world = self.state_manager.world_data

        # Create flavor event
        event = Event(
            type=EventType.FLAVOR_ACTION,
            context={
                "verb": intent.verb,
                "action_hint": intent.action_hint.value if intent.action_hint else None,
                "target": intent.target,
                "target_id": intent.target_id,
                "topic": intent.topic,
                "manner": intent.manner,
            },
        )
        events = [event]

        snapshot = self.visibility_resolver.build_snapshot(state, world)
        narrative, narrator_debug = await self.narrator.narrate(events, snapshot)

        self.state_manager.increment_turn()

        pipeline_debug = self._build_pipeline_debug(
            raw_input=raw_input,
            intent=None,  # FlavorIntent doesn't have model_dump compatible with ActionIntent
            validation_result=None,
            events=events,
            narrator_debug=narrator_debug,
            interactor_debug=interactor_debug,
            flavor_intent=intent,
        )

        # Log the turn
        self._log_turn(
            raw_input=raw_input,
            intent=None,
            validation_result=None,
            events=events,
            narrator_debug=narrator_debug,
            narrative=narrative,
            interactor_debug=interactor_debug,
            flavor_intent=intent,
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
