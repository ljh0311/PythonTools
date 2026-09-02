"""StorageService unit tests."""

from __future__ import annotations

from pathlib import Path

from backend.services.storage import StorageService


def test_save_and_list_recent(tmp_path: Path, png_bytes: bytes):
    store = StorageService(root=tmp_path / "out")
    meta = store.save(
        image_bytes=png_bytes,
        mime_type="image/png",
        prompt="a red square",
        model="gemini-3.1-flash-image",
    )
    assert meta["filename"].endswith(".png")
    assert meta["prompt"] == "a red square"
    assert meta["size_bytes"] == len(png_bytes)
    path = Path(meta["path"])
    assert path.is_file()
    assert path.read_bytes() == png_bytes

    items = store.list_recent(limit=10)
    assert len(items) == 1
    assert items[0]["id"] == meta["id"]
    assert items[0]["url"] == f"/api/outputs/{meta['filename']}"


def test_resolve_rejects_traversal(tmp_path: Path, png_bytes: bytes):
    store = StorageService(root=tmp_path / "out")
    meta = store.save(image_bytes=png_bytes, mime_type="image/png")
    assert store.resolve(meta["filename"]) is not None
    assert store.resolve("../secrets.txt") is None
    assert store.resolve("..\\secrets.txt") is None
    assert store.resolve("") is None
