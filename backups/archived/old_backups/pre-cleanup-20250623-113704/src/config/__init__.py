"""
配置管理模組
"""

from .mcp_config import (
    MCPClientConfig,
    MCPConfigManager,
    MCPServerConfig,
    get_mcp_config,
    get_server_config,
    validate_server_config,
)


# 重新導出原配置模組的函數以保持向後相容
def get_settings():
    """保持向後相容的設定函數"""
    import sys
    from pathlib import Path

    # 動態導入避免循環依賴
    config_path = Path(__file__).parent.parent / "config.py"
    spec = importlib.util.spec_from_file_location("main_config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    return config_module.get_settings()


import importlib.util

__all__ = [
    "get_settings",
    "MCPServerConfig",
    "MCPClientConfig",
    "MCPConfigManager",
    "get_mcp_config",
    "get_server_config",
    "validate_server_config",
]
