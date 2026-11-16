import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings

# --- Ortam değişkenlerinden okuma ---


def test_reads_prefixed_env_vars(monkeypatch):
    monkeypatch.setenv("FUELPAY_ENVIRONMENT", "staging")
    monkeypatch.setenv("FUELPAY_DOCS_ENABLED", "false")

    settings = Settings()

    assert settings.environment == "staging"
    assert settings.docs_enabled is False


def test_ignores_unprefixed_env_vars(monkeypatch):
    # Yanlış prefix: ENVIRONMENT tek başına okunmamalı.
    monkeypatch.delenv("FUELPAY_ENVIRONMENT")
    monkeypatch.setenv("ENVIRONMENT", "production")

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert {e["loc"] for e in exc_info.value.errors()} == {("environment",)}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("true", True), ("1", True), ("false", False), ("0", False)],
)
def test_docs_enabled_parses_bool(monkeypatch, raw, expected):
    monkeypatch.setenv("FUELPAY_DOCS_ENABLED", raw)
    assert Settings().docs_enabled is expected


# --- Geçersiz / eksik değerler ---


def test_rejects_unknown_environment(monkeypatch):
    monkeypatch.setenv("FUELPAY_ENVIRONMENT", "prod")
    with pytest.raises(ValidationError):
        Settings()


def test_rejects_non_bool_docs_enabled(monkeypatch):
    monkeypatch.setenv("FUELPAY_DOCS_ENABLED", "maybe")
    with pytest.raises(ValidationError):
        Settings()


@pytest.mark.parametrize("missing", ["FUELPAY_ENVIRONMENT", "FUELPAY_DOCS_ENABLED"])
def test_required_settings_have_no_default(monkeypatch, missing):
    monkeypatch.delenv(missing)
    with pytest.raises(ValidationError):
        Settings()


# --- .env dosyası ---


def test_reads_from_env_file(monkeypatch, tmp_path):
    monkeypatch.delenv("FUELPAY_ENVIRONMENT")
    monkeypatch.delenv("FUELPAY_DOCS_ENABLED")
    env_file = tmp_path / ".env"
    env_file.write_text(
        "FUELPAY_ENVIRONMENT=staging\nFUELPAY_DOCS_ENABLED=false\n", encoding="utf-8"
    )

    settings = Settings(_env_file=env_file)

    assert settings.environment == "staging"
    assert settings.docs_enabled is False


def test_env_var_overrides_env_file(monkeypatch, tmp_path):
    monkeypatch.setenv("FUELPAY_ENVIRONMENT", "production")
    env_file = tmp_path / ".env"
    env_file.write_text("FUELPAY_ENVIRONMENT=staging\n", encoding="utf-8")

    assert Settings(_env_file=env_file).environment == "production"


# --- get_settings cache'i ---


def test_get_settings_is_cached():
    assert get_settings() is get_settings()


def test_cache_clear_picks_up_new_env(monkeypatch):
    assert get_settings().environment == "test"

    monkeypatch.setenv("FUELPAY_ENVIRONMENT", "staging")
    assert get_settings().environment == "test"  # hâlâ cache'teki değer

    get_settings.cache_clear()
    assert get_settings().environment == "staging"
