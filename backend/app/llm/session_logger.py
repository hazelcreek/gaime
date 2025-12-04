"""
Session-based LLM interaction logger.

Creates human-readable log files for each game session with
clearly separated LLM interactions.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


# Get project root and logs directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"


class SessionLogger:
    """Logs LLM interactions for a game session to a dedicated file."""
    
    def __init__(self, session_id: str, world_id: str):
        self.session_id = session_id
        self.world_id = world_id
        self.interaction_count = 0
        self.log_file: Path | None = None
        self._first_interaction_timestamp: str | None = None
    
    def _ensure_log_file(self) -> Path:
        """Create the log file on first interaction."""
        if self.log_file is None:
            # Create world-specific directory
            world_dir = LOGS_DIR / self.world_id
            world_dir.mkdir(parents=True, exist_ok=True)
            
            # Use timestamp of first interaction in filename
            self._first_interaction_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{self._first_interaction_timestamp}_{self.session_id}.log"
            self.log_file = world_dir / filename
            
            # Write header
            with open(self.log_file, "w") as f:
                f.write(f"GAIME Session Log\n")
                f.write(f"================\n")
                f.write(f"Session ID: {self.session_id}\n")
                f.write(f"World: {self.world_id}\n")
                f.write(f"Started: {datetime.now().isoformat()}\n")
                f.write(f"\n")
        
        return self.log_file
    
    def log_interaction(
        self,
        system_prompt: str,
        user_prompt: str,
        raw_response: str,
        parsed_response: dict[str, Any],
        model: str
    ) -> None:
        """Log an LLM interaction to the session file."""
        log_file = self._ensure_log_file()
        self.interaction_count += 1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a") as f:
            # Interaction header
            f.write("═" * 70 + "\n")
            f.write(f"LLM INTERACTION #{self.interaction_count} | {timestamp} | {model}\n")
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
    model: str
) -> None:
    """Convenience function to log an LLM interaction."""
    logger = get_session_logger(session_id, world_id)
    logger.log_interaction(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        raw_response=raw_response,
        parsed_response=parsed_response,
        model=model
    )

