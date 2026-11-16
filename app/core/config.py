from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

type Environment = Literal["local", "test", "staging", "production"]


class Settings(BaseSettings):
    environment: Environment
    docs_enabled: bool

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="FUELPAY_",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
