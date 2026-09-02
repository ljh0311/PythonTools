"""Gemini Nano Banana image generation wrapper."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Sequence

from backend.config import UNIT_COST_USD, get_api_key, get_default_model


@dataclass
class ReferenceImage:
    data: bytes
    mime_type: str


@dataclass
class GenerateResult:
    image_bytes: bytes
    mime_type: str
    model: str
    model_text: str | None
    estimated_cost_usd: float | None


class MissingApiKeyError(Exception):
    """Raised when GEMINI_API_KEY / GOOGLE_API_KEY is not set."""


class NoImageInResponseError(Exception):
    """Raised when the model response contains no image part."""


def _mime_from_name(filename: str | None, fallback: str = "image/png") -> str:
    if not filename:
        return fallback
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in {"jpg", "jpeg"}:
        return "image/jpeg"
    if ext == "webp":
        return "image/webp"
    if ext == "gif":
        return "image/gif"
    if ext == "png":
        return "image/png"
    return fallback


class GeminiImageService:
    """Plug-and-play Gemini image generate/edit service."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else get_api_key()

    @property
    def has_api_key(self) -> bool:
        return bool(self._api_key)

    def generate(
        self,
        prompt: str,
        refs: Sequence[ReferenceImage] | None = None,
        model: str | None = None,
        aspect: str | None = None,
    ) -> GenerateResult:
        if not self._api_key:
            raise MissingApiKeyError(
                "Missing GEMINI_API_KEY or GOOGLE_API_KEY. "
                "Set one in .env or the environment."
            )

        from google import genai
        from google.genai import types

        model_id = model or get_default_model()
        refs = list(refs or [])

        contents: list = []
        for ref in refs:
            contents.append(
                types.Part.from_bytes(data=ref.data, mime_type=ref.mime_type)
            )
        contents.append(prompt)

        # Aspect is accepted for API stability; Flash image models may ignore it.
        config_kwargs: dict = {"response_modalities": ["TEXT", "IMAGE"]}
        if aspect:
            try:
                config_kwargs["image_config"] = types.ImageConfig(
                    aspect_ratio=aspect
                )
            except (TypeError, AttributeError, ValueError):
                pass

        client = genai.Client(api_key=self._api_key)
        config = types.GenerateContentConfig(**config_kwargs)
        response = client.models.generate_content(
            model=model_id,
            contents=contents if len(contents) > 1 else prompt,
            config=config,
        )

        image_bytes, mime_type, model_text = self._extract_image(response)
        unit = UNIT_COST_USD.get(model_id)
        return GenerateResult(
            image_bytes=image_bytes,
            mime_type=mime_type,
            model=model_id,
            model_text=model_text,
            estimated_cost_usd=unit,
        )

    @staticmethod
    def _extract_image(response) -> tuple[bytes, str, str | None]:
        texts: list[str] = []
        for part in response.parts or []:
            if getattr(part, "text", None):
                texts.append(part.text)
                continue
            inline = getattr(part, "inline_data", None)
            if inline is None:
                continue
            data = getattr(inline, "data", None)
            if data is None:
                continue
            mime = (getattr(inline, "mime_type", None) or "image/png").lower()
            if isinstance(data, str):
                data = base64.b64decode(data)
            model_text = " ".join(texts)[:500] if texts else None
            return data, mime, model_text

        raise NoImageInResponseError("No image part in Gemini response.")


def ref_from_upload(
    data: bytes,
    filename: str | None = None,
    content_type: str | None = None,
) -> ReferenceImage:
    mime = content_type or _mime_from_name(filename)
    if mime == "application/octet-stream":
        mime = _mime_from_name(filename)
    return ReferenceImage(data=data, mime_type=mime)
