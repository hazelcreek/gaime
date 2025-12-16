"""
Audio API endpoints.
Provides audio file discovery for the frontend.
"""

from fastapi import APIRouter
from pathlib import Path

router = APIRouter(prefix="/audio", tags=["audio"])

# Path to frontend public audio directory (relative to backend)
FRONTEND_AUDIO_PATH = (
    Path(__file__).parent.parent.parent.parent / "frontend" / "public" / "audio"
)


@router.get("/menu-tracks")
async def get_menu_tracks() -> dict:
    """
    Return a list of available menu music tracks.
    Scans frontend/public/audio/menu/ for .mp3 files.
    """
    menu_dir = FRONTEND_AUDIO_PATH / "menu"

    if not menu_dir.exists():
        return {"tracks": []}

    # Find all .mp3 files in the menu directory
    tracks = [
        f"/audio/menu/{f.name}"
        for f in menu_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".mp3"
    ]

    # Sort for consistent ordering (random selection happens on frontend)
    tracks.sort()

    return {"tracks": tracks}
