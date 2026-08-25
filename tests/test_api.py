import pytest
from fastapi.testclient import TestClient

from vinyl_api.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def listing_payload():
    return {
        "release_id": 123,
        "listings": [{"listing_id": "api-test", "price": 12.5, "currency": "USD"}],
    }


def test_health_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_writes_require_configured_api_key(client, monkeypatch):
    monkeypatch.setenv("VINYL_API_KEY", "test-secret")

    response = client.post("/listings/bulk", json=listing_payload())

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_writes_accept_configured_api_key(client, monkeypatch):
    monkeypatch.setenv("VINYL_API_KEY", "test-secret")

    response = client.post(
        "/listings/bulk",
        json=listing_payload(),
        headers={"Authorization": "Bearer test-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"saved": 1}


def test_keyless_local_mode_allows_writes(client, monkeypatch):
    monkeypatch.delenv("VINYL_API_KEY", raising=False)

    response = client.post("/listings/bulk", json=listing_payload())

    assert response.status_code == 200
    assert response.json() == {"saved": 1}
