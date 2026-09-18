"""Application configuration. Loaded once via get_settings() (cached), never
instantiated at import time elsewhere — always injected via Depends."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    # --- VLM provider selection ---
    vlm_provider: Literal["openai", "bedrock"] = Field(default="openai")

    # --- OpenAI-compatible VLM connection (used when vlm_provider=openai) ---
    vlm_base_url: str = Field(default="http://192.168.1.123:1234/v1")
    vlm_api_key: str = Field(default="not-needed")
    vlm_model: str = Field(default="qwen3.8-27b-ridge")
    vlm_timeout_seconds: float = Field(default=60.0)
    vlm_max_retries: int = Field(default=3)
    vlm_retry_backoff_seconds: float = Field(default=1.5)
    vlm_max_tokens: int = Field(default=1500)
    # Optional attribution headers some OpenAI-compatible providers use
    # (e.g. OpenRouter's leaderboard attribution). Left blank/unset for
    # providers that don't use them.
    vlm_http_referer: str | None = Field(default=None)
    vlm_x_title: str | None = Field(default=None)

    # --- AWS Bedrock connection (used when vlm_provider=bedrock) ---
    # Credentials are NOT configured here — boto3 resolves them from the
    # standard AWS credential chain (env vars, ~/.aws/credentials, or an
    # attached IAM role). Only non-secret routing config lives in Settings.
    bedrock_model_id: str = Field(default="amazon.nova-lite-v1:0")
    bedrock_region: str = Field(default="us-east-1")
    bedrock_max_tokens: int = Field(default=1500)
    bedrock_max_retries: int = Field(default=3)
    bedrock_retry_backoff_seconds: float = Field(default=1.5)

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
    app_name: str = Field(default="site-installation-verification-service")


@lru_cache
def get_settings() -> Settings:
    return Settings()
