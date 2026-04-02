"""Configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "PARSEMUX_", "env_file": ".env", "env_file_encoding": "utf-8"}

    host: str = "0.0.0.0"
    port: int = 8000
    ui_port: int = 7860
    upload_dir: str = "/tmp/parsemux_uploads"
    max_file_size_mb: int = 100
    default_parser: str | None = None  # override auto-routing
    # Server-side VLM key for local dev (provider auto-detected from key prefix)
    vlm_api_key: str | None = None
    # CORS: comma-separated allowed origins. "*" for dev, restrict in production.
    cors_origins: str = "*"


settings = Settings()
