"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        meeting_baas_api_key: API key for Meeting BaaS service
        ngrok_auth_token: Authentication token for ngrok (optional)
        host: Server host address
        port: Server port number
        bot_name: Display name for the bot in meetings
        bot_image_url: Avatar image URL for the bot
        entry_message: Message the bot sends when joining
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Meeting BaaS API
    meeting_baas_api_key: str

    # Ngrok (optional for local testing)
    ngrok_auth_token: str | None = None

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Bot configuration
    bot_name: str = "Transcription Bot"
    bot_image_url: str = "https://example.com/bot-avatar.jpg"
    entry_message: str = "Hi, I'm here to transcribe this meeting."


# Global settings instance
settings = Settings()
