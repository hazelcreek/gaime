"""
Manage Images Screen - Generate and regenerate world images.
"""
import asyncio
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Button, Select, Static, 
    ProgressBar, DataTable, Checkbox
)


class ManageImagesScreen(Screen):
    """Screen for managing world images."""
    
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
    
    #progress-section {
        margin-top: 1;
    }
    
    #image-status {
        margin-top: 1;
    }
    """
    
    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("a", "select_all", "Select All"),
        ("n", "select_none", "Select None"),
    ]
    
    selected_locations: set[str] = set()
    
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
                    "[dim]Select locations to regenerate. Variants (for dynamic NPCs) are included automatically.[/]",
                    classes="info-text"
                )
                
                yield DataTable(id="locations-table")
                
                with Horizontal(classes="button-row"):
                    yield Button("🔄 Generate All", id="generate-all", variant="primary")
                    yield Button("✨ Regenerate Selected", id="regenerate-selected", variant="success")
                    yield Button("Back", id="back", variant="default")
                
                with Vertical(id="progress-section"):
                    yield ProgressBar(id="image-progress", total=100)
                    yield Static("", id="image-status")
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Load worlds on mount."""
        await self.load_worlds()
        
        # Setup table
        table = self.query_one("#locations-table", DataTable)
        table.add_columns("✓", "Location", "Has Image", "Variants")
        table.cursor_type = "row"
    
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
    
    def refresh_table_selection(self) -> None:
        """Refresh checkmarks in table."""
        table = self.query_one("#locations-table", DataTable)
        for row_key in table.rows:
            loc_id = str(row_key.value)
            check = "✓" if loc_id in self.selected_locations else " "
            # Update the first column
            table.update_cell(row_key, table.columns[0].key, check)
    
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
            await self.load_locations(str(event.value))
    
    async def load_locations(self, world_id: str) -> None:
        """Load locations for the selected world."""
        from gaime_builder.core.world_generator import WorldGenerator
        from gaime_builder.core.image_generator import ImageGenerator
        
        generator = WorldGenerator(self.app.worlds_dir)
        image_gen = ImageGenerator(self.app.worlds_dir)
        
        locations = generator.get_world_locations(world_id)
        existing_images = image_gen.list_location_images(world_id)
        
        table = self.query_one("#locations-table", DataTable)
        table.clear()
        self.selected_locations.clear()
        
        for loc in locations:
            loc_id = loc["id"]
            loc_name = loc["name"]
            
            image_info = existing_images.get(loc_id, {})
            has_image = "✓" if image_info else "✗"
            variant_count = image_info.get("variant_count", 0) if image_info else 0
            variants_text = str(variant_count) if variant_count > 0 else "-"
            
            table.add_row(" ", loc_name, has_image, variants_text, key=loc_id)
    
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
            await self.generate_all_images()
        elif event.button.id == "regenerate-selected":
            await self.regenerate_selected_images()
    
    async def generate_all_images(self) -> None:
        """Generate all images for the selected world."""
        world_select = self.query_one("#world-select", Select)
        if not world_select.value:
            self.notify("Please select a world first", severity="warning")
            return
        
        world_id = str(world_select.value)
        
        progress_bar = self.query_one("#image-progress", ProgressBar)
        status = self.query_one("#image-status", Static)
        
        # Disable buttons
        self.query_one("#generate-all", Button).disabled = True
        self.query_one("#regenerate-selected", Button).disabled = True
        
        def update_progress(progress: float, message: str):
            progress_bar.update(progress=int(progress * 100))
            status.update(f"[cyan]{message}[/]")
        
        try:
            from gaime_builder.core.image_generator import ImageGenerator
            
            image_gen = ImageGenerator(self.app.worlds_dir)
            
            status.update("[cyan]Starting image generation...[/]")
            progress_bar.update(progress=0)
            
            results = await image_gen.generate_all_images(
                world_id=world_id,
                progress_callback=update_progress
            )
            
            success_count = sum(1 for r in results.values() if r is not None)
            total_count = len(results)
            
            progress_bar.update(progress=100)
            status.update(f"[green]✓ Generated {success_count}/{total_count} images[/]")
            
            self.notify(f"Generated {success_count}/{total_count} images", severity="information")
            
            # Reload table
            await self.load_locations(world_id)
            
        except Exception as e:
            status.update(f"[red]✗ Error: {str(e)}[/]")
            self.notify(f"Error: {str(e)}", severity="error")
        finally:
            self.query_one("#generate-all", Button).disabled = False
            self.query_one("#regenerate-selected", Button).disabled = False
    
    async def regenerate_selected_images(self) -> None:
        """Regenerate images for selected locations."""
        if not self.selected_locations:
            self.notify("Please select at least one location", severity="warning")
            return
        
        world_select = self.query_one("#world-select", Select)
        if not world_select.value:
            self.notify("Please select a world first", severity="warning")
            return
        
        world_id = str(world_select.value)
        location_ids = list(self.selected_locations)
        
        progress_bar = self.query_one("#image-progress", ProgressBar)
        status = self.query_one("#image-status", Static)
        
        # Disable buttons
        self.query_one("#generate-all", Button).disabled = True
        self.query_one("#regenerate-selected", Button).disabled = True
        
        try:
            from gaime_builder.core.image_generator import ImageGenerator
            
            image_gen = ImageGenerator(self.app.worlds_dir)
            
            total = len(location_ids)
            success_count = 0
            
            for i, loc_id in enumerate(location_ids):
                progress = (i / total)
                progress_bar.update(progress=int(progress * 100))
                status.update(f"[cyan]Regenerating {loc_id} (with variants)...[/]")
                
                try:
                    await image_gen.regenerate_location(
                        world_id=world_id,
                        location_id=loc_id,
                        include_variants=True
                    )
                    success_count += 1
                except Exception as e:
                    self.notify(f"Failed: {loc_id} - {e}", severity="warning")
            
            progress_bar.update(progress=100)
            status.update(f"[green]✓ Regenerated {success_count}/{total} location(s)[/]")
            
            self.notify(f"Regenerated {success_count}/{total} images", severity="information")
            
            # Reload table
            await self.load_locations(world_id)
            
        except Exception as e:
            status.update(f"[red]✗ Error: {str(e)}[/]")
            self.notify(f"Error: {str(e)}", severity="error")
        finally:
            self.query_one("#generate-all", Button).disabled = False
            self.query_one("#regenerate-selected", Button).disabled = False

