"""Generate route tests — Gemini client mocked (no paid API)."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.services.gemini_image import GenerateResult, MissingApiKeyError


def test_generate_missing_key_returns_400(client):
    res = client.post(
        "/api/generate",
        data={"prompt": "a blue circle"},
    )
    assert res.status_code == 400
    assert "API_KEY" in res.json()["detail"].upper() or "key" in res.json()["detail"].lower()


def test_generate_empty_prompt_returns_400(client):
    res = client.post("/api/generate", data={"prompt": "   "})
    assert res.status_code == 400


def test_generate_with_mocked_gemini(client, monkeypatch, png_bytes: bytes, tmp_path):
    def fake_generate(self, prompt, refs=None, model=None, aspect=None):
        return GenerateResult(
            image_bytes=png_bytes,
            mime_type="image/png",
            model=model or "gemini-3.1-flash-image",
            model_text="ok",
            estimated_cost_usd=0.085,
        )

    monkeypatch.setattr(
        "backend.routes.generate.GeminiImageService.generate",
        fake_generate,
    )
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")

    res = client.post(
        "/api/generate",
        data={"prompt": "a green triangle", "aspect": "1:1"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["model"] == "gemini-3.1-flash-image"
    assert body["image"]["filename"].endswith(".png")
    assert body["image"]["prompt"] == "a green triangle"
    assert body["estimated_cost_usd"] == 0.085

    listed = client.get("/api/outputs")
    assert listed.status_code == 200
    assert listed.json()["count"] >= 1

    filename = body["image"]["filename"]
    file_res = client.get(f"/api/outputs/{filename}")
    assert file_res.status_code == 200
    assert file_res.content == png_bytes


def test_service_missing_key_raises():
    from backend.services.gemini_image import GeminiImageService

    svc = GeminiImageService(api_key="")
    try:
        svc.generate("hello")
        raise AssertionError("expected MissingApiKeyError")
    except MissingApiKeyError:
        pass


def test_extract_image_from_response(png_bytes: bytes):
    from backend.services.gemini_image import GeminiImageService

    part = MagicMock()
    part.text = None
    part.inline_data = MagicMock(data=png_bytes, mime_type="image/png")
    response = MagicMock(parts=[part])

    data, mime, text = GeminiImageService._extract_image(response)
    assert data == png_bytes
    assert mime == "image/png"
    assert text is None
