"""Configuration safety tests.

The production fail-fast rules must never regress: no insecure default
secret and no sqlite database URL may be accepted in staging/production.
"""
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**kwargs) -> Settings:
    defaults = dict(
        environment="production",
        secret_key="a-very-long-strong-random-production-secret",
        database_url="postgresql://user:pass@host:5432/db",
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def test_production_accepts_strong_secret_and_postgres():
    settings = _settings()
    assert settings.is_production_like


def test_production_rejects_missing_secret():
    with pytest.raises(ValidationError):
        _settings(secret_key="")


def test_production_rejects_placeholder_secret():
    with pytest.raises(ValidationError):
        _settings(secret_key="your-secret-key-here-change-me")


def test_production_rejects_sqlite():
    with pytest.raises(ValidationError):
        _settings(database_url="sqlite:///./dev.db")


def test_production_requires_postgres_url():
    with pytest.raises(ValidationError):
        _settings(database_url="mysql://user:pass@host/db")


def test_test_environment_allows_sqlite_with_test_secret():
    settings = Settings(
        environment="test",
        secret_key="test-key",
        database_url="sqlite://",
    )
    assert settings.is_test
    assert settings.is_url_sqlite()


def test_invalid_environment_rejected():
    with pytest.raises(ValidationError):
        _settings(environment="banana")


def test_cors_origins_parsed():
    settings = Settings(
        environment="test",
        secret_key="k",
        database_url="sqlite://",
        cors_origins="http://a.test, http://b.test",
    )
    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]
