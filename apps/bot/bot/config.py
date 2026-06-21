"""
Configuration loader for the KalshiBot worker.

Reads environment variables from Railway (production) or .env (local).
All exchange and sportsbook secrets stay here — never in the dashboard.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Worker configuration from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str
    supabase_service_role_key: str

    kalshi_api_key_id: str = ""
    kalshi_private_key: str = ""
    kalshi_base_url: str = "https://demo-api.kalshi.co/trade-api/v2"
    kalshi_ws_url: str = "wss://demo-api.kalshi.co/trade-api/ws/v2"

    odds_api_key: str = ""
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"

    bot_env: str = "paper"
    worker_id: str = "bot-1"
    deployed_version: str = "local"

    fetcher_tick_seconds: float = 1.0
    strategy_tick_seconds: float = 2.0
    executor_tick_seconds: float = 2.0


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
