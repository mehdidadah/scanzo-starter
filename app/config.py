"""
Application configuration using Pydantic Settings.
All settings can be overridden via environment variables.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # === Application Info ===
    app_name: str = "Scanzo API"
    version: str = "1.0.0"
    debug: bool = False

    # === OpenAI Configuration ===
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_max_retries: int = 3
    openai_timeout: int = 30  # seconds

    # === API Configuration ===
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        # "application/pdf",  # Future support
    ]

    # === Rate Limiting ===
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60

    # === CORS Configuration ===
    cors_origins: List[str] = ["*"]

    # === Image Processing ===
    image_max_size: int = 1536  # Max dimension for resizing
    image_quality: int = 85     # JPEG quality (1-100)

    # === Logging ===
    log_level: str = "INFO"
    log_format: str = "json"  # "json" or "text"

    # === Security (Future) ===
    api_key_enabled: bool = False
    api_keys: List[str] = []

    # === Database (Future) ===
    # database_url: Optional[str] = None

    # === Redis Cache (Future) ===
    # redis_url: Optional[str] = None

    # === Monitoring (Optional) ===
    # sentry_dsn: Optional[str] = None
    # enable_metrics: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow extra fields from .env
        extra="ignore"
    )

    def validate_settings(self) -> None:
        """Validate critical settings on startup"""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required. "
                "Please set it in your .env file or environment variables."
            )

        if self.api_key_enabled and not self.api_keys:
            raise ValueError(
                "API_KEY_ENABLED is True but no API_KEYS provided. "
                "Please add API keys or disable API key authentication."
            )

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.debug

    @property
    def max_file_size_mb(self) -> float:
        """Get max file size in MB for display"""
        return self.max_file_size / (1024 * 1024)


# Create global settings instance
settings = Settings()

# Validate on import (fail fast)
try:
    settings.validate_settings()
except ValueError as e:
    import logging
    logging.error(f"Configuration error: {e}")
    # Allow running without OpenAI key for development/testing
    if "OPENAI_API_KEY" not in str(e):
        raise