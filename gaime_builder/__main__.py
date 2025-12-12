#!/usr/bin/env python3
"""
GAIME World Builder TUI
A terminal interface for creating and managing game worlds.
"""
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import click

@click.command()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--worlds-dir', type=click.Path(exists=True, file_okay=False), 
              default=None, help='Path to worlds directory')
def main(debug: bool, worlds_dir: str | None):
    """Launch the GAIME World Builder TUI."""
    from gaime_builder.app import WorldBuilderApp
    
    app = WorldBuilderApp(debug=debug, worlds_dir=worlds_dir)
    app.run()


if __name__ == "__main__":
    main()

