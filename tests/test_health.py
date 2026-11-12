import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def openapi(client):
    return client.get("/openapi.json").json()


# --- Yanıt sözleşmesi ---


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body_is_exact_contract(client):
    response = client.get("/health")
    assert response.json() == {
        "status": "ok",
        "service": "fuelpay-tsm",
        "version": "0.1.0",
    }


def test_health_version_matches_app_version(client):
    # health.py'deki sabit sürüm ile FastAPI app sürümü ayrışmasın.
    response = client.get("/health")
    assert response.json()["version"] == app.version


def test_health_returns_json_content_type(client):
    response = client.get("/health")
    assert response.headers["content-type"].startswith("application/json")


def test_unknown_path_returns_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


# --- HTTP metodları ---


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_health_rejects_non_get_methods(client, method):
    response = client.request(method.upper(), "/health")
    assert response.status_code == 405
    assert response.headers["allow"] == "GET"


# --- OpenAPI sözleşmesi (client'ların gördüğü şema) ---


def test_openapi_documents_health_under_health_tag(openapi):
    operation = openapi["paths"]["/health"]["get"]
    assert operation["tags"] == ["health"]


def test_openapi_health_response_uses_status_response_schema(openapi):
    operation = openapi["paths"]["/health"]["get"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/StatusResponse"}


def test_openapi_status_response_fields(openapi):
    properties = openapi["components"]["schemas"]["StatusResponse"]["properties"]
    assert set(properties) == {"status", "service", "version"}
    assert all(p["type"] == "string" for p in properties.values())


def test_openapi_status_response_all_fields_required(openapi):
    schema = openapi["components"]["schemas"]["StatusResponse"]
    assert set(schema["required"]) == {"status", "service", "version"}


def test_openapi_status_response_literal_fields_are_const(openapi):
    properties = openapi["components"]["schemas"]["StatusResponse"]["properties"]
    assert properties["status"]["const"] == "ok"
    assert properties["service"]["const"] == "fuelpay-tsm"
    assert "const" not in properties["version"]
