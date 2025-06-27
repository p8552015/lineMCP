"""
配置管理模組

提供運行時環境和 MCP 服務器的配置管理：
- 運行時環境配置
- MCP 服務器配置
- 動態配置載入

遵循 OCP (開閉原則)，支援擴展新的配置類型。
"""

from .runtime_config import RuntimeConfig, get_runtime_config
from .server_config import ServerConfigManager, load_server_configs

__all__ = [
    "RuntimeConfig",
    "get_runtime_config",
    "ServerConfigManager",
    "load_server_configs",
]
