"""
Tests for system endpoints: /, /api/v1/status, /api/v1/test, /api/v1/log.
"""

from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "Visanté AI Engine"
    assert "version" in data
    assert data["docs"] == "/docs"
    assert data["status"] == "/api/v1/status"
    assert data["test"] == "/api/v1/test"
    assert data["log"] == "/api/v1/log"


def test_status(client: TestClient) -> None:
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "Visanté AI Engine"
    assert data["status"] == "online"
    assert "version" in data


def test_test_endpoint(client: TestClient) -> None:
    r = client.get("/api/v1/test")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "Visanté AI Engine"
    assert "version" in data


def test_log_default(client: TestClient) -> None:
    r = client.get("/api/v1/log")
    assert r.status_code == 200
    data = r.json()
    assert "count" in data
    assert "logs" in data
    assert isinstance(data["logs"], list)
    assert data["count"] == len(data["logs"])


def test_log_with_limit(client: TestClient) -> None:
    r = client.get("/api/v1/log?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] <= 5
    assert len(data["logs"]) <= 5
