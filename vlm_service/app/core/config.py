"""Application configuration. Loaded once via get_settings() (cached), never
instantiated at import time elsewhere — always injected via Depends."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # --- VLM connection ---
    vlm_base_url: str = Field(default="http://192.168.1.123:1234/v1")
    vlm_api_key: str = Field(default="not-needed")
    vlm_model: str = Field(default="qwen3.8-27b-ridge")
    vlm_timeout_seconds: float = Field(default=60.0)
    vlm_max_retries: int = Field(default=3)
    vlm_retry_backoff_seconds: float = Field(default=1.5)

    # --- Image processing ---
    image_max_dimension_px: int = Field(default=1536)
    image_min_size_bytes: int = Field(default=1024)
    image_allowed_extensions: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".webp")
    image_jpeg_quality: int = Field(default=85)

    # --- Review policy ---
    review_confidence_threshold: float = Field(default=0.6)

    # --- Persistence ---
    database_path: str = Field(default="./data/app.db")

    # --- Server ---
    log_level: str = Field(default="INFO")
    app_name: str = Field(default="site-cleanliness-service")


@lru_cache
def get_settings() -> Settings:
    return Settings()
