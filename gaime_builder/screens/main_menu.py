"""
Main Menu Screen - Entry point for the World Builder TUI.
"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Footer, Static


class MainMenuScreen(Screen):
    """Main menu with primary actions."""
    
    CSS = """
    #menu-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    
    #menu-panel {
        width: 60;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 2 4;
    }
    
    .menu-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }
    
    .menu-subtitle {
        text-align: center;
        color: $text-muted;
        margin: 0 0 2 0;
    }
    
    .menu-button {
        width: 100%;
        margin: 1 0;
    }
    
    #version-text {
        text-align: center;
        color: $text-disabled;
        margin-top: 2;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Create main menu UI."""
        yield Header()
        
        with Container(id="menu-container"):
            with Vertical(id="menu-panel"):
                yield Static("[bold cyan]🎮 GAIME World Builder[/]", classes="menu-title")
                yield Static("Create and manage text adventure worlds", classes="menu-subtitle")
                
                yield Button("🌍  Create New World", id="create", variant="primary", classes="menu-button")
                yield Button("🖼️  Generate Images", id="images", variant="success", classes="menu-button")
                yield Button("🎨  Style Tester", id="style-tester", variant="warning", classes="menu-button")
                yield Button("📁  Manage Worlds", id="manage", variant="default", classes="menu-button")
                yield Button("❌  Exit", id="exit", variant="error", classes="menu-button")
                
                yield Static("v0.1.0", id="version-text")
        
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "create":
            from gaime_builder.screens.create_world import CreateWorldScreen
            self.app.push_screen(CreateWorldScreen())
        elif event.button.id == "images":
            from gaime_builder.screens.manage_images import ManageImagesScreen
            self.app.push_screen(ManageImagesScreen())
        elif event.button.id == "style-tester":
            from gaime_builder.screens.style_tester import StyleTesterScreen
            self.app.push_screen(StyleTesterScreen())
        elif event.button.id == "manage":
            from gaime_builder.screens.manage_worlds import ManageWorldsScreen
            self.app.push_screen(ManageWorldsScreen())
        elif event.button.id == "exit":
            self.app.exit()

