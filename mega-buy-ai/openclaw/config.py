"""OpenClaw configuration — loads from existing .env files."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


# Load .env from python/ directory (has all keys)
_env_path = Path(__file__).parent.parent.parent / "python" / ".env"


class Settings(BaseSettings):
    # Claude API (backup)
    anthropic_api_key: str = ""
    openclaw_model: str = "claude-sonnet-4-20250514"
    openclaw_max_tokens: int = 4096

    # OpenAI API (primary — much cheaper)
    openai_api_key: str = ""
    openai_triage_model: str = "gpt-4o-mini"       # $0.002/alert for triage
    openai_deep_model: str = "gpt-4o"              # $0.02/alert for deep analysis
    openai_budget_usd: float = 25.0                # Initial budget to track

    # Telegram
    telegram_token: str = ""
    telegram_chat_id: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # Pipeline
    poll_interval_sec: int = 5
    analysis_timeout_sec: int = 30

    # Circuit Breaker
    max_daily_losses: int = 999    # Disabled during learning phase — re-enable later (3/7)
    max_weekly_losses: int = 999   # Disabled during learning phase — re-enable later (3/7)
    max_concurrent_positions: int = 5

    # APIs
    simulation_api_url: str = "http://localhost:8001"
    backtest_db_path: str = str(Path(__file__).parent.parent / "backtest" / "data" / "backtest.db")
    binance_api_url: str = "https://api.binance.com"

    class Config:
        env_file = str(_env_path)
        env_file_encoding = "utf-8"
        extra = "ignore"


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
