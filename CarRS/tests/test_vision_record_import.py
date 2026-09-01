"""Tests for vision-based rental record import."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.vision_record_import import (
    check_ollama_available,
    encode_image_base64,
    extract_record_from_image,
    list_vision_models,
    summarize_extraction,
    _build_vision_prompt,
    _post_process_fields,
)


class TestVisionRecordImport(unittest.TestCase):
    def test_encode_image_base64_png(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"\x89PNG\r\n\x1a\nfake")
            path = tmp.name
        try:
            encoded = encode_image_base64(path)
            self.assertTrue(len(encoded) > 0)
        finally:
            os.unlink(path)

    def test_encode_image_rejects_unknown_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"not an image")
            path = tmp.name
        try:
            with self.assertRaises(ValueError):
                encode_image_base64(path)
        finally:
            os.unlink(path)

    def test_build_vision_prompt_includes_schema(self):
        prompt = _build_vision_prompt()
        self.assertIn("collection_location", prompt)
        self.assertIn("car_model", prompt)
        self.assertIn("JSON ONLY", prompt)

    def test_post_process_normalizes_provider_and_date(self):
        import pandas as pd

        raw = {
            "provider": "getgo",
            "date": "2025-01-15",
            "distance": 50,
            "consumption": 10,
            "confidence": 0.9,
        }
        processed = _post_process_fields(raw.copy())
        self.assertEqual(processed["provider"], "Getgo")
        self.assertTrue(hasattr(processed["date"], "year"))
        self.assertEqual(processed["fuel_usage"], 5.0)

    @patch("components.vision_record_import.check_ollama_available", return_value=False)
    def test_extract_when_ollama_unavailable(self, _mock_check):
        result = extract_record_from_image("/tmp/fake.png")
        self.assertFalse(result["ok"])
        self.assertIn("Ollama", result["error"])

    @patch("components.vision_record_import.check_ollama_available", return_value=True)
    @patch("components.vision_record_import.call_ollama_vision_chat")
    def test_extract_parses_mock_response(self, mock_chat, _mock_check):
        mock_response = json.dumps(
            {
                "date": "2025-06-01",
                "provider": "Getgo",
                "car_model": "Honda Fit",
                "distance": 32.0,
                "duration": 2.5,
                "total_cost": 38.5,
                "region": "Singapore",
                "collection_location": "Bedok",
                "confidence": 0.88,
                "reasoning": "From receipt totals",
            }
        )
        mock_chat.return_value = mock_response

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"\x89PNG\r\n\x1a\nfake")
            path = tmp.name

        try:
            result = extract_record_from_image(path, model_name="llama3.2-vision")
            self.assertTrue(result["ok"])
            self.assertEqual(result["fields"]["car_model"], "Honda Fit")
            self.assertEqual(result["fields"]["provider"], "Getgo")
            self.assertEqual(result["fields"]["distance"], 32.0)
            self.assertEqual(result["confidence"], 0.88)
            self.assertIn("receipt", result["reasoning"].lower())
        finally:
            os.unlink(path)

    @patch("components.vision_record_import.requests.get")
    def test_list_vision_models_filters_names(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "models": [
                    {"name": "llama3.1:3b"},
                    {"name": "llama3.2-vision"},
                    {"name": "moondream"},
                ]
            },
        )
        models = list_vision_models()
        self.assertIn("llama3.2-vision", models)
        self.assertIn("moondream", models)
        self.assertNotIn("llama3.1:3b", models)

    def test_summarize_extraction_ok_and_error(self):
        ok_summary = summarize_extraction(
            {
                "ok": True,
                "fields": {"car_model": "Mazda 3", "distance": 40},
                "confidence": 0.8,
                "reasoning": "ok",
            }
        )
        self.assertIn("Mazda 3", ok_summary)
        err_summary = summarize_extraction({"ok": False, "error": "timeout"})
        self.assertIn("timeout", err_summary)

    @patch("components.vision_record_import.requests.get")
    def test_check_ollama_available(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        self.assertTrue(check_ollama_available())
        mock_get.side_effect = requests.exceptions.ConnectionError("down")
        self.assertFalse(check_ollama_available())


if __name__ == "__main__":
    unittest.main()
