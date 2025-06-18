from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LINE Configuration
    line_channel_access_token: str
    line_channel_secret: str

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.7

    # MCP Server Configuration
    mcp_server_url: str
    mcp_api_key: str
    context7_mcp_url: str = "http://localhost:3001"
    postgres_mcp_url: str = "http://localhost:3002"
    postgres_connection_string: str = "postgresql://localhost:5432/mcp_test"

    # Application Configuration
    app_env: str = "development"
    app_debug: bool = False
    app_port: int = 8000
    app_host: str = "0.0.0.0"

    # Security
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 15

    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Observability
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "line-mcp-webhook"
    prometheus_port: int = 9090

    # Cost Control
    monthly_token_budget_usd: float = 150.0
    token_price_per_1k_input: float = 0.01
    token_price_per_1k_output: float = 0.03

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    @property
    def redis_url(self) -> str:
        password = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()