"""
Narrator AI for the two-phase game engine.

This module generates narrative prose from confirmed game events.
The narrator receives events and a PerceptionSnapshot, and produces
rich descriptive text without determining game mechanics.

See planning/two-phase-game-loop-spec.md Section: Prompt Specifications
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.llm.client import get_completion, parse_json_response, get_model_string
from app.llm.prompt_loader import get_loader
from app.llm.session_logger import log_llm_interaction
from app.models.game import LLMDebugInfo
from app.models.event import Event, EventType, RejectionEvent

if TYPE_CHECKING:
    from app.models.perception import PerceptionSnapshot
    from app.models.world import WorldData


class NarratorAI:
    """LLM-powered narrator for the two-phase game engine.

    The narrator takes confirmed events and a perception snapshot
    and generates rich prose. It does NOT determine game mechanics.

    Responsibilities:
        - Generate atmospheric location descriptions
        - Narrate successful actions
        - Turn rejections into natural in-world explanations
        - Emphasize discovery moments

    Example:
        >>> narrator = NarratorAI(world_data, debug=True)
        >>> events = [Event(type=EventType.LOCATION_CHANGED, ...)]
        >>> narrative = await narrator.narrate(events, snapshot)
    """

    def __init__(
        self,
        world_data: "WorldData",
        session_id: str | None = None,
        debug: bool = False,
    ):
        """Initialize the narrator.

        Args:
            world_data: The world data for context
            session_id: Optional session ID for logging
            debug: Whether to capture debug info
        """
        self.world_data = world_data
        self.session_id = session_id
        self.debug = debug
        self.last_debug_info: LLMDebugInfo | None = None

    async def narrate(
        self,
        events: list[Event],
        snapshot: "PerceptionSnapshot",
    ) -> tuple[str, LLMDebugInfo | None]:
        """Generate narrative prose from events.

        Args:
            events: List of events to narrate
            snapshot: What the player can currently perceive

        Returns:
            Tuple of (narrative text, debug info if enabled)
        """
        system_prompt = self._build_system_prompt(snapshot)
        user_prompt = self._build_user_prompt(events, snapshot)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = await get_completion(
            messages, response_format={"type": "json_object"}
        )
        parsed = parse_json_response(response)

        model = get_model_string()

        # Log interaction if session_id provided
        if self.session_id:
            log_llm_interaction(
                session_id=self.session_id,
                world_id=self.world_data.world.name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                raw_response=response or "",
                parsed_response=parsed,
                model=model,
            )

        # Capture debug info if enabled
        debug_info = None
        if self.debug:
            debug_info = LLMDebugInfo(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                raw_response=response or "",
                parsed_response=parsed,
                model=model,
                timestamp=datetime.now().isoformat(),
            )
            self.last_debug_info = debug_info

        narrative = parsed.get("narrative", "Something happens...")
        return narrative, debug_info

    def _build_system_prompt(self, snapshot: "PerceptionSnapshot") -> str:
        """Build the system prompt with world and location context.

        Args:
            snapshot: Current perception snapshot

        Returns:
            Formatted system prompt
        """
        world = self.world_data.world

        # Format exits
        exits_lines = []
        for exit in snapshot.visible_exits:
            exit_desc = f"- {exit.direction}: leads to {exit.destination_name}"
            if exit.description:
                exit_desc += f" ({exit.description})"
            exits_lines.append(exit_desc)
        exits_description = (
            "\n".join(exits_lines) if exits_lines else "No visible exits"
        )

        # Format visible items
        items_lines = []
        for item in snapshot.visible_items:
            item_desc = f"- {item.name}"
            if item.description:
                item_desc += f": {item.description}"
            if item.is_new:
                item_desc += " [NEWLY DISCOVERED]"
            items_lines.append(item_desc)
        items_description = "\n".join(items_lines) if items_lines else "Nothing of note"

        # Format inventory
        inventory_lines = [item.name for item in snapshot.inventory]
        inventory_description = (
            ", ".join(inventory_lines) if inventory_lines else "Nothing"
        )

        # Get hero name
        hero_name = getattr(world, "hero_name", "the hero") or "the hero"

        # Load prompt template
        prompt_template = get_loader().get_prompt("narrator", "system_prompt.txt")

        return prompt_template.format(
            world_name=world.name,
            theme=world.theme,
            tone=world.tone,
            hero_name=hero_name,
            location_name=snapshot.location_name,
            location_atmosphere=snapshot.location_atmosphere or "",
            exits_description=exits_description,
            items_description=items_description,
            inventory_description=inventory_description,
        )

    def _build_user_prompt(
        self,
        events: list[Event],
        snapshot: "PerceptionSnapshot",
    ) -> str:
        """Build the user prompt describing events to narrate.

        Args:
            events: List of events to narrate
            snapshot: Current perception snapshot

        Returns:
            Formatted user prompt
        """
        lines = ["## Events to Narrate\n"]

        for event in events:
            lines.append(self._describe_event(event, snapshot))

        lines.append("\nGenerate the narrative for these events.")

        return "\n".join(lines)

    def _describe_event(
        self,
        event: Event,
        snapshot: "PerceptionSnapshot",
    ) -> str:
        """Generate description of a single event for the prompt.

        Args:
            event: The event to describe
            snapshot: Current perception snapshot

        Returns:
            Event description string
        """
        if event.type == EventType.LOCATION_CHANGED:
            return self._describe_location_changed(event, snapshot)
        elif event.type == EventType.ACTION_REJECTED:
            return self._describe_rejection(event)
        else:
            # Generic event description
            return f"Event: {event.type.value} - {event.subject or 'unknown'}"

    def _describe_location_changed(
        self,
        event: Event,
        snapshot: "PerceptionSnapshot",
    ) -> str:
        """Describe a LOCATION_CHANGED event.

        Args:
            event: The location change event
            snapshot: Current perception snapshot

        Returns:
            Event description
        """
        context = event.context
        is_opening = context.get("is_opening", False)
        first_visit = context.get("first_visit", snapshot.first_visit)
        from_location = context.get("from_location")
        direction = context.get("direction")

        lines = [
            f"### LOCATION_CHANGED: Player {'arrives at' if is_opening else 'moved to'} {snapshot.location_name}"
        ]

        if is_opening:
            lines.append("- This is the OPENING of the game")
            lines.append("- Set the scene dramatically")
            lines.append("- Establish atmosphere and introduce the location")
        elif first_visit:
            lines.append("- This is the player's FIRST VISIT to this location")
            lines.append("- Describe the location in detail")
            lines.append("- Establish the atmosphere")
        else:
            lines.append("- Player has been here before")
            lines.append("- Acknowledge familiarity briefly")
            lines.append("- Note any changes since last visit")

        if direction:
            lines.append(f"- Player traveled: {direction}")

        if from_location:
            from_loc = self.world_data.get_location(from_location)
            from_name = from_loc.name if from_loc else from_location
            lines.append(f"- Came from: {from_name}")

        lines.append(f"- Atmosphere: {snapshot.location_atmosphere or 'unspecified'}")

        return "\n".join(lines)

    def _describe_rejection(self, event: Event) -> str:
        """Describe an ACTION_REJECTED event.

        Args:
            event: The rejection event

        Returns:
            Event description
        """
        # Handle both Event and RejectionEvent
        if isinstance(event, RejectionEvent):
            rejection_code = event.rejection_code
            rejection_reason = event.rejection_reason
            would_have = event.would_have
        else:
            rejection_code = event.context.get("rejection_code", "unknown")
            rejection_reason = event.context.get(
                "rejection_reason", "The action failed."
            )
            would_have = event.context.get("would_have")

        lines = [
            "### ACTION_REJECTED: Player's action was blocked",
            f"- Code: {rejection_code}",
            f"- Reason: {rejection_reason}",
            "- Make this feel NATURAL, not like an error message",
            "- The player should understand why they can't do this",
        ]

        if would_have:
            lines.append(f"- Hint at what might work: {would_have}")

        return "\n".join(lines)
