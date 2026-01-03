"""
Interactor AI for the two-phase game engine.

This module parses player input into structured intents using LLM-based
entity resolution. It receives a PerceptionSnapshot and resolves player
descriptions to entity IDs.

Output decision tree:
    - Known action + resolved target → ActionIntent
    - Known action + unresolved target → FlavorIntent(action_hint=X)
    - Unknown action → FlavorIntent(verb="whatever")

See planning/two-phase-game-loop-spec.md Section: Phase 1 - Parse Intent
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from app.llm.client import get_completion, get_model_string, parse_json_response
from app.llm.prompt_loader import get_loader
from app.models.game import LLMDebugInfo
from app.engine.two_phase.models.intent import (
    ActionIntent,
    ActionType,
    FlavorIntent,
    Intent,
)

if TYPE_CHECKING:
    from app.engine.two_phase.models.perception import PerceptionSnapshot
    from app.models.world import WorldData

logger = logging.getLogger(__name__)


class InteractorAI:
    """LLM-powered parser for the two-phase game engine.

    The Interactor takes raw player input and a PerceptionSnapshot,
    then uses an LLM to resolve entity references and classify the action.

    Responsibilities:
        - Resolve "the letter" to "old_letter" using visible entities
        - Classify verbs into ActionTypes
        - Produce FlavorIntent for unresolved targets or unknown verbs

    Example:
        >>> interactor = InteractorAI(world_data, session_id="abc", debug=True)
        >>> intent = await interactor.parse("examine the letter", snapshot)
        >>> isinstance(intent, ActionIntent)
        True
        >>> intent.target_id
        'old_letter'
    """

    def __init__(
        self,
        world_data: "WorldData",
        session_id: str | None = None,
        debug: bool = False,
    ):
        """Initialize the interactor.

        Args:
            world_data: The world data for context
            session_id: Optional session ID for logging
            debug: Whether to capture debug info
        """
        self.world_data = world_data
        self.session_id = session_id
        self.debug = debug
        self.last_debug_info: LLMDebugInfo | None = None

    async def parse(
        self,
        raw_input: str,
        snapshot: "PerceptionSnapshot",
    ) -> tuple[Intent, LLMDebugInfo | None]:
        """Parse player input into a structured intent.

        Args:
            raw_input: The raw player input string
            snapshot: What the player can currently perceive

        Returns:
            Tuple of (Intent, debug info if enabled)
        """
        system_prompt = self._build_system_prompt(snapshot)
        user_prompt = f'Player input: "{raw_input}"\n\nParse this action.'

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = await get_completion(
            messages,
            response_format={"type": "json_object"},
            temperature=0.3,  # Lower temperature for more deterministic parsing
        )
        parsed = parse_json_response(result.content)

        model = get_model_string()

        # Capture debug info if enabled
        debug_info = None
        if self.debug:
            debug_info = LLMDebugInfo(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                raw_response=result.content or "",
                parsed_response=parsed,
                model=model,
                timestamp=datetime.now().isoformat(),
                duration_ms=result.duration_ms,
                tokens_input=result.tokens_input,
                tokens_output=result.tokens_output,
                tokens_total=result.tokens_total,
            )
            self.last_debug_info = debug_info

        # Convert parsed response to Intent
        intent = self._parse_response(parsed, raw_input)
        return intent, debug_info

    def _build_system_prompt(self, snapshot: "PerceptionSnapshot") -> str:
        """Build the system prompt with available entities.

        Args:
            snapshot: Current perception snapshot

        Returns:
            Formatted system prompt
        """
        # Format items at location
        items_lines = []
        for item in snapshot.visible_items:
            items_lines.append(f'- {item.id} - "{item.name}"')
        items_at_location = "\n".join(items_lines) if items_lines else "None"

        # Format details
        details_lines = []
        for detail in snapshot.visible_details:
            details_lines.append(f'- {detail.id} - "{detail.name}"')
        details_at_location = "\n".join(details_lines) if details_lines else "None"

        # Format NPCs
        npcs_lines = []
        for npc in snapshot.visible_npcs:
            npcs_lines.append(f'- {npc.id} - "{npc.name}"')
        npcs_present = "\n".join(npcs_lines) if npcs_lines else "None"

        # Format inventory
        inventory_lines = []
        for item in snapshot.inventory:
            inventory_lines.append(f'- {item.id} - "{item.name}"')
        inventory = "\n".join(inventory_lines) if inventory_lines else "Empty"

        # Format exits (include description for natural language matching)
        exits_lines = []
        for exit in snapshot.visible_exits:
            if exit.description:
                exits_lines.append(
                    f"- {exit.direction}: {exit.destination_name} ({exit.description})"
                )
            else:
                exits_lines.append(f"- {exit.direction}: {exit.destination_name}")
        available_exits = "\n".join(exits_lines) if exits_lines else "None"

        # Load prompt template
        prompt_template = get_loader().get_prompt("interactor", "system_prompt.txt")

        return prompt_template.format(
            location_id=snapshot.location_id,
            location_name=snapshot.location_name,
            items_at_location=items_at_location,
            details_at_location=details_at_location,
            npcs_present=npcs_present,
            inventory=inventory,
            available_exits=available_exits,
        )

    def _parse_response(self, parsed: dict, raw_input: str) -> Intent:
        """Convert parsed LLM response to an Intent object.

        Args:
            parsed: The parsed JSON response from the LLM
            raw_input: The original player input

        Returns:
            ActionIntent or FlavorIntent
        """
        intent_type = parsed.get("type", "flavor_intent")

        if intent_type == "action_intent":
            return self._build_action_intent(parsed, raw_input)
        else:
            return self._build_flavor_intent(parsed, raw_input)

    def _build_action_intent(self, parsed: dict, raw_input: str) -> ActionIntent:
        """Build an ActionIntent from parsed response.

        Args:
            parsed: The parsed JSON response
            raw_input: The original player input

        Returns:
            ActionIntent
        """
        # Parse action type
        action_type_str = parsed.get("action_type", "EXAMINE").upper()
        try:
            action_type = ActionType(action_type_str.lower())
        except ValueError:
            # Default to EXAMINE if unknown
            logger.warning(
                f"Unknown action type: {action_type_str}, defaulting to EXAMINE"
            )
            action_type = ActionType.EXAMINE

        return ActionIntent(
            action_type=action_type,
            raw_input=raw_input,
            verb=parsed.get("verb", action_type_str.lower()),
            target_id=parsed.get("target_id", ""),
            instrument_id=parsed.get("instrument_id"),
            topic_id=parsed.get("topic_id"),
            recipient_id=parsed.get("recipient_id"),
            confidence=parsed.get("confidence", 0.8),
        )

    def _build_flavor_intent(self, parsed: dict, raw_input: str) -> FlavorIntent:
        """Build a FlavorIntent from parsed response.

        Args:
            parsed: The parsed JSON response
            raw_input: The original player input

        Returns:
            FlavorIntent
        """
        # Parse action hint if present
        action_hint = None
        action_hint_str = parsed.get("action_hint")
        if action_hint_str:
            try:
                action_hint = ActionType(action_hint_str.lower())
            except ValueError:
                logger.warning(f"Unknown action hint: {action_hint_str}")
                action_hint = None

        return FlavorIntent(
            verb=parsed.get("verb", "do"),
            raw_input=raw_input,
            action_hint=action_hint,
            target=parsed.get("target"),
            target_id=parsed.get("target_id"),
            topic=parsed.get("topic"),
            manner=parsed.get("manner"),
        )
