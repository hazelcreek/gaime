"""
Manage Images Screen - Generate and regenerate world images.

Features:
- Background processing using Textual workers (non-blocking UI)
- Per-location status tracking (pending/generating/done/error)
- Hash-based outdated image detection
- "Regenerate missing/outdated" button
"""
import asyncio
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Select, Static, 
    ProgressBar, DataTable, Checkbox, Label
)
from textual.worker import Worker, WorkerState, get_current_worker

from gaime_builder.core.tasks import TaskQueue, TaskStatus


class ManageImagesScreen(Screen):
    """Screen for managing world images with background processing."""
    
    # Store column keys for later reference
    check_column_key: str = ""
    status_column_key: str = ""
    
    CSS = """
    #images-container {
        padding: 2;
        width: 100%;
        height: 100%;
    }
    
    #images-panel {
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
    
    #world-select {
        width: 100%;
        margin: 1 0;
    }
    
    #locations-table {
        height: 18;
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
    
    #queue-status {
        margin-bottom: 1;
        color: $text;
    }
    
    #current-task {
        color: $secondary;
        margin-bottom: 1;
    }
    
    #image-status {
        margin-top: 1;
    }
    
    .status-pending {
        color: $text-muted;
    }
    
    .status-generating {
        color: $warning;
    }
    
    .status-done {
        color: $success;
    }
    
    .status-error {
        color: $error;
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
    ]
    
    def __init__(self):
        super().__init__()
        self.selected_locations: set[str] = set()
        self.task_queue = TaskQueue()
        self._current_world_id: Optional[str] = None
        self._location_statuses: dict[str, dict] = {}  # loc_id -> {status, message}
        self._active_worker: Optional[Worker] = None
    
    def compose(self) -> ComposeResult:
        """Create image management UI."""
        yield Header()
        
        with Container(id="images-container"):
            with Vertical(id="images-panel"):
                yield Static("[bold]🖼️ Manage World Images[/]", classes="panel-title")
                
                yield Select(
                    id="world-select",
                    prompt="Select a world...",
                    options=[]
                )
                
                yield Static(
                    "[dim]Select locations to regenerate. "
                    "⚠️ = outdated, ✗ = missing. "
                    "Press [bold]r[/] to regenerate missing/outdated.[/]",
                    classes="info-text"
                )
                
                yield DataTable(id="locations-table")
                
                with Horizontal(classes="button-row"):
                    yield Button("🔄 Generate All", id="generate-all", variant="primary")
                    yield Button("⚠️ Regen Missing/Outdated", id="regenerate-outdated", variant="warning")
                    yield Button("✨ Regenerate Selected", id="regenerate-selected", variant="success")
                    yield Button("Cancel", id="cancel-generation", variant="error", disabled=True)
                
                with Horizontal(classes="button-row"):
                    yield Button("Back", id="back", variant="default")
                
                with Vertical(id="progress-section"):
                    yield Static("", id="queue-status")
                    yield Static("", id="current-task")
                    yield ProgressBar(id="image-progress", total=100)
                    yield Static("", id="image-status")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Load worlds on mount."""
        await self.load_worlds()
        
        # Setup table
        table = self.query_one("#locations-table", DataTable)
        col_keys = table.add_columns("✓", "Location", "Status", "Image", "Variants")
        self.check_column_key = col_keys[0]
        self.status_column_key = col_keys[2]
        table.cursor_type = "row"
        
        # Add task queue listener
        self.task_queue.add_listener(self._on_task_update)
    
    def _on_task_update(self, task_id: str, task) -> None:
        """Handle task state changes from the queue."""
        # This runs in the main thread, safe to update UI directly
        self._update_task_display()
    
    def _update_task_display(self) -> None:
        """Update the task progress display."""
        active = self.task_queue.get_active_task()
        pending = self.task_queue.get_pending_tasks()
        
        queue_status = self.query_one("#queue-status", Static)
        current_task = self.query_one("#current-task", Static)
        progress_bar = self.query_one("#image-progress", ProgressBar)
        status = self.query_one("#image-status", Static)
        
        if active:
            queue_status.update(f"[cyan]Queue: {len(pending)} pending[/]")
            current_task.update(f"[bold]{active.name}[/]: {active.progress.message}")
            progress_bar.update(progress=int(active.progress.current * 100))
            
            if active.progress.sub_task:
                status.update(f"[dim]{active.progress.sub_task}[/]")
            else:
                status.update("")
        elif pending:
            queue_status.update(f"[cyan]Queue: {len(pending)} pending, waiting to start...[/]")
            current_task.update("")
            status.update("")
        else:
            queue_status.update("[dim]No active tasks[/]")
            current_task.update("")
            status.update("")
    
    def action_go_back(self) -> None:
        """Go back to previous screen."""
        self.app.pop_screen()
    
    def action_select_all(self) -> None:
        """Select all locations."""
        table = self.query_one("#locations-table", DataTable)
        for row_key in table.rows:
            self.selected_locations.add(str(row_key.value))
        self.refresh_table_selection()
    
    def action_select_none(self) -> None:
        """Deselect all locations."""
        self.selected_locations.clear()
        self.refresh_table_selection()
    
    def action_regenerate_outdated(self) -> None:
        """Trigger regeneration of missing/outdated images."""
        self.query_one("#regenerate-outdated", Button).press()
    
    def refresh_table_selection(self) -> None:
        """Refresh checkmarks in table."""
        table = self.query_one("#locations-table", DataTable)
        for row_key in table.rows:
            loc_id = str(row_key.value)
            check = "✓" if loc_id in self.selected_locations else " "
            table.update_cell(row_key, self.check_column_key, check)
    
    def _update_location_status_in_table(self, loc_id: str, status: str, message: str = "") -> None:
        """Update the status column for a location in the table."""
        self._location_statuses[loc_id] = {"status": status, "message": message}
        
        table = self.query_one("#locations-table", DataTable)
        
        status_display = {
            "pending": "[dim]⏳ Pending[/]",
            "generating": "[yellow]🔄 Generating...[/]",
            "variants": "[yellow]🔄 Variants...[/]",
            "done": "[green]✓ Done[/]",
            "error": f"[red]✗ Error[/]",
            "idle": "",
        }.get(status, status)
        
        # Find the row for this location and update status column
        for row_key in table.rows:
            if str(row_key.value) == loc_id:
                table.update_cell(row_key, self.status_column_key, status_display)
                break
    
    async def load_worlds(self) -> None:
        """Load available worlds."""
        from gaime_builder.core.world_generator import WorldGenerator
        
        generator = WorldGenerator(self.app.worlds_dir)
        worlds = generator.list_worlds()
        
        world_select = self.query_one("#world-select", Select)
        options = [(w["name"], w["id"]) for w in worlds]
        world_select.set_options(options)
    
    async def on_select_changed(self, event: Select.Changed) -> None:
        """Handle world selection change."""
        if event.select.id == "world-select" and event.value:
            self._current_world_id = str(event.value)
            await self.load_locations(self._current_world_id)
    
    async def load_locations(self, world_id: str) -> None:
        """Load locations for the selected world with status info."""
        from gaime_builder.core.world_generator import WorldGenerator
        from gaime_builder.core.image_generator import ImageGenerator
        
        generator = WorldGenerator(self.app.worlds_dir)
        image_gen = ImageGenerator(self.app.worlds_dir)
        
        locations = generator.get_world_locations(world_id)
        
        table = self.query_one("#locations-table", DataTable)
        table.clear()
        self.selected_locations.clear()
        self._location_statuses.clear()
        
        for loc in locations:
            loc_id = loc["id"]
            loc_name = loc["name"]
            
            # Get detailed status including outdated detection
            status = image_gen.get_location_image_status(world_id, loc_id)
            
            # Build status display
            if not status["has_image"]:
                image_display = "[red]✗ Missing[/]"
            elif status["is_outdated"]:
                image_display = f"[yellow]⚠️ Outdated[/]"
            else:
                image_display = "[green]✓[/]"
            
            # Variants display
            if status["variant_count"] > 0:
                if status["variants_outdated"] > 0:
                    variants_text = f"{status['variant_count']} ([yellow]{status['variants_outdated']} outdated[/])"
                else:
                    variants_text = f"[green]{status['variant_count']}[/]"
            else:
                variants_text = "[dim]-[/]"
            
            # Task status (initially empty)
            task_status = ""
            
            table.add_row(" ", loc_name, task_status, image_display, variants_text, key=loc_id)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Toggle location selection on row click."""
        loc_id = str(event.row_key.value)
        
        if loc_id in self.selected_locations:
            self.selected_locations.remove(loc_id)
        else:
            self.selected_locations.add(loc_id)
        
        self.refresh_table_selection()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "generate-all":
            await self.start_generation_batch(force_all=True)
        elif event.button.id == "regenerate-outdated":
            await self.start_generation_batch(only_outdated=True)
        elif event.button.id == "regenerate-selected":
            await self.start_generation_batch(selected_only=True)
        elif event.button.id == "cancel-generation":
            self._cancel_generation()
    
    def _cancel_generation(self) -> None:
        """Cancel the current generation batch."""
        if self._active_worker:
            self._active_worker.cancel()
            self.notify("Cancelling generation...", severity="warning")
    
    async def start_generation_batch(
        self,
        force_all: bool = False,
        only_outdated: bool = False,
        selected_only: bool = False
    ) -> None:
        """Start a batch image generation using a background worker."""
        if not self._current_world_id:
            self.notify("Please select a world first", severity="warning")
            return
        
        if selected_only and not self.selected_locations:
            self.notify("Please select at least one location", severity="warning")
            return
        
        # Determine which locations to process
        from gaime_builder.core.image_generator import ImageGenerator
        from gaime_builder.core.world_generator import WorldGenerator
        
        image_gen = ImageGenerator(self.app.worlds_dir)
        generator = WorldGenerator(self.app.worlds_dir)
        
        all_locations = generator.get_world_locations(self._current_world_id)
        
        # Build list of what to regenerate
        # Each item: {"location_id": str, "smart": bool}
        # smart=True means use regenerate_outdated (only regen what's needed)
        # smart=False means force full regeneration
        regen_list = []
        
        if force_all:
            # Force regenerate everything
            for loc in all_locations:
                regen_list.append({
                    "location_id": loc["id"],
                    "smart": False,  # Force full regen
                })
            batch_name = "Generate All Images"
        elif only_outdated:
            # Smart regeneration - only what's needed
            needs_gen = image_gen.get_locations_needing_generation(self._current_world_id)
            if not needs_gen:
                self.notify("All images are up to date!", severity="information")
                return
            for loc in needs_gen:
                regen_list.append({
                    "location_id": loc["location_id"],
                    "smart": True,  # Only regen what's outdated
                })
            batch_name = f"Regenerate {len(needs_gen)} Missing/Outdated"
        else:
            # Selected - force regenerate selected locations
            for loc_id in self.selected_locations:
                regen_list.append({
                    "location_id": loc_id,
                    "smart": False,  # Force full regen of selected
                })
            batch_name = f"Regenerate {len(regen_list)} Selected"
        
        # Mark all locations as pending
        for item in regen_list:
            self._update_location_status_in_table(item["location_id"], "pending")
        
        # Disable/enable buttons
        self._set_generation_controls(running=True)
        
        # Start background worker
        self._active_worker = self.run_worker(
            self._generate_images_worker(
                self._current_world_id,
                regen_list,
                batch_name
            ),
            name="image_generation",
            exclusive=True,
        )
    
    def _set_generation_controls(self, running: bool) -> None:
        """Enable/disable generation controls based on running state."""
        self.query_one("#generate-all", Button).disabled = running
        self.query_one("#regenerate-outdated", Button).disabled = running
        self.query_one("#regenerate-selected", Button).disabled = running
        self.query_one("#cancel-generation", Button).disabled = not running
    
    async def _generate_images_worker(
        self,
        world_id: str,
        regen_list: list[dict],
        batch_name: str
    ) -> dict[str, bool]:
        """
        Background worker for image generation.
        
        Args:
            world_id: World to process
            regen_list: List of dicts with:
                - location_id: str
                - smart: bool - if True, use smart regeneration (only what's outdated)
            batch_name: Display name for progress
        
        This runs in a separate thread, keeping the UI responsive.
        """
        from gaime_builder.core.image_generator import ImageGenerator
        
        worker = get_current_worker()
        image_gen = ImageGenerator(self.app.worlds_dir)
        
        results = {}
        total = len(regen_list)
        
        # Update progress display
        self._update_progress_display(0.0, batch_name, f"Starting {total} location(s)...")
        
        for i, item in enumerate(regen_list):
            loc_id = item["location_id"]
            use_smart = item["smart"]
            
            if worker.is_cancelled:
                self._update_location_status_in_table(loc_id, "idle", "Cancelled")
                break
            
            # Update status to generating
            self._update_location_status_in_table(loc_id, "generating", "")
            
            progress = i / total
            self._update_progress_display(progress, batch_name, f"Processing {loc_id}...")
            
            try:
                # Define callbacks that update UI
                def progress_callback(prog: float, msg: str):
                    overall = (i + prog) / total
                    self._update_progress_display(overall, batch_name, msg)
                
                def location_callback(lid: str, status: str, msg: str):
                    self._update_location_status_in_table(lid, status, msg)
                
                if use_smart:
                    # Smart regeneration - only regenerate what's actually outdated
                    # This will skip base if only variants are outdated
                    await image_gen.regenerate_outdated(
                        world_id=world_id,
                        location_id=loc_id,
                        progress_callback=progress_callback
                    )
                else:
                    # Force full regeneration (base + all variants)
                    await image_gen.regenerate_location(
                        world_id=world_id,
                        location_id=loc_id,
                        include_variants=True,
                        progress_callback=progress_callback
                    )
                
                results[loc_id] = True
                self._update_location_status_in_table(loc_id, "done", "")
                
            except Exception as e:
                results[loc_id] = False
                self._update_location_status_in_table(loc_id, "error", str(e))
                self.notify(f"Error generating {loc_id}: {e}", severity="error")
            
            # Small delay between locations to avoid rate limiting
            await asyncio.sleep(0.5)
        
        # Finalize
        success_count = sum(1 for r in results.values() if r)
        final_msg = f"Completed: {success_count}/{len(results)} successful"
        
        self._update_progress_display(1.0, batch_name, final_msg)
        
        return results
    
    def _update_progress_display(self, progress: float, task_name: str, message: str) -> None:
        """Update the progress display widgets."""
        queue_status = self.query_one("#queue-status", Static)
        current_task = self.query_one("#current-task", Static)
        progress_bar = self.query_one("#image-progress", ProgressBar)
        status = self.query_one("#image-status", Static)
        
        queue_status.update(f"[cyan]{task_name}[/]")
        current_task.update(f"[bold]{int(progress * 100)}%[/]")
        progress_bar.update(progress=int(progress * 100))
        status.update(f"[dim]{message}[/]")
    
    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.worker.name == "image_generation":
            # Check if worker reached a terminal state
            terminal_states = {WorkerState.SUCCESS, WorkerState.CANCELLED, WorkerState.ERROR}
            if event.state in terminal_states:
                self._set_generation_controls(running=False)
                self._active_worker = None
                
                # Reload table to show updated status
                if self._current_world_id:
                    self.run_worker(
                        self.load_locations(self._current_world_id),
                        name="reload_locations"
                    )
                
                if event.state == WorkerState.SUCCESS:
                    self.notify("Image generation complete!", severity="information")
                elif event.state == WorkerState.CANCELLED:
                    self.notify("Image generation cancelled", severity="warning")
                elif event.state == event.state.ERROR:
                    self.notify(f"Image generation failed: {event.worker.error}", severity="error")
