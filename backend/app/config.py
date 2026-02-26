"""AURORA configuration — all settings from environment variables."""

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── Mode ───
    aurora_mode: str = "paper"
    aurora_log_level: str = "INFO"

    # ─── Alpaca ───
    alpaca_api_key: SecretStr
    alpaca_secret_key: SecretStr
    alpaca_base_url: str = "https://paper-api.alpaca.markets"
    alpaca_data_url: str = "https://data.alpaca.markets"

    # ─── Anthropic ───
    anthropic_api_key: SecretStr
    claude_model: str = "claude-sonnet-4-5-20250929"
    claude_max_reviews_per_day: int = 50

    # ─── Database ───
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "aurora"
    db_user: str = "aurora"
    db_password: SecretStr

    # ─── Redis ───
    redis_url: str = "redis://redis:6379/0"

    # ─── Security ───
    jwt_secret: SecretStr
    jwt_expiry_minutes: int = 30
    allowed_origins: str = "http://localhost:3000"

    # ─── Trading ───
    watchlist: str = "AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,JPM,V,UNH,SPY,QQQ"
    trading_start_hour: int = 9
    trading_end_hour: int = 16
    signal_interval_minutes: int = 5

    # ─── Risk Limits ───
    max_position_pct: float = 5.0
    max_daily_loss_pct: float = 3.0
    max_weekly_loss_pct: float = 5.0
    max_monthly_loss_pct: float = 8.0
    max_drawdown_pct: float = 12.0
    max_open_positions: int = 8
    max_trades_per_day: int = 10

    @property
    def database_url(self) -> str:
        password = self.db_password.get_secret_value()
        return f"postgresql+asyncpg://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        password = self.db_password.get_secret_value()
        return f"postgresql://{self.db_user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def watchlist_symbols(self) -> list[str]:
        return [s.strip().upper() for s in self.watchlist.split(",") if s.strip()]

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @field_validator("aurora_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("paper", "live"):
            raise ValueError("aurora_mode must be 'paper' or 'live'")
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def get_settings() -> Settings:
    return Settings()
