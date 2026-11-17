import pytest

from app import __version__

ENVIRONMENTS = ["local", "test", "staging", "production"]


@pytest.fixture
def status_properties(openapi):
    """StatusResponse alanları; $ref'ler (ör. Environment) çözülmüş hâlde."""
    schemas = openapi["components"]["schemas"]

    def resolve(prop):
        if "$ref" in prop:
            return schemas[prop["$ref"].rsplit("/", 1)[-1]]
        return prop

    return {
        name: resolve(prop)
        for name, prop in schemas["StatusResponse"]["properties"].items()
    }


# --- Yanıt sözleşmesi ---


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body_is_exact_contract(client):
    response = client.get("/health")
    assert response.json() == {
        "status": "ok",
        "service": "fuelpay-tsm",
        "version": __version__,
        "environment": "test",
    }


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_health_environment_comes_from_settings(make_client, environment):
    client = make_client(ENVIRONMENT=environment)
    assert client.get("/health").json()["environment"] == environment


def test_health_version_matches_app_version(client):
    response = client.get("/health")
    assert response.json()["version"] == client.app.version


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


def test_openapi_status_response_fields(status_properties):
    assert set(status_properties) == {"status", "service", "version", "environment"}
    assert all(p["type"] == "string" for p in status_properties.values())


def test_openapi_status_response_all_fields_required(openapi):
    schema = openapi["components"]["schemas"]["StatusResponse"]
    assert set(schema["required"]) == {"status", "service", "version", "environment"}


def test_openapi_status_response_literal_fields(status_properties):
    properties = status_properties
    assert properties["status"]["const"] == "ok"
    assert properties["service"]["const"] == "fuelpay-tsm"
    assert properties["environment"]["enum"] == ENVIRONMENTS
    assert "const" not in properties["version"]
    assert "enum" not in properties["version"]
