#!/usr/bin/env python3
"""
MCP 配置管理
統一管理所有 MCP 相關配置，取代分散的配置文件
"""

import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class MCPServerConfig:
    """MCP 服務器配置"""

    name: str
    protocol: str = "stdio"  # stdio, http, websocket
    command: str | None = None
    args: list[str] = field(default_factory=list)
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    timeout: int = 10
    retry_attempts: int = 3
    retry_delay: float = 1.0

    # HTTP 特定配置
    url: str | None = None
    api_key: str | None = None

    # WebSocket 特定配置
    ws_url: str | None = None


@dataclass
class MCPClientConfig:
    """MCP 客戶端配置"""

    connection_pool_size: int = 5
    connection_timeout: int = 10
    request_timeout: int = 30
    max_retries: int = 3
    fallback_enabled: bool = True
    validate_responses: bool = True
    sanitize_errors: bool = True


@dataclass
class NLToSQLConfig:
    """NL-to-SQL 服務配置"""
    
    # 全域解析器設定
    default_confidence_threshold: float = 0.5
    max_parse_time: int = 5000  # 毫秒
    verbose_logging: bool = True
    
    # 並行解析設定
    parallel_parsing_enabled: bool = True
    max_concurrent_parsers: int = 3
    timeout_per_parser: int = 2000  # 毫秒
    
    # 解析器權重配置
    rule_based_parser_weight: float = 1.0
    ai_enhanced_parser_weight: float = 1.2
    
    # 回退策略設定
    fallback_strategy_enabled: bool = True
    fallback_threshold: float = 0.5
    
    # AI 服務配置
    ai_service_timeout: int = 3000  # 毫秒
    ai_service_max_retries: int = 2
    
    # 快取設定
    cache_enabled: bool = True
    cache_size: int = 1000
    cache_ttl: int = 300  # 秒
    
    # 統計設定
    statistics_enabled: bool = True
    
    # 熱重載設定
    hot_reload_enabled: bool = False


class MCPConfigManager:
    """MCP 配置管理器 - 統一配置管理"""

    def __init__(self, settings=None):
        """初始化配置管理器"""
        self.settings = settings
        self._servers: dict[str, MCPServerConfig] = {}
        self._client_config = MCPClientConfig()
        self._nl_to_sql_config = NLToSQLConfig()

        # 只在有 settings 時初始化預設配置
        if settings:
            self._init_default_servers()
            self._init_nl_to_sql_config()

    def _init_default_servers(self):
        """初始化預設服務器配置"""

        # SQLite STDIO 服務器 (生產級)
        sqlite_env = {
            "ASYNCIO_FORCE_SELECT_SELECTOR": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONUTF8": "1",
        }

        self._servers["sqlite"] = MCPServerConfig(
            name="sqlite",
            protocol="stdio",
            command="python3",
            args=[
                self.settings.mcp_sqlite_server_path,
                self.settings.mcp_sqlite_db_path,
            ],
            cwd=str(Path(self.settings.mcp_sqlite_server_path).parent),
            env=sqlite_env,
            timeout=self.settings.mcp_stdio_timeout,
            retry_attempts=self.settings.mcp_connection_retry_attempts,
            retry_delay=self.settings.mcp_connection_retry_delay,
        )

        # PostgreSQL HTTP 服務器 (可選)
        if hasattr(self.settings, "postgres_mcp_url"):
            self._servers["postgres"] = MCPServerConfig(
                name="postgres",
                protocol="http",
                url=self.settings.postgres_mcp_url,
                timeout=30,
                retry_attempts=3,
                retry_delay=1.0,
            )

        # Context7 HTTP 服務器 (可選)
        if hasattr(self.settings, "context7_mcp_url"):
            self._servers["context7"] = MCPServerConfig(
                name="context7",
                protocol="http",
                url=self.settings.context7_mcp_url,
                timeout=30,
                retry_attempts=3,
                retry_delay=1.0,
            )

    def _init_nl_to_sql_config(self):
        """初始化 NL-to-SQL 配置"""
        # 嘗試從環境變數覆蓋配置
        env_config = self._load_nl_to_sql_env_config()
        if env_config:
            self._apply_nl_to_sql_env_config(env_config)
        
        # 嘗試從 YAML 文件載入配置（向後兼容）
        yaml_config = self._load_nl_to_sql_yaml_config()
        if yaml_config:
            self._apply_nl_to_sql_yaml_config(yaml_config)

    def _load_nl_to_sql_env_config(self) -> Dict[str, Any]:
        """從環境變數載入 NL-to-SQL 配置"""
        env_config = {}
        
        # 環境變數前綴
        prefix = "NL_TO_SQL_"
        
        # 定義環境變數映射
        env_mappings = {
            f"{prefix}CONFIDENCE_THRESHOLD": ("default_confidence_threshold", float),
            f"{prefix}MAX_PARSE_TIME": ("max_parse_time", int),
            f"{prefix}VERBOSE_LOGGING": ("verbose_logging", lambda x: x.lower() in ('true', '1', 'yes')),
            f"{prefix}PARALLEL_PARSING": ("parallel_parsing_enabled", lambda x: x.lower() in ('true', '1', 'yes')),
            f"{prefix}MAX_CONCURRENT_PARSERS": ("max_concurrent_parsers", int),
            f"{prefix}TIMEOUT_PER_PARSER": ("timeout_per_parser", int),
            f"{prefix}RULE_PARSER_WEIGHT": ("rule_based_parser_weight", float),
            f"{prefix}AI_PARSER_WEIGHT": ("ai_enhanced_parser_weight", float),
            f"{prefix}FALLBACK_ENABLED": ("fallback_strategy_enabled", lambda x: x.lower() in ('true', '1', 'yes')),
            f"{prefix}FALLBACK_THRESHOLD": ("fallback_threshold", float),
            f"{prefix}AI_TIMEOUT": ("ai_service_timeout", int),
            f"{prefix}AI_MAX_RETRIES": ("ai_service_max_retries", int),
            f"{prefix}CACHE_ENABLED": ("cache_enabled", lambda x: x.lower() in ('true', '1', 'yes')),
            f"{prefix}CACHE_SIZE": ("cache_size", int),
            f"{prefix}CACHE_TTL": ("cache_ttl", int),
            f"{prefix}STATISTICS_ENABLED": ("statistics_enabled", lambda x: x.lower() in ('true', '1', 'yes')),
            f"{prefix}HOT_RELOAD": ("hot_reload_enabled", lambda x: x.lower() in ('true', '1', 'yes')),
        }
        
        for env_var, (config_key, converter) in env_mappings.items():
            if env_var in os.environ:
                try:
                    env_config[config_key] = converter(os.environ[env_var])
                except (ValueError, TypeError) as e:
                    # 靜默忽略轉換錯誤，保持預設值
                    pass
        
        return env_config

    def _load_nl_to_sql_yaml_config(self) -> Optional[Dict[str, Any]]:
        """從 YAML 文件載入 NL-to-SQL 配置（向後兼容）"""
        if not self.settings:
            return None
            
        try:
            # 構建配置文件路徑
            config_dir = Path(self.settings.project_root) / "apps" / "bot" / "src" / "services" / "nl_to_sql" / "config"
            parser_settings_file = config_dir / "parser_settings.yaml"
            
            if parser_settings_file.exists():
                with open(parser_settings_file, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f)
                    return self._extract_nl_to_sql_config_from_yaml(yaml_config)
        except Exception as e:
            # 靜默忽略 YAML 載入錯誤
            pass
        
        return None

    def _extract_nl_to_sql_config_from_yaml(self, yaml_config: Dict[str, Any]) -> Dict[str, Any]:
        """從 YAML 配置中提取 NL-to-SQL 設定"""
        extracted_config = {}
        
        # 提取全域設定
        global_settings = yaml_config.get("global_parser_settings", {})
        if "default_confidence_threshold" in global_settings:
            extracted_config["default_confidence_threshold"] = global_settings["default_confidence_threshold"]
        if "max_parse_time" in global_settings:
            extracted_config["max_parse_time"] = global_settings["max_parse_time"]
        if "verbose_logging" in global_settings:
            extracted_config["verbose_logging"] = global_settings["verbose_logging"]
        
        # 提取並行解析設定
        parallel_config = global_settings.get("parallel_parsing", {})
        if "enabled" in parallel_config:
            extracted_config["parallel_parsing_enabled"] = parallel_config["enabled"]
        if "max_concurrent_parsers" in parallel_config:
            extracted_config["max_concurrent_parsers"] = parallel_config["max_concurrent_parsers"]
        if "timeout_per_parser" in parallel_config:
            extracted_config["timeout_per_parser"] = parallel_config["timeout_per_parser"]
        
        # 提取策略設定
        strategy_settings = yaml_config.get("strategy_settings", {})
        parser_weights = strategy_settings.get("parser_weights", {})
        if "RuleBasedParser" in parser_weights:
            extracted_config["rule_based_parser_weight"] = parser_weights["RuleBasedParser"]
        if "AIEnhancedParser" in parser_weights:
            extracted_config["ai_enhanced_parser_weight"] = parser_weights["AIEnhancedParser"]
        
        # 提取回退策略設定
        fallback_strategy = strategy_settings.get("fallback_strategy", {})
        if "enabled" in fallback_strategy:
            extracted_config["fallback_strategy_enabled"] = fallback_strategy["enabled"]
        if "threshold" in fallback_strategy:
            extracted_config["fallback_threshold"] = fallback_strategy["threshold"]
        
        return extracted_config

    def _apply_nl_to_sql_env_config(self, env_config: Dict[str, Any]):
        """應用環境變數配置到 NL-to-SQL 設定"""
        for key, value in env_config.items():
            if hasattr(self._nl_to_sql_config, key):
                setattr(self._nl_to_sql_config, key, value)

    def _apply_nl_to_sql_yaml_config(self, yaml_config: Dict[str, Any]):
        """應用 YAML 配置到 NL-to-SQL 設定"""
        for key, value in yaml_config.items():
            if hasattr(self._nl_to_sql_config, key):
                setattr(self._nl_to_sql_config, key, value)

    def get_server_config(self, server_name: str) -> MCPServerConfig | None:
        """獲取服務器配置"""
        return self._servers.get(server_name)

    def add_server_config(self, config: MCPServerConfig):
        """添加服務器配置"""
        self._servers[config.name] = config

    def list_servers(self) -> list[str]:
        """列出所有服務器名稱"""
        return list(self._servers.keys())

    def get_client_config(self) -> MCPClientConfig:
        """獲取客戶端配置"""
        return self._client_config

    def update_client_config(self, **kwargs):
        """更新客戶端配置"""
        for key, value in kwargs.items():
            if hasattr(self._client_config, key):
                setattr(self._client_config, key, value)

    def get_nl_to_sql_config(self) -> NLToSQLConfig:
        """獲取 NL-to-SQL 配置"""
        return self._nl_to_sql_config

    def update_nl_to_sql_config(self, **kwargs):
        """更新 NL-to-SQL 配置"""
        for key, value in kwargs.items():
            if hasattr(self._nl_to_sql_config, key):
                setattr(self._nl_to_sql_config, key, value)

    def get_nl_to_sql_config_dict(self) -> Dict[str, Any]:
        """獲取 NL-to-SQL 配置的字典格式"""
        return {
            "default_confidence_threshold": self._nl_to_sql_config.default_confidence_threshold,
            "max_parse_time": self._nl_to_sql_config.max_parse_time,
            "verbose_logging": self._nl_to_sql_config.verbose_logging,
            "parallel_parsing_enabled": self._nl_to_sql_config.parallel_parsing_enabled,
            "max_concurrent_parsers": self._nl_to_sql_config.max_concurrent_parsers,
            "timeout_per_parser": self._nl_to_sql_config.timeout_per_parser,
            "rule_based_parser_weight": self._nl_to_sql_config.rule_based_parser_weight,
            "ai_enhanced_parser_weight": self._nl_to_sql_config.ai_enhanced_parser_weight,
            "fallback_strategy_enabled": self._nl_to_sql_config.fallback_strategy_enabled,
            "fallback_threshold": self._nl_to_sql_config.fallback_threshold,
            "ai_service_timeout": self._nl_to_sql_config.ai_service_timeout,
            "ai_service_max_retries": self._nl_to_sql_config.ai_service_max_retries,
            "cache_enabled": self._nl_to_sql_config.cache_enabled,
            "cache_size": self._nl_to_sql_config.cache_size,
            "cache_ttl": self._nl_to_sql_config.cache_ttl,
            "statistics_enabled": self._nl_to_sql_config.statistics_enabled,
            "hot_reload_enabled": self._nl_to_sql_config.hot_reload_enabled,
        }

    def validate_server_config(self, server_name: str) -> tuple[bool, str | None]:
        """驗證服務器配置"""
        config = self.get_server_config(server_name)
        if not config:
            return False, f"服務器 '{server_name}' 不存在"

        if config.protocol == "stdio":
            if not config.command:
                return False, f"STDIO 服務器 '{server_name}' 缺少 command"

            # 檢查命令文件是否存在
            if config.args and len(config.args) > 0:
                script_path = config.args[0]
                if not os.path.exists(script_path):
                    return False, f"服務器腳本不存在：{script_path}"

        elif config.protocol == "http":
            if not config.url:
                return False, f"HTTP 服務器 '{server_name}' 缺少 URL"

        elif config.protocol == "websocket":
            if not config.ws_url:
                return False, f"WebSocket 服務器 '{server_name}' 缺少 WebSocket URL"

        else:
            return False, f"不支援的協議：{config.protocol}"

        return True, None

    def get_config_summary(self) -> dict[str, Any]:
        """獲取統一配置摘要"""
        summary = {
            "servers": {
                name: {
                    "protocol": config.protocol,
                    "command": config.command if config.protocol == "stdio" else None,
                    "url": config.url if config.protocol == "http" else None,
                    "timeout": config.timeout,
                    "retry_attempts": config.retry_attempts,
                }
                for name, config in self._servers.items()
            },
            "client": {
                "connection_pool_size": self._client_config.connection_pool_size,
                "request_timeout": self._client_config.request_timeout,
                "max_retries": self._client_config.max_retries,
                "fallback_enabled": self._client_config.fallback_enabled,
            },
            "nl_to_sql": {
                "confidence_threshold": self._nl_to_sql_config.default_confidence_threshold,
                "max_parse_time": self._nl_to_sql_config.max_parse_time,
                "parallel_parsing": self._nl_to_sql_config.parallel_parsing_enabled,
                "max_concurrent_parsers": self._nl_to_sql_config.max_concurrent_parsers,
                "parser_weights": {
                    "rule_based": self._nl_to_sql_config.rule_based_parser_weight,
                    "ai_enhanced": self._nl_to_sql_config.ai_enhanced_parser_weight,
                },
                "fallback_enabled": self._nl_to_sql_config.fallback_strategy_enabled,
                "fallback_threshold": self._nl_to_sql_config.fallback_threshold,
                "cache_enabled": self._nl_to_sql_config.cache_enabled,
                "cache_size": self._nl_to_sql_config.cache_size,
                "statistics_enabled": self._nl_to_sql_config.statistics_enabled,
            },
        }
        
        # 只有在有 settings 時才添加 project_root
        if self.settings and hasattr(self.settings, 'project_root'):
            summary["project_root"] = self.settings.project_root
            
        return summary


# 單例模式
_mcp_config_manager = None


def get_mcp_config() -> MCPConfigManager:
    """獲取 MCP 配置管理器實例"""
    global _mcp_config_manager
    if _mcp_config_manager is None:
        # 延遲導入避免循環導入
        try:
            import os
            from pathlib import Path

            from pydantic_settings import BaseSettings, SettingsConfigDict

            # 直接在這裡定義基本設定
            project_root = str(Path(__file__).parent.parent.parent.parent.parent)
            sqlite_server_path = os.path.join(
                project_root, "apps/servers/src/sqlite/server_fixed.py"
            )
            sqlite_db_path = os.path.join(
                project_root, "apps/servers/src/sqlite/test.db"
            )

            # 創建一個簡單的設定物件
            class SimpleSettings:
                def __init__(self):
                    self.project_root = project_root
                    self.mcp_sqlite_server_path = sqlite_server_path
                    self.mcp_sqlite_db_path = sqlite_db_path
                    self.mcp_stdio_timeout = 10
                    self.mcp_connection_retry_attempts = 3
                    self.mcp_connection_retry_delay = 1.0

            simple_settings = SimpleSettings()
            _mcp_config_manager = MCPConfigManager(simple_settings)
        except ImportError:
            # 回退到無設定的配置管理器
            _mcp_config_manager = MCPConfigManager()

    return _mcp_config_manager


# 便利函數
def get_server_config(server_name: str) -> MCPServerConfig | None:
    """獲取服務器配置的便利函數"""
    return get_mcp_config().get_server_config(server_name)


def validate_server_config(server_name: str) -> tuple[bool, str | None]:
    """驗證服務器配置的便利函數"""
    return get_mcp_config().validate_server_config(server_name)


def get_nl_to_sql_config() -> NLToSQLConfig:
    """獲取 NL-to-SQL 配置的便利函數"""
    return get_mcp_config().get_nl_to_sql_config()


def get_nl_to_sql_config_dict() -> Dict[str, Any]:
    """獲取 NL-to-SQL 配置字典的便利函數"""
    return get_mcp_config().get_nl_to_sql_config_dict()


def update_nl_to_sql_config(**kwargs):
    """更新 NL-to-SQL 配置的便利函數"""
    return get_mcp_config().update_nl_to_sql_config(**kwargs)
