"""
Create World Screen - Form for generating new game worlds.
"""
import asyncio

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Input, TextArea, 
    Label, Static, ProgressBar, Select
)


class CreateWorldScreen(Screen):
    """Screen for creating a new world."""
    
    CSS = """
    #form-container {
        padding: 2;
        width: 100%;
        height: 100%;
    }
    
    #form-panel {
        width: 100%;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 2;
        margin: 1;
    }
    
    .form-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .form-row {
        width: 100%;
        height: auto;
        margin: 1 0;
    }
    
    .form-row Label {
        width: 20;
        margin-right: 1;
    }
    
    .form-row Input {
        width: 1fr;
    }
    
    .form-row Select {
        width: 1fr;
    }
    
    #description {
        height: 6;
        width: 1fr;
    }
    
    .button-row {
        width: 100%;
        height: auto;
        margin-top: 2;
    }
    
    .button-row Button {
        margin-right: 2;
    }
    
    #progress-panel {
        width: 100%;
        height: auto;
        background: $panel;
        border: thick $success;
        padding: 2;
        margin: 1;
        display: none;
    }
    
    #progress-panel.visible {
        display: block;
    }
    
    #progress-status {
        margin-top: 1;
    }
    
    .error-text {
        color: $error;
        margin: 1 0;
    }
    
    .success-text {
        color: $success;
        margin: 1 0;
    }
    """
    
    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create world form UI."""
        yield Header()
        
        with Container(id="form-container"):
            with Vertical(id="form-panel"):
                yield Static("[bold]🌍 Create New World[/]", classes="form-title")
                
                with Horizontal(classes="form-row"):
                    yield Label("Description:")
                    yield TextArea(
                        id="description",
                        tab_behavior="focus",
                    )
                
                with Horizontal(classes="form-row"):
                    yield Label("Theme (optional):")
                    yield Input(
                        id="theme",
                        placeholder="horror, sci-fi, fantasy, mystery, etc."
                    )
                
                with Horizontal(classes="form-row"):
                    yield Label("Visual Style:")
                    yield Select(
                        id="style-preset",
                        options=[],
                        prompt="Select style preset..."
                    )
                
                with Horizontal(classes="form-row"):
                    yield Label("Locations:")
                    yield Input(
                        id="num_locations",
                        placeholder="6",
                        value="6"
                    )
                
                with Horizontal(classes="form-row"):
                    yield Label("NPCs:")
                    yield Input(
                        id="num_npcs",
                        placeholder="3",
                        value="3"
                    )
                
                with Horizontal(classes="button-row"):
                    yield Button("✨ Generate World", id="generate", variant="primary")
                    yield Button("Cancel", id="cancel", variant="default")
            
            with Vertical(id="progress-panel"):
                yield Static("[bold]Generating world...[/]", id="progress-title")
                yield ProgressBar(id="progress-bar", total=100)
                yield Static("", id="progress-status")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Focus description on mount and load style presets."""
        self.query_one("#description", TextArea).focus()
        self._load_style_presets()
    
    def _load_style_presets(self) -> None:
        """Load available style presets into the select widget."""
        from gaime_builder.core.style_loader import get_presets
        
        presets = get_presets()
        preset_names = sorted(presets.list_presets())
        
        # Build options with friendly display names
        options = []
        for name in preset_names:
            preset_data = presets.get_preset(name)
            display_name = preset_data.get("name", name) if preset_data else name
            options.append((f"{display_name} ({name})", name))
        
        style_select = self.query_one("#style-preset", Select)
        style_select.set_options(options)
        
        # Set default to classic-fantasy
        if "classic-fantasy" in preset_names:
            style_select.value = "classic-fantasy"
    
    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "generate":
            await self.generate_world()
    
    async def generate_world(self) -> None:
        """Generate world using AI."""
        # Get form values
        description = self.query_one("#description", TextArea).text.strip()
        theme = self.query_one("#theme", Input).value.strip() or None
        style_select = self.query_one("#style-preset", Select)
        style_preset = str(style_select.value) if style_select.value else "classic-fantasy"
        
        try:
            num_locations = int(self.query_one("#num_locations", Input).value or "6")
        except ValueError:
            num_locations = 6
        
        try:
            num_npcs = int(self.query_one("#num_npcs", Input).value or "3")
        except ValueError:
            num_npcs = 3
        
        if not description:
            self.notify("Please enter a world description", severity="error")
            return
        
        # Show progress
        progress_panel = self.query_one("#progress-panel")
        progress_panel.add_class("visible")
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        status = self.query_one("#progress-status", Static)
        
        # Disable buttons
        self.query_one("#generate", Button).disabled = True
        self.query_one("#cancel", Button).disabled = True
        
        def update_progress(progress: float, message: str):
            progress_bar.update(progress=int(progress * 100))
            status.update(f"[cyan]{message}[/]")
        
        try:
            from gaime_builder.core.world_generator import WorldGenerator
            
            generator = WorldGenerator(self.app.worlds_dir)
            
            result = await generator.generate(
                prompt=description,
                theme=theme,
                num_locations=num_locations,
                num_npcs=num_npcs,
                progress_callback=update_progress
            )
            
            # Save the world with style preset
            world_id = result["world_id"]
            update_progress(0.95, f"Saving world '{world_id}'...")
            
            generator.save_world(world_id, result, style_preset=style_preset)
            
            progress_bar.update(progress=100)
            status.update(f"[green]✓ World '{world_id}' created successfully![/]")
            
            self.notify(f"World '{world_id}' created!", severity="information")
            
            # Offer to generate images
            await asyncio.sleep(1.5)
            self.app.pop_screen()
            
        except Exception as e:
            status.update(f"[red]✗ Error: {str(e)}[/]")
            self.notify(f"Error: {str(e)}", severity="error")
        finally:
            # Re-enable buttons
            self.query_one("#generate", Button).disabled = False
            self.query_one("#cancel", Button).disabled = False

