"""Fixed, packaged UI resources. Never serve arbitrary filesystem paths."""
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse

ICONS = frozenset({"arrow-right", "chevron-down", "file-text", "shield", "user",
                   "book-open", "bar-chart-2", "alert-circle", "clock", "check-circle",
                   "home", "upload", "shopping-cart", "coffee", "truck", "log-out"})
ASSETS = {
    "friday-jade-orb.png": "image/png",  # Historical bookmarked asset.
    "friday-orb.png": "image/png",
    "friday-soft-studio-buddy.png": "image/png",
    "friday-brand.png": "image/png",
    "friday-team-logo.png": "image/png",
    "friday-windowsill.png": "image/png",
    "friday-inter.ttf": "font/ttf",
    **{"friday-icon-" + icon + ".svg": "image/svg+xml" for icon in ICONS},
}


def friday_asset(name: str) -> FileResponse:
    media_type = ASSETS.get(name)
    if media_type is None:
        raise HTTPException(404, "Unknown Friday asset")
    return FileResponse(Path(__file__).parent / "assets" / name, media_type=media_type)
