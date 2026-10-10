"""Serve public site files only; never mount the repository root."""
from fastapi import HTTPException
from fastapi.responses import FileResponse
from .config import PROJECT_ROOT

PAGES = {'index.html', 'history.html', 'roles.html', 'facial.html', 'music.html', 'video.html', 'gallery.html', 'about.html'}
ASSET_DIRS = {'css', 'js', 'images', 'audio', 'media'}
EXTENSIONS = {'.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.mp3', '.wav', '.ogg', '.mp4', '.webm', '.woff', '.woff2', '.ttf'}

def public_file(path: str):
    parts = path.split('/')
    if not path:
        path, parts = 'index.html', ['index.html']
    allowed = path in PAGES or (parts[0] in ASSET_DIRS and len(parts) > 1)
    if not allowed or any(p.startswith('.') or p in ('', '..') or '\\' in p for p in parts):
        raise HTTPException(404)
    target = (PROJECT_ROOT / path).resolve()
    if PROJECT_ROOT not in target.parents or not target.is_file():
        raise HTTPException(404)
    if path not in PAGES and target.suffix.lower() not in EXTENSIONS:
        raise HTTPException(404)
    return FileResponse(target, headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
