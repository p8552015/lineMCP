from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # MCP STDIO Configuration (生產級)
    mcp_project_root: str = ""  # 自動推斷項目根目錄
    mcp_sqlite_server_script: str = "apps/servers/src/sqlite/server_fixed.py"
    mcp_sqlite_database_path: str = "apps/servers/src/sqlite/test.db"
    mcp_stdio_timeout: int = 10
    mcp_connection_retry_attempts: int = 3
    mcp_connection_retry_delay: float = 1.0

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
    redis_password: str | None = None

    # Observability
    otel_enabled: bool = True
    otel_exporter_otlp_endpoint: str = ""  # 空字串表示不使用 OTLP 導出器
    otel_service_name: str = "line-mcp-webhook"
    otel_auto_detect_endpoint: bool = True  # 自動檢測 OTLP 端點可用性
    otel_fallback_to_console: bool = True  # 在開發環境中降級為控制台導出
    prometheus_port: int = 9090

    # Cost Control
    monthly_token_budget_usd: float = 150.0
    token_price_per_1k_input: float = 0.01
    token_price_per_1k_output: float = 0.03

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # Google AI Configuration
    google_api_key: str | None = None
    google_model: str = "gemini-1.5-flash"

    # AI Model Preferences
    ai_model_provider: str = "google"  # google, openai, auto
    ai_enable_enhanced_nl: bool = True
    ai_fallback_to_rules: bool = True
    ai_rules_first: bool = True  # 規則優先
    
    # Architecture Configuration
    # 新架構已完成遷移，永久啟用
    use_new_architecture: bool = True
    service_factory_type: str = "enhanced"
    
    # NL-to-SQL SOLID 架構配置
    nl_to_sql_enabled: bool = True
    nl_to_sql_config_dir: str = "src/services/nl_to_sql/config"
    composite_parser_fallback_threshold: float = 0.5
    enable_query_statistics: bool = True
    ai_parser_timeout: int = 3000
    rule_parser_cache_size: int = 1000
    enable_config_hot_reload: bool = False

    @property
    def redis_url(self) -> str:
        password = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{password}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def project_root(self) -> str:
        """自動推斷項目根目錄"""
        if self.mcp_project_root:
            return self.mcp_project_root

        # 從當前文件位置推斷項目根目錄
        # /path/to/lineMCP/apps/bot/src/config.py -> /path/to/lineMCP
        current_file = Path(__file__).absolute()
        # config.py -> src -> bot -> apps -> lineMCP (根目錄)
        return str(current_file.parent.parent.parent.parent)

    @property
    def mcp_sqlite_server_path(self) -> str:
        """MCP SQLite 服務器腳本的完整路徑"""
        return str(Path(self.project_root) / self.mcp_sqlite_server_script)

    @property
    def mcp_sqlite_db_path(self) -> str:
        """MCP SQLite 資料庫的完整路徑"""
        return str(Path(self.project_root) / self.mcp_sqlite_database_path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
