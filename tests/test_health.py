import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body_is_exact_contract(client):
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_health_returns_json_content_type(client):
    response = client.get("/health")
    assert response.headers["content-type"].startswith("application/json")


def test_health_rejects_post(client):
    response = client.post("/health")
    assert response.status_code == 405
