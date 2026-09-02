from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CAREERFLOW_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = Field(default=8743, ge=1, le=65535)
    local_token: SecretStr = SecretStr("")
    data_dir: Path = Path("data")
    log_level: str = "info"
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    model: str = "gpt-5.6-terra"
    reasoning_effort: Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"] = "medium"
    telemetry_enabled: bool = True
    local_diagnostics_enabled: bool = True
    diagnostics_max_bytes: int = Field(default=5_000_000, ge=100_000, le=50_000_000)

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.data_dir / 'careerflow.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
