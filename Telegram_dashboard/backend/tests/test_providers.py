"""Provider config and Ollama model-tag matching.

Run:
  cd Telegram_dashboard
  python -m unittest backend.tests.test_providers -v
"""

from __future__ import annotations

import unittest

from backend.config import GEMINI_MODEL
from backend.services.providers.ollama import OllamaProvider


class TestGeminiModelDefault(unittest.TestCase):
    def test_default_is_not_retired_gemini_2_0_flash(self) -> None:
        self.assertNotEqual(GEMINI_MODEL, "gemini-2.0-flash")
        self.assertTrue(GEMINI_MODEL.startswith("gemini-"))


class TestOllamaModelInstalled(unittest.TestCase):
    def test_matches_base_tag_and_latest_alias(self) -> None:
        provider = OllamaProvider(model="llama3.2")
        names = ["llama3.2:latest", "qwen2.5:latest"]
        self.assertTrue(provider._model_installed(names))

    def test_matches_tagged_qwen(self) -> None:
        provider = OllamaProvider(model="qwen2.5:3b")
        self.assertTrue(provider._model_installed(["qwen2.5:3b"]))
        self.assertFalse(provider._model_installed(["llama3.2:latest"]))


if __name__ == "__main__":
    unittest.main()
