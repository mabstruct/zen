from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OPAQUE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".svg", ".bmp", ".tiff", ".tif"}

MAGIC = {".pdf": b"%PDF", ".docx": b"PK", ".pptx": b"PK", ".xlsx": b"PK"}


@dataclass
class Extraction:
    status: str
    markdown: str
    title: str | None
    error: str | None = None


def extract(path: Path) -> Extraction:
    if path.suffix.lower() in OPAQUE_EXT:
        return Extraction("none", "", None)
    if path.suffix.lower() in {".md", ".txt"}:
        return Extraction("ok", path.read_text(encoding="utf-8", errors="replace"), None)
    try:
        magic = MAGIC.get(path.suffix.lower())
        if magic and not path.read_bytes().startswith(magic):
            return Extraction("failed", "", None, f"not a valid {path.suffix.lower()[1:]} file")
        from markitdown import MarkItDown

        result = MarkItDown(enable_plugins=False).convert(str(path))
        text = (result.markdown or "").strip()
        if not text:
            return Extraction("failed", "", result.title, "empty extraction")
        return Extraction("ok", text + "\n", result.title or None)
    except Exception as e:  # third-party boundary: every failure becomes a flagged companion
        return Extraction("failed", "", None, f"{type(e).__name__}: {e}")
