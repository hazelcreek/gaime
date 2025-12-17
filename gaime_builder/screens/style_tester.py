"""
Style Tester Screen - Generate images for a location across all style presets.

Features:
- Select a world and location
- Generate the location's main image using every available style preset
- Save images to a dedicated directory (not in world folders)
- Images named as "location_preset.png"
- Includes promptlogs subfolder for debugging
- Hash-based outdated image detection
- "Regenerate missing/outdated" button
- Selection support for "force regenerate selected" styles
"""
import asyncio
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Select, Static,
    ProgressBar, DataTable
)
from textual.worker import Worker, WorkerState, get_current_worker

from gaime_builder.core.tasks import StyleTestHashTracker


# Default output directory for style tests (relative to workspace root)
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "style_test_output"


class StyleTesterScreen(Screen):
    """Screen for testing all style presets against a single location."""

    # Store column keys for later reference
    check_column_key: str = ""
    status_column_key: str = ""
    image_column_key: str = ""

    CSS = """
    #style-tester-container {
        padding: 2;
        width: 100%;
        height: 100%;
    }

    #style-tester-panel {
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

    #world-select, #location-select {
        width: 100%;
        margin: 1 0;
    }

    #presets-table {
        height: 14;
        margin: 1 0;
    }

    .button-row {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    .button-row Button {
        margin-right: 1;
    }

    #progress-section {
        margin-top: 1;
        padding: 1;
        background: $surface;
        border: round $primary-lighten-2;
    }

    #batch-status {
        margin-bottom: 1;
        color: $text;
    }

    #current-preset {
        color: $secondary;
        margin-bottom: 1;
    }

    #output-info {
        color: $text-muted;
        margin-top: 1;
    }

    .status-outdated {
        color: $warning;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("a", "select_all", "Select All"),
        ("n", "select_none", "Select None"),
        ("r", "regenerate_outdated", "Regen Outdated"),
        ("f5", "refresh_status", "Refresh"),
    ]

    def __init__(self):
        super().__init__()
        self._current_world_id: Optional[str] = None
        self._current_location_id: Optional[str] = None
        self._current_location_name: Optional[str] = None
        self._active_worker: Optional[Worker] = None
        self._preset_statuses: dict[str, str] = {}  # preset_name -> generation status
        self._selected_presets: set[str] = set()  # Selected presets for force regeneration
        self._hash_tracker: Optional[StyleTestHashTracker] = None

    def compose(self) -> ComposeResult:
        """Create style tester UI."""
        yield Header()

        with Container(id="style-tester-container"):
            with Vertical(id="style-tester-panel"):
                yield Static("[bold]🎨 Style Tester[/]", classes="panel-title")

                yield Static(
                    "[dim]Generate images for a location using all available style presets. "
                    "⚠️ = outdated, ✗ = missing. "
                    "Press [bold]r[/] to regenerate missing/outdated.[/]",
                    classes="info-text"
                )

                yield Select(
                    id="world-select",
                    prompt="1. Select a world...",
                    options=[]
                )

                yield Select(
                    id="location-select",
                    prompt="2. Select a location...",
                    options=[],
                    disabled=True
                )

                yield Static("[bold]Style Presets:[/]", classes="info-text")
                yield DataTable(id="presets-table")

                with Horizontal(classes="button-row"):
                    yield Button("🔄 Generate All", id="generate", variant="primary", disabled=True)
                    yield Button("⚠️ Regen Missing/Outdated", id="regenerate-outdated", variant="warning", disabled=True)
                    yield Button("✨ Regen Selected", id="regenerate-selected", variant="success", disabled=True)
                    yield Button("Cancel", id="cancel", variant="error", disabled=True)

                with Horizontal(classes="button-row"):
                    yield Button("🔃 Refresh Status", id="refresh-status", variant="default")
                    yield Button("Back", id="back", variant="default")

                with Vertical(id="progress-section"):
                    yield Static("", id="batch-status")
                    yield Static("", id="current-preset")
                    yield ProgressBar(id="style-progress", total=100)
                    yield Static("", id="output-info")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize screen on mount."""
        # Initialize hash tracker
        self._hash_tracker = StyleTestHashTracker(self.app.worlds_dir, DEFAULT_OUTPUT_DIR)
        await self.load_worlds()
        await self.load_presets_table()

    async def load_worlds(self) -> None:
        """Load available worlds into the world selector."""
        from gaime_builder.core.world_generator import WorldGenerator

        generator = WorldGenerator(self.app.worlds_dir)
        worlds = generator.list_worlds()

        world_select = self.query_one("#world-select", Select)
        options = [(w["name"], w["id"]) for w in worlds]
        world_select.set_options(options)

    async def load_presets_table(self) -> None:
        """Load all available style presets into the table."""
        from gaime_builder.core.style_loader import get_presets

        presets = get_presets()
        preset_names = sorted(presets.list_presets())

        table = self.query_one("#presets-table", DataTable)
        # Capture column keys for later cell updates - with selection checkbox and image status
        col_keys = table.add_columns("✓", "Preset", "Status", "Image")
        self.check_column_key = col_keys[0]
        self.status_column_key = col_keys[2]
        self.image_column_key = col_keys[3]
        table.cursor_type = "row"

        for preset_name in preset_names:
            preset_data = presets.get_preset(preset_name)
            display_name = preset_data.get("name", preset_name) if preset_data else preset_name
            self._preset_statuses[preset_name] = "idle"
            # Image status will be updated when location is selected
            table.add_row(" ", display_name, "", "[dim]-[/]", key=preset_name)

    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle selector changes."""
        if event.select.id == "world-select" and event.value:
            self._current_world_id = str(event.value)
            await self.load_locations(self._current_world_id)

            # Enable location selector
            location_select = self.query_one("#location-select", Select)
            location_select.disabled = False

            # Disable generate until location is selected
            self.query_one("#generate", Button).disabled = True
            self.query_one("#regenerate-outdated", Button).disabled = True
            self.query_one("#regenerate-selected", Button).disabled = True

            # Reset preset image statuses
            await self._reset_preset_image_statuses()

        elif event.select.id == "location-select" and event.value:
            self._current_location_id = str(event.value)

            # Get location name for output folder
            from gaime_builder.core.world_generator import WorldGenerator
            generator = WorldGenerator(self.app.worlds_dir)
            locations = generator.get_world_locations(self._current_world_id)
            for loc in locations:
                if loc["id"] == self._current_location_id:
                    self._current_location_name = loc["name"]
                    break

            # Enable generate buttons
            self.query_one("#generate", Button).disabled = False
            self.query_one("#regenerate-outdated", Button).disabled = False

            # Update output info
            output_dir = self._get_output_dir()
            output_info = self.query_one("#output-info", Static)
            output_info.update(f"[dim]Output: {output_dir}[/]")

            # Clear selection and refresh all statuses (reload presets + recalculate hashes)
            self._selected_presets.clear()
            await self._refresh_all_statuses()

    async def _reset_preset_image_statuses(self) -> None:
        """Reset all preset image statuses to default."""
        table = self.query_one("#presets-table", DataTable)
        for row_key in table.rows:
            table.update_cell(row_key, self.image_column_key, "[dim]-[/]")
            table.update_cell(row_key, self.check_column_key, " ")
        self._selected_presets.clear()

    async def _update_all_preset_statuses(self) -> None:
        """Update image status for all presets based on hash tracking."""
        if not self._current_world_id or not self._current_location_id or not self._hash_tracker:
            return

        from gaime_builder.core.style_loader import get_presets

        presets = get_presets()
        preset_names = sorted(presets.list_presets())

        table = self.query_one("#presets-table", DataTable)

        for preset_name in preset_names:
            status = self._hash_tracker.get_preset_status(
                self._current_world_id,
                self._current_location_id,
                preset_name
            )

            # Build status display
            if not status["has_image"]:
                image_display = "[red]✗ Missing[/]"
            elif status["is_outdated"]:
                image_display = "[yellow]⚠️ Outdated[/]"
            else:
                image_display = "[green]✓[/]"

            # Find the row and update
            for row_key in table.rows:
                if str(row_key.value) == preset_name:
                    table.update_cell(row_key, self.image_column_key, image_display)
                    break

    async def _refresh_all_statuses(self, show_notification: bool = False) -> None:
        """
        Refresh all status information by reloading presets and recalculating hashes.

        This forces a full refresh from disk, catching:
        - Modified style preset YAML files
        - Modified world/location YAML files
        - New or deleted image files

        Args:
            show_notification: If True, show a notification when refresh completes.
        """
        from gaime_builder.core.style_loader import get_presets

        # Reload style presets from disk (clears cache)
        presets = get_presets()
        presets.reload()

        # Recreate hash tracker to ensure fresh state
        self._hash_tracker = StyleTestHashTracker(self.app.worlds_dir, DEFAULT_OUTPUT_DIR)

        # Update status display
        await self._update_all_preset_statuses()

        if show_notification:
            self.notify("Status refreshed from disk", severity="information")

    async def load_locations(self, world_id: str) -> None:
        """Load locations for the selected world."""
        from gaime_builder.core.world_generator import WorldGenerator

        generator = WorldGenerator(self.app.worlds_dir)
        locations = generator.get_world_locations(world_id)

        location_select = self.query_one("#location-select", Select)
        options = [(loc["name"], loc["id"]) for loc in locations]
        location_select.set_options(options)

    def _get_output_dir(self) -> Path:
        """Get the output directory for the current test."""
        if self._current_world_id and self._current_location_id:
            return DEFAULT_OUTPUT_DIR / self._current_world_id / self._current_location_id
        return DEFAULT_OUTPUT_DIR

    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()

    def action_select_all(self) -> None:
        """Select all presets."""
        from gaime_builder.core.style_loader import get_presets

        presets = get_presets()
        preset_names = presets.list_presets()
        self._selected_presets = set(preset_names)
        self._refresh_table_selection()
        self._update_regenerate_selected_button()

    def action_select_none(self) -> None:
        """Deselect all presets."""
        self._selected_presets.clear()
        self._refresh_table_selection()
        self._update_regenerate_selected_button()

    def action_regenerate_outdated(self) -> None:
        """Trigger regeneration of missing/outdated images."""
        self.query_one("#regenerate-outdated", Button).press()

    def action_refresh_status(self) -> None:
        """Trigger refresh of preset statuses."""
        self.query_one("#refresh-status", Button).press()

    def _refresh_table_selection(self) -> None:
        """Refresh checkmarks in table."""
        table = self.query_one("#presets-table", DataTable)
        for row_key in table.rows:
            preset_name = str(row_key.value)
            check = "✓" if preset_name in self._selected_presets else " "
            table.update_cell(row_key, self.check_column_key, check)

    def _update_regenerate_selected_button(self) -> None:
        """Enable/disable regenerate selected button based on selection."""
        has_selection = len(self._selected_presets) > 0
        has_location = self._current_world_id and self._current_location_id
        self.query_one("#regenerate-selected", Button).disabled = not (has_selection and has_location)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle preset selection on row click."""
        preset_name = str(event.row_key.value)

        if preset_name in self._selected_presets:
            self._selected_presets.remove(preset_name)
        else:
            self._selected_presets.add(preset_name)

        self._refresh_table_selection()
        self._update_regenerate_selected_button()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "generate":
            await self.start_generation(force_all=True)
        elif event.button.id == "regenerate-outdated":
            await self.start_generation(only_outdated=True)
        elif event.button.id == "regenerate-selected":
            await self.start_generation(selected_only=True)
        elif event.button.id == "cancel":
            self._cancel_generation()
        elif event.button.id == "refresh-status":
            await self._refresh_all_statuses(show_notification=True)

    def _cancel_generation(self) -> None:
        """Cancel the current generation batch."""
        if self._active_worker:
            self._active_worker.cancel()
            self.notify("Cancelling generation...", severity="warning")

    def _set_generation_controls(self, running: bool) -> None:
        """Enable/disable controls based on running state."""
        self.query_one("#generate", Button).disabled = running
        self.query_one("#regenerate-outdated", Button).disabled = running
        self.query_one("#regenerate-selected", Button).disabled = running
        self.query_one("#cancel", Button).disabled = not running
        self.query_one("#world-select", Select).disabled = running
        self.query_one("#location-select", Select).disabled = running

    def _update_preset_status(self, preset_name: str, status: str) -> None:
        """Update the generation status display for a preset in the table."""
        self._preset_statuses[preset_name] = status

        table = self.query_one("#presets-table", DataTable)

        status_display = {
            "idle": "",
            "pending": "[dim]⏳ Pending[/]",
            "generating": "[yellow]🔄 Generating...[/]",
            "done": "[green]✓ Done[/]",
            "error": "[red]✗ Error[/]",
            "skipped": "[dim]Skipped[/]",
        }.get(status, status)

        # Find the row and update status column using stored column key
        for row_key in table.rows:
            if str(row_key.value) == preset_name:
                table.update_cell(row_key, self.status_column_key, status_display)
                break

    def _reset_preset_statuses(self, preset_names: list[str] | None = None) -> None:
        """Reset generation statuses to pending for specified presets (or all)."""
        from gaime_builder.core.style_loader import get_presets

        table = self.query_one("#presets-table", DataTable)

        if preset_names is None:
            presets = get_presets()
            preset_names = list(presets.list_presets())

        for row_key in table.rows:
            preset_name = str(row_key.value)
            if preset_name in preset_names:
                self._preset_statuses[preset_name] = "pending"
                table.update_cell(row_key, self.status_column_key, "[dim]⏳ Pending[/]")
            else:
                # Mark others as skipped if we're doing selective generation
                if preset_names:
                    self._preset_statuses[preset_name] = "idle"
                    table.update_cell(row_key, self.status_column_key, "")

    async def start_generation(
        self,
        force_all: bool = False,
        only_outdated: bool = False,
        selected_only: bool = False
    ) -> None:
        """Start the batch generation process."""
        if not self._current_world_id or not self._current_location_id:
            self.notify("Please select a world and location first", severity="warning")
            return

        if selected_only and not self._selected_presets:
            self.notify("Please select at least one preset", severity="warning")
            return

        from gaime_builder.core.style_loader import get_presets

        presets = get_presets()
        all_preset_names = sorted(presets.list_presets())

        # Determine which presets to process
        if force_all:
            target_presets = all_preset_names
            batch_name = "Generate All Styles"
        elif only_outdated:
            # Get presets that need generation
            needs_gen = self._hash_tracker.get_presets_needing_generation(
                self._current_world_id,
                self._current_location_id,
                all_preset_names
            )
            if not needs_gen:
                self.notify("All style images are up to date!", severity="information")
                return
            target_presets = [item["preset_name"] for item in needs_gen]
            batch_name = f"Regenerate {len(target_presets)} Missing/Outdated"
        else:  # selected_only
            target_presets = sorted(self._selected_presets)
            batch_name = f"Regenerate {len(target_presets)} Selected"

        # Reset statuses for target presets
        self._reset_preset_statuses(target_presets)

        # Update controls
        self._set_generation_controls(running=True)

        # Start worker
        self._active_worker = self.run_worker(
            self._generate_styles_worker(target_presets, batch_name),
            name="style_test_generation",
            exclusive=True,
        )

    async def _generate_styles_worker(
        self,
        target_presets: list[str],
        batch_name: str
    ) -> dict[str, bool]:
        """
        Background worker to generate images for specified style presets.

        Args:
            target_presets: List of preset names to generate
            batch_name: Display name for progress

        Returns dict mapping preset name to success/failure.
        """
        from gaime_builder.core.style_loader import resolve_style
        from gaime_builder.core.image_generator import ImageGenerator
        import yaml

        worker = get_current_worker()
        results = {}
        total = len(target_presets)

        # Load world data
        world_path = self.app.worlds_dir / self._current_world_id
        locations_yaml = world_path / "locations.yaml"
        world_yaml = world_path / "world.yaml"
        npcs_yaml = world_path / "npcs.yaml"
        items_yaml = world_path / "items.yaml"

        # Load world metadata
        theme = "fantasy"
        tone = "atmospheric"

        if world_yaml.exists():
            with open(world_yaml) as f:
                world_data = yaml.safe_load(f) or {}
                theme = world_data.get("theme", theme)
                tone = world_data.get("tone", tone)

        # Load locations
        locations = {}
        if locations_yaml.exists():
            with open(locations_yaml) as f:
                locations = yaml.safe_load(f) or {}

        loc_data = locations.get(self._current_location_id, {})
        loc_name = loc_data.get("name", self._current_location_id)
        atmosphere = loc_data.get("atmosphere", "")

        # Load NPCs and items for context
        npcs_data = {}
        if npcs_yaml.exists():
            with open(npcs_yaml) as f:
                npcs_data = yaml.safe_load(f) or {}

        items_data = {}
        if items_yaml.exists():
            with open(items_yaml) as f:
                items_data = yaml.safe_load(f) or {}

        # Build location context
        image_gen = ImageGenerator(self.app.worlds_dir)
        context = image_gen._build_location_context(
            self._current_location_id, loc_data, locations, npcs_data, items_data
        )

        # Setup output directory
        output_dir = self._get_output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Update progress display
        self._update_progress_display(0.0, batch_name, "Starting...")

        for i, preset_name in enumerate(target_presets):
            if worker.is_cancelled:
                self._update_preset_status(preset_name, "idle")
                break

            # Update status
            self._update_preset_status(preset_name, "generating")

            progress = i / total
            self._update_progress_display(progress, batch_name, f"Generating: {preset_name}")

            try:
                # Resolve style for this preset
                style_block = resolve_style(preset_name)

                # Generate image with this style
                await image_gen.generate_location_image(
                    location_id=f"{self._current_location_id}_{preset_name}",
                    location_name=loc_name,
                    atmosphere=atmosphere,
                    theme=theme,
                    tone=tone,
                    output_dir=output_dir,
                    context=context,
                    style_block=style_block
                )

                # Compute and save hash metadata
                prompt_hash = self._hash_tracker.compute_preset_hash(
                    self._current_world_id,
                    self._current_location_id,
                    preset_name
                )
                self._hash_tracker.update_metadata(
                    self._current_world_id,
                    self._current_location_id,
                    preset_name,
                    prompt_hash
                )

                results[preset_name] = True
                self._update_preset_status(preset_name, "done")

            except Exception as e:
                results[preset_name] = False
                self._update_preset_status(preset_name, "error")
                self.notify(f"Error generating {preset_name}: {str(e)[:50]}", severity="error")

            # Small delay between generations to avoid rate limiting
            await asyncio.sleep(1.0)

        # Final progress update
        success_count = sum(1 for r in results.values() if r)
        final_msg = f"Completed: {success_count}/{len(results)} successful"

        self._update_progress_display(1.0, batch_name, final_msg)

        return results

    def _update_progress_display(self, progress: float, task_name: str, message: str) -> None:
        """Update the progress display widgets."""
        batch_status = self.query_one("#batch-status", Static)
        current_preset = self.query_one("#current-preset", Static)
        progress_bar = self.query_one("#style-progress", ProgressBar)

        batch_status.update(f"[cyan]{task_name}[/]")
        current_preset.update(f"[bold]{int(progress * 100)}%[/] - {message}")
        progress_bar.update(progress=int(progress * 100))

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.worker.name == "style_test_generation":
            # Check if worker finished (success, error, or cancelled)
            finished_states = {WorkerState.SUCCESS, WorkerState.ERROR, WorkerState.CANCELLED}
            if event.state in finished_states:
                self._set_generation_controls(running=False)
                self._active_worker = None

                output_dir = self._get_output_dir()

                # Refresh preset statuses to show updated image states
                if self._current_world_id and self._current_location_id:
                    self.run_worker(
                        self._update_all_preset_statuses(),
                        name="refresh_statuses"
                    )

                if event.state == WorkerState.SUCCESS:
                    self.notify(
                        f"Style test complete! Images saved to:\n{output_dir}",
                        severity="information",
                        timeout=10
                    )
                elif event.state == WorkerState.CANCELLED:
                    self.notify("Style test cancelled", severity="warning")
                elif event.state == WorkerState.ERROR:
                    self.notify(
                        f"Style test failed: {event.worker.error}",
                        severity="error"
                    )
