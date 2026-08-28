"""Extract rental record fields from receipt/booking images via local Ollama vision models."""
import base64
import os
import time

import pandas as pd
import requests

from car_rental_recommender_core import (
    extract_dataset_examples_for_llm,
    normalize_provider_name,
    parse_llm_json_response,
)

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_VISION_MODEL = "llama3.2-vision"
VISION_MODEL_HINTS = (
    "vision",
    "llava",
    "moondream",
    "bakllava",
    "minicpm-v",
    "gemma3",
    "qwen2.5vl",
    "qwen2-vl",
    "llama3.2-vision",
)

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

FIELD_KEYS = (
    "date",
    "provider",
    "car_model",
    "distance",
    "duration",
    "start_time",
    "end_time",
    "fuel_pumped",
    "total_cost",
    "is_weekend",
    "consumption",
    "fuel_usage",
    "fuel_cost",
    "mileage_cost",
    "duration_cost",
    "kwh_used",
    "electricity_cost",
    "region",
    "collection_location",
)


def _empty_fields():
    return {key: None for key in FIELD_KEYS}


def check_ollama_available(timeout=2):
    """Return True if Ollama responds on localhost."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False


def list_vision_models(timeout=5):
    """
    List locally installed Ollama models likely to support vision.
    Falls back to DEFAULT_VISION_MODEL if none detected.
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=timeout)
        response.raise_for_status()
        models = response.json().get("models", [])
        names = [m.get("name", "") for m in models if m.get("name")]
        vision_models = [
            name
            for name in names
            if any(hint in name.lower() for hint in VISION_MODEL_HINTS)
        ]
        if vision_models:
            return vision_models
        return names[:5] if names else [DEFAULT_VISION_MODEL]
    except requests.RequestException:
        return [DEFAULT_VISION_MODEL]


def encode_image_base64(image_path):
    """Read image file and return base64 string for Ollama multimodal API."""
    if not image_path or not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported image type '{ext}'. Use: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}"
        )

    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _build_vision_prompt(df=None):
    """Build extraction prompt aligned with CSV schema and text LLM parser."""
    dataset_examples = (
        extract_dataset_examples_for_llm(df)
        if df is not None
        else {"car_models": [], "providers": [], "example_rows": []}
    )

    dataset_ref = ""
    if dataset_examples["car_models"]:
        dataset_ref += f"Car models format: {', '.join(dataset_examples['car_models'][:10])}\n"
    if dataset_examples["providers"]:
        dataset_ref += f"Providers format: {', '.join(dataset_examples['providers'])}\n"

    example_json = """{
  "date": "2025-12-31",
  "provider": "Getgo",
  "car_model": "Honda Shuttle",
  "distance": 42.5,
  "duration": 3.0,
  "start_time": "09:00",
  "end_time": "12:00",
  "fuel_pumped": null,
  "total_cost": 45.20,
  "is_weekend": false,
  "consumption": null,
  "fuel_usage": null,
  "fuel_cost": null,
  "mileage_cost": null,
  "duration_cost": 27.00,
  "kwh_used": null,
  "electricity_cost": null,
  "region": "Singapore",
  "collection_location": "Tampines Hub",
  "confidence": 0.85,
  "reasoning": "Extracted from booking screenshot"
}"""

    return f"""You are reading a car rental receipt, booking confirmation, or invoice image.
Extract rental record fields matching this dataset schema.

{dataset_ref}
Rules:
- Separate car model and provider when both appear together.
- Provider names must match dataset format (case-sensitive).
- Use null for missing values.
- Date format: YYYY-MM-DD.
- Times as HH:MM when visible.
- Region: Singapore or Malaysia when inferable.
- collection_location: pickup/collection point if shown.

Return ONLY valid JSON with this structure:
{example_json}

JSON ONLY. NO markdown. NO text before or after."""


def call_ollama_vision_chat(image_path, prompt, model_name=DEFAULT_VISION_MODEL, timeout=120):
    """Call Ollama /api/chat with a base64-encoded image."""
    image_b64 = encode_image_base64(image_path)
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
        },
    }

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    message = response.json().get("message", {})
    return message.get("content", "")


def _post_process_fields(extracted_data, df=None):
    """Normalize provider, parse dates, and compute derived fuel fields."""
    if extracted_data.get("provider"):
        extracted_data["provider"] = normalize_provider_name(
            extracted_data["provider"], df
        )

    if extracted_data.get("date"):
        try:
            extracted_data["date"] = pd.to_datetime(extracted_data["date"])
        except Exception:
            extracted_data["date"] = None

    if (
        extracted_data.get("distance")
        and extracted_data.get("consumption")
        and not extracted_data.get("fuel_usage")
    ):
        try:
            extracted_data["fuel_usage"] = (
                extracted_data["distance"] / extracted_data["consumption"]
            )
        except Exception:
            pass

    if (
        extracted_data.get("distance")
        and extracted_data.get("fuel_usage")
        and not extracted_data.get("consumption")
    ):
        try:
            extracted_data["consumption"] = (
                extracted_data["distance"] / extracted_data["fuel_usage"]
            )
        except Exception:
            pass

    if "confidence" not in extracted_data:
        extracted_data["confidence"] = 0.7

    return extracted_data


def extract_record_from_image(image_path, df=None, model_name=DEFAULT_VISION_MODEL):
    """
    Extract rental record fields from an image using a local Ollama vision model.

    Returns:
        {
            "ok": bool,
            "fields": dict,
            "confidence": float,
            "reasoning": str,
            "error": str | None,
        }
    """
    result = {
        "ok": False,
        "fields": _empty_fields(),
        "confidence": 0.0,
        "reasoning": "",
        "error": None,
    }

    if not image_path:
        result["error"] = "No image path provided."
        return result

    if not check_ollama_available():
        result["error"] = (
            "Cannot connect to Ollama. Start Ollama and install a vision model "
            "(e.g. ollama pull llama3.2-vision)."
        )
        return result

    try:
        prompt = _build_vision_prompt(df)
        response_text = None
        for attempt in range(2):
            try:
                response_text = call_ollama_vision_chat(
                    image_path, prompt, model_name=model_name
                )
                break
            except requests.exceptions.Timeout:
                if attempt == 0:
                    time.sleep(2)
                    continue
                raise
            except requests.exceptions.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status == 404:
                    result["error"] = (
                        f"Vision model '{model_name}' not found. "
                        f"Install it with: ollama pull {model_name}"
                    )
                    return result
                raise

        if not response_text:
            result["error"] = "Empty response from Ollama vision model."
            return result

        parsed = parse_llm_json_response(response_text)
        if parsed is None:
            result["error"] = "Failed to parse JSON from vision model response."
            result["reasoning"] = response_text[:500]
            return result

        parsed = _post_process_fields(parsed, df)

        fields = _empty_fields()
        for key in FIELD_KEYS:
            if key in parsed and parsed[key] is not None:
                fields[key] = parsed[key]

        confidence = float(parsed.get("confidence", 0.7) or 0.7)
        reasoning = str(parsed.get("reasoning", "") or "")

        result["ok"] = True
        result["fields"] = fields
        result["confidence"] = confidence
        result["reasoning"] = reasoning
        return result

    except FileNotFoundError as exc:
        result["error"] = str(exc)
    except ValueError as exc:
        result["error"] = str(exc)
    except requests.exceptions.ConnectionError:
        result["error"] = (
            "Cannot connect to Ollama. Start Ollama and install a vision model."
        )
    except requests.exceptions.Timeout:
        result["error"] = "Ollama vision request timed out. Try a smaller model."
    except Exception as exc:
        result["error"] = f"Vision extraction failed: {exc}"

    return result


def summarize_extraction(result):
    """Human-readable summary of found and missing fields."""
    if not result.get("ok"):
        return result.get("error") or "Extraction failed."

    fields = result.get("fields") or {}
    found = []
    missing = []
    labels = {
        "date": "Date",
        "provider": "Provider",
        "car_model": "Car model",
        "distance": "Distance (km)",
        "duration": "Rental hours",
        "start_time": "Start time",
        "end_time": "End time",
        "total_cost": "Total cost",
        "region": "Region",
        "collection_location": "Collection location",
        "fuel_pumped": "Fuel pumped",
        "fuel_usage": "Fuel usage",
        "consumption": "Consumption",
    }

    for key, label in labels.items():
        value = fields.get(key)
        if value is not None and value != "":
            found.append(f"{label}: {value}")
        else:
            missing.append(label)

    lines = [
        f"Confidence: {result.get('confidence', 0):.0%}",
        f"Found ({len(found)}): " + (", ".join(found) if found else "none"),
    ]
    if missing:
        lines.append(f"Missing: {', '.join(missing)}")
    if result.get("reasoning"):
        lines.append(f"Note: {result['reasoning']}")
    return "\n".join(lines)
