"""Health endpoint smoke tests."""

from __future__ import annotations


def test_health_ok_without_api_key(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["has_api_key"] is False
    assert "default_model" in body


def test_health_reports_key_when_set(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["has_api_key"] is True
