"""Local disk storage for generated images."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.config import OUTPUTS_DIR, ensure_outputs_dir


def _suffix_for_mime(mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if "jpeg" in mime or "jpg" in mime:
        return ".jpg"
    if "webp" in mime:
        return ".webp"
    return ".png"


class StorageService:
    """Write and list images under outputs/."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or OUTPUTS_DIR
        ensure_outputs_dir()
        if root is not None:
            self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prompt: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        self.root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        short = uuid4().hex[:8]
        suffix = _suffix_for_mime(mime_type)
        filename = f"gemini-{stamp}-{short}{suffix}"
        path = self.root / filename
        path.write_bytes(image_bytes)

        created_at = datetime.now(timezone.utc).isoformat()
        meta = {
            "id": filename,
            "filename": filename,
            "path": str(path.resolve()),
            "url": f"/api/outputs/{filename}",
            "mime_type": mime_type,
            "prompt": prompt,
            "model": model,
            "created_at": created_at,
            "size_bytes": len(image_bytes),
        }
        meta_path = path.with_suffix(path.suffix + ".json")
        try:
            import json

            meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except OSError:
            pass
        return meta

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.root.is_dir():
            return []
        images = [
            p
            for p in self.root.iterdir()
            if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        ]
        images.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        items: list[dict[str, Any]] = []
        for path in images[:limit]:
            items.append(self._item_from_path(path))
        return items

    def resolve(self, filename: str) -> Path | None:
        """Resolve a safe path under outputs/; reject traversal."""
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            return None
        path = (self.root / filename).resolve()
        try:
            path.relative_to(self.root.resolve())
        except ValueError:
            return None
        if not path.is_file():
            return None
        return path

    def _item_from_path(self, path: Path) -> dict[str, Any]:
        import json

        meta_path = path.with_suffix(path.suffix + ".json")
        if meta_path.is_file():
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                data.setdefault("url", f"/api/outputs/{path.name}")
                return data
            except (OSError, json.JSONDecodeError):
                pass
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(path.suffix.lower(), "image/png")
        return {
            "id": path.name,
            "filename": path.name,
            "path": str(path.resolve()),
            "url": f"/api/outputs/{path.name}",
            "mime_type": mime,
            "prompt": None,
            "model": None,
            "created_at": mtime.isoformat(),
            "size_bytes": path.stat().st_size,
        }
