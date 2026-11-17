import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app

ENV_PREFIX = "FUELPAY_"


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Her testi geliştiricinin ortamından ve .env dosyasından yalıtır.

    - .env okumayı kapatır (Settings(_env_file=None)'ın sınıf düzeyindeki karşılığı).
    - Shell'den gelen tüm FUELPAY_* değişkenlerini siler.
    - Bilinen, sabit varsayılanları yazar.
    - get_settings cache'ini test öncesi ve sonrası temizler.
    monkeypatch hepsini test bitince geri alır.
    """
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for name in list(os.environ):
        if name.upper().startswith(ENV_PREFIX):
            monkeypatch.delenv(name)
    monkeypatch.setenv("FUELPAY_ENVIRONMENT", "test")
    monkeypatch.setenv("FUELPAY_DOCS_ENABLED", "true")

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def make_client(monkeypatch):
    """Verilen ortam değişkenleriyle yeni bir app kurar ve TestClient döner."""
    clients = []

    def _make(**env: str) -> TestClient:
        for key, value in env.items():
            monkeypatch.setenv(f"{ENV_PREFIX}{key}", value)
        get_settings.cache_clear()
        client = TestClient(create_app())
        client.__enter__()
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client):
    return make_client()


@pytest.fixture
def openapi(client):
    return client.get("/openapi.json").json()
