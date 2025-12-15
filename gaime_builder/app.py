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
        Binding("d", "toggle_dark", "Dark Mode"),
        Binding("escape", "go_back", "Back"),
        Binding("?", "show_help", "Help"),
        Binding("1", "go_create", "Create World", show=False),
        Binding("2", "go_images", "Generate Images", show=False),
        Binding("3", "go_style_tester", "Style Tester", show=False),
        Binding("4", "go_manage", "Manage Worlds", show=False),
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
        self.debug_mode = debug  # Renamed to avoid conflict with Textual's debug property
        
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
    
    # action_toggle_dark is inherited from Textual's App class
    
    def action_go_back(self) -> None:
        """Go back to previous screen."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
    
    def action_show_help(self) -> None:
        """Show help information."""
        self.notify(
            "Keyboard: [1] Create World | [2] Images | [3] Style Tester | [4] Manage | [d] Dark Mode | [q] Quit",
            title="Help",
            timeout=5
        )
    
    def action_go_create(self) -> None:
        """Navigate to create world screen."""
        from gaime_builder.screens.create_world import CreateWorldScreen
        # Pop to root and push create screen
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(CreateWorldScreen())
    
    def action_go_images(self) -> None:
        """Navigate to images screen."""
        from gaime_builder.screens.manage_images import ManageImagesScreen
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(ManageImagesScreen())
    
    def action_go_style_tester(self) -> None:
        """Navigate to style tester screen."""
        from gaime_builder.screens.style_tester import StyleTesterScreen
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(StyleTesterScreen())
    
    def action_go_manage(self) -> None:
        """Navigate to manage worlds screen."""
        from gaime_builder.screens.manage_worlds import ManageWorldsScreen
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(ManageWorldsScreen())

