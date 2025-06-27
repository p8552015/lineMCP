"""
Node.js MCP 支援架構模組

提供多運行時環境（Node.js、Python）的 MCP 服務器支援，
遵循 SOLID 原則的企業級設計。

主要功能：
- 多運行時環境管理
- 統一 MCP 服務器工廠
- 自動依賴檢查和安裝
- 進程生命週期管理
- 環境驗證和錯誤恢復

架構設計原則：
- SRP: 每個類別專注單一職責
- OCP: 對擴展開放，對修改封閉
- LSP: 所有實現類別可以互換使用
- ISP: 介面細粒度設計
- DIP: 依賴抽象而非具體實現
"""

from .implementations.nodejs_runtime_manager import NodeJSRuntimeManager

# 實現類別將在後續任務中添加
from .implementations.universal_mcp_factory import UniversalMCPServerFactory
from .interfaces.runtime_interfaces import IRuntimeManager, RuntimeInfo, RuntimeType
from .interfaces.server_interfaces import IMCPServerFactory, MCPServerConfig
from .interfaces.validation_interfaces import IEnvironmentValidator, ValidationResult

# from .implementations.python_runtime_manager import PythonRuntimeManager
# from .implementations.environment_validator import EnvironmentValidator

__version__ = "1.0.0"
__author__ = "Claude Code Assistant"

__all__ = [
    # 介面
    "IRuntimeManager",
    "IMCPServerFactory",
    "IEnvironmentValidator",
    # 資料類型
    "RuntimeType",
    "RuntimeInfo",
    "MCPServerConfig",
    "ValidationResult",
    # 實現類別（將在後續任務中添加）
    "UniversalMCPServerFactory",
    "NodeJSRuntimeManager",
    # "PythonRuntimeManager",
    # "EnvironmentValidator",
]
