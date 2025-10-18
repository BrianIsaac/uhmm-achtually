"""Configuration management for the fact-checker bot.

Loads settings from environment variables using Pydantic Settings.
Loads development configuration from dev_config.yaml.
"""

import yaml
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Daily.co
    daily_api_key: str
    daily_room_url: str
    daily_bot_token: str | None = None

    # APIs
    groq_api_key: str
    avalon_api_key: str | None = None
    exa_api_key: str | None = None

    # Configuration
    allowed_domains: str = "docs.python.org,kubernetes.io,owasp.org,nist.gov,postgresql.org"
    python_env: str = "development"
    log_level: str = "INFO"

    @property
    def allowed_domains_list(self) -> list[str]:
        """Parse allowed domains from comma-separated string.

        Returns:
            List of allowed domain strings
        """
        return [d.strip() for d in self.allowed_domains.split(",")]


class VADConfig(BaseModel):
    """VAD configuration settings."""
    disable: bool = False
    start_secs: float = 0.2
    stop_secs: float = 0.2
    min_volume: float = 0.6


class ContinuousAudioConfig(BaseModel):
    """Continuous audio processing configuration."""
    buffer_duration: float = 2.5
    overlap: bool = True


class GroqSTTConfig(BaseModel):
    """Groq STT configuration settings."""
    model: str = "whisper-large-v3-turbo"
    language: str = "en"


class AvalonSTTConfig(BaseModel):
    """Avalon STT configuration settings."""
    model: str = "avalon-1"
    language: str = "en"


class STTConfig(BaseModel):
    """STT configuration settings with provider selection."""
    provider: Literal["groq", "avalon"] = "groq"
    groq: GroqSTTConfig = GroqSTTConfig()
    avalon: AvalonSTTConfig = AvalonSTTConfig()


class LLMConfig(BaseModel):
    """LLM configuration settings for claim extraction and verification."""
    claim_extraction_model: str = "llama-3.3-70b-versatile"
    verification_model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.1


class LoggingConfig(BaseModel):
    """Logging configuration settings."""
    level: str = "INFO"
    log_transcriptions: bool = True


class DevConfig(BaseModel):
    """Development configuration loaded from dev_config.yaml."""
    vad: VADConfig = VADConfig()
    continuous_audio: ContinuousAudioConfig = ContinuousAudioConfig()
    stt: STTConfig = STTConfig()
    llm: LLMConfig = LLMConfig()
    logging: LoggingConfig = LoggingConfig()


def load_dev_config() -> DevConfig:
    """Load development configuration from YAML file.

    Returns:
        DevConfig instance with loaded settings

    Raises:
        FileNotFoundError: If dev_config.yaml does not exist
    """
    config_path = Path(__file__).parent.parent.parent / "dev_config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"dev_config.yaml not found at {config_path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    return DevConfig(**data)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Application settings instance
    """
    return Settings()


@lru_cache
def get_dev_config() -> DevConfig:
    """Get cached development configuration.

    Returns:
        DevConfig instance
    """
    return load_dev_config()
