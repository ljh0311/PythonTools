"""API routes for health, generate, and outputs."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.config import get_api_key, get_default_model
from backend.services.gemini_image import (
    GeminiImageService,
    MissingApiKeyError,
    NoImageInResponseError,
    ref_from_upload,
)
from backend.services.storage import StorageService

router = APIRouter(prefix="/api")
storage = StorageService()


@router.get("/health")
def health() -> dict:
    """Liveness check — works without an API key."""
    return {
        "status": "ok",
        "has_api_key": bool(get_api_key()),
        "default_model": get_default_model(),
    }


@router.post("/generate")
async def generate(
    prompt: str = Form(...),
    model: str | None = Form(None),
    aspect: str | None = Form(None),
    files: list[UploadFile] | None = File(None),
) -> dict:
    """
    Generate or edit an image via Gemini Nano Banana.

    Multipart fields:
      - prompt (required): text prompt
      - model (optional): model id
      - aspect (optional): aspect ratio string e.g. "1:1", "16:9"
      - files (optional, repeatable): reference images
    """
    prompt = (prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    refs = []
    for upload in files or []:
        data = await upload.read()
        if not data:
            continue
        refs.append(
            ref_from_upload(
                data,
                filename=upload.filename,
                content_type=upload.content_type,
            )
        )

    service = GeminiImageService()
    try:
        result = service.generate(
            prompt=prompt,
            refs=refs,
            model=model or None,
            aspect=aspect or None,
        )
    except MissingApiKeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NoImageInResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface Gemini/SDK errors clearly
        raise HTTPException(
            status_code=502, detail=f"Gemini generate failed: {exc}"
        ) from exc

    saved = storage.save(
        image_bytes=result.image_bytes,
        mime_type=result.mime_type,
        prompt=prompt,
        model=result.model,
    )
    return {
        "ok": True,
        "image": saved,
        "model": result.model,
        "model_text": result.model_text,
        "estimated_cost_usd": result.estimated_cost_usd,
        "reference_count": len(refs),
    }


@router.get("/outputs")
def list_outputs(limit: int = 50) -> dict:
    """List recent saved images (newest first)."""
    limit = max(1, min(limit, 200))
    items = storage.list_recent(limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/outputs/{filename}")
def get_output(filename: str) -> FileResponse:
    """Serve a saved image file."""
    path = storage.resolve(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Output not found")
    media = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")
    return FileResponse(path, media_type=media, filename=path.name)
