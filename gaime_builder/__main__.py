#!/usr/bin/env python3
"""
GAIME World Builder TUI
A terminal interface for creating and managing game worlds.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import click


def setup_logging(debug: bool = False) -> Path:
    """Configure logging to both console and file.

    Returns:
        Path to the log file
    """
    # Create logs directory
    logs_dir = Path(__file__).parent.parent / "logs" / "builder"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = logs_dir / f"builder_{timestamp}.log"

    # Configure root logger
    log_level = logging.DEBUG if debug else logging.INFO

    # File handler - always verbose
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)

    # Console handler - respects debug flag (but we minimize this for TUI)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.ERROR)  # Only errors to console to not interfere with TUI
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Also configure litellm to be less noisy
    logging.getLogger("litellm").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    return log_file


@click.command()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--worlds-dir', type=click.Path(exists=True, file_okay=False),
              default=None, help='Path to worlds directory')
def main(debug: bool, worlds_dir: str | None):
    """Launch the GAIME World Builder TUI."""
    log_file = setup_logging(debug=debug)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("GAIME World Builder starting")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Worlds dir: {worlds_dir or 'default'}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 60)

    from gaime_builder.app import WorldBuilderApp

    app = WorldBuilderApp(debug=debug, worlds_dir=worlds_dir)
    app._log_file = log_file  # Store for access in screens

    try:
        app.run()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise
    finally:
        logger.info("GAIME World Builder shutdown")


if __name__ == "__main__":
    main()
