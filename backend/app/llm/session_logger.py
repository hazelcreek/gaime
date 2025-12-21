"""
Session-based LLM interaction logger.

Creates human-readable log files for each game session with
clearly separated LLM interactions.

Supports both classic engine (single LLM call per turn) and
two-phase engine (parser -> validator -> narrator pipeline).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.game import LLMDebugInfo


# Get project root and logs directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"


class SessionLogger:
    """Logs LLM interactions for a game session to a dedicated file."""

    def __init__(self, session_id: str, world_id: str):
        self.session_id = session_id
        self.world_id = world_id
        self.interaction_count = 0
        self.turn_count = 0
        self.log_file: Path | None = None
        self._first_interaction_timestamp: str | None = None

    def _ensure_log_file(self) -> Path:
        """Create the log file on first interaction."""
        if self.log_file is None:
            # Create world-specific directory
            world_dir = LOGS_DIR / self.world_id
            world_dir.mkdir(parents=True, exist_ok=True)

            # Use timestamp of first interaction in filename
            self._first_interaction_timestamp = datetime.now().strftime(
                "%Y-%m-%d_%H-%M-%S"
            )
            filename = f"{self._first_interaction_timestamp}_{self.session_id}.log"
            self.log_file = world_dir / filename

            # Write header
            with open(self.log_file, "w") as f:
                f.write("GAIME Session Log\n")
                f.write("================\n")
                f.write(f"Session ID: {self.session_id}\n")
                f.write(f"World: {self.world_id}\n")
                f.write(f"Started: {datetime.now().isoformat()}\n")
                f.write("\n")

        return self.log_file

    def log_interaction(
        self,
        system_prompt: str,
        user_prompt: str,
        raw_response: str,
        parsed_response: dict[str, Any],
        model: str,
    ) -> None:
        """Log an LLM interaction to the session file."""
        log_file = self._ensure_log_file()
        self.interaction_count += 1

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_file, "a") as f:
            # Interaction header
            f.write("═" * 70 + "\n")
            f.write(
                f"LLM INTERACTION #{self.interaction_count} | {timestamp} | {model}\n"
            )
            f.write("═" * 70 + "\n\n")

            # System prompt
            f.write("─── SYSTEM PROMPT ───\n")
            f.write(system_prompt)
            f.write("\n\n")

            # User prompt
            f.write("─── USER PROMPT ───\n")
            f.write(user_prompt)
            f.write("\n\n")

            # Raw response
            f.write("─── RAW RESPONSE ───\n")
            f.write(raw_response or "(empty)")
            f.write("\n\n")

            # Parsed result (pretty-printed JSON)
            f.write("─── PARSED RESULT ───\n")
            try:
                f.write(json.dumps(parsed_response, indent=2, ensure_ascii=False))
            except (TypeError, ValueError):
                f.write(str(parsed_response))
            f.write("\n\n")

            # Memory updates (if present)
            memory_updates = parsed_response.get("memory_updates", {})
            if memory_updates:
                f.write("─── MEMORY UPDATES ───\n")

                # NPC interactions
                npc_interactions = memory_updates.get("npc_interactions", {})
                if npc_interactions:
                    f.write("NPC Interactions:\n")
                    for npc_id, update in npc_interactions.items():
                        parts = [f"  {npc_id}:"]
                        if isinstance(update, dict):
                            if update.get("topic_discussed"):
                                parts.append(f"topic=\"{update['topic_discussed']}\"")
                            if update.get("player_disposition"):
                                parts.append(f"player={update['player_disposition']}")
                            if update.get("npc_disposition"):
                                parts.append(f"npc={update['npc_disposition']}")
                            if update.get("notable_moment"):
                                moment = (
                                    update["notable_moment"][:50] + "..."
                                    if len(update.get("notable_moment", "")) > 50
                                    else update.get("notable_moment", "")
                                )
                                parts.append(f'notable="{moment}"')
                        f.write(" ".join(parts) + "\n")

                # New discoveries
                new_discoveries = memory_updates.get("new_discoveries", [])
                if new_discoveries:
                    f.write("New Discoveries:\n")
                    for discovery in new_discoveries:
                        f.write(f"  - {discovery}\n")

                f.write("\n")

    def log_two_phase_turn(
        self,
        raw_input: str,
        parser_type: str,
        parsed_intent: dict | None,
        interactor_debug: "LLMDebugInfo | None",
        validation_result: dict | None,
        events: list[dict],
        narrator_debug: "LLMDebugInfo | None",
        narrative: str,
    ) -> None:
        """Log a complete two-phase engine turn to the session file.

        Captures the full pipeline: input -> parser -> validation -> events -> narrator.

        Args:
            raw_input: The original player input string
            parser_type: "rule_based" or "interactor"
            parsed_intent: ActionIntent or FlavorIntent as dict
            interactor_debug: LLMDebugInfo from InteractorAI (if used)
            validation_result: Validation result dict
            events: List of event dicts
            narrator_debug: LLMDebugInfo from NarratorAI
            narrative: The final narrative text
        """
        log_file = self._ensure_log_file()
        self.turn_count += 1

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(log_file, "a") as f:
            # Turn header
            f.write("═" * 70 + "\n")
            f.write(f"TWO-PHASE TURN #{self.turn_count} | {timestamp}\n")
            f.write("═" * 70 + "\n\n")

            # Player input
            f.write("─── PLAYER INPUT ───\n")
            f.write(f'"{raw_input}"\n\n')

            # Parser section
            f.write("─── PARSER ───\n")
            f.write(f"Type: {parser_type}\n")

            if parser_type == "rule_based" and parsed_intent:
                # For rule-based, show the intent directly
                f.write("\nParsed Intent:\n")
                self._write_intent(f, parsed_intent)
                f.write("\n")
            elif parser_type == "interactor" and interactor_debug:
                # For interactor, show full LLM details
                f.write("\n─── INTERACTOR LLM ───\n")
                self._write_llm_debug(f, interactor_debug)

                if parsed_intent:
                    f.write("Parsed Intent:\n")
                    self._write_intent(f, parsed_intent)
                    f.write("\n")

            # Validation section
            if validation_result:
                f.write("─── VALIDATION ───\n")
                is_valid = validation_result.get("valid", False)
                f.write(f"Result: {'VALID' if is_valid else 'REJECTED'}\n")

                if not is_valid:
                    code = validation_result.get("rejection_code", "unknown")
                    reason = validation_result.get("rejection_reason", "")
                    f.write(f"Code: {code}\n")
                    f.write(f"Reason: {reason}\n")

                    hint = validation_result.get("hint")
                    if hint:
                        f.write(f"Hint: {hint}\n")

                context = validation_result.get("context", {})
                if context:
                    f.write("Context:\n")
                    for key, value in context.items():
                        # Truncate long values
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        f.write(f"  {key}: {value_str}\n")

                f.write("\n")

            # Events section
            if events:
                f.write("─── EVENTS ───\n")
                for i, event in enumerate(events, 1):
                    event_type = event.get("type", "unknown")
                    subject = event.get("subject", "")
                    f.write(f"{i}. {event_type}")
                    if subject:
                        f.write(f" ({subject})")
                    f.write("\n")

                    context = event.get("context", {})
                    if context:
                        for key, value in context.items():
                            if value is not None:
                                value_str = str(value)
                                if len(value_str) > 80:
                                    value_str = value_str[:80] + "..."
                                f.write(f"   {key}: {value_str}\n")

                f.write("\n")

            # Narrator section
            if narrator_debug:
                f.write("─── NARRATOR LLM ───\n")
                self._write_llm_debug(f, narrator_debug)

            # Final narrative
            f.write("─── FINAL NARRATIVE ───\n")
            f.write(f"{narrative}\n\n")

    def _write_llm_debug(self, f, debug: "LLMDebugInfo") -> None:
        """Write LLM debug info to file.

        Args:
            f: File handle to write to
            debug: LLMDebugInfo object
        """
        model = debug.model if hasattr(debug, "model") else "unknown"
        f.write(f"Model: {model}\n\n")

        f.write("System Prompt:\n")
        f.write(debug.system_prompt)
        f.write("\n\n")

        f.write("User Prompt:\n")
        f.write(debug.user_prompt)
        f.write("\n\n")

        f.write("Raw Response:\n")
        f.write(debug.raw_response or "(empty)")
        f.write("\n\n")

    def _write_intent(self, f, intent: dict) -> None:
        """Write parsed intent to file in a readable format.

        Args:
            f: File handle to write to
            intent: Intent dict (ActionIntent or FlavorIntent)
        """
        # Determine intent type
        if "action_type" in intent:
            f.write("  type: action_intent\n")
            f.write(f"  action_type: {intent.get('action_type', 'unknown')}\n")
            f.write(f"  target_id: {intent.get('target_id', '')}\n")
            f.write(f"  verb: {intent.get('verb', '')}\n")

            if intent.get("instrument_id"):
                f.write(f"  instrument_id: {intent['instrument_id']}\n")
            if intent.get("topic_id"):
                f.write(f"  topic_id: {intent['topic_id']}\n")
            if intent.get("recipient_id"):
                f.write(f"  recipient_id: {intent['recipient_id']}\n")
            if intent.get("confidence") is not None:
                f.write(f"  confidence: {intent['confidence']}\n")
        else:
            # FlavorIntent
            f.write("  type: flavor_intent\n")
            f.write(f"  verb: {intent.get('verb', '')}\n")

            if intent.get("action_hint"):
                f.write(f"  action_hint: {intent['action_hint']}\n")
            if intent.get("target"):
                f.write(f"  target: {intent['target']}\n")
            if intent.get("target_id"):
                f.write(f"  target_id: {intent['target_id']}\n")
            if intent.get("topic"):
                f.write(f"  topic: {intent['topic']}\n")
            if intent.get("manner"):
                f.write(f"  manner: {intent['manner']}\n")


# Store active loggers per session
_session_loggers: dict[str, SessionLogger] = {}


def get_session_logger(session_id: str, world_id: str) -> SessionLogger:
    """Get or create a session logger for the given session."""
    if session_id not in _session_loggers:
        _session_loggers[session_id] = SessionLogger(session_id, world_id)
    return _session_loggers[session_id]


def log_llm_interaction(
    session_id: str,
    world_id: str,
    system_prompt: str,
    user_prompt: str,
    raw_response: str,
    parsed_response: dict[str, Any],
    model: str,
) -> None:
    """Convenience function to log an LLM interaction."""
    logger = get_session_logger(session_id, world_id)
    logger.log_interaction(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        raw_response=raw_response,
        parsed_response=parsed_response,
        model=model,
    )


def log_two_phase_turn(
    session_id: str,
    world_id: str,
    raw_input: str,
    parser_type: str,
    parsed_intent: dict | None,
    interactor_debug: "LLMDebugInfo | None",
    validation_result: dict | None,
    events: list[dict],
    narrator_debug: "LLMDebugInfo | None",
    narrative: str,
) -> None:
    """Convenience function to log a two-phase engine turn.

    Args:
        session_id: The session ID
        world_id: The world ID
        raw_input: The original player input string
        parser_type: "rule_based" or "interactor"
        parsed_intent: ActionIntent or FlavorIntent as dict
        interactor_debug: LLMDebugInfo from InteractorAI (if used)
        validation_result: Validation result dict
        events: List of event dicts
        narrator_debug: LLMDebugInfo from NarratorAI
        narrative: The final narrative text
    """
    logger = get_session_logger(session_id, world_id)
    logger.log_two_phase_turn(
        raw_input=raw_input,
        parser_type=parser_type,
        parsed_intent=parsed_intent,
        interactor_debug=interactor_debug,
        validation_result=validation_result,
        events=events,
        narrator_debug=narrator_debug,
        narrative=narrative,
    )
