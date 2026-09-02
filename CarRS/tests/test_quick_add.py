"""Tests for quick-add shortcut parsing."""

from pathlib import Path

from components.quick_add import load_shortcuts, parse_quick_add, save_shortcuts


def test_parse_example_shortcut():
    result = parse_quick_add(
        "1 hour rental(40km), mazda 3",
        known_models=["Mazda 3", "Honda Vezel"],
    )
    assert result["ok"] is True
    assert result["hours"] == 1.0
    assert result["distance"] == 40.0
    assert result["car_model"] == "Mazda 3"


def test_parse_with_location_and_rating():
    result = parse_quick_add(
        "2h 60km getgo, honda vezel from Tampines rating 3",
        known_models=["Honda Vezel"],
    )
    assert result["ok"] is True
    assert result["hours"] == 2.0
    assert result["distance"] == 60.0
    assert result["provider"] == "Getgo"
    assert result["car_model"] == "Honda Vezel"
    assert result["collection_location"] == "Tampines"
    assert result["distance_rating"] == 3


def test_parse_missing_fields():
    result = parse_quick_add("mazda 3")
    assert result["ok"] is False
    assert "hours" in result["error"]


def test_save_and_load_shortcuts(tmp_path: Path):
    path = tmp_path / "shortcuts.json"
    save_shortcuts(["1 hour rental(40km), mazda 3", "dup", "dup"], path=path)
    loaded = load_shortcuts(path)
    assert loaded[0] == "1 hour rental(40km), mazda 3"
    assert loaded.count("dup") == 1
