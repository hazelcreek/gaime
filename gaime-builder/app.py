"""
GAIME World Builder - Main TUI Application

A terminal interface for creating and managing text adventure game worlds.
"""
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding

from gaime_builder.screens.main_menu import MainMenuScreen


class WorldBuilderApp(App):
    """GAIME World Builder TUI Application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    .title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }
    
    .subtitle {
        text-align: center;
        color: $text-muted;
        margin: 0 0 2 0;
    }
    
    .error {
        color: $error;
        margin: 1 0;
    }
    
    .success {
        color: $success;
        margin: 1 0;
    }
    
    .info-text {
        color: $text-muted;
        margin: 1 0;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
        Binding("escape", "go_back", "Back"),
    ]
    
    TITLE = "GAIME World Builder"
    SUB_TITLE = "AI-Powered Text Adventure Authoring"
    
    def __init__(self, debug: bool = False, worlds_dir: Optional[str] = None):
        """Initialize the app.
        
        Args:
            debug: Enable debug mode
            worlds_dir: Optional path to worlds directory (defaults to ./worlds)
        """
        super().__init__()
        self.debug = debug
        
        if worlds_dir:
            self.worlds_dir = Path(worlds_dir)
        else:
            # Default to worlds/ in the project root
            self.worlds_dir = Path(__file__).parent.parent / "worlds"
        
        if not self.worlds_dir.exists():
            self.worlds_dir.mkdir(parents=True, exist_ok=True)
    
    def on_mount(self) -> None:
        """Show main menu on startup."""
        self.push_screen(MainMenuScreen())
    
    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark
    
    def action_go_back(self) -> None:
        """Go back to previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()

