"""
Manage Worlds Screen - View, validate, and manage existing worlds.
"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Static, DataTable
)


class ManageWorldsScreen(Screen):
    """Screen for managing existing worlds."""
    
    CSS = """
    #worlds-container {
        padding: 2;
        width: 100%;
        height: 100%;
    }
    
    #worlds-panel {
        width: 100%;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 2;
        margin: 1;
    }
    
    .panel-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .info-text {
        color: $text-muted;
        margin: 1 0;
    }
    
    #worlds-table {
        height: 15;
        margin: 1 0;
    }
    
    .button-row {
        width: 100%;
        height: auto;
        margin: 1 0;
    }
    
    .button-row Button {
        margin-right: 2;
    }
    
    #details-panel {
        width: 100%;
        height: auto;
        background: $surface;
        border: round $secondary;
        padding: 2;
        margin-top: 1;
    }
    
    #details-content {
        height: auto;
    }
    
    .detail-title {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }
    """
    
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("r", "refresh", "Refresh"),
    ]
    
    def compose(self) -> ComposeResult:
        """Create world management UI."""
        yield Header()
        
        with Container(id="worlds-container"):
            with Vertical(id="worlds-panel"):
                yield Static("[bold]📁 Manage Worlds[/]", classes="panel-title")
                
                yield Static(
                    "[dim]Select a world to view details or validate. Press [bold]r[/bold] to refresh.[/]",
                    classes="info-text"
                )
                
                yield DataTable(id="worlds-table")
                
                with Horizontal(classes="button-row"):
                    yield Button("✅ Validate", id="validate", variant="primary")
                    yield Button("🔄 Refresh", id="refresh", variant="default")
                    yield Button("Back", id="back", variant="default")
                
                with Vertical(id="details-panel"):
                    yield Static("[bold]World Details[/]", classes="detail-title")
                    yield Static("Select a world to see details", id="details-content")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Load worlds on mount."""
        # Setup table
        table = self.query_one("#worlds-table", DataTable)
        table.add_columns("World Name", "Theme", "Locations", "NPCs")
        table.cursor_type = "row"
        
        await self.load_worlds()
    
    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
    
    async def action_refresh(self) -> None:
        """Refresh world list."""
        await self.load_worlds()
        self.notify("World list refreshed", severity="information")
    
    async def load_worlds(self) -> None:
        """Load available worlds."""
        from gaime_builder.core.world_generator import WorldGenerator
        
        generator = WorldGenerator(self.app.worlds_dir)
        worlds = generator.list_worlds()
        
        table = self.query_one("#worlds-table", DataTable)
        table.clear()
        
        for world in worlds:
            world_id = world["id"]
            world_name = world["name"]
            theme = world.get("theme", "") or "-"
            
            # Count locations and NPCs
            locations = generator.get_world_locations(world_id)
            loc_count = len(locations)
            
            # Count NPCs (simplified)
            import yaml
            npcs_yaml = self.app.worlds_dir / world_id / "npcs.yaml"
            npc_count = 0
            if npcs_yaml.exists():
                with open(npcs_yaml) as f:
                    npcs = yaml.safe_load(f) or {}
                    npc_count = len(npcs)
            
            table.add_row(world_name, theme, str(loc_count), str(npc_count), key=world_id)
    
    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Show world details on row selection."""
        world_id = str(event.row_key.value)
        await self.show_world_details(world_id)
    
    async def show_world_details(self, world_id: str) -> None:
        """Display details for the selected world."""
        import yaml
        
        world_path = self.app.worlds_dir / world_id
        world_yaml = world_path / "world.yaml"
        
        details = self.query_one("#details-content", Static)
        
        if not world_yaml.exists():
            details.update(f"[red]World '{world_id}' not found[/]")
            return
        
        with open(world_yaml) as f:
            data = yaml.safe_load(f) or {}
        
        name = data.get("name", world_id)
        theme = data.get("theme", "Not specified")
        tone = data.get("tone", "Not specified")
        premise = data.get("premise", "No premise")[:200]
        
        player = data.get("player", {})
        starting_loc = player.get("starting_location", "Not set")
        
        victory = data.get("victory", {})
        victory_loc = victory.get("location", "Not set")
        
        text = f"""[bold]{name}[/]
        
[cyan]Theme:[/] {theme}
[cyan]Tone:[/] {tone}
[cyan]Premise:[/] {premise}...

[cyan]Starting Location:[/] {starting_loc}
[cyan]Victory Location:[/] {victory_loc}

[dim]Path: {world_path}[/]"""
        
        details.update(text)
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "refresh":
            await self.action_refresh()
        elif event.button.id == "validate":
            await self.validate_selected()
    
    async def validate_selected(self) -> None:
        """Validate the selected world."""
        table = self.query_one("#worlds-table", DataTable)
        
        if table.cursor_row is None:
            self.notify("Please select a world to validate", severity="warning")
            return
        
        row_key = table.get_row_at(table.cursor_row)
        if not row_key:
            return
        
        # Get world_id from cursor position
        cursor_row = table.cursor_row
        row_keys = list(table.rows.keys())
        if cursor_row < len(row_keys):
            world_id = str(row_keys[cursor_row].value)
        else:
            self.notify("Could not determine selected world", severity="error")
            return
        
        from gaime_builder.core.world_generator import WorldGenerator
        
        generator = WorldGenerator(self.app.worlds_dir)
        is_valid, messages = generator.validate_world(world_id)
        
        details = self.query_one("#details-content", Static)
        
        if is_valid and not messages:
            details.update(f"[green]✓ World '{world_id}' is valid![/]")
            self.notify(f"World '{world_id}' is valid!", severity="information")
        elif is_valid:
            # Has warnings but no errors
            warning_text = "\n".join(f"⚠️  {m}" for m in messages)
            details.update(f"[yellow]World '{world_id}' has warnings:[/]\n\n{warning_text}")
            self.notify(f"World has {len(messages)} warning(s)", severity="warning")
        else:
            error_text = "\n".join(f"❌ {m}" for m in messages)
            details.update(f"[red]World '{world_id}' has errors:[/]\n\n{error_text}")
            self.notify(f"World has errors", severity="error")

