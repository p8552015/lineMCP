#!/usr/bin/env python3
"""
MCP 配置管理
統一管理所有 MCP 相關配置，取代分散的配置文件
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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


class MCPConfigManager:
    """MCP 配置管理器"""

    def __init__(self, settings=None):
        """初始化配置管理器"""
        self.settings = settings
        self._servers: dict[str, MCPServerConfig] = {}
        self._client_config = MCPClientConfig()

        # 只在有 settings 時初始化預設配置
        if settings:
            self._init_default_servers()

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
        """獲取配置摘要"""
        return {
            "project_root": self.settings.project_root,
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
        }


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
