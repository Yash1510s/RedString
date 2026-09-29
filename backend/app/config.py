"""Application configuration via environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RedString"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    frontend_origin: str = "http://localhost:3000"

    database_url: str = "sqlite+aiosqlite:///./osint.db"

    cache_ttl_seconds: int = 86400
    github_token: str | None = None
    certspotter_api_key: str | None = None

    llm_provider: str = Field(default="none", description="none, gemini, openai, anthropic, ollama")
    llm_api_key: str | None = None
    llm_model: str | None = None
    ollama_base_url: str = "http://localhost:11434"


settings = Settings()
