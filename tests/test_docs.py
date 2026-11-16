import pytest

DOC_PATHS = ["/docs", "/redoc", "/openapi.json"]


@pytest.mark.parametrize("path", DOC_PATHS)
def test_docs_served_when_enabled(make_client, path):
    client = make_client(DOCS_ENABLED="true")
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", DOC_PATHS)
def test_docs_hidden_when_disabled(make_client, path):
    client = make_client(DOCS_ENABLED="false")
    assert client.get(path).status_code == 404


def test_health_still_works_when_docs_disabled(make_client):
    client = make_client(DOCS_ENABLED="false")
    assert client.get("/health").status_code == 200
