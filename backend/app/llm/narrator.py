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
        elif event.type == EventType.ITEM_EXAMINED:
            return self._describe_item_examined(event)
        elif event.type == EventType.DETAIL_EXAMINED:
            return self._describe_detail_examined(event)
        elif event.type == EventType.ITEM_TAKEN:
            return self._describe_item_taken(event)
        elif event.type == EventType.FLAVOR_ACTION:
            return self._describe_flavor_action(event, snapshot)
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

    def _describe_item_examined(self, event: Event) -> str:
        """Describe an ITEM_EXAMINED event.

        Args:
            event: The examine event

        Returns:
            Event description
        """
        context = event.context
        entity_name = context.get("entity_name", event.subject or "something")
        description = context.get("description", "")
        in_inventory = context.get("in_inventory", False)

        lines = [
            f"### ITEM_EXAMINED: Player examined {entity_name}",
            f"- Description: {description}",
        ]

        if in_inventory:
            lines.append("- The item is in the player's inventory")
            lines.append("- Narrate as if they're holding and studying it")
        else:
            lines.append("- The item is at the current location")
            lines.append("- Narrate as if they're looking at it closely")

        lines.append("- Keep the tone consistent with the location atmosphere")

        return "\n".join(lines)

    def _describe_detail_examined(self, event: Event) -> str:
        """Describe a DETAIL_EXAMINED event.

        Args:
            event: The examine event

        Returns:
            Event description
        """
        context = event.context
        entity_name = context.get("entity_name", event.subject or "something")
        description = context.get("description", "")

        lines = [
            f"### DETAIL_EXAMINED: Player examined {entity_name} (scenery/detail)",
            f"- Description: {description}",
            "- This is part of the location scenery, not an item",
            "- Provide an atmospheric description fitting the location",
            "- Keep the response focused on this detail",
        ]

        return "\n".join(lines)

    def _describe_item_taken(self, event: Event) -> str:
        """Describe an ITEM_TAKEN event.

        Args:
            event: The take event

        Returns:
            Event description
        """
        context = event.context
        item_name = context.get("item_name", event.subject or "something")
        take_description = context.get("take_description", "")

        lines = [
            f"### ITEM_TAKEN: Player picked up {item_name}",
        ]

        if take_description:
            lines.append(f"- Author's description: {take_description}")
            lines.append("- Use or expand on this description")
        else:
            lines.append("- No specific take description provided")
            lines.append("- Generate a brief, atmospheric description of picking it up")

        lines.append("- Keep the response brief (1-2 sentences)")
        lines.append("- End with the item now being in their possession")

        return "\n".join(lines)

    def _describe_flavor_action(
        self,
        event: Event,
        snapshot: "PerceptionSnapshot",
    ) -> str:
        """Describe a FLAVOR_ACTION event.

        Args:
            event: The flavor event
            snapshot: Current perception snapshot

        Returns:
            Event description
        """
        context = event.context
        verb = context.get("verb", "do something")
        action_hint = context.get("action_hint")
        target = context.get("target")
        target_id = context.get("target_id")
        topic = context.get("topic")
        manner = context.get("manner")

        lines = ["### FLAVOR_ACTION: Atmospheric action (no state change)"]

        if action_hint == "examine":
            # Improvised examine - target not in world
            lines.append(f'- Player tried to examine: "{target or "something"}"')
            lines.append("- This target is NOT a defined entity")
            lines.append("- Improvise a brief, atmospheric description")
            lines.append("- Keep it to 1-2 sentences")
            lines.append("- Do NOT invent important items or clues")
            lines.append(
                f"- Match the location atmosphere: {snapshot.location_atmosphere or 'unspecified'}"
            )
        elif action_hint == "take":
            # Improvised take - target not in world
            lines.append(f'- Player tried to take: "{target or "something"}"')
            lines.append("- This target cannot be taken (not a defined item)")
            lines.append("- Gently explain why this can't be taken")
            lines.append("- Keep the response natural, not an error message")
        elif action_hint == "talk" or action_hint == "ask":
            # Improvised dialogue
            if target_id:
                npc = self.world_data.get_npc(target_id)
                npc_name = npc.name if npc else target_id
                lines.append(f"- Player is speaking to: {npc_name}")
            else:
                lines.append(f'- Player is speaking to: "{target or "someone"}"')

            if topic:
                lines.append(f'- Topic: "{topic}"')
                lines.append("- This topic is NOT defined in the NPC's knowledge")
                lines.append(
                    "- The NPC should respond in-character but without spoilers"
                )
                lines.append("- Keep the response brief and atmospheric")
        else:
            # Generic flavor action (dance, jump, etc.)
            lines.append(f'- Verb: "{verb}"')
            if manner:
                lines.append(f'- Manner: "{manner}"')
            if target:
                lines.append(f'- Target: "{target}"')
            lines.append("- This is purely atmospheric")
            lines.append("- Generate a brief, fitting response (1-2 sentences)")
            lines.append("- Match the location mood")

        return "\n".join(lines)
