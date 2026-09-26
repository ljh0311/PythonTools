"""Smoke tests for CarRS local web API."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

csv_path = os.path.join(ROOT, "22 - Sheet1.csv")
pytestmark = pytest.mark.skipif(not os.path.exists(csv_path), reason="Local CSV not present")


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    from web.app import app, reload_data

    reload_data()
    return TestClient(app)


def test_health_ok(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["rows"] >= 10


def test_recommend(client):
    res = client.post(
        "/api/recommend",
        json={
            "distance_km": 40,
            "duration_hours": 1,
            "is_weekend": False,
            "region": "Singapore",
            "use_ml": True,
            "top_n": 4,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["recommendations"]
    assert body["recommendations"][0]["total_cost"] > 0


def test_index_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"CarRS" in res.content
