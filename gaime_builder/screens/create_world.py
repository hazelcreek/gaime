"""
Create World Screen - Form for generating new game worlds.

Uses Textual workers for background LLM processing to keep UI responsive.
"""
import asyncio
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Input, TextArea,
    Label, Static, ProgressBar, Select, Checkbox
)
from textual.worker import Worker, WorkerState, get_current_worker


class CreateWorldScreen(Screen):
    """Screen for creating a new world."""

    CSS = """
    #form-container {
        padding: 2;
        width: 100%;
        height: 100%;
        overflow-y: auto;
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

    .checkbox-row {
        width: 100%;
        height: auto;
        margin: 1 0;
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

    #result-panel {
        width: 100%;
        height: auto;
        background: $surface;
        border: thick $secondary;
        padding: 2;
        margin: 1;
        display: none;
    }

    #result-panel.visible {
        display: block;
    }

    .result-title {
        text-style: bold;
        color: $secondary;
        margin-bottom: 1;
    }

    #pitch-content {
        margin: 1 0;
        padding: 1;
        background: $panel;
    }

    #spoiler-content {
        margin: 1 0;
        padding: 1;
        background: $error-darken-3;
        display: none;
    }

    #spoiler-content.visible {
        display: block;
    }

    .spoiler-warning {
        color: $error;
        text-style: bold;
        margin-bottom: 1;
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

    def __init__(self):
        super().__init__()
        self._generation_result: dict | None = None
        self._active_worker: Optional[Worker] = None

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
                    yield Button("⏹️ Stop", id="stop-generation", variant="error", disabled=True)
                    yield Button("Cancel", id="cancel", variant="default")

            with Vertical(id="progress-panel"):
                yield Static("[bold]Generating world...[/]", id="progress-title")
                yield ProgressBar(id="progress-bar", total=100)
                yield Static("", id="progress-status")

            with Vertical(id="result-panel"):
                yield Static("[bold]✓ World Generated![/]", classes="result-title")
                yield Static("", id="world-name-display")
                yield Static("[bold]About this world:[/]")
                yield Static("", id="pitch-content")

                with Horizontal(classes="checkbox-row"):
                    yield Checkbox("Show Spoilers (puzzle solutions, secrets)", id="show-spoilers")

                with Vertical(id="spoiler-content"):
                    yield Static("⚠️ SPOILERS BELOW", classes="spoiler-warning")
                    yield Static("", id="spoiler-text")

                with Horizontal(classes="button-row"):
                    yield Button("Done", id="done", variant="primary")
                    yield Button("Create Another", id="create-another", variant="default")

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

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes."""
        if event.checkbox.id == "show-spoilers":
            spoiler_content = self.query_one("#spoiler-content")
            if event.value:
                spoiler_content.add_class("visible")
            else:
                spoiler_content.remove_class("visible")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "cancel":
            self.app.pop_screen()
        elif event.button.id == "generate":
            self.start_world_generation()
        elif event.button.id == "stop-generation":
            self._stop_generation()
        elif event.button.id == "done":
            self.app.pop_screen()
        elif event.button.id == "create-another":
            self._reset_form()

    def _stop_generation(self) -> None:
        """Stop the active world generation."""
        if self._active_worker:
            self._active_worker.cancel()
            self.notify("Stopping generation...", severity="warning")

    def _reset_form(self) -> None:
        """Reset the form for creating another world."""
        # Hide result panel
        self.query_one("#result-panel").remove_class("visible")
        self.query_one("#progress-panel").remove_class("visible")

        # Clear form
        self.query_one("#description", TextArea).clear()
        self.query_one("#theme", Input).value = ""

        # Reset checkbox
        self.query_one("#show-spoilers", Checkbox).value = False
        self.query_one("#spoiler-content").remove_class("visible")

        # Clear result data
        self._generation_result = None

        # Focus description
        self.query_one("#description", TextArea).focus()

    def _format_design_brief(self, brief: dict) -> str:
        """Format the design brief for display."""
        lines = []

        # Puzzle Threads
        if "puzzle_threads" in brief:
            lines.append("[bold]Puzzle Threads:[/]")
            for thread in brief["puzzle_threads"]:
                name = thread.get("name", "Unknown")
                is_primary = " (Primary)" if thread.get("is_primary") else ""
                gate = thread.get("gate_type", "")
                lines.append(f"  • {name}{is_primary} [{gate}]")
                for step in thread.get("steps", []):
                    lines.append(f"    → {step}")
            lines.append("")

        # Navigation Loop
        if "navigation_loop" in brief:
            loop = brief["navigation_loop"]
            lines.append("[bold]Shortcut:[/]")
            lines.append(f"  {loop.get('description', '')}")
            lines.append(f"  Unlocked by: {loop.get('unlocked_by', '')}")
            lines.append("")

        # Optional Secrets
        if "optional_secrets" in brief:
            lines.append("[bold]Optional Secrets:[/]")
            for secret in brief["optional_secrets"]:
                lines.append(f"  • {secret.get('name', '')}: {secret.get('description', '')}")
            lines.append("")

        # Victory
        if "victory_condition" in brief:
            victory = brief["victory_condition"]
            lines.append("[bold]Victory:[/]")
            lines.append(f"  Location: {victory.get('location', '')}")
            if victory.get("required_items"):
                lines.append(f"  Items needed: {', '.join(victory['required_items'])}")

        return "\n".join(lines)

    def start_world_generation(self) -> None:
        """Start world generation in a background worker."""
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

        # Disable/enable buttons
        self.query_one("#generate", Button).disabled = True
        self.query_one("#stop-generation", Button).disabled = False
        self.query_one("#cancel", Button).disabled = True

        # Start background worker
        self._active_worker = self.run_worker(
            self._generate_world_worker(
                description=description,
                theme=theme,
                style_preset=style_preset,
                num_locations=num_locations,
                num_npcs=num_npcs,
            ),
            name="world_generation",
            exclusive=True,
        )

    async def _generate_world_worker(
        self,
        description: str,
        theme: str | None,
        style_preset: str,
        num_locations: int,
        num_npcs: int,
    ) -> dict:
        """
        Background worker for world generation.

        This runs the LLM calls without blocking the UI.
        """
        from gaime_builder.core.world_generator import WorldGenerator

        worker = get_current_worker()

        def update_progress(progress: float, message: str):
            """Update progress directly (safe since async worker runs in main thread)."""
            self._update_generation_progress(progress, message)

        generator = WorldGenerator(self.app.worlds_dir)

        # Generate the world
        result = await generator.generate(
            prompt=description,
            theme=theme,
            num_locations=num_locations,
            num_npcs=num_npcs,
            progress_callback=update_progress
        )

        if worker.is_cancelled:
            raise asyncio.CancelledError("Generation cancelled by user")

        # Save the world with style preset
        world_id = result["world_id"]
        update_progress(0.95, f"Saving world '{world_id}'...")

        generator.save_world(world_id, result, style_preset=style_preset)

        update_progress(1.0, f"World '{world_id}' created successfully!")

        return result

    def _update_generation_progress(self, progress: float, message: str) -> None:
        """Update the progress display (called from main thread)."""
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        status = self.query_one("#progress-status", Static)

        progress_bar.update(progress=int(progress * 100))
        status.update(f"[cyan]{message}[/]")

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.worker.name == "world_generation":
            if event.worker.is_finished:
                self._active_worker = None

                # Re-enable buttons
                self.query_one("#generate", Button).disabled = False
                self.query_one("#stop-generation", Button).disabled = True
                self.query_one("#cancel", Button).disabled = False

                if event.state == WorkerState.SUCCESS:
                    # Get the result from the worker
                    result = event.worker.result
                    self._show_generation_result(result)
                elif event.state == WorkerState.CANCELLED:
                    self.notify("World generation cancelled", severity="warning")
                    self.query_one("#progress-panel").remove_class("visible")
                elif event.state == WorkerState.ERROR:
                    error_msg = str(event.worker.error) if event.worker.error else "Unknown error"
                    self.query_one("#progress-status", Static).update(f"[red]✗ Error: {error_msg}[/]")
                    self.notify(f"Generation failed: {error_msg}", severity="error")

    def _show_generation_result(self, result: dict) -> None:
        """Show the generation result panel."""
        self._generation_result = result

        world_id = result.get("world_id", "unknown")
        world_name = result.get("world_name", world_id)

        # Update result panel content
        self.query_one("#world-name-display", Static).update(
            f"[bold cyan]{world_name}[/] ({world_id})"
        )

        pitch = result.get("spoiler_free_pitch", "No description available.")
        self.query_one("#pitch-content", Static).update(pitch)

        # Format and set spoiler content
        brief = result.get("design_brief", {})
        if brief:
            spoiler_text = self._format_design_brief(brief)
            self.query_one("#spoiler-text", Static).update(spoiler_text)
        else:
            self.query_one("#spoiler-text", Static).update("No design brief available.")

        # Hide progress, show result
        self.query_one("#progress-panel").remove_class("visible")
        self.query_one("#result-panel").add_class("visible")

        self.notify(f"World '{world_id}' created!", severity="information")
