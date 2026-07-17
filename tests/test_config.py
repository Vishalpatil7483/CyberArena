"""Configuration tests."""

import pytest
from pydantic import ValidationError

from app.core.config import Environment, ProductionSettings, Settings
from app.core.config import TestingSettings as EnvTestingSettings


def test_defaults() -> None:
    settings = Settings(_env_file=None, environment=Environment.DEVELOPMENT)
    assert settings.app_name == "CyberArena"
    assert settings.environment == Environment.DEVELOPMENT


def test_production_rejects_default_secret_key() -> None:
    with pytest.raises(ValidationError):
        ProductionSettings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            secret_key="change-me",
        )


def test_production_rejects_short_secret_key() -> None:
    with pytest.raises(ValidationError):
        ProductionSettings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            secret_key="short",
        )


def test_production_accepts_strong_secret_key() -> None:
    settings = ProductionSettings(
        _env_file=None,
        environment=Environment.PRODUCTION,
        secret_key="x" * 64,
    )
    assert settings.is_production


def test_testing_uses_in_memory_db() -> None:
    settings = EnvTestingSettings(_env_file=None)
    assert settings.database_url == "sqlite:///:memory:"


def test_invalid_log_level_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_level="VERBOSE")
