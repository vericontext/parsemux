"""Configuration via environment variables."""

from __future__ import annotations

from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "PARSEMUX_", "env_file": ".env", "env_file_encoding": "utf-8"}

    # Mode: "local" = full OSS, "demo" = cloud demo with restrictions
    mode: Literal["local", "demo"] = "local"

    host: str = "0.0.0.0"
    port: int = 8000
    ui_port: int = 7860
    upload_dir: str = "/tmp/parsemux_uploads"
    default_parser: str | None = None

    # Server-side VLM key (local dev only, provider auto-detected from key prefix)
    vlm_api_key: str | None = None

    # CORS: comma-separated allowed origins
    cors_origins: str = "*"

    # Demo mode limits
    max_file_size_mb: int = 100        # local: 100MB, demo: 10MB
    demo_max_file_size_mb: int = 10
    demo_rate_limit_per_min: int = 10  # requests per minute per IP
    demo_max_pages: int = 50           # max pages to parse in demo
    demo_disable_mcp: bool = True      # disable /mcp in demo mode

    @property
    def effective_max_file_size(self) -> int:
        """Max file size in bytes based on mode."""
        mb = self.demo_max_file_size_mb if self.mode == "demo" else self.max_file_size_mb
        return mb * 1024 * 1024

    @property
    def is_demo(self) -> bool:
        return self.mode == "demo"


settings = Settings()
