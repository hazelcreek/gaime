"""
Style Tester Screen - Generate images for a location across all style presets.

Features:
- Select a world and location
- Generate the location's main image using every available style preset
- Save images to a dedicated directory (not in world folders)
- Images named as "location_preset.png"
- Includes promptlogs subfolder for debugging
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
from textual.worker import Worker, get_current_worker


# Default output directory for style tests (relative to workspace root)
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "style_test_output"


class StyleTesterScreen(Screen):
    """Screen for testing all style presets against a single location."""
    
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
    """
    
    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]
    
    def __init__(self):
        super().__init__()
        self._current_world_id: Optional[str] = None
        self._current_location_id: Optional[str] = None
        self._current_location_name: Optional[str] = None
        self._active_worker: Optional[Worker] = None
        self._preset_statuses: dict[str, str] = {}  # preset_name -> status
    
    def compose(self) -> ComposeResult:
        """Create style tester UI."""
        yield Header()
        
        with Container(id="style-tester-container"):
            with Vertical(id="style-tester-panel"):
                yield Static("[bold]🎨 Style Tester[/]", classes="panel-title")
                
                yield Static(
                    "[dim]Generate images for a location using all available style presets. "
                    "Images are saved to a dedicated output directory for comparison.[/]",
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
                    yield Button("🚀 Generate All Styles", id="generate", variant="primary", disabled=True)
                    yield Button("Cancel", id="cancel", variant="error", disabled=True)
                    yield Button("Back", id="back", variant="default")
                
                with Vertical(id="progress-section"):
                    yield Static("", id="batch-status")
                    yield Static("", id="current-preset")
                    yield ProgressBar(id="style-progress", total=100)
                    yield Static("", id="output-info")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize screen on mount."""
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
        table.add_columns("Preset", "Status")
        table.cursor_type = "none"
        
        for preset_name in preset_names:
            preset_data = presets.get_preset(preset_name)
            display_name = preset_data.get("name", preset_name) if preset_data else preset_name
            self._preset_statuses[preset_name] = "pending"
            table.add_row(display_name, "[dim]Pending[/]", key=preset_name)
    
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
            
            # Enable generate button
            self.query_one("#generate", Button).disabled = False
            
            # Update output info
            output_dir = self._get_output_dir()
            output_info = self.query_one("#output-info", Static)
            output_info.update(f"[dim]Output: {output_dir}[/]")
    
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
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "generate":
            await self.start_generation()
        elif event.button.id == "cancel":
            self._cancel_generation()
    
    def _cancel_generation(self) -> None:
        """Cancel the current generation batch."""
        if self._active_worker:
            self._active_worker.cancel()
            self.notify("Cancelling generation...", severity="warning")
    
    def _set_generation_controls(self, running: bool) -> None:
        """Enable/disable controls based on running state."""
        self.query_one("#generate", Button).disabled = running
        self.query_one("#cancel", Button).disabled = not running
        self.query_one("#world-select", Select).disabled = running
        self.query_one("#location-select", Select).disabled = running
    
    def _update_preset_status(self, preset_name: str, status: str) -> None:
        """Update the status display for a preset in the table."""
        self._preset_statuses[preset_name] = status
        
        table = self.query_one("#presets-table", DataTable)
        
        status_display = {
            "pending": "[dim]Pending[/]",
            "generating": "[yellow]🔄 Generating...[/]",
            "done": "[green]✓ Done[/]",
            "error": "[red]✗ Error[/]",
        }.get(status, status)
        
        # Find the row and update status column
        for row_key in table.rows:
            if str(row_key.value) == preset_name:
                table.update_cell(row_key, "Status", status_display)
                break
    
    def _reset_preset_statuses(self) -> None:
        """Reset all preset statuses to pending."""
        table = self.query_one("#presets-table", DataTable)
        for row_key in table.rows:
            preset_name = str(row_key.value)
            self._preset_statuses[preset_name] = "pending"
            table.update_cell(row_key, "Status", "[dim]Pending[/]")
    
    async def start_generation(self) -> None:
        """Start the batch generation process."""
        if not self._current_world_id or not self._current_location_id:
            self.notify("Please select a world and location first", severity="warning")
            return
        
        # Reset statuses
        self._reset_preset_statuses()
        
        # Update controls
        self._set_generation_controls(running=True)
        
        # Start worker
        self._active_worker = self.run_worker(
            self._generate_all_styles_worker(),
            name="style_test_generation",
            exclusive=True,
        )
    
    async def _generate_all_styles_worker(self) -> dict[str, bool]:
        """
        Background worker to generate images for all style presets.
        
        Returns dict mapping preset name to success/failure.
        """
        from gaime_builder.core.style_loader import get_presets, resolve_style
        from gaime_builder.core.image_generator import (
            ImageGenerator, LocationContext, ExitInfo, ItemInfo,
            _save_prompt_markdown, get_image_prompt
        )
        from gaime_builder.core.world_generator import WorldGenerator
        import yaml
        
        worker = get_current_worker()
        results = {}
        
        # Get preset list
        presets = get_presets()
        preset_names = sorted(presets.list_presets())
        total = len(preset_names)
        
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
        self.call_from_thread(
            self._update_progress_display,
            0.0, f"Testing {total} style presets", f"Starting..."
        )
        
        for i, preset_name in enumerate(preset_names):
            if worker.is_cancelled:
                self.call_from_thread(
                    self._update_preset_status,
                    preset_name, "pending"
                )
                break
            
            # Update status
            self.call_from_thread(
                self._update_preset_status,
                preset_name, "generating"
            )
            
            progress = i / total
            self.call_from_thread(
                self._update_progress_display,
                progress, f"Testing {total} style presets", f"Generating: {preset_name}"
            )
            
            try:
                # Resolve style for this preset
                style_block = resolve_style(preset_name)
                
                # Generate image with this style
                output_filename = f"{self._current_location_id}_{preset_name}.png"
                
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
                
                # Rename the generated file to match our naming convention
                # (generate_location_image creates location_id.png)
                generated_path = output_dir / f"{self._current_location_id}_{preset_name}.png"
                final_path = output_dir / output_filename
                
                # The file is already correctly named since we used the combined ID
                
                results[preset_name] = True
                self.call_from_thread(
                    self._update_preset_status,
                    preset_name, "done"
                )
                
            except Exception as e:
                results[preset_name] = False
                self.call_from_thread(
                    self._update_preset_status,
                    preset_name, "error"
                )
                self.call_from_thread(
                    self.notify,
                    f"Error generating {preset_name}: {str(e)[:50]}",
                    severity="error"
                )
            
            # Small delay between generations to avoid rate limiting
            await asyncio.sleep(1.0)
        
        # Final progress update
        success_count = sum(1 for r in results.values() if r)
        final_msg = f"Completed: {success_count}/{len(results)} successful"
        
        self.call_from_thread(
            self._update_progress_display,
            1.0, "Style Test Complete", final_msg
        )
        
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
            if event.state.is_finished:
                self._set_generation_controls(running=False)
                self._active_worker = None
                
                output_dir = self._get_output_dir()
                
                if event.state == event.state.SUCCESS:
                    self.notify(
                        f"Style test complete! Images saved to:\n{output_dir}",
                        severity="information",
                        timeout=10
                    )
                elif event.state == event.state.CANCELLED:
                    self.notify("Style test cancelled", severity="warning")
                elif event.state == event.state.ERROR:
                    self.notify(
                        f"Style test failed: {event.worker.error}",
                        severity="error"
                    )
