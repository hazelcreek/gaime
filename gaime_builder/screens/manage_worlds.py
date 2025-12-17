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
        overflow-y: auto;
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
        min-height: 10;
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

    .spoiler-warning {
        color: $error;
        text-style: bold;
        margin: 1 0;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("r", "refresh", "Refresh"),
        ("s", "view_spoilers", "Spoilers"),
    ]

    def compose(self) -> ComposeResult:
        """Create world management UI."""
        yield Header()

        with Container(id="worlds-container"):
            with Vertical(id="worlds-panel"):
                yield Static("[bold]📁 Manage Worlds[/]", classes="panel-title")

                yield Static(
                    "[dim]Select a world to view details. Press [bold]r[/bold] to refresh, [bold]s[/bold] for spoilers.[/]",
                    classes="info-text"
                )

                yield DataTable(id="worlds-table")

                with Horizontal(classes="button-row"):
                    yield Button("✅ Validate", id="validate", variant="primary")
                    yield Button("🔍 View Spoilers", id="spoilers", variant="warning")
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

    async def action_view_spoilers(self) -> None:
        """View spoilers for the selected world."""
        await self.view_spoilers_selected()

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

    def _get_selected_world_id(self) -> str | None:
        """Get the world_id of the currently selected row."""
        table = self.query_one("#worlds-table", DataTable)

        if table.cursor_row is None:
            return None

        cursor_row = table.cursor_row
        row_keys = list(table.rows.keys())
        if cursor_row < len(row_keys):
            return str(row_keys[cursor_row].value)
        return None

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

        # Check if spoilers exist
        spoilers_path = world_path / "spoilers.md"
        spoilers_status = "[green]Available[/]" if spoilers_path.exists() else "[dim]Not available[/]"

        text = f"""[bold]{name}[/]

[cyan]Theme:[/] {theme}
[cyan]Tone:[/] {tone}
[cyan]Premise:[/] {premise}...

[cyan]Starting Location:[/] {starting_loc}
[cyan]Victory Location:[/] {victory_loc}

[cyan]Spoilers:[/] {spoilers_status}

[dim]Path: {world_path}[/]"""

        details.update(text)

    async def view_spoilers_selected(self) -> None:
        """View spoilers for the selected world."""
        world_id = self._get_selected_world_id()

        if not world_id:
            self.notify("Please select a world first", severity="warning")
            return

        from gaime_builder.core.world_generator import WorldGenerator

        generator = WorldGenerator(self.app.worlds_dir)
        spoilers = generator.get_world_spoilers(world_id)

        details = self.query_one("#details-content", Static)

        if spoilers is None:
            details.update(
                f"[yellow]No spoilers available for '{world_id}'[/]\n\n"
                "[dim]This world was created before the two-pass generation system was added, "
                "or the spoilers.md file was deleted.[/]"
            )
            self.notify("No spoilers available for this world", severity="warning")
            return

        # Format spoilers for display (convert markdown to rich text)
        formatted = self._format_spoilers_for_display(spoilers)
        details.update(formatted)
        self.notify("Showing spoilers - contains puzzle solutions!", severity="warning")

    def _format_spoilers_for_display(self, spoilers_md: str) -> str:
        """Convert spoilers.md content to rich text for display."""
        lines = []
        lines.append("[bold red]⚠️ SPOILERS - PUZZLE SOLUTIONS BELOW ⚠️[/]\n")

        for line in spoilers_md.split("\n"):
            # Convert markdown headers to rich text
            if line.startswith("# "):
                lines.append(f"[bold cyan]{line[2:]}[/]")
            elif line.startswith("## "):
                lines.append(f"\n[bold yellow]{line[3:]}[/]")
            elif line.startswith("### "):
                lines.append(f"[bold]{line[4:]}[/]")
            elif line.startswith("**") and line.endswith("**"):
                # Bold text
                lines.append(f"[bold]{line[2:-2]}[/]")
            elif line.startswith("- "):
                lines.append(f"  • {line[2:]}")
            elif line.startswith("---"):
                lines.append("[dim]─" * 40 + "[/]")
            elif line.strip():
                lines.append(line)
            else:
                lines.append("")

        return "\n".join(lines)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "refresh":
            await self.action_refresh()
        elif event.button.id == "validate":
            await self.validate_selected()
        elif event.button.id == "spoilers":
            await self.view_spoilers_selected()

    async def validate_selected(self) -> None:
        """Validate the selected world."""
        world_id = self._get_selected_world_id()

        if not world_id:
            self.notify("Please select a world to validate", severity="warning")
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
