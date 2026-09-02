"""Shared fixtures for Gemini Image Studio tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """FastAPI TestClient with isolated outputs dir and no API key by default."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    import backend.config as config
    import backend.routes.generate as generate_routes
    from backend.services.storage import StorageService

    out = tmp_path / "outputs"
    out.mkdir()
    monkeypatch.setattr(config, "OUTPUTS_DIR", out)
    generate_routes.storage = StorageService(root=out)

    from backend.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def png_bytes() -> bytes:
    """Minimal valid 1x1 PNG."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
        b"\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
