"""Application configuration.

Settings are loaded from environment variables (and a local ``.env`` file
during development). Use ``get_settings()`` everywhere instead of
instantiating ``Settings`` directly so values are read once and cached.
"""

from enum import Enum
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "CyberArena"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    secret_key: str = "change-me"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite:///./cyberarena.db"
    database_echo: bool = False

    # Sessions
    session_cookie_name: str = "cyberarena_session"
    session_max_age: int = 60 * 60 * 8  # 8 hours

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/cyberarena.log"

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return upper


class DevelopmentSettings(Settings):
    debug: bool = True
    database_echo: bool = False
    log_level: str = "DEBUG"


class ProductionSettings(Settings):
    debug: bool = False
    log_level: str = "INFO"

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_set(cls, value: str) -> str:
        if value == "change-me" or len(value) < 32:
            raise ValueError(
                "SECRET_KEY must be set to a strong value (>= 32 chars) in production"
            )
        return value


class TestingSettings(Settings):
    debug: bool = True
    database_url: str = "sqlite:///:memory:"
    log_level: str = "WARNING"


@lru_cache
def get_settings() -> Settings:
    """Return the settings instance for the current environment."""
    base = Settings()
    per_env: dict[Environment, type[Settings]] = {
        Environment.DEVELOPMENT: DevelopmentSettings,
        Environment.PRODUCTION: ProductionSettings,
        Environment.TESTING: TestingSettings,
    }
    return per_env[base.environment]()
