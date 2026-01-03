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
from app.models.game import LLMDebugInfo
from app.engine.two_phase.models.event import Event, EventType, RejectionEvent

if TYPE_CHECKING:
    from app.engine.two_phase.models.perception import PerceptionSnapshot
    from app.engine.two_phase.models.state import NarrationEntry
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
        history: list["NarrationEntry"] | None = None,
    ) -> tuple[str, LLMDebugInfo | None]:
        """Generate narrative prose from events.

        Args:
            events: List of events to narrate
            snapshot: What the player can currently perceive
            history: Recent narration history for style variation

        Returns:
            Tuple of (narrative text, debug info if enabled)
        """
        system_prompt = self._build_system_prompt(snapshot, history)
        user_prompt = self._build_user_prompt(events, snapshot)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        result = await get_completion(messages, response_format={"type": "json_object"})
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

        narrative = parsed.get("narrative", "Something happens...")
        return narrative, debug_info

    def _build_system_prompt(
        self,
        snapshot: "PerceptionSnapshot",
        history: list["NarrationEntry"] | None = None,
    ) -> str:
        """Build the system prompt with world and location context.

        Args:
            snapshot: Current perception snapshot
            history: Recent narration history for style variation

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

        # Format narration history for variation
        history_section = self._format_history_section(history, snapshot.location_id)

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
            narration_history=history_section,
        )

    def _format_history_section(
        self,
        history: list["NarrationEntry"] | None,
        current_location_id: str,
    ) -> str:
        """Format narration history for the system prompt.

        Formats recent narrations to help avoid repetition:
        - Last 3 entries: full text with location context
        - Entries 4-5: one-line summaries

        Args:
            history: Recent narration history
            current_location_id: Current location for context

        Returns:
            Formatted history section string
        """
        if not history:
            return "No previous narrations in this session."

        lines = []

        # Split into recent (full) and older (summary)
        recent = history[-3:] if len(history) >= 3 else history
        older = history[:-3] if len(history) > 3 else []

        if recent:
            lines.append("### Recent (full text):")
            for entry in reversed(recent):  # Most recent first
                loc_marker = (
                    "(same location)"
                    if entry.location_id == current_location_id
                    else ""
                )
                # Show full text for recent entries (for phrase avoidance)
                lines.append(
                    f"[Turn {entry.turn}, {entry.location_id}] {loc_marker}\n{entry.text}"
                )

        if older:
            lines.append("\n### Older (summaries):")
            for entry in reversed(older):
                # First sentence only
                first_sentence = entry.text.split(".")[0] + "."
                lines.append(f"[Turn {entry.turn}] {first_sentence}")

        return "\n".join(lines)

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
        if event.type == EventType.SCENE_BROWSED:
            return self._describe_scene_browsed(event, snapshot)
        elif event.type == EventType.LOCATION_CHANGED:
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

    def _describe_scene_browsed(
        self,
        event: Event,
        snapshot: "PerceptionSnapshot",
    ) -> str:
        """Describe a SCENE_BROWSED event.

        This event triggers comprehensive scene description including all
        visible items, NPCs, exits, and location details.

        Args:
            event: The scene browsed event
            snapshot: Current perception snapshot

        Returns:
            Event description
        """
        context = event.context
        is_opening = context.get("is_opening", False)
        first_visit = context.get("first_visit", False)
        is_manual_browse = context.get("is_manual_browse", False)
        from_location = context.get("from_location")
        direction = context.get("direction")

        lines = [
            f"### SCENE_BROWSED: Comprehensive scene description for {snapshot.location_name}"
        ]

        if is_opening:
            lines.append("- This is the OPENING of the game")
            lines.append("- Set the scene dramatically and theatrically")
            lines.append("- Establish atmosphere, stakes, and situation")
            lines.append("- Make the player feel immersed immediately")

            # Include premise and starting situation for context
            premise = context.get("premise")
            starting_situation = context.get("starting_situation")
            hero_name = context.get("hero_name")

            if premise:
                lines.append("\n### Premise (explain this to the player):")
                lines.append(premise)

            if starting_situation:
                lines.append("\n### Starting Situation (weave this into the opening):")
                lines.append(starting_situation)

            if hero_name:
                lines.append(f"\n### Player Character: {hero_name}")
                lines.append("- Address them by name to personalize the opening")
        elif first_visit:
            lines.append("- This is the player's FIRST VISIT to this location")
            lines.append("- Provide a vivid, complete description")
            lines.append("- Establish the atmosphere strongly")
        elif is_manual_browse:
            lines.append("- Player is LOOKING AROUND manually")
            lines.append("- Check narration history above for repetition")
            lines.append("- If player has browsed here repeatedly, be more concise")
            lines.append("- Add subtle irony if nothing has changed")

        if direction:
            lines.append(f"- Player traveled: {direction}")

        if from_location:
            from_loc = self.world_data.get_location(from_location)
            from_name = from_loc.name if from_loc else from_location
            lines.append(f"- Came from: {from_name}")

        lines.append(f"\n- Atmosphere: {snapshot.location_atmosphere or 'unspecified'}")

        # Visible items
        visible_items = context.get("visible_items", [])
        if visible_items:
            lines.append("\n### Visible Items to Mention:")
            for item_name in visible_items:
                lines.append(f"- {item_name}")
        else:
            lines.append("\n### Items: None visible")

        # Visible NPCs
        visible_npcs = context.get("visible_npcs", [])
        if visible_npcs:
            lines.append("\n### NPCs Present:")
            for npc_name in visible_npcs:
                lines.append(f"- {npc_name}")

        # Visible exits
        visible_exits = context.get("visible_exits", [])
        if visible_exits:
            lines.append("\n### Available Exits:")
            for exit_info in visible_exits:
                lines.append(
                    f"- {exit_info['direction']}: leads to {exit_info['destination']}"
                )

        lines.append("\n### Instructions:")
        lines.append("- Weave ALL visible elements naturally into prose (not a list)")
        lines.append("- Make exits feel like natural parts of the space")
        lines.append("- Give items presence without over-describing")
        lines.append("- If NPCs present, briefly note their presence/activity")

        return "\n".join(lines)

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
            lines.append("- Provide a vivid, complete description")
            lines.append("- Establish the atmosphere strongly")
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

        # For first visits, include visible entities for comprehensive description
        if first_visit or is_opening:
            visible_items = context.get("visible_items", [])
            if visible_items:
                lines.append("\n### Visible Items to Mention:")
                for item_name in visible_items:
                    lines.append(f"- {item_name}")

            visible_npcs = context.get("visible_npcs", [])
            if visible_npcs:
                lines.append("\n### NPCs Present:")
                for npc_name in visible_npcs:
                    lines.append(f"- {npc_name}")

            visible_exits = context.get("visible_exits", [])
            if visible_exits:
                lines.append("\n### Available Exits:")
                for exit_info in visible_exits:
                    lines.append(
                        f"- {exit_info['direction']}: leads to {exit_info['destination']}"
                    )

            lines.append("\n### Instructions:")
            lines.append(
                "- Weave ALL visible elements naturally into prose (not a list)"
            )
            lines.append("- Make exits feel like natural parts of the space")
            lines.append("- Give items presence without over-describing")
            lines.append("- If NPCs present, briefly note their presence/activity")

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
