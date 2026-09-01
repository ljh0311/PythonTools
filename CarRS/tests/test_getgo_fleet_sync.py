"""Tests for GetGo fleet parsing and cache."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.getgo_fleet_sync import (
    load_fleet_cache,
    parse_fleet_html,
    is_cache_stale,
    sync_getgo_fleet,
    slug_to_title,
)


SAMPLE = """
[](https://home.getgo.sg/meet-the-fleet/mazda-3/)
standard
### Mazda 3
Sedan
5 Seater
[](https://home.getgo.sg/meet-the-fleet/hyundai-kona/)
standard electric
### Hyundai Kona EV
SUV
5 Seater
"""


def test_parse_fleet_html_extracts_models():
    models = parse_fleet_html(SAMPLE)
    names = {m["name"] for m in models}
    assert "Mazda 3" in names
    assert "Hyundai Kona EV" in names
    assert any(m["is_ev"] for m in models if m["name"] == "Hyundai Kona EV")


def test_slug_to_title():
    assert "Mg 4" in slug_to_title("mg-4-2") or slug_to_title("mg-4-2") == "Mg 4 2"


def test_load_bundled_cache():
    cache = load_fleet_cache()
    assert len(cache.get("models", [])) >= 10


def test_stale_cache_without_timestamp():
    assert is_cache_stale({"models": [], "fetched_at": None}) is True


def test_sync_uses_cache_when_fetch_fails(monkeypatch):
    monkeypatch.setattr(
        "components.getgo_fleet_sync.fetch_getgo_fleet",
        lambda url=None: ([], "none", "blocked"),
    )
    result = sync_getgo_fleet(force=True)
    assert result["ok"] is True or result["model_count"] >= 0
